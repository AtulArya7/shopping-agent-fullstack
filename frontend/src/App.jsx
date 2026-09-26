import { useEffect, useRef, useState } from "react";
import ChatMessage from "./components/ChatMessage.jsx";
import ChatInput from "./components/ChatInput.jsx";
import ImageUploader from "./components/ImageUploader.jsx";
import { createSession, sendImage, sendMessage } from "./api.js";
import "./App.css";

const SESSION_KEY = "pantry_session_id";

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const scrollRef = useRef(null);

  // On first load, reuse a session from this browser tab or mint a new one.
  useEffect(() => {
    const existing = sessionStorage.getItem(SESSION_KEY);
    if (existing) {
      setSessionId(existing);
      return;
    }
    createSession()
      .then(({ session_id }) => {
        sessionStorage.setItem(SESSION_KEY, session_id);
        setSessionId(session_id);
      })
      .catch(() => setError("Couldn't reach the AI backend. Is it running on localhost:8000?"));
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isLoading]);

  function startNewSession() {
    createSession().then(({ session_id }) => {
      sessionStorage.setItem(SESSION_KEY, session_id);
      setSessionId(session_id);
      setMessages([]);
      setError(null);
    });
  }

  async function handleSend(text) {
    if (!sessionId) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setIsLoading(true);
    setError(null);
    try {
      const { response } = await sendMessage(sessionId, text);
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleImage(file) {
    if (!sessionId) return;
    setMessages((prev) => [...prev, { role: "user", content: "", imageLabel: file.name }]);
    setIsLoading(true);
    setError(null);
    try {
      const { response } = await sendImage(sessionId, file);
      setMessages((prev) => [...prev, { role: "assistant", content: response }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <JarMark />
          <div>
            <h1 className="sidebar__title">The Pantry</h1>
            <p className="sidebar__tagline">An AI clerk for the shop</p>
          </div>
        </div>

        <ImageUploader onSubmit={handleImage} disabled={isLoading || !sessionId} />

        <div className="sidebar__footer">
          <span className="sidebar__session">
            Session {sessionId ? sessionId.slice(0, 8) : "…"}
          </span>
          <button className="sidebar__reset" type="button" onClick={startNewSession}>
            New session
          </button>
        </div>
      </aside>

      <main className="chat">
        <div className="chat__log" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="chat__empty">
              Tell me what you're looking for — try "organic honey under $15 with a 4+ rating."
            </div>
          )}
          {messages.map((m, i) => (
            <ChatMessage key={i} role={m.role} content={m.content} imageLabel={m.imageLabel} />
          ))}
          {isLoading && (
            <div className="message message--assistant">
              <div className="message__meta">Assistant</div>
              <div className="message__body message__body--thinking">Thinking…</div>
            </div>
          )}
        </div>

        {error && (
          <div className="chat__error">
            {error}
          </div>
        )}

        <ChatInput onSend={handleSend} disabled={isLoading || !sessionId} />
      </main>
    </div>
  );
}

function JarMark() {
  return (
    <svg className="sidebar__mark" width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
      <path
        d="M10 3H18V6.5L20 8.5V24C20 25.1 19.1 26 18 26H10C8.9 26 8 25.1 8 24V8.5L10 6.5V3Z"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <line x1="8" y1="13" x2="20" y2="13" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
