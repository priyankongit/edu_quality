import { boot } from "./boot";

export class FrappeError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

type Args = Record<string, unknown>;

let csrf = boot.csrf_token || "";

/** The session endpoint returns a fresh token; keep it so writes also work under `vite dev`. */
export function setCsrfToken(token?: string) {
  if (token) csrf = token;
}

function stripHtml(text: string) {
  // DOMParser never runs scripts or loads images, unlike innerHTML on a live element.
  const doc = new DOMParser().parseFromString(text, "text/html");
  return doc.body.textContent?.trim() || text;
}

function errorMessage(data: Record<string, unknown>, status: number) {
  if (typeof data._server_messages === "string") {
    try {
      const messages = (JSON.parse(data._server_messages) as string[]).map(
        (m) => (JSON.parse(m) as { message: string }).message,
      );
      if (messages.length) return stripHtml(messages.join("\n"));
    } catch {
      // fall through to the generic messages below
    }
  }
  if (typeof data.message === "string" && data.message) return stripHtml(data.message);
  if (status === 401 || status === 403) return "You don't have access to this. Try signing in again.";
  if (status >= 500) return "The server ran into a problem. Try again in a moment.";
  return "Something went wrong. Check your connection and try again.";
}

/** Call a whitelisted Frappe method and return its `message`. */
export async function call<T>(
  method: string,
  args?: Args,
  { http = "POST" }: { http?: "GET" | "POST" } = {},
): Promise<T> {
  let url = `/api/method/${method}`;
  const headers: Record<string, string> = { Accept: "application/json" };
  const init: RequestInit = { method: http, credentials: "same-origin", headers };

  if (http === "GET") {
    if (args) {
      const params = new URLSearchParams();
      for (const [key, value] of Object.entries(args)) {
        if (value === undefined || value === null) continue;
        params.set(key, typeof value === "string" ? value : JSON.stringify(value));
      }
      url += `?${params}`;
    }
  } else {
    headers["Content-Type"] = "application/json";
    headers["X-Frappe-CSRF-Token"] = csrf;
    init.body = JSON.stringify(args ?? {});
  }

  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new FrappeError("You're offline. Check your connection and try again.", 0);
  }
  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) throw new FrappeError(errorMessage(data, res.status), res.status);
  return data.message as T;
}

export async function login(usr: string, pwd: string) {
  try {
    await call("login", { usr, pwd });
  } catch (err) {
    if (err instanceof FrappeError && err.status === 401) {
      throw new FrappeError("That email or password isn't right.", 401);
    }
    throw err;
  }
  // Reload so the server renders a fresh CSRF token for the new session.
  window.location.replace("/school/");
}

export async function logout() {
  await call("logout").catch(() => undefined);
  window.location.replace("/school/");
}

/** Files attached in Frappe are site-relative; make sure they resolve from /school routes. */
export function fileUrl(path?: string | null) {
  if (!path) return "";
  if (/^(https?:|data:|blob:)/.test(path)) return path;
  return path.startsWith("/") ? path : `/${path}`;
}
