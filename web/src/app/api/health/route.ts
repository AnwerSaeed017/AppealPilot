/**
 * Liveness for the web app alone, for a platform's health check. It does not call the
 * API, so a slow API cannot get the web app restarted.
 */
export function GET() {
  return Response.json({ status: "ok" });
}
