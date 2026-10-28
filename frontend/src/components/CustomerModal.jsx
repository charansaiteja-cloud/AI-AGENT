import { useEffect, useState } from "react";
import Icon from "./Icon";
import { getErrorMessage } from "../api";

export default function CustomerModal({
  mode = "create",
  customer = null,
  onClose,
  onSubmit,
}) {
  const [name, setName] = useState(customer?.name || "");
  const [email, setEmail] = useState(customer?.email || "");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const editing = mode === "edit";

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape" && !busy) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [busy, onClose]);

  async function handleSubmit(event) {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanEmail = email.trim();

    if (!cleanName) {
      setError("Enter a customer name.");
      return;
    }

    setBusy(true);
    setError("");

    try {
      await onSubmit({
        name: cleanName,
        email: cleanEmail || null,
      });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <div
        className="customer-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="customer-modal-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-heading">
          <div className="modal-heading-icon">
            <Icon name={editing ? "pencil" : "user"} size={20} />
          </div>
          <div>
            <h2 id="customer-modal-title">
              {editing ? "Edit customer" : "New customer"}
            </h2>
            <p>
              {editing
                ? "Update the profile shown across conversations."
                : "Create an isolated profile and memory bank for this customer."}
            </p>
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={onClose}
            aria-label="Close dialog"
            disabled={busy}
          >
            <Icon name="x" size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="customer-form">
          <label className="field">
            <span className="field-label">Name</span>
            <input
              className="text-input"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Sarah Chen"
              maxLength={120}
              autoFocus
              required
            />
          </label>

          <label className="field">
            <span className="field-label">
              Email <span className="field-optional">optional</span>
            </span>
            <input
              className="text-input"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="sarah@example.com"
              maxLength={255}
            />
          </label>

          <div className="privacy-note">
            <Icon name="shield" size={16} />
            <span>
              Each customer gets a separate Hindsight bank. Memories are never
              recalled across customers.
            </span>
          </div>

          {error ? (
            <div className="inline-error" role="alert">
              <Icon name="alert" size={16} />
              <span>{error}</span>
            </div>
          ) : null}

          <div className="modal-actions">
            <button
              type="button"
              className="button button-ghost"
              onClick={onClose}
              disabled={busy}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="button button-primary"
              disabled={busy}
            >
              {busy
                ? "Saving…"
                : editing
                  ? "Save changes"
                  : "Create customer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
