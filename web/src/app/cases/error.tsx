"use client";

import { ServerCrashIcon } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function CasesError({ error, retry }: { error: unknown; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center gap-3 py-24 text-center" role="alert">
      <ServerCrashIcon className="size-8 text-muted-foreground" aria-hidden="true" />
      <h1 className="text-xl font-semibold">This page could not be loaded</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        The AppealPilot service did not answer as expected. Check that the API is running, then try again.
      </p>
      <Button variant="outline" onClick={() => retry()}>
        Try again
      </Button>
    </div>
  );
}
