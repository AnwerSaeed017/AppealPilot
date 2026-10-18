import type { NextRequest } from "next/server";

import { caseEventsUrl } from "@/lib/api/client";

/**
 * Relays a case's live event stream from the API to the browser.
 *
 * The browser only ever talks to this app, so the API's address stays on the server and
 * no cross-origin access is needed. The stream is passed through as it arrives.
 */
export async function GET(request: NextRequest, context: RouteContext<"/api/cases/[id]/events">) {
  const { id } = await context.params;
  let upstream: Response;
  try {
    upstream = await fetch(caseEventsUrl(id), {
      headers: { accept: "text/event-stream" },
      signal: request.signal,
    });
  } catch {
    return new Response("The AppealPilot service could not be reached.", { status: 502 });
  }
  if (!upstream.ok || upstream.body === null) {
    return new Response(null, { status: upstream.status === 404 ? 404 : 502 });
  }
  return new Response(upstream.body, {
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
      "x-accel-buffering": "no",
    },
  });
}
