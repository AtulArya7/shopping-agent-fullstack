# AI Shopping Assistant

A full-stack agentic shopping application with a Streamlit interface, FastAPI
backend, LangChain/Groq tool-calling agent, multimodal search, authenticated
users, durable preferences, private order history, guardrails, and LangSmith
evaluation scaffolding.

## Capabilities

- Product search, rating lookup, image understanding, and confirmed checkout
- Public live catalog backed by SQLite
- Protected catalog administration
- Account registration and login with scrypt password hashing
- Opaque, hashed, expiring bearer sessions
- Per-user chat sessions and order isolation
- Persistent explicit shopping preferences
- Agent tools for order-history summaries and preference memory
- Pre-agent off-topic guardrail
- LangSmith tracing and offline regression dataset

## Architecture

```text
Streamlit UI
    |
    v
FastAPI authentication + API
    |
    +--> deterministic guardrail
    |
    +--> LangChain agent
            +--> search_products
            +--> get_rating
            +--> describe_product_image
            +--> checkout
            +--> get_order_history
            +--> get_user_preferences
            +--> save_user_preference
    |
    v
SQLite: products, reviews, users, sessions, preferences, orders
```

The authenticated user ID is placed in trusted request context. It is never
supplied by the model, preventing one user from accessing another user's orders
or preferences through tool arguments.

## Run locally

Use Python 3.11. Run once from the project root:

```powershell
.\setup.ps1
```

Create `backend/.env`:

```dotenv
GROQ_API_KEY=your-groq-key
ADMIN_PASSWORD=choose-a-long-private-password

# Optional LangSmith observability
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=shopping-agent
```

Every future run:

```powershell
.\run.ps1
```

Open `http://127.0.0.1:8501`. The launcher starts FastAPI internally at
`http://127.0.0.1:8000` and stops it when Streamlit exits.

## UI navigation

Navigation uses icons only and omits the icon for the current page:

- 🏠 Home cover
- 🗃️ Catalog and protected administration
- 💬 Authenticated shopping chat
- 📦 Private order history
- 👤 Account, login, registration, and preferences

## Memory model

- **Short-term memory:** authenticated in-process chat history
- **Long-term user memory:** structured preferences in SQLite
- **Business memory:** user-scoped orders and aggregate history

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover password authentication, user-isolated orders and preferences,
chat-session ownership, admin protection, pre-agent guardrails, and contextual
icon navigation.

## LangSmith evaluations

The `evals/` directory contains a versioned dataset and deterministic response
and tool-trajectory evaluators.

```powershell
$env:LANGSMITH_TRACING = "true"
$env:LANGSMITH_API_KEY = "your-key"
$env:LANGSMITH_PROJECT = "shopping-agent"
$env:EVAL_USER_EMAIL = "an-existing-test-account@example.com"

.\.venv\Scripts\python.exe evals\upload_dataset.py
.\.venv\Scripts\python.exe evals\run_evaluation.py
```

## Render

Create one Docker Web Service from the repository root:

- Dockerfile: `./Dockerfile`
- Health check: `/_stcore/health`
- Environment variables: `GROQ_API_KEY`, `ADMIN_PASSWORD`
- Optional tracing: `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`

Render's free filesystem is ephemeral. For durable production accounts,
preferences, and orders, migrate SQLite to a managed PostgreSQL database.
