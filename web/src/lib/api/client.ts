import "server-only";

import createClient from "openapi-fetch";

import { apiUrl } from "./config";
import { ApiFailure, ApiUnavailable, failureFrom } from "./errors";
import type { paths } from "./schema";
import type {
  ApiEnvelope,
  CasePage,
  CaseStatus,
  CaseView,
  HumanDecision,
  SampleCase,
} from "./types";

/**
 * The data access layer: every call the web app makes to the API goes through here, on
 * the server. Pages and Server Actions use these functions, never `fetch` directly.
 */

const REQUEST_TIMEOUT_MS = 15_000;

function client() {
  return createClient<paths>({
    baseUrl: apiUrl(),
    fetch: (request: Request) => fetch(request, { signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) }),
  });
}

type Outcome<T> = { data?: ApiEnvelope<T>; error?: unknown; response: Response };

async function call<T>(request: () => Promise<Outcome<T>>): Promise<T> {
  let outcome: Outcome<T>;
  try {
    outcome = await request();
  } catch (cause) {
    throw new ApiUnavailable(cause);
  }
  const { data, error, response } = outcome;
  if (!response.ok || data === undefined) {
    throw failureFrom(response.status, error ?? data);
  }
  if (!data.success || data.data == null) {
    throw failureFrom(response.status, data);
  }
  return data.data;
}

/** The value, or null when the API says it does not exist. */
async function orNotFound<T>(request: Promise<T>): Promise<T | null> {
  try {
    return await request;
  } catch (error) {
    if (error instanceof ApiFailure && error.status === 404) return null;
    throw error;
  }
}

export function listCases(page: number, pageSize: number, status?: CaseStatus): Promise<CasePage> {
  return call(() =>
    client().GET("/cases", {
      params: { query: { page, page_size: pageSize, status: status ?? null } },
    }),
  );
}

export function getCase(caseId: string): Promise<CaseView | null> {
  return orNotFound(
    call(() => client().GET("/cases/{case_id}", { params: { path: { case_id: caseId } } })),
  );
}

export function listSamples(): Promise<SampleCase[]> {
  return call(() => client().GET("/samples"));
}

export function submitCase(input: unknown): Promise<CaseView> {
  // The body is checked by the API, which owns every field rule; it is passed through
  // as it came so the API's own messages reach the user.
  return call(() =>
    client().POST("/cases", { body: input as paths["/cases"]["post"]["requestBody"]["content"]["application/json"] }),
  );
}

export function decideCase(caseId: string, decision: HumanDecision): Promise<CaseView> {
  return call(() =>
    client().POST("/cases/{case_id}/decision", {
      params: { path: { case_id: caseId } },
      body: decision,
    }),
  );
}

export function retryCase(caseId: string): Promise<CaseView> {
  return call(() =>
    client().POST("/cases/{case_id}/retry", { params: { path: { case_id: caseId } } }),
  );
}

/** The live event stream of a case, as the API sends it. */
export function caseEventsUrl(caseId: string): string {
  return `${apiUrl()}/cases/${encodeURIComponent(caseId)}/events`;
}
