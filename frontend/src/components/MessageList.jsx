import { useEffect, useRef } from "react";
import Icon from "./Icon";
import {
  formatDateTime,
  formatFileSize,
  initials,
  isImage,
} from "../utils/format";

function AttachmentCard({ attachment }) {
  const url = attachment.download_url;
  const image = isImage(attachment.content_type);

  if (image && url) {
    return (
      <a
        className="attachment-image"
        href={url}
        target="_blank"
        rel="noreferrer"
        title={attachment.original_filename}
      >
        <img
          src={`${url}?inline=true`}
          alt={attachment.original_filename}
          loading="lazy"
        />
        <span>
          <Icon name="image" size={13} />
          {attachment.original_filename}
        </span>
      </a>
    );
  }

  return (
    <a
      className="attachment-file"
      href={url || undefined}
      target={url ? "_blank" : undefined}
      rel={url ? "noreferrer" : undefined}
      download={url ? attachment.original_filename : undefined}
    >
      <span className="attachment-file-icon">
        <Icon name="file" size={16} />
      </span>
      <span className="attachment-file-copy">
        <span>{attachment.original_filename}</span>
        <span>{formatFileSize(attachment.file_size)}</span>
      </span>
      {url ? <Icon name="download" size={15} /> : null}
    </a>
  );
}

function RecallCard({ turn }) {
  if (!turn?.memories?.length) {
    return null;
  }

  return (
    <div className="recall-card">
      <div className="recall-card-head">
        <span className="recall-icon">
          <Icon name="brain" size={16} />
        </span>
        <div>
          <strong>
            Recalled {turn.memories.length}{" "}
            {turn.memories.length === 1 ? "memory" : "memories"}
          </strong>
          <span>Used to personalize this reply</span>
        </div>
        <span className="recall-latency">
          {turn.latencyMs ? `${(turn.latencyMs / 1000).toFixed(1)}s` : ""}
        </span>
      </div>
      <div className="recall-items">
        {turn.memories.slice(0, 3).map((memory) => (
          <span key={memory.id || memory.text} className="recall-chip">
            {memory.text}
          </span>
        ))}
        {turn.memories.length > 3 ? (
          <span className="recall-chip recall-chip-more">
            +{turn.memories.length - 3} more
          </span>
        ) : null}
      </div>
      {turn.memorySaved ? (
        <div className="recall-saved">
          <Icon name="check" size={13} />
          Saved to this customer&apos;s memory
        </div>
      ) : null}
    </div>
  );
}

export default function MessageList({
  messages,
  loading,
  sending,
  customer,
  lastTurn,
  onCopy,
}) {
  const scrollRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!scrollRef.current) {
      return;
    }
    const frame = window.requestAnimationFrame(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [messages.length, sending]);

  if (loading) {
    return (
      <div className="message-scroll" aria-label="Loading conversation">
        <div className="message-skeletons">
          <div className="message-skeleton">
            <span className="skeleton-avatar" />
            <span className="skeleton-lines">
              <span />
              <span />
            </span>
          </div>
          <div className="message-skeleton align-right">
            <span className="skeleton-lines">
              <span />
              <span />
            </span>
            <span className="skeleton-avatar" />
          </div>
          <div className="message-skeleton">
            <span className="skeleton-avatar" />
            <span className="skeleton-lines">
              <span />
              <span />
              <span />
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (!messages.length && !sending) {
    return null;
  }

  return (
    <div className="message-scroll" ref={scrollRef}>
      <div className="message-stack">
        {messages.map((message, index) => {
          const assistant = message.role === "assistant";
          const isLastAssistant =
            assistant && index === messages.length - 1 && !sending;

          return (
            <div
              key={message.id}
              className={`message-row ${assistant ? "assistant" : "user"}`}
            >
              <div
                className={`avatar ${assistant ? "avatar-assistant" : "avatar-user"}`}
                aria-hidden="true"
              >
                {assistant ? (
                  <Icon name="logo" size={18} strokeWidth={1.9} />
                ) : (
                  initials(customer?.name || "You")
                )}
              </div>

              <div className="message-body">
                <div className="message-meta">
                  <strong>{assistant ? "Support AI" : customer?.name || "You"}</strong>
                  <span>{formatDateTime(message.created_at)}</span>
                  {assistant && message.memory_count ? (
                    <span className="memory-used-badge">
                      <Icon name="brain" size={12} />
                      {message.memory_count} recalled
                    </span>
                  ) : null}
                  {assistant ? (
                    <button
                      type="button"
                      className="copy-button"
                      onClick={() => onCopy(message.content)}
                      aria-label="Copy reply"
                      title="Copy reply"
                    >
                      <Icon name="copy" size={14} />
                    </button>
                  ) : null}
                </div>

                <div className="message-bubble">
                  <div className="message-text">{message.content}</div>
                  {message.attachments?.length ? (
                    <div className="message-attachments">
                      {message.attachments.map((attachment) => (
                        <AttachmentCard
                          key={attachment.id}
                          attachment={attachment}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>

                {isLastAssistant ? <RecallCard turn={lastTurn} /> : null}
              </div>
            </div>
          );
        })}

        {sending ? (
          <div className="message-row assistant thinking-row">
            <div className="avatar avatar-assistant" aria-hidden="true">
              <Icon name="logo" size={18} strokeWidth={1.9} />
            </div>
            <div className="message-body">
              <div className="message-meta">
                <strong>Support AI</strong>
                <span>thinking</span>
              </div>
              <div className="thinking-bubble" aria-label="Support AI is thinking">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        ) : null}

        <div ref={bottomRef} className="scroll-anchor" />
      </div>
    </div>
  );
}
