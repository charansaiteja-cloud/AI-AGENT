import Icon from "./Icon";
import { initials } from "../utils/format";

export default function ChatHeader({
  customer,
  conversation,
  health,
  memoryOpen,
  onToggleSidebar,
  onToggleMemory,
  onEditCustomer,
  onDeleteCustomer,
}) {
  const ollamaOnline = health?.ollama === "available";
  const memoryOnline = health?.hindsight === "available";

  return (
    <header className="chat-header">
      <div className="chat-header-left">
        <button
          type="button"
          className="icon-button mobile-menu"
          onClick={onToggleSidebar}
          aria-label="Open sidebar"
        >
          <Icon name="menu" size={20} />
        </button>

        <div className="avatar avatar-header" aria-hidden="true">
          {customer ? initials(customer.name) : <Icon name="users" size={18} />}
        </div>

        <div className="chat-identity">
          <div className="chat-name-row">
            <h1>{customer?.name || "No customer selected"}</h1>
            {customer ? (
              <span className="customer-pill">
                <span className="status-dot online" />
                Customer
              </span>
            ) : null}
          </div>
          <p>
            {conversation
              ? conversation.title
              : customer?.email || "Add a customer to begin"}
          </p>
        </div>
      </div>

      <div className="chat-header-actions">
        <div className="status-cluster" aria-label="Service status">
          <span className={`status-pill ${ollamaOnline ? "ok" : "warn"}`}>
            <span className={`status-dot ${ollamaOnline ? "online" : "offline"}`} />
            <span className="status-pill-label">
              {ollamaOnline ? health?.model || "Ollama" : "Ollama offline"}
            </span>
          </span>
          <span className={`status-pill ${memoryOnline ? "ok" : "warn"}`}>
            <Icon name={memoryOnline ? "brain" : "cloudOff"} size={14} />
            <span className="status-pill-label">
              {memoryOnline ? "Memory on" : "Memory off"}
            </span>
          </span>
        </div>

        {customer ? (
          <>
            <button
              type="button"
              className="icon-button"
              onClick={onEditCustomer}
              aria-label="Edit customer"
              title="Edit customer"
            >
              <Icon name="pencil" size={17} />
            </button>
            <button
              type="button"
              className="icon-button danger-hover"
              onClick={onDeleteCustomer}
              aria-label="Delete customer"
              title="Delete customer"
            >
              <Icon name="trash" size={17} />
            </button>
          </>
        ) : null}

        <button
          type="button"
          className={`icon-button memory-toggle ${memoryOpen ? "active" : ""}`}
          onClick={onToggleMemory}
          aria-label="Toggle memory panel"
          title="Memory inspector"
        >
          <Icon name="brain" size={18} />
        </button>
      </div>
    </header>
  );
}
