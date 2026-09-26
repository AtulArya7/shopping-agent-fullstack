# AI Shopping Assistant — FastAPI + React

The same LangChain/Groq shopping agent that used to run inside a single
Streamlit script, split into a real backend + frontend:

```
Browser (React)  --fetch-->  FastAPI (Python)  --.invoke()-->  LangChain agent
     :5173                       :8000                          -> Groq LLM
                                                                  -> SQLite (store.db)
```

- **`backend/`** — FastAPI app. Your original `shopping_agent.py`,
  `reviews_api.py`, and `setup_db.py` are untouched; `main.py` is the only
  new file, and it just exposes the agent over HTTP.
- **`frontend/`** — React (Vite) single-page app. A chat log, a text input,
  and a "shop by photo" uploader in the sidebar — the same two flows your
  Streamlit sidebar had.

## Why this instead of Streamlit

Streamlit re-runs your whole script top-to-bottom on every interaction and
mixes UI code with app logic in one file. Splitting it into a backend that
only speaks JSON over HTTP, and a frontend that only renders UI, is the
pattern almost every real product uses — and it means either side can be
replaced independently later (swap React for a mobile app, swap FastAPI for
a different agent framework) without touching the other.

## Project structure

```
shopping-agent-fullstack/
├── backend/
│   ├── main.py              # FastAPI routes (new)
│   ├── shopping_agent.py    # your agent, tools, system prompt (unchanged)
│   ├── reviews_api.py       # unchanged
│   ├── setup_db.py          # unchanged
│   ├── store.db             # pre-seeded — delete and rerun setup_db.py to reset
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx           # layout + session/message state
    │   ├── api.js            # fetch calls to the backend
    │   └── components/
    │       ├── ChatMessage.jsx
    │       ├── ChatInput.jsx
    │       └── ImageUploader.jsx
    ├── package.json
    └── .env.example
```

## Running it locally

**Backend** (Terminal 1):
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env and paste your GROQ_API_KEY
uvicorn main:app --reload --port 8000
```

**Frontend** (Terminal 2):
```bash
cd frontend
npm install
cp .env.example .env        # defaults to http://localhost:8000, fine for local dev
npm run dev
```

Open the URL Vite prints (usually `http://localhost:5173`).

## How a message actually flows through the app

This is the part worth understanding, not just copying:

1. You type a message and hit **Send**. `ChatInput.jsx` calls `onSend(text)`,
   which is `handleSend` in `App.jsx`.
2. `handleSend` adds your message to React state immediately (so it appears
   in the UI right away), then calls `sendMessage()` from `api.js`.
3. `api.js` does a `fetch()` `POST` to `http://localhost:8000/api/chat` with
   a JSON body: `{ session_id, message }`.
4. FastAPI's `chat()` route in `main.py` receives that, looks up the
   session's message history (an in-memory dict, keyed by `session_id`),
   appends your new message, and calls `agent.invoke({"messages": history})`
   — the exact same call your old `if __name__ == "__main__"` block made.
5. Inside `shopping_agent.py`, the LangChain agent decides which tools to
   call (`search_products`, `get_rating`, `checkout`), each of which reads
   from `store.db` via SQLite.
6. The agent's final answer comes back through FastAPI as JSON:
   `{ response, session_id }`.
7. `api.js` returns that to `App.jsx`, which adds it to the message list —
   React re-renders, and you see the assistant's reply.

The image-upload path (`ImageUploader.jsx` → `sendImage()` →
`/api/chat/image`) works the same way, except the browser sends the file as
`multipart/form-data`, and the backend saves it to a temp file so
`describe_product_image` (in `shopping_agent.py`) can open it by path exactly
like it did before.

## Things to know before you deploy this

- **Session storage is in-memory.** `SESSIONS = {}` in `main.py` lives only
  as long as the Python process runs — restart the server, and every
  session's chat history is gone. Fine for a demo; for anything persistent,
  swap that dict for Redis or a database table (the rest of the code doesn't
  need to change).
- **`store.db` is a file, not a database server.** Same caveat as before:
  works great on one server instance, won't survive being scaled across
  multiple instances or a container restart.
- **The 40-message-per-session cap** in `main.py` isn't there to protect your
  wallet — Groq's free tier has no card on file, so it can't bill you. It's
  there so one visitor to a live demo can't eat the whole shared rate limit
  while someone else is trying it.

## Deploying this

The root `Dockerfile` builds the React frontend and the FastAPI backend into
**one container**: FastAPI serves your `/api/*` routes and also serves the
built frontend as static files (see the `StaticFiles` mount at the bottom of
`backend/main.py`). One container, one URL, no CORS to configure in
production — the browser and the API are the same origin.

### Option A — Hugging Face Space (recommended, free, no card required)

1. Create a new Space at huggingface.co/new-space, SDK = **Docker**.
2. Push this repo to it (either connect your GitHub repo in the Space
   settings, or `git remote add hf <space-url> && git push hf main`).
3. Add this block to the very top of **this Space's** `README.md` (Spaces
   read it as config — GitHub ignores it, so only add it in the Space, not
   in your GitHub repo's copy):
   ```yaml
   ---
   title: AI Shopping Assistant
   emoji: 🫙
   colorFrom: green
   colorTo: yellow
   sdk: docker
   app_port: 7860
   ---
   ```
4. In the Space's **Settings → Variables and secrets**, add `GROQ_API_KEY`
   as a secret.
5. That's it — the Space builds the Dockerfile and gives you a URL like
   `you-username-ai-shopping-assistant.hf.space`.

Free CPU Basic Spaces don't require a card on file, and only sleep after
around 48 hours of no traffic (waking back up on the next visit) — gentler
than most free-tier web hosts.

### Option B — split hosting (closer to how most real teams deploy)

Frontend and backend as two separate deployments — more moving parts, but
each side scales and redeploys independently, which is the more common
real-world pattern:

- **Backend** → Render (or Fly.io, or a second Hugging Face Docker Space
  pointed at just `backend/`). Set `GROQ_API_KEY` and `FRONTEND_ORIGIN`
  (your frontend's deployed URL) as environment variables there.
- **Frontend** → Vercel or Netlify. Connect the repo, set the root directory
  to `frontend`, and set `VITE_API_URL` to your backend's deployed URL as a
  build-time environment variable.

Render's free web services spin down after 15 minutes of inactivity (cold
start ~30-60s on the next request) — fine for a portfolio link, just expect
the first visitor after a while to wait a moment.

### Either way

- Swap the in-memory `SESSIONS` dict in `main.py` for Redis or a database
  once you want conversations to survive a restart.
- Test the Docker build locally first if you can (`docker build -t
  shopping-agent .`) — this sandbox couldn't run Docker to verify it for
  you, so give it a run-through before pushing.
