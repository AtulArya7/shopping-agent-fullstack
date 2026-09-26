"""Streamlit UI for the authenticated AI shopping assistant."""

import os

import requests
import streamlit as st


BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
PAGES = ["Home", "Catalog", "Chat", "Orders", "Account"]
NAV_ICONS = {
    "Home": "🏠",
    "Catalog": "🗃️",
    "Chat": "💬",
    "Orders": "📦",
    "Account": "👤",
}

st.set_page_config(page_title="AI Shopping Assistant", page_icon="🛒", layout="wide")
st.markdown(
    """
    <style>
    .stApp {
        background: radial-gradient(circle at 8% 8%, rgba(99,102,241,.15), transparent 30%),
                    radial-gradient(circle at 92% 18%, rgba(16,185,129,.13), transparent 28%),
                    linear-gradient(145deg,#f8fafc 0%,#eef2ff 48%,#ecfdf5 100%);
    }
    .block-container {max-width:1180px;padding-top:3.8rem;padding-bottom:3rem}
    .cover-hero {padding:4.5rem 3rem;margin:.5rem 0 2rem;border-radius:30px;color:white;
        text-align:center;background:linear-gradient(125deg,#111827 0%,#312e81 52%,#065f46 100%);
        box-shadow:0 28px 70px rgba(30,41,59,.22)}
    .cover-hero h1 {margin:0;color:white;font-size:clamp(2.5rem,6vw,4.8rem);line-height:1.04;letter-spacing:-.055em}
    .cover-hero p {max-width:720px;margin:1.35rem auto 0;color:rgba(255,255,255,.78);font-size:1.15rem;line-height:1.7}
    .hero-badge {display:inline-block;padding:.45rem .9rem;margin-bottom:1.1rem;border:1px solid rgba(255,255,255,.28);
        border-radius:999px;background:rgba(255,255,255,.10);font-size:.82rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
    .launch-card {min-height:260px;padding:2rem;border:1px solid rgba(148,163,184,.24);border-radius:24px;
        background:rgba(255,255,255,.82);box-shadow:0 18px 45px rgba(51,65,85,.10);
        transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease}
    .launch-card:hover {transform:translateY(-7px);border-color:rgba(79,70,229,.38);
        box-shadow:0 28px 65px rgba(51,65,85,.18)}
    .launch-icon {display:grid;width:78px;height:78px;place-items:center;margin-bottom:1.35rem;border-radius:22px;
        font-size:2.5rem;background:linear-gradient(145deg,#e0e7ff,#d1fae5)}
    .launch-card h2 {margin:0 0 .75rem;color:#0f172a;font-size:1.65rem}
    .launch-card p {margin:0;color:#64748b;font-size:1rem;line-height:1.65}
    .nav-brand {font-weight:850;color:#0f172a;font-size:1.05rem;letter-spacing:-.02em}
    div.stButton>button {min-height:2.8rem;border:0;border-radius:14px;font-weight:700}
    .st-key-top_nav {position:sticky;top:3.25rem;z-index:999;padding:.65rem .85rem .35rem;
        margin-bottom:1rem;border:1px solid rgba(148,163,184,.22);border-radius:18px;
        background:rgba(248,250,252,.90);backdrop-filter:blur(18px);
        box-shadow:0 12px 35px rgba(15,23,42,.10)}
    [class*="st-key-nav_"] button {height:3.35rem;min-height:3.35rem;padding:0;overflow:visible;
        display:flex;align-items:center;justify-content:center;background:white;
        border:1px solid rgba(148,163,184,.22);box-shadow:0 5px 16px rgba(15,23,42,.07)}
    [class*="st-key-nav_"] button p {margin:0;overflow:visible;font-size:1.45rem;line-height:1.5!important}
    [class*="st-key-nav_"] button:hover {transform:translateY(-2px);border-color:rgba(79,70,229,.45);
        box-shadow:0 10px 24px rgba(79,70,229,.16)}
    .st-key-home_catalog_cta button,.st-key-home_chat_cta button {color:white;
        background:linear-gradient(90deg,#4f46e5,#0f766e);box-shadow:0 12px 28px rgba(79,70,229,.22);
        transition:transform .2s ease,box-shadow .2s ease,filter .2s ease}
    .st-key-home_catalog_cta button:hover,.st-key-home_chat_cta button:hover {color:white;
        transform:translateY(-3px);filter:brightness(1.08);box-shadow:0 18px 36px rgba(79,70,229,.30)}
    [data-testid="stMetric"] {background:rgba(255,255,255,.7);padding:1rem;border-radius:16px;border:1px solid rgba(148,163,184,.2)}
    </style>
    """,
    unsafe_allow_html=True,
)


