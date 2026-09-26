export default function ChatMessage({ role, content, imageLabel }) {
  const isUser = role === "user";

  return (
    <div className={`message message--${isUser ? "user" : "assistant"}`}>
      <div className="message__meta">{isUser ? "You" : "Assistant"}</div>
      {imageLabel ? (
        <div className="message__image-tag">
          <span className="message__image-tag-label">Photo</span>
          Searching by photo: {imageLabel}
        </div>
      ) : (
        <div className="message__body">{content}</div>
      )}
    </div>
  );
}
