// Nullish coalescing (not ||) matters here: an empty string is a deliberate
// value meaning "same origin as the page" (used when the frontend is built
// into the same container as the API — see the root Dockerfile). "||" would
// treat "" as unset and silently fall back to localhost.
const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

/**
 * Reads a JSON error body (FastAPI's HTTPException shape: { detail: "..." })
 * and throws a plain Error with that message so callers can just try/catch.
 */
async function unwrap(response) {
  if (response.ok) return response.json();

  let detail = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (body?.detail) detail = body.detail;
  } catch {
    // response wasn't JSON — keep the generic message
  }
  throw new Error(detail);
}

export async function createSession() {
  const res = await fetch(`${API_URL}/api/session/new`, { method: "POST" });
  return unwrap(res); // { session_id }
}

export async function sendMessage(sessionId, message) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  return unwrap(res); // { response, session_id }
}

export async function sendImage(sessionId, file) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("file", file);

  const res = await fetch(`${API_URL}/api/chat/image`, {
    method: "POST",
    body: formData,
  });
  return unwrap(res); // { response, session_id }
}
