import { useRef, useState } from "react";

export default function ImageUploader({ onSubmit, disabled }) {
  const inputRef = useRef(null);
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);

  function handleFileChange(e) {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
  }

  function handleSubmit() {
    if (!file || disabled) return;
    onSubmit(file);
    setFile(null);
    setPreviewUrl(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="uploader">
      <div className="uploader__label">Shop by photo</div>
      <p className="uploader__hint">Upload a product photo and I'll find similar items in the store.</p>

      <label className="uploader__dropzone">
        <input
          ref={inputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          hidden
        />
        {previewUrl ? (
          <img className="uploader__preview" src={previewUrl} alt="Selected product" />
        ) : (
          <span className="uploader__dropzone-text">Choose an image…</span>
        )}
      </label>

      <button
        className="uploader__submit"
        type="button"
        onClick={handleSubmit}
        disabled={!file || disabled}
      >
        Find similar items
      </button>
    </div>
  );
}
