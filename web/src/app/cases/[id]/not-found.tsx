import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function CaseNotFound() {
  return (
    <div className="flex flex-col items-center gap-3 py-24 text-center">
      <h1 className="text-xl font-semibold">Case not found</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        There is no case with this ID. It may have been mistyped, or it belongs to a different database.
      </p>
      <Button asChild variant="outline">
        <Link href="/cases">Back to all cases</Link>
      </Button>
    </div>
  );
}
