"""
Streamlit frontend — talks to the FastAPI backend over plain HTTP,
the same way frontend/src/api.js does. It never imports shopping_agent.py
directly; it only calls /api/session/new, /api/chat, and /api/chat/image.

This is deliberately a thinner client than the original app.py: all the
actual logic (session history, rate-limit handling, calling the agent)
lives in backend/main.py. This file only renders UI and makes requests.
"""

import os

import requests
import streamlit as st

# st.secrets.get() raises StreamlitSecretNotFoundError (not just "no key")
# when there's no secrets.toml file at all — which is the normal case for
# local dev, so this can't be a plain .get() with a default. Streamlit
# Community Cloud always has a secrets store (even if empty), so the
# try/except only ever fires locally.
def get_backend_url() -> str:
    try:
        if "BACKEND_URL" in st.secrets:
            return st.secrets["BACKEND_URL"]
    except Exception:
        pass
    return os.getenv("BACKEND_URL", "http://localhost:8000")


BACKEND_URL = get_backend_url()

st.set_page_config(page_title="AI Shopping Assistant", page_icon="🛒", layout="wide")
st.title("🛒 AI Shopping Assistant")
st.caption("Tell me what you want — I'll search, rate, and order the best match for you.")


def call_backend(method: str, path: str, **kwargs):
    """
    Wraps requests.<method> and turns network failures / non-2xx responses
    into a plain string error, so the UI can always show *something* instead
    of crashing — e.g. Render's free tier can take 30-60s to wake up from
    sleep, and that first request will time out rather than 500.
    """
    try:
        resp = requests.request(method, f"{BACKEND_URL}{path}", timeout=90, **kwargs)
    except requests.exceptions.ConnectionError:
        return None, "Can't reach the backend. If it's on Render's free tier, it may be waking up from sleep — try again in ~30 seconds."
    except requests.exceptions.Timeout:
        return None, "The backend took too long to respond (possibly waking up from sleep). Try again shortly."

    if resp.ok:
        return resp.json(), None

    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    return None, detail


# ---------------------------------------------------------------------------
# Session — mint one session_id per browser tab, same idea as sessionStorage
# in the React version, just kept in st.session_state instead.
# ---------------------------------------------------------------------------
if "session_id" not in st.session_state:
    data, error = call_backend("POST", "/api/session/new")
    if error:
        st.error(error)
        st.stop()
    st.session_state.session_id = data["session_id"]

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------------------------------------------------------------------------
# Sidebar — shop by image
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Shop by Image")
    st.caption("Upload a photo of a product and I'll find similar items in our store.")

    uploaded_file = st.file_uploader("Upload product image", type=["jpg", "jpeg", "png", "webp"])
    if uploaded_file:
        st.image(uploaded_file, use_container_width=True)

    if uploaded_file and st.button("Find similar products", use_container_width=True):
        st.session_state.messages.append({"role": "user", "image_label": uploaded_file.name})

        with st.spinner("Analyzing image and searching…"):
            # Sends the actual file bytes over HTTP — the backend is on a
            # different machine now, so a local file path wouldn't mean
            # anything to it. This is the one real behavior change from
            # the original app.py, which passed the agent a path directly.
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            data, error = call_backend(
                "POST", "/api/chat/image",
                data={"session_id": st.session_state.session_id},
                files=files,
            )
        reply = error or data["response"]
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()

    if st.button("New session", use_container_width=True):
        for key in ("session_id", "messages"):
            st.session_state.pop(key, None)
        st.rerun()

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg.get("image_label"):
            st.markdown(f"Searching by image: **{msg['image_label']}**")
        else:
            st.markdown(msg["content"].replace("$", r"\$"))

# ---------------------------------------------------------------------------
# Text input
# ---------------------------------------------------------------------------
if prompt := st.chat_input("e.g. I want organic honey under $15 with 4+ rating"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            data, error = call_backend(
                "POST", "/api/chat",
                json={"session_id": st.session_state.session_id, "message": prompt},
            )
        reply = error or data["response"].replace("`", "")
        st.markdown(reply.replace("$", r"\$"))

    st.session_state.messages.append({"role": "assistant", "content": reply})
