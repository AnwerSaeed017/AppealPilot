import {
  BookOpenIcon,
  ChevronRightIcon,
  FileSearchIcon,
  ListChecksIcon,
  PenLineIcon,
  ShieldCheckIcon,
  UserCheckIcon,
} from "lucide-react";

const STAGES = [
  { icon: ListChecksIcon, title: "Rules", text: "Deadlines, modifiers, duplicates" },
  { icon: BookOpenIcon, title: "Policy", text: "The payer's own clauses" },
  { icon: FileSearchIcon, title: "Record", text: "Quoted facts from the note" },
  { icon: PenLineIcon, title: "Draft", text: "Every claim cited" },
  { icon: ShieldCheckIcon, title: "Verify", text: "Each quote checked" },
  { icon: UserCheckIcon, title: "You decide", text: "Nothing leaves without you" },
];

/** What happens to a case, shown once at the top of the page where cases start. */
export function PipelineHero() {
  return (
    <section
      aria-labelledby="pipeline-heading"
      className="relative overflow-hidden rounded-2xl bg-brand px-6 py-7 text-brand-foreground shadow-md sm:px-8"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-24 -right-24 size-72 rounded-full bg-primary/40 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-28 left-1/3 size-72 rounded-full bg-cta/20 blur-3xl"
      />
      <div className="relative space-y-6">
        <div className="max-w-2xl space-y-2">
          <h2 id="pipeline-heading" className="text-xl font-semibold tracking-tight text-balance sm:text-2xl">
            From a denial to a verified, cited response
          </h2>
          <p className="text-sm text-brand-muted text-pretty">
            Each case runs through the same six steps. Facts come from the claim and the record, every sentence
            in the draft points to the exact words it rests on, and a person makes the final call.
          </p>
        </div>
        <ol className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {STAGES.map((stage, index) => {
            const Icon = stage.icon;
            return (
              <li key={stage.title} className="relative flex items-center gap-2">
                <div className="flex w-full items-start gap-2.5 rounded-xl bg-white/8 p-3 ring-1 ring-white/10">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-white/12">
                    <Icon className="size-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium">
                      <span className="sr-only">Step {index + 1}: </span>
                      {stage.title}
                    </p>
                    <p className="text-xs text-brand-muted">{stage.text}</p>
                  </div>
                </div>
                {index < STAGES.length - 1 ? (
                  <ChevronRightIcon className="hidden size-4 shrink-0 text-brand-muted lg:block" aria-hidden="true" />
                ) : null}
              </li>
            );
          })}
        </ol>
      </div>
    </section>
  );
}
