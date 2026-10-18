"use client";

import { LoaderCircleIcon } from "lucide-react";

import { Button, type ButtonProps } from "@/components/ui/button";

/** A button that shows a spinner and blocks double submits while its action runs. */
export function PendingButton({
  pending,
  pendingLabel,
  children,
  disabled,
  ...props
}: ButtonProps & { pending: boolean; pendingLabel?: string }) {
  return (
    <Button disabled={pending || disabled} aria-busy={pending} {...props}>
      {pending ? (
        <>
          <LoaderCircleIcon className="animate-spin" aria-hidden="true" />
          {pendingLabel ?? children}
        </>
      ) : (
        children
      )}
    </Button>
  );
}
