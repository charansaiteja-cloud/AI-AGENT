import { useEffect } from "react";
import Icon from "./Icon";

export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) {
      return undefined;
    }

    const timer = window.setTimeout(onClose, 4200);
    return () => window.clearTimeout(timer);
  }, [toast, onClose]);

  if (!toast) {
    return null;
  }

  const isError = toast.type === "error";

  return (
    <div
      className={`toast ${isError ? "toast-error" : "toast-success"}`}
      role="status"
      aria-live="polite"
    >
      <span className="toast-icon">
        <Icon name={isError ? "alert" : "check"} size={17} />
      </span>
      <span className="toast-message">{toast.message}</span>
      <button
        type="button"
        className="icon-button icon-button-small"
        onClick={onClose}
        aria-label="Dismiss notification"
      >
        <Icon name="x" size={15} />
      </button>
    </div>
  );
}
