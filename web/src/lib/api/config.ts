import "server-only";

const DEFAULT_API_URL = "http://127.0.0.1:8000";

/**
 * Where the AppealPilot API runs. Read on the server only: the browser never calls the
 * API directly, so its address is never sent to the client.
 */
export function apiUrl(): string {
  return (process.env.API_URL ?? DEFAULT_API_URL).replace(/\/+$/, "");
}
