import { useMemo, useState } from "react";
import Icon from "./Icon";
import {
  formatRelativeTime,
  initials,
  truncate,
} from "../utils/format";

export default function Sidebar({
  customers,
  activeCustomerId,
  onSelectCustomer,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onAddCustomer,
  onLoadDemo,
  onClose,
  isOpen,
  loading,
  memoryAvailable,
  demoBusy,
}) {
  const [query, setQuery] = useState("");
  const activeCustomer = customers.find(
    (customer) => customer.id === activeCustomerId,
  );

  const filteredConversations = useMemo(() => {
    const clean = query.trim().toLowerCase();
    if (!clean) {
      return conversations;
    }
    return conversations.filter((conversation) => {
      const haystack = `${conversation.title} ${conversation.last_message || ""}`;
      return haystack.toLowerCase().includes(clean);
    });
  }, [conversations, query]);

  return (
    <>
      <div
        className={`sidebar-scrim ${isOpen ? "visible" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside className={`sidebar ${isOpen ? "open" : ""}`} aria-label="Customers and conversations">
        <div className="brand-row">
          <div className="brand-mark">
            <Icon name="logo" size={19} strokeWidth={2} />
          </div>
          <div className="brand-copy">
            <span className="brand-name">Support AI</span>
            <span className="brand-subtitle">Memory-aware support</span>
          </div>
          <button
            type="button"
            className="icon-button sidebar-close"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <Icon name="x" size={18} />
          </button>
        </div>

        <div className="customer-switcher">
          <div className="avatar avatar-customer" aria-hidden="true">
            {activeCustomer ? initials(activeCustomer.name) : <Icon name="users" size={17} />}
          </div>
          <div className="customer-switcher-copy">
            <span className="eyebrow">Customer</span>
            <div className="select-wrap">
              <select
                className="customer-select"
                value={activeCustomerId ?? ""}
                onChange={(event) => onSelectCustomer(Number(event.target.value))}
                disabled={!customers.length}
                aria-label="Select customer"
              >
                {!customers.length ? (
                  <option value="">No customers yet</option>
                ) : null}
                {customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>
                    {customer.name}
                  </option>
                ))}
              </select>
              <Icon name="chevronDown" size={15} />
            </div>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onAddCustomer}
            aria-label="Add customer"
            title="Add customer"
          >
            <Icon name="plus" size={18} />
          </button>
        </div>

        {activeCustomer?.email ? (
          <p className="customer-email">{activeCustomer.email}</p>
        ) : null}

        <button
          type="button"
          className="new-conversation"
          onClick={onNewConversation}
          disabled={!activeCustomerId}
        >
          <Icon name="plus" size={17} />
          <span>New conversation</span>
          <kbd>⌘ K</kbd>
        </button>

        <div className="conversation-heading">
          <span>Conversations</span>
          <span className="count-badge">{conversations.length}</span>
        </div>

        <label className="search-box">
          <Icon name="search" size={15} />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search conversations"
            aria-label="Search conversations"
          />
        </label>

        <div className="conversation-list">
          {loading.conversations ? (
            <div className="sidebar-skeleton" aria-label="Loading conversations">
              <span />
              <span />
              <span />
            </div>
          ) : null}

          {!loading.conversations && !filteredConversations.length ? (
            <div className="conversation-empty">
              <span className="empty-icon">
                <Icon name="message" size={19} />
              </span>
              <p>{query ? "No matching conversations." : "No conversations yet."}</p>
              <span>
                {query
                  ? "Try a different search."
                  : "Send a message to start one."}
              </span>
            </div>
          ) : null}

          {filteredConversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              className={`conversation-item ${
                conversation.id === activeConversationId ? "active" : ""
              }`}
              onClick={() => onSelectConversation(conversation.id)}
              aria-current={
                conversation.id === activeConversationId ? "true" : undefined
              }
            >
              <span className="conversation-icon">
                <Icon name="message" size={16} />
              </span>
              <span className="conversation-copy">
                <span className="conversation-title">
                  {truncate(conversation.title || "New conversation", 40)}
                </span>
                <span className="conversation-preview">
                  {conversation.last_message
                    ? truncate(conversation.last_message, 56)
                    : "No messages yet"}
                </span>
              </span>
              <span className="conversation-meta">
                <span>{formatRelativeTime(conversation.updated_at)}</span>
                {conversation.message_count ? (
                  <span className="message-count">
                    {conversation.message_count}
                  </span>
                ) : null}
              </span>
            </button>
          ))}
        </div>

        <div className="sidebar-footer">
          <div className="memory-status">
            <span
              className={`status-dot ${memoryAvailable ? "online" : "offline"}`}
            />
            <span>
              {memoryAvailable ? "Hindsight memory online" : "Memory offline"}
            </span>
          </div>
          <button
            type="button"
            className="demo-button"
            onClick={onLoadDemo}
            disabled={demoBusy}
          >
            <Icon name="sparkles" size={16} />
            <span>{demoBusy ? "Loading demo…" : "Load demo customer"}</span>
            <Icon name="chevronRight" size={14} className="demo-chevron" />
          </button>
          <p className="local-note">
            Local-first · Ollama + Hindsight
          </p>
        </div>
      </aside>
    </>
  );
}
