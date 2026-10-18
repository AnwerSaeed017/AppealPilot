import type { ApiErrorDetail } from "./types";

/** A request the API answered with an error, in the API's own terms. */
export class ApiFailure extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: readonly ApiErrorDetail[] = [],
  ) {
    super(message);
    this.name = "ApiFailure";
  }
}

/** The service could not be reached at all. */
export class ApiUnavailable extends Error {
  constructor(cause: unknown) {
    super("The AppealPilot service could not be reached.", { cause });
    this.name = "ApiUnavailable";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Reads the error out of a failed response body.
 *
 * Every endpoint answers with the same envelope, so its `error` is used when present.
 * Anything else, such as a proxy's HTML error page, becomes a generic failure.
 */
export function failureFrom(status: number, body: unknown): ApiFailure {
  const error = isRecord(body) && isRecord(body.error) ? body.error : null;
  if (error && typeof error.code === "string" && typeof error.message === "string") {
    const details = Array.isArray(error.details)
      ? error.details.filter(
          (detail): detail is ApiErrorDetail =>
            isRecord(detail) && typeof detail.message === "string",
        )
      : [];
    return new ApiFailure(status, error.code, error.message, details);
  }
  return new ApiFailure(status, "UNEXPECTED_RESPONSE", `The service answered with HTTP ${status}.`);
}

/** One line per problem, suitable for showing under a form. */
export function describeFailure(failure: ApiFailure): string[] {
  if (failure.details.length === 0) return [failure.message];
  return failure.details.map((detail) =>
    detail.field ? `${detail.field}: ${detail.message}` : detail.message,
  );
}
