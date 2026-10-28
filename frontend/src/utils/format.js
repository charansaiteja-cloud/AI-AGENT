const relativeFormatter = new Intl.RelativeTimeFormat("en", {
  numeric: "auto",
});

const dateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const timeFormatter = new Intl.DateTimeFormat("en", {
  hour: "numeric",
  minute: "2-digit",
});

const units = [
  ["year", 365 * 24 * 60 * 60 * 1000],
  ["month", 30 * 24 * 60 * 60 * 1000],
  ["week", 7 * 24 * 60 * 60 * 1000],
  ["day", 24 * 60 * 60 * 1000],
  ["hour", 60 * 60 * 1000],
  ["minute", 60 * 1000],
];

export function formatRelativeTime(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const diff = date.getTime() - Date.now();
  const absolute = Math.abs(diff);

  if (absolute < 45 * 1000) {
    return "just now";
  }

  for (const [unit, milliseconds] of units) {
    if (absolute >= milliseconds) {
      return relativeFormatter.format(Math.round(diff / milliseconds), unit);
    }
  }

  return relativeFormatter.format(Math.round(diff / 1000), "second");
}

export function formatDateTime(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const today = new Date();
  const sameDay =
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate();

  if (sameDay) {
    return timeFormatter.format(date);
  }

  return `${dateFormatter.format(date)}, ${timeFormatter.format(date)}`;
}

export function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 B";
  }

  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** index;
  const rounded =
    value >= 10 || index === 0 ? Math.round(value) : Math.round(value * 10) / 10;
  return `${rounded} ${units[index]}`;
}

export function initials(name) {
  const cleaned = (name || "").trim();
  if (!cleaned) {
    return "?";
  }

  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

export function truncate(text, max = 80) {
  const cleaned = (text || "").replace(/\s+/g, " ").trim();
  if (cleaned.length <= max) {
    return cleaned;
  }
  return `${cleaned.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
}

export function isImage(contentType) {
  return typeof contentType === "string" && contentType.startsWith("image/");
}

const kindLabels = {
  name: "Name",
  company: "Company",
  product: "Device",
  operating_system: "System",
  issue: "Issue",
  preference: "Preference",
  account: "Account",
  contact: "Contact",
  interaction: "Conversation",
  other: "Memory",
};

export function kindLabel(kind) {
  return kindLabels[kind] || "Memory";
}

export function memoryGroup(kind) {
  if (kind === "issue") {
    return "issues";
  }
  if (kind === "preference") {
    return "preferences";
  }
  if (kind === "interaction") {
    return "conversations";
  }
  return "profile";
}
