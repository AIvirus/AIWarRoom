// Tiny fetch wrapper for our own JSON API.
// Every API error has one shape: {"error": {"code", "message", "fields"}}; we turn it into
// an ApiError the page can show as-is.

export class ApiError extends Error {
  constructor(status, body) {
    const error = (body && body.error) || {};
    super(error.message || `Request failed (${status})`);
    this.status = status;
    this.code = error.code || "error";
    this.fields = error.fields || {};
  }
}

function csrfToken() {
  // Django puts the CSRF token in a cookie; unsafe requests must echo it in a header.
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api(url, { method = "GET", body, signal } = {}) {
  const response = await fetch(url, {
    method,
    signal,
    credentials: "same-origin",
    headers: {
      Accept: "application/json",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...(method !== "GET" ? { "X-CSRFToken": csrfToken() } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const data = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}

// Call `fn` only after the user has stopped changing things for `ms` milliseconds.
export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

export const prefersReducedMotion = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
