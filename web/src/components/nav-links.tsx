"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/cases", label: "Cases" },
  { href: "/cases/new", label: "New case" },
  { href: "/evaluation", label: "Evaluation" },
] as const;

/** The links with the current page marked. Reads the URL, so it renders behind Suspense. */
export function NavLinks() {
  return <NavLinkList pathname={usePathname()} />;
}

/** The links alone; with no pathname nothing is marked, which is the prerendered shell. */
export function NavLinkList({ pathname }: { pathname: string | null }) {
  return (
    <nav aria-label="Main" className="flex items-center gap-1">
      {LINKS.map((link) => {
        const active =
          pathname !== null &&
          (pathname === link.href ||
            (link.href === "/cases" && pathname.startsWith("/cases/") && pathname !== "/cases/new"));
        return (
          <Link
            key={link.href}
            href={link.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "rounded-md px-2 py-1.5 text-sm font-medium whitespace-nowrap sm:px-3 text-brand-muted transition-colors hover:bg-white/10 hover:text-brand-foreground focus-visible:outline-2 focus-visible:outline-brand-foreground",
              active && "bg-white/15 text-brand-foreground",
            )}
          >
            {link.label}
          </Link>
        );
      })}
    </nav>
  );
}
