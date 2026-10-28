import { useMemo, useState } from "react";
import Icon from "./Icon";
import {
  formatDateTime,
  kindLabel,
  memoryGroup,
} from "../utils/format";

const filters = [
  { id: "all", label: "All" },
  { id: "profile", label: "Profile" },
  { id: "issues", label: "Issues" },
  { id: "preferences", label: "Preferences" },
  { id: "conversations", label: "Turns" },
];

const kindIcons = {
  name: "user",
  company: "users",
  product: "memory",
  operating_system: "activity",
  issue: "alert",
  preference: "sparkles",
  account: "shield",
  contact: "user",
  interaction: "message",
  other: "brain",
};

export default function MemoryPanel({
  open,
  onClose,
  customer,
  memories,
  loading,
  available,
  error,
  onRefresh,
  onClear,
  clearing,
}) {
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const clean = query.trim().toLowerCase();
    return memories.filter((memory) => {
      const matchesFilter =
        filter === "all" || memoryGroup(memory.kind) === filter;
      const matchesQuery =
        !clean ||
        memory.text.toLowerCase().includes(clean) ||
        kindLabel(memory.kind).toLowerCase().includes(clean);
      return matchesFilter && matchesQuery;
    });
  }, [memories, filter, query]);

  return (
    <>
      <div
        className={`memory-scrim ${open ? "visible" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`memory-panel ${open ? "open" : ""}`}
        aria-label="Customer memory"
      >
        <div className="memory-heading">
          <div>
            <span className="eyebrow">Long-term memory</span>
            <h2>
              <Icon name="brain" size={18} />
              Memory
            </h2>
          </div>
          <div className="memory-heading-actions">
            <button
              type="button"
              className="icon-button"
              onClick={onRefresh}
              aria-label="Refresh memories"
              title="Refresh memories"
              disabled={loading || !customer}
            >
              <Icon name="refresh" size={16} className={loading ? "spin" : ""} />
            </button>
            <button
              type="button"
              className="icon-button memory-close"
              onClick={onClose}
              aria-label="Close memory panel"
            >
              <Icon name="x" size={18} />
            </button>
          </div>
        </div>

        {customer ? (
          <div className="memory-customer">
            <span className="memory-customer-icon">
              <Icon name="database" size={16} />
            </span>
            <div>
              <strong>{customer.name}</strong>
              <span>Isolated Hindsight bank</span>
            </div>
            <span className={`status-dot ${available ? "online" : "offline"}`} />
          </div>
        ) : null}

        {!customer ? (
          <div className="memory-empty">
            <span className="memory-empty-icon">
              <Icon name="users" size={22} />
            </span>
            <h3>No customer selected</h3>
            <p>Choose a customer to inspect their long-term memory.</p>
          </div>
        ) : null}

        {customer && !available && !loading ? (
          <div className="memory-empty">
            <span className="memory-empty-icon warn">
              <Icon name="cloudOff" size={22} />
            </span>
            <h3>Memory is offline</h3>
            <p>
              {error ||
                "Hindsight is not reachable. Chat still works, but nothing will be recalled or saved."}
            </p>
            <button type="button" className="button button-secondary button-small" onClick={onRefresh}>
              <Icon name="refresh" size={14} />
              Try again
            </button>
          </div>
        ) : null}

        {customer && available ? (
          <>
            <div className="memory-stats">
              <div>
                <strong>{memories.length}</strong>
                <span>memories</span>
              </div>
              <div>
                <strong>
                  {new Set(memories.map((memory) => memory.kind)).size}
                </strong>
                <span>fact types</span>
              </div>
              <div>
                <strong>{filtered.length}</strong>
                <span>shown</span>
              </div>
            </div>

            <label className="memory-search">
              <Icon name="search" size={14} />
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Filter memories"
                aria-label="Filter memories"
              />
            </label>

            <div className="memory-filters" role="tablist" aria-label="Memory filters">
              {filters.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={filter === item.id}
                  className={`memory-filter ${filter === item.id ? "active" : ""}`}
                  onClick={() => setFilter(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="memory-list">
              {loading ? (
                <div className="memory-skeletons" aria-label="Loading memories">
                  <span />
                  <span />
                  <span />
                </div>
              ) : null}

              {!loading && !memories.length ? (
                <div className="memory-empty">
                  <span className="memory-empty-icon">
                    <Icon name="brain" size={22} />
                  </span>
                  <h3>Nothing remembered yet</h3>
                  <p>
                    Share details like a name, device, recurring issue, or
                    response preference. Useful facts are extracted after each
                    reply.
                  </p>
                </div>
              ) : null}

              {!loading && memories.length && !filtered.length ? (
                <div className="memory-empty compact">
                  <h3>No matches</h3>
                  <p>Try another filter or search term.</p>
                </div>
              ) : null}

              {!loading
                ? filtered.map((memory) => (
                    <article className="memory-card" key={memory.id || memory.text}>
                      <div className="memory-card-top">
                        <span className={`memory-kind kind-${memoryGroup(memory.kind)}`}>
                          <Icon
                            name={kindIcons[memory.kind] || "brain"}
                            size={12}
                          />
                          {kindLabel(memory.kind)}
                        </span>
                        {memory.created_at ? (
                          <span className="memory-date">
                            {formatDateTime(memory.created_at)}
                          </span>
                        ) : null}
                      </div>
                      <p>{memory.text}</p>
                      <div className="memory-card-foot">
                        <span>{memory.source === "profile_extraction" ? "Extracted fact" : "Conversation"}</span>
                        {memory.score ? (
                          <span className="memory-score">
                            {Math.round(memory.score * 100)}% match
                          </span>
                        ) : null}
                      </div>
                    </article>
                  ))
                : null}
            </div>

            <div className="memory-footer">
              <div className="memory-explainer">
                <Icon name="info" size={14} />
                <p>
                  Facts are extracted from each turn, stored in this
                  customer&apos;s bank, and recalled for later conversations.
                </p>
              </div>
              <button
                type="button"
                className="memory-clear"
                onClick={onClear}
                disabled={!memories.length || clearing}
              >
                <Icon name="trash" size={14} />
                {clearing ? "Clearing…" : "Clear customer memory"}
              </button>
            </div>
          </>
        ) : null}
      </aside>
    </>
  );
}
