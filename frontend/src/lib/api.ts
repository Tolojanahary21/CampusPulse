export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"
).replace(/\/$/, "");
export class ApiError extends Error {
  status: number;
  retryAfterSeconds?: number;
  constructor(status: number, message: string, retryAfterSeconds?: number) {
    super(message);
    this.status = status;
    this.retryAfterSeconds = retryAfterSeconds;
    this.name = "ApiError";
  }
}
export function csrfToken(cookie: string) {
  const cookies = cookie.split(";").map((value) => value.trim());
  const csrfCookie =
    cookies.find((value) => value.startsWith("__Host-campuspulse_csrf=")) ??
    cookies.find((value) => value.startsWith("campuspulse_csrf="));
  return csrfCookie?.slice(csrfCookie.indexOf("=") + 1) || "";
}
export async function api<T = Record<string, unknown>>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (
    typeof document !== "undefined" &&
    !["GET", "HEAD"].includes((options.method || "GET").toUpperCase())
  ) {
    const token = csrfToken(document.cookie);
    if (token) headers.set("X-CSRF-Token", decodeURIComponent(token));
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      credentials: "include",
    });
  } catch {
    throw new ApiError(
      0,
      "Connexion au serveur impossible. Vérifiez votre connexion puis réessayez.",
    );
  }
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? detail
          .map(
            (e: { loc?: string[]; msg?: string }) =>
              `${e.loc?.slice(1).join(".") || "Champ"} : ${e.msg || "valeur invalide"}`,
          )
          .join(" · ")
      : typeof detail === "string"
        ? detail
        : "La demande n’a pas pu aboutir.";
    if (
      response.status === 401 &&
      typeof window !== "undefined" &&
      !path.startsWith("/auth/")
    )
      window.dispatchEvent(new Event("session-expired"));
    const retryAfterHeader = response.headers.get("Retry-After");
    const retryAfterSeconds = retryAfterHeader ? Number(retryAfterHeader) : undefined;
    throw new ApiError(
      response.status,
      message,
      Number.isFinite(retryAfterSeconds) ? retryAfterSeconds : undefined,
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
export function mutate<T = Record<string, unknown>>(
  path: string,
  method: string,
  data?: unknown,
) {
  return api<T>(path, {
    method,
    body: data === undefined ? undefined : JSON.stringify(data),
  });
}