def token() -> str | None:
    return st.session_state.get("auth_token")


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {token()}"} if token() else {}


def call_backend(method: str, path: str, authenticated: bool = False, **kwargs):
    headers = dict(kwargs.pop("headers", {}))
    if authenticated:
        headers.update(auth_headers())
    try:
        response = requests.request(
            method, f"{BACKEND_URL}{path}", headers=headers, timeout=90, **kwargs
        )
    except requests.exceptions.ConnectionError:
        return None, "Can't reach the backend. Start the app with .\\run.ps1."
    except requests.exceptions.Timeout:
        return None, "The backend took too long to respond."
    if response.ok:
        return response.json(), None
    try:
        return None, response.json().get("detail", response.text)
    except ValueError:
        return None, response.text


def navigate(page: str):
    st.session_state.page = page


def render_navigation():
    current = st.session_state.get("page", "Home")
    if current not in PAGES:
        current = "Home"
        st.session_state.page = current
    with st.container(key="top_nav"):
        brand, *nav_columns = st.columns([5, 1, 1, 1, 1], vertical_alignment="center")
        brand.markdown('<div class="nav-brand">AI SHOPPING ASSISTANT</div>', unsafe_allow_html=True)
        other_pages = [page for page in PAGES if page != current]
        for column, page in zip(nav_columns, other_pages):
            column.button(
                NAV_ICONS[page], key=f"nav_{page}", help=page,
                width="stretch", on_click=navigate, args=(page,),
            )


def require_login_view(message: str) -> bool:
    if token():
        return True
    st.warning(message)
    st.button("👤", help="Open Account", on_click=navigate, args=("Account",))
    return False


def fetch_products():
    data, error = call_backend("GET", "/api/products")
    return ([] if error else data["products"]), error


