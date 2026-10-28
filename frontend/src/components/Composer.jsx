import { useEffect, useRef, useState } from "react";
import Icon from "./Icon";
import { formatFileSize, isImage } from "../utils/format";

const ACCEPTED =
  ".png,.jpg,.jpeg,.gif,.webp,.txt,.md,.csv,.json,.pdf";

export default function Composer({
  value,
  onChange,
  onSend,
  onAttach,
  attachments,
  onRemoveAttachment,
  disabled,
  sending,
  uploading,
  placeholder,
  focusToken,
  maxLength = 4000,
}) {
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) {
      return;
    }
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 190)}px`;
  }, [value]);

  useEffect(() => {
    if (focusToken) {
      textareaRef.current?.focus();
    }
  }, [focusToken]);

  function handleKeyDown(event) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      if (!disabled && !sending && value.trim()) {
        onSend();
      }
    }
  }

  function handleFileInput(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (files.length) {
      onAttach(files);
    }
  }

  function handleDrop(event) {
    event.preventDefault();
    setDragging(false);
    const files = Array.from(event.dataTransfer.files || []);
    if (files.length) {
      onAttach(files);
    }
  }

  return (
    <div className="composer-wrap">
      <div
        className={`composer ${dragging ? "dragging" : ""} ${
          disabled ? "disabled" : ""
        }`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) {
            setDragging(true);
          }
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        {attachments.length || uploading ? (
          <div className="composer-attachments">
            {attachments.map((attachment) => (
              <span className="draft-attachment" key={attachment.id}>
                <span className="draft-attachment-icon">
                  <Icon
                    name={isImage(attachment.content_type) ? "image" : "file"}
                    size={14}
                  />
                </span>
                <span className="draft-attachment-name">
                  {attachment.original_filename}
                </span>
                <span className="draft-attachment-size">
                  {formatFileSize(attachment.file_size)}
                </span>
                <button
                  type="button"
                  className="draft-remove"
                  onClick={() => onRemoveAttachment(attachment)}
                  aria-label={`Remove ${attachment.original_filename}`}
                  disabled={uploading}
                >
                  <Icon name="x" size={13} />
                </button>
              </span>
            ))}
            {uploading ? (
              <span className="draft-attachment uploading">
                <span className="mini-spinner" />
                Uploading…
              </span>
            ) : null}
          </div>
        ) : null}

        <textarea
          ref={textareaRef}
          className="composer-input"
          rows={1}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          aria-label="Message"
          maxLength={maxLength}
          disabled={disabled || sending}
        />

        <div className="composer-toolbar">
          <div className="composer-tools">
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED}
              multiple
              onChange={handleFileInput}
              className="visually-hidden"
              tabIndex={-1}
            />
            <button
              type="button"
              className="composer-icon-button"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled || sending || uploading}
              aria-label="Attach files"
              title="Attach an image, PDF, or text file"
            >
              <Icon name="paperclip" size={18} />
            </button>
            <span className="composer-hint">
              <span className="desktop-hint">
                Enter to send · Shift+Enter for a new line
              </span>
              <span className="mobile-hint">Attach files · Enter to send</span>
            </span>
          </div>

          <div className="composer-send-group">
            {value.length > maxLength * 0.8 ? (
              <span
                className={`char-count ${
                  value.length >= maxLength ? "limit" : ""
                }`}
              >
                {value.length}/{maxLength}
              </span>
            ) : null}
            <button
              type="button"
              className="send-button"
              onClick={onSend}
              disabled={disabled || sending || !value.trim()}
              aria-label="Send message"
              title="Send message"
            >
              {sending ? (
                <span className="button-spinner" />
              ) : (
                <Icon name="arrowUp" size={19} strokeWidth={2.1} />
              )}
            </button>
          </div>
        </div>

        {dragging ? (
          <div className="drop-overlay">
            <Icon name="paperclip" size={20} />
            Drop files to attach
          </div>
        ) : null}
      </div>
      <p className="composer-disclaimer">
        Support AI can make mistakes. Verify important account or product details.
      </p>
    </div>
  );
}
