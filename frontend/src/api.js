const API_BASE = "";

export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function extractDetail(payload) {
  if (!payload) {
    return "";
  }

  if (typeof payload === "string") {
    return payload;
  }

  const detail = payload.detail;

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }
        const location = Array.isArray(item?.loc)
          ? item.loc.filter((part) => part !== "body").join(".")
          : "";
        return location ? `${location}: ${item?.msg ?? "Invalid value"}` : item?.msg;
      })
      .filter(Boolean)
      .join(" ");
  }

  return "";
}

async function request(path, options = {}) {
  const { method = "GET", body, headers = {}, signal } = options;
  const requestHeaders = { Accept: "application/json", ...headers };
  const init = { method, headers: requestHeaders, signal };

  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, init);
  } catch (error) {
    if (error.name === "AbortError") {
      throw error;
    }
    throw new ApiError(
      "Could not reach the support server. Check that the backend is running.",
      0,
    );
  }

  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    const detail = extractDetail(payload);
    throw new ApiError(
      detail || `Request failed with status ${response.status}.`,
      response.status,
      payload,
    );
  }

  return payload;
}

export const api = {
  health: () => request("/api/health"),
  models: () => request("/api/models"),

  customers: {
    list: () => request("/api/customers"),
    create: (payload) =>
      request("/api/customers", { method: "POST", body: payload }),
    update: (customerId, payload) =>
      request(`/api/customers/${customerId}`, {
        method: "PATCH",
        body: payload,
      }),
    remove: (customerId) =>
      request(`/api/customers/${customerId}`, { method: "DELETE" }),
    conversations: (customerId) =>
      request(`/api/customers/${customerId}/conversations`),
    memories: (customerId) =>
      request(`/api/customers/${customerId}/memories`),
    clearMemories: (customerId) =>
      request(`/api/customers/${customerId}/memories`, { method: "DELETE" }),
  },

  conversations: {
    create: (customerId, payload = {}) =>
      request(`/api/customers/${customerId}/conversations`, {
        method: "POST",
        body: payload,
      }),
    update: (conversationId, payload) =>
      request(`/api/conversations/${conversationId}`, {
        method: "PATCH",
        body: payload,
      }),
    remove: (conversationId) =>
      request(`/api/conversations/${conversationId}`, { method: "DELETE" }),
    messages: (conversationId) =>
      request(`/api/conversations/${conversationId}/messages`),
    attachments: (conversationId) =>
      request(`/api/conversations/${conversationId}/attachments`),
    upload: (conversationId, file) => {
      const form = new FormData();
      form.append("file", file);
      return request(`/api/conversations/${conversationId}/attachments`, {
        method: "POST",
        body: form,
      });
    },
    deleteAttachment: (attachmentId) =>
      request(`/api/attachments/${attachmentId}`, { method: "DELETE" }),
  },

  chat: (payload) => request("/api/chat", { method: "POST", body: payload }),

  demo: {
    seed: () => request("/api/demo/seed", { method: "POST" }),
    scenario: () => request("/api/demo/scenario"),
  },
};

export function getErrorMessage(error) {
  if (error?.name === "AbortError") {
    return "";
  }
  return error?.message || "Something went wrong. Please try again.";
}
