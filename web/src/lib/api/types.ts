/** Names for the API's payloads, taken from the generated OpenAPI types. */
import type { components } from "./schema";

type Schemas = components["schemas"];

export type ApiEnvelope<T> = {
  success: boolean;
  data?: T | null;
  error?: Schemas["ApiError"] | null;
  meta: Schemas["ResponseMeta"];
};

export type CaseStatus = Schemas["CaseStatus"];
export type RecommendedAction = Schemas["RecommendedAction"];
export type CaseSummary = Schemas["CaseSummary"];
export type CasePage = Schemas["CasePage"];
export type CaseView = Schemas["CaseView"];
export type CaseState = Schemas["CaseState"];
export type CaseInput = Schemas["CaseInput-Output"];
export type CaseInputSubmission = Schemas["CaseInput-Input"];
export type Claim = Schemas["Claim-Output"];
export type ClaimLine = Schemas["ClaimLine-Output"];
export type Denial = Schemas["Denial-Output"];
export type SupportingDocument = Schemas["SupportingDocument-Output"];
export type PriorClaim = Schemas["PriorClaim-Output"];
export type VisitNote = Schemas["VisitNote"];
export type AuditEvent = Schemas["AuditEvent"];
export type LlmCallRecord = Schemas["LlmCallRecord"];
export type Finding = Schemas["Finding"];
export type FindingCode = Schemas["FindingCode"];
export type CaseClause = Schemas["CaseClause"];
export type ClauseOrigin = Schemas["ClauseOrigin"];
export type PolicyClause = Schemas["PolicyClause"];
export type NoteFact = Schemas["NoteFact"];
export type TriageDecision = Schemas["TriageDecision"];
export type Draft = Schemas["Draft"];
export type Assertion = Schemas["Assertion"];
export type Citation = Schemas["Citation"];
export type VerificationReport = Schemas["VerificationReport"];
export type AssertionVerdict = Schemas["AssertionVerdict"];
export type HumanDecision = Schemas["HumanDecision"];
export type HumanDecisionKind = Schemas["HumanDecisionKind"];
export type SampleCase = Schemas["SampleCase"];
export type ApiErrorDetail = Schemas["ErrorDetail"];
export type EvaluationBenchmarks = Schemas["EvaluationBenchmarks"];
export type EvaluationRun = Schemas["EvaluationRun"];
export type Tally = Schemas["Tally"];
export type TallyPair = Schemas["TallyPair"];
export type NumberPair = Schemas["NumberPair"];
export type ActionResult = Schemas["ActionResult"];
export type CaseOutcome = Schemas["CaseOutcome"];
export type PlantedErrorResult = Schemas["PlantedErrorResult"];
