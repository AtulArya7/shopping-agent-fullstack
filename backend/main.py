"""FastAPI API for authenticated shopping, catalog, memory, and administration."""

import hmac
import os
import re
import shutil
import sqlite3
import tempfile
import uuid

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field


BACKEND_DIR = os.path.dirname(__file__)
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from auth import authenticate_token, hash_password, issue_token, revoke_token, verify_password
from database import (
    create_product,
    create_user,
    delete_preference,
    delete_product,
    get_user_by_email,
    list_preferences,
    list_products,
    list_user_orders,
    migrate_database,
    order_summary,
    set_preference,
    update_product,
)
from guardrails import REJECTION_MESSAGE, check_shopping_message
from shopping_agent import agent
from user_context import current_user_id


migrate_database()
app = FastAPI(title="AI Shopping Assistant API", version="3.0.0")

SESSIONS: dict[str, dict] = {}
MAX_MESSAGES_PER_SESSION = 40
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class Registration(Credentials):
    name: str = Field(min_length=2, max_length=80)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    session_id: str


class ProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=80)
    price: float = Field(ge=0, le=1_000_000)
    description: str = Field(min_length=2, max_length=500)
    is_organic: bool = False


class PreferenceInput(BaseModel):
    key: str = Field(min_length=2, max_length=80)
    value: str = Field(min_length=1, max_length=200)


def require_admin(x_admin_password: str | None = Header(default=None)) -> None:
    configured_password = os.getenv("ADMIN_PASSWORD")
    if not configured_password:
        raise HTTPException(status_code=503, detail="Admin access is not configured.")
    if not x_admin_password or not hmac.compare_digest(x_admin_password, configured_password):
        raise HTTPException(status_code=401, detail="Invalid admin password.")


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Please log in.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Please log in.")
    return token


def current_user(token: str = Depends(bearer_token)) -> dict:
    user = authenticate_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Your session is invalid or expired.")
    return user


def session_history(session_id: str, user_id: int) -> list[dict]:
    session = SESSIONS.get(session_id)
    if session is None or session["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session["messages"]


def run_agent(history: list[dict], user_id: int) -> str:
    context_token = current_user_id.set(user_id)
    try:
        result = agent.invoke({"messages": history})
    except Exception as exc:
        message = str(exc)
        if "429" in message or "rate_limit" in message.lower():
            raise HTTPException(
                status_code=429,
                detail="The AI backend is rate-limited. Please try again in a minute.",
            ) from exc
        raise HTTPException(status_code=500, detail=f"Agent error: {message}") from exc
    finally:
        current_user_id.reset(context_token)

    reply = result["messages"][-1].content.replace("`", "")
    history.append({"role": "assistant", "content": reply})
    return reply


def auth_payload(user: dict, token: str) -> dict:
    safe_user = {key: user[key] for key in ("id", "name", "email", "created_at")}
    return {"token": token, "user": safe_user}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/products")
def products():
    return {"products": list_products()}


@app.post("/api/auth/register")
def register(payload: Registration):
    if not EMAIL_PATTERN.match(payload.email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    try:
        user = create_user(payload.name, payload.email, hash_password(payload.password))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc
    return auth_payload(user, issue_token(user["id"]))


@app.post("/api/auth/login")
def login(payload: Credentials):
    user_with_password = get_user_by_email(payload.email)
    if user_with_password is None or not verify_password(
        payload.password, user_with_password["password_hash"]
    ):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    user = {key: user_with_password[key] for key in ("id", "name", "email", "created_at")}
    return auth_payload(user, issue_token(user["id"]))


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return {"user": user}


@app.post("/api/auth/logout")
def logout(token: str = Depends(bearer_token), user: dict = Depends(current_user)):
    revoke_token(token)
    for session_id in [
        key for key, value in SESSIONS.items() if value["user_id"] == user["id"]
    ]:
        SESSIONS.pop(session_id, None)
    return {"logged_out": True}


@app.post("/api/session/new")
def new_session(user: dict = Depends(current_user)):
    session_id = str(uuid.uuid4())
    SESSIONS[session_id] = {"user_id": user["id"], "messages": []}
    return {"session_id": session_id}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: dict = Depends(current_user)):
    history = session_history(req.session_id, user["id"])
    if len(history) >= MAX_MESSAGES_PER_SESSION:
        raise HTTPException(status_code=429, detail="This session has reached its message limit.")
    guardrail = check_shopping_message(req.message, has_history=bool(history))
    if not guardrail.allowed:
        return ChatResponse(response=REJECTION_MESSAGE, session_id=req.session_id)
    history.append({"role": "user", "content": req.message})
    return ChatResponse(
        response=run_agent(history, user["id"]), session_id=req.session_id
    )


@app.post("/api/chat/image", response_model=ChatResponse)
async def chat_with_image(
    session_id: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(current_user),
):
    history = session_history(session_id, user["id"])
    if len(history) >= MAX_MESSAGES_PER_SESSION:
        raise HTTPException(status_code=429, detail="This session has reached its message limit.")
    suffix = os.path.splitext(file.filename or "")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        image_path = tmp.name
    prompt = (
        "I uploaded a product image. Please analyze it and find similar products "
        f"in the store. Image path: {image_path}"
    )
    history.append({"role": "user", "content": prompt})
    try:
        reply = run_agent(history, user["id"])
    finally:
        os.unlink(image_path)
    return ChatResponse(response=reply, session_id=session_id)


@app.get("/api/orders/me")
def my_orders(user: dict = Depends(current_user)):
    return {
        "orders": list_user_orders(user["id"]),
        "summary": order_summary(user["id"]),
    }


@app.get("/api/preferences/me")
def my_preferences(user: dict = Depends(current_user)):
    return {"preferences": list_preferences(user["id"])}


@app.put("/api/preferences/me")
def save_preference(payload: PreferenceInput, user: dict = Depends(current_user)):
    set_preference(user["id"], payload.key.strip().lower(), payload.value.strip())
    return {"preferences": list_preferences(user["id"])}


@app.delete("/api/preferences/me/{key}")
def remove_preference(key: str, user: dict = Depends(current_user)):
    if not delete_preference(user["id"], key):
        raise HTTPException(status_code=404, detail="Preference not found.")
    return {"deleted": True}


@app.get("/api/admin/verify", dependencies=[Depends(require_admin)])
def verify_admin():
    return {"authenticated": True}


@app.post("/api/admin/products", dependencies=[Depends(require_admin)])
def add_product(product: ProductInput):
    return {"product": create_product(product.model_dump())}


@app.put("/api/admin/products/{product_id}", dependencies=[Depends(require_admin)])
def edit_product(product_id: int, product: ProductInput):
    updated = update_product(product_id, product.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"product": updated}


@app.delete("/api/admin/products/{product_id}", dependencies=[Depends(require_admin)])
def remove_product(product_id: int):
    if not delete_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"deleted": True}
