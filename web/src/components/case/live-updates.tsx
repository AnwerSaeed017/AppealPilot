"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

type Connection = "connecting" | "live" | "reconnecting";

/** How long to gather step events before re-rendering the page once for all of them. */
const REFRESH_DELAY_MS = 250;

/**
 * Follows a running case. Each step the workflow records arrives as a server-sent event;
 * the page is then re-rendered on the server, so what is shown always comes from the
 * API's saved state. The stream ends with a `status` event when the run stops.
 */
export function LiveUpdates({ caseId }: { caseId: string }) {
  const router = useRouter();
  const [connection, setConnection] = useState<Connection>("connecting");

  useEffect(() => {
    const source = new EventSource(`/api/cases/${encodeURIComponent(caseId)}/events`);
    let timer: ReturnType<typeof setTimeout> | undefined;

    const refreshSoon = () => {
      if (timer !== undefined) return;
      timer = setTimeout(() => {
        timer = undefined;
        router.refresh();
      }, REFRESH_DELAY_MS);
    };

    source.addEventListener("open", () => setConnection("live"));
    source.addEventListener("step", refreshSoon);
    source.addEventListener("status", () => {
      source.close();
      router.refresh();
    });
    // EventSource reconnects by itself; the replayed steps only trigger one refresh.
    source.addEventListener("error", () => setConnection("reconnecting"));

    return () => {
      source.close();
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [caseId, router]);

  const label = connection === "live" ? "Live" : connection === "connecting" ? "Connecting" : "Reconnecting";
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border bg-card px-2.5 py-1 text-xs font-medium"
      role="status"
      aria-live="polite"
    >
      <span
        aria-hidden="true"
        className={cn(
          "size-2 rounded-full",
          connection === "live" ? "animate-pulse bg-success" : "bg-warning",
        )}
      />
      {label}
    </span>
  );
}
