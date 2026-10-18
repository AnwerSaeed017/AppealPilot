import { ShieldCheckIcon } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { NavLinkList, NavLinks } from "./nav-links";

function Mark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-7">
      <rect width="24" height="24" rx="7" className="fill-brand-foreground" />
      <path
        d="M7 16.5 11.2 7h1.6l4.2 9.5M8.7 13h6.6"
        className="stroke-brand"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AppHeader() {
  return (
    <header className="sticky top-0 z-40 bg-brand text-brand-foreground shadow-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6 lg:px-8">
        <Link
          href="/cases"
          className="flex items-center gap-2.5 rounded-md font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-brand-foreground"
        >
          <Mark />
          <span className="text-[15px]">AppealPilot</span>
        </Link>
        <Suspense fallback={<NavLinkList pathname={null} />}>
          <NavLinks />
        </Suspense>
        <p className="ml-auto hidden items-center gap-1.5 text-xs text-brand-muted md:flex">
          <ShieldCheckIcon className="size-3.5" aria-hidden="true" />
          Every draft is verified and waits for your approval
        </p>
      </div>
    </header>
  );
}