def render_home():
    st.markdown(
        """
        <section class="cover-hero">
          <div class="hero-badge">AI-powered store experience</div>
          <h1>Shop smarter.<br>Choose with confidence.</h1>
          <p>Explore the live product database or talk to an assistant that compares products,
          remembers preferences, understands images, and helps complete your order.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    catalog, chat = st.columns(2, gap="large")
    with catalog:
        st.markdown(
            '<div class="launch-card"><div class="launch-icon">🗃️</div><h2>Explore the database</h2>'
            '<p>Browse every product, rating, price, and organic option available to the agent.</p></div>',
            unsafe_allow_html=True,
        )
        st.button("Browse catalog →", key="home_catalog_cta", width="stretch", on_click=navigate, args=("Catalog",))
    with chat:
        st.markdown(
            '<div class="launch-card"><div class="launch-icon">💬</div><h2>Chat with the assistant</h2>'
            '<p>Search, compare, remember preferences, review history, and order conversationally.</p></div>',
            unsafe_allow_html=True,
        )
        st.button("Start shopping →", key="home_chat_cta", width="stretch", on_click=navigate, args=("Chat",))


def admin_headers(password: str) -> dict[str, str]:
    return {"X-Admin-Password": password}


def render_admin_controls():
    password = st.text_input("Admin password", type="password", key="admin_password")
    if not password:
        st.caption("Enter ADMIN_PASSWORD to manage catalog items.")
        return
    _, error = call_backend("GET", "/api/admin/verify", headers=admin_headers(password))
    if error:
        st.error(error)
        return
    st.success("Administrator authenticated")
    add_tab, edit_tab = st.tabs(["Add product", "Edit / delete"])
    with add_tab:
        with st.form("add_product", clear_on_submit=True):
            name = st.text_input("Product name")
            category = st.text_input("Category")
            price = st.number_input("Price", min_value=0.0, step=0.50)
            description = st.text_area("Description")
            organic = st.checkbox("Organic")
            add = st.form_submit_button("Add product")
        if add:
            data, error = call_backend(
                "POST", "/api/admin/products", headers=admin_headers(password),
                json={"name":name,"category":category,"price":price,"description":description,"is_organic":organic},
            )
            st.error(error) if error else st.success(f"Added {data['product']['name']}.")
    with edit_tab:
        products, error = fetch_products()
        if error or not products:
            st.error(error or "No products available.")
            return
        product_id = st.selectbox(
            "Product", [p["id"] for p in products],
            format_func=lambda value: next(p["name"] for p in products if p["id"] == value),
        )
        selected = next(p for p in products if p["id"] == product_id)
        with st.form("edit_product"):
            name = st.text_input("Name", value=selected["name"])
            category = st.text_input("Category", value=selected["category"])
            price = st.number_input("Price", min_value=0.0, value=float(selected["price"]), step=0.50)
            description = st.text_area("Description", value=selected["description"])
            organic = st.checkbox("Organic", value=selected["is_organic"])
            save = st.form_submit_button("Save changes")
        if save:
            _, error = call_backend(
                "PUT", f"/api/admin/products/{product_id}", headers=admin_headers(password),
                json={"name":name,"category":category,"price":price,"description":description,"is_organic":organic},
            )
            if error: st.error(error)
            else: st.success("Product updated."); st.rerun()
        confirm = st.checkbox("Confirm deletion")
        if st.button("Delete product", disabled=not confirm):
            _, error = call_backend("DELETE", f"/api/admin/products/{product_id}", headers=admin_headers(password))
            if error: st.error(error)
            else: st.success("Product deleted."); st.rerun()


def render_catalog():
    st.title("🗃️ Product Database")
    products, error = fetch_products()
    if error:
        st.error(error); return
    categories = sorted({p["category"] for p in products})
    a, b, c = st.columns(3)
    a.metric("Products", len(products)); b.metric("Categories", len(categories))
    c.metric("Organic", sum(p["is_organic"] for p in products))
    with st.expander("🔐 Admin rights — add, update, or delete items"):
        render_admin_controls()
    search_col, category_col, organic_col = st.columns([2,1,1])
    search = search_col.text_input("Search catalog")
    category = category_col.selectbox("Category", ["All", *categories])
    organic_only = organic_col.checkbox("Organic only")
    filtered = products
    if search:
        query = search.lower()
        filtered = [p for p in filtered if query in f"{p['name']} {p['category']} {p['description']}".lower()]
    if category != "All": filtered = [p for p in filtered if p["category"] == category]
    if organic_only: filtered = [p for p in filtered if p["is_organic"]]
    rows = [{"ID":p["id"],"Product":p["name"],"Category":p["category"],"Price":p["price"],
             "Rating":p["average_rating"],"Reviews":p["review_count"],
             "Organic":"Yes" if p["is_organic"] else "No","Description":p["description"]} for p in filtered]
    st.dataframe(rows, width="stretch", hide_index=True,
                 column_config={"Price":st.column_config.NumberColumn(format="$%.2f")})


def ensure_chat_session() -> bool:
    if "session_id" not in st.session_state:
        data, error = call_backend("POST", "/api/session/new", authenticated=True)
        if error: st.error(error); return False
        st.session_state.session_id = data["session_id"]
    st.session_state.setdefault("messages", [])
    return True


def render_chat():
    st.title("💬 Shopping Chat")
    if not require_login_view("Log in to chat, save preferences, and place user-specific orders."):
        return
    if not ensure_chat_session(): return
    with st.expander("📷 Shop by image"):
        upload = st.file_uploader("Product photo", type=["jpg","jpeg","png","webp"])
        if upload and st.button("Find similar products"):
            data, error = call_backend(
                "POST", "/api/chat/image", authenticated=True,
                data={"session_id":st.session_state.session_id},
                files={"file":(upload.name, upload.getvalue())},
            )
            st.session_state.messages.extend([
                {"role":"user","content":f"Uploaded {upload.name}"},
                {"role":"assistant","content":error or data["response"]},
            ]); st.rerun()
    if st.button("New chat"):
        st.session_state.pop("session_id", None); st.session_state.messages=[]; st.rerun()
    for message in st.session_state.messages:
        with st.chat_message(message["role"]): st.markdown(message["content"].replace("$",r"\$"))
    if prompt := st.chat_input("Find organic honey under $20"):
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                data, error = call_backend(
                    "POST", "/api/chat", authenticated=True,
                    json={"session_id":st.session_state.session_id,"message":prompt},
                )
            reply = error or data["response"]; st.markdown(reply.replace("$",r"\$"))
        st.session_state.messages.append({"role":"assistant","content":reply})


def render_orders():
    st.title("📦 My Orders")
    if not require_login_view("Log in to view your private order history."): return
    data, error = call_backend("GET", "/api/orders/me", authenticated=True)
    if error: st.error(error); return
    summary = data["summary"]["totals"]
    a, b = st.columns(2); a.metric("Orders", summary["order_count"]); b.metric("Total spent", f"${summary['total_spent']:.2f}")
    if not data["orders"]: st.info("You have not placed any orders yet."); return
    st.dataframe(data["orders"], width="stretch", hide_index=True,
                 column_config={"price":st.column_config.NumberColumn("Price",format="$%.2f")})


def save_auth(data: dict):
    st.session_state.auth_token = data["token"]
    st.session_state.user = data["user"]
    st.session_state.pop("session_id", None); st.session_state.messages=[]


def render_preferences():
    data, error = call_backend("GET", "/api/preferences/me", authenticated=True)
    if error: st.error(error); return
    preferences = data["preferences"]
    if preferences: st.dataframe(preferences, width="stretch", hide_index=True)
    else: st.info("No saved preferences yet. You can also say: Remember my budget is $20.")
    with st.form("preference_form", clear_on_submit=True):
        key = st.selectbox("Preference", ["max_price","minimum_rating","organic_only","preferred_category","dietary_requirement","preferred_brand"])
        value = st.text_input("Value")
        save = st.form_submit_button("Save preference")
    if save:
        _, error = call_backend("PUT", "/api/preferences/me", authenticated=True, json={"key":key,"value":value})
        if error: st.error(error)
        else: st.success("Preference saved."); st.rerun()
    if preferences:
        remove_key = st.selectbox("Remove preference", [p["preference_key"] for p in preferences])
        if st.button("Remove selected preference"):
            _, error = call_backend("DELETE", f"/api/preferences/me/{remove_key}", authenticated=True)
            if error: st.error(error)
            else: st.rerun()


def render_account():
    st.title("👤 Account")
    if token():
        user = st.session_state.get("user", {})
        st.subheader(f"Hello, {user.get('name','shopper')}")
        st.caption(user.get("email", "D"))
        st.subheader("Shopping preferences")
        render_preferences()
        if st.button("Log out"):
            call_backend("POST", "/api/auth/logout", authenticated=True)
            for key in ("auth_token","user","session_id","messages"):
                st.session_state.pop(key, None)
            navigate("Home"); st.rerun()
        return
    login_tab, register_tab = st.tabs(["Log in", "Create account"])
    with login_tab:
        with st.form("login"):
            email = st.text_input("Email", placeholder="name@email.com", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submit = st.form_submit_button("Log in")
        if submit:
            data, error = call_backend("POST", "/api/auth/login", json={"email":email,"password":password})
            if error: st.error(error)
            else: save_auth(data); navigate("Chat"); st.rerun()
    with register_tab:
        with st.form("register"):
            name = st.text_input("Name")
            email = st.text_input("Email", placeholder="name@email.com", key="register_email")
            password = st.text_input("Password (8+ characters)", type="password", key="register_password")
            submit = st.form_submit_button("Create account")
        if submit:
            data, error = call_backend("POST", "/api/auth/register", json={"name":name,"email":email,"password":password})
            if error: st.error(error)
            else: save_auth(data); navigate("Chat"); st.rerun()


st.session_state.setdefault("page", "Home")
render_navigation()
{
    "Home": render_home,
    "Catalog": render_catalog,
    "Chat": render_chat,
    "Orders": render_orders,
    "Account": render_account,
}[st.session_state.page]()
