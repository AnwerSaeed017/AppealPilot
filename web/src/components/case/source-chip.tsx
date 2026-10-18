"use client";

import { ExternalLinkIcon, FileTextIcon, ScaleIcon, TriangleAlertIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { highlightQuote } from "@/lib/quote";
import type { CitedSource } from "@/lib/sources";
import { cn } from "@/lib/utils";

function Highlighted({ text, quote }: { text: string; quote: string | null }) {
  const mark = useRef<HTMLElement>(null);
  useEffect(() => {
    mark.current?.scrollIntoView({ block: "center" });
  }, []);
  const segments = quote ? highlightQuote(text, quote) : [{ text, highlighted: false }];
  return (
    <p className="text-sm leading-relaxed whitespace-pre-wrap">
      {segments.map((segment, index) =>
        segment.highlighted ? (
          <mark key={index} ref={mark} className="rounded-sm bg-highlight px-0.5 text-foreground">
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </p>
  );
}

/**
 * A reference to a clause or document. Opening it shows the full source beside the draft,
 * with the quoted words highlighted, so a reviewer can check each claim in one click.
 */
export function SourceChip({
  sourceId,
  source,
  quote = null,
  failed = false,
}: {
  sourceId: string;
  source: CitedSource | null;
  quote?: string | null;
  failed?: boolean;
}) {
  const Icon = source?.kind === "document" ? FileTextIcon : ScaleIcon;
  const quoteFound = source !== null && quote !== null && highlightQuote(source.text, quote).some((s) => s.highlighted);
  return (
    <Sheet>
      <SheetTrigger
        className={cn(
          "inline-flex max-w-full items-center gap-1 rounded-md border bg-card px-1.5 py-0.5 font-mono text-[11px] text-foreground transition-colors hover:border-primary/50 hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring",
          failed && "border-danger/40 text-danger",
        )}
        aria-label={`Open source ${sourceId}`}
      >
        <Icon className="size-3 shrink-0" aria-hidden="true" />
        <span className="truncate">{sourceId}</span>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone="outline" className="font-mono">
              {sourceId}
            </Badge>
            {source?.url ? <Badge tone="info">Official source</Badge> : null}
          </div>
          <SheetTitle>{source?.title ?? "Source not found"}</SheetTitle>
          <SheetDescription>
            {source?.subtitle ?? "This citation names a source that is not part of the case."}
          </SheetDescription>
        </SheetHeader>
        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
          {quote ? (
            <figure className="space-y-1.5">
              <figcaption className="text-xs font-medium text-muted-foreground">Quoted</figcaption>
              <blockquote className="border-l-2 border-primary pl-3 text-sm italic">“{quote}”</blockquote>
              {source && !quoteFound ? (
                <p className="flex items-center gap-1.5 text-xs text-danger">
                  <TriangleAlertIcon className="size-3.5" aria-hidden="true" />
                  These words do not appear in the source.
                </p>
              ) : null}
            </figure>
          ) : null}
          {source ? (
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Full text</p>
              <Highlighted text={source.text} quote={quote} />
            </div>
          ) : null}
        </div>
        {source?.url ? (
          <div className="border-t px-6 py-4">
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            >
              Read it at the source <ExternalLinkIcon className="size-3.5" aria-hidden="true" />
            </a>
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}
