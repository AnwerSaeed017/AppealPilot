// A stand-in for the AppealPilot API, for end-to-end tests of the web app.
//
// It serves the fixtures in tests/fixtures (built from the API's own schemas), answers
// with the API's envelope, and plays a new run's steps over server-sent events the way
// the API does. POST /__reset restores the fixtures between tests.
import { readFileSync } from "node:fs";
import { createServer } from "node:http";

const PORT = Number(process.env.MOCK_API_PORT ?? 8765);
const STEP_DELAY_MS = Number(process.env.MOCK_STEP_DELAY_MS ?? 120);
const fixtures = new URL("../../fixtures/", import.meta.url);

function load(name) {
  return JSON.parse(readFileSync(new URL(name, fixtures), "utf-8"));
}

let views;
let samples;
let evaluations;
let runSteps;
let created;

function reset() {
  views = new Map(load("cases.json").map((view) => [view.summary.case_id, view]));
  samples = load("samples.json");
  evaluations = load("evaluations.json");
  runSteps = load("run-events.json");
  created = 0;
}
reset();

const clone = (value) => structuredClone(value);

function envelope(data) {
  return { success: true, data, error: null, meta: { timestamp: new Date().toISOString() } };
}

function failure(code, message, details = []) {
  return { success: false, data: null, error: { code, message, details }, meta: { timestamp: new Date().toISOString() } };
}

function send(response, status, body) {
  response.writeHead(status, { "content-type": "application/json" });
  response.end(JSON.stringify(body));
}

async function readJson(request) {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const text = Buffer.concat(chunks).toString("utf-8");
  return text ? JSON.parse(text) : null;
}

function touch(view) {
  view.summary.updated_at = new Date().toISOString();
  if (view.state) view.summary.status = view.state.status;
}

/** A new case starts with no steps; its run is played when someone follows it. */
function startCase(input) {
  created += 1;
  const id = `case-new-${created}`;
  const template = clone(views.get("case-modifier-25"));
  const now = new Date().toISOString();
  const pending = {
    ...template.state,
    case_id: id,
    case_input: input,
    status: "RUNNING",
    audit: [],
  };
  const view = {
    summary: {
      ...template.summary,
      case_id: id,
      claim_id: input.claim.claim_id,
      payer_id: input.claim.payer_id,
      carc_code: input.denial.carc_code,
      status: "RUNNING",
      action: null,
      verified: null,
      created_at: now,
      updated_at: now,
    },
    state: { ...pending, findings: [], clauses: [], note_facts: [], triage: null, draft: null, verification: null, writer_attempts: 0 },
  };
  view.script = { finished: pending, steps: clone(runSteps).map((item) => item.event) };
  views.set(id, view);
  return view;
}

/** The view as the API sends it, without the mock's own bookkeeping. */
function publicView(view) {
  return { summary: view.summary, state: view.state };
}

function sse(response, name, data) {
  response.write(`event: ${name}\ndata: ${JSON.stringify(data)}\n\n`);
}

async function follow(view, request, response) {
  response.writeHead(200, {
    "content-type": "text/event-stream",
    "cache-control": "no-cache",
    connection: "keep-alive",
  });
  let closed = false;
  request.on("close", () => {
    closed = true;
  });
  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  let sequence = 0;
  for (const event of view.state?.audit ?? []) {
    sequence += 1;
    sse(response, "step", { sequence, event });
  }

  const script = view.script;
  if (script) {
    while (script.steps.length > 0 && !closed) {
      await wait(STEP_DELAY_MS);
      const event = script.steps.shift();
      view.state.audit.push(event);
      sequence += 1;
      sse(response, "step", { sequence, event });
      touch(view);
    }
    if (!closed) {
      const audit = view.state.audit;
      view.state = { ...clone(script.finished), audit, status: "AWAITING_APPROVAL" };
      view.summary.action = view.state.triage?.action ?? null;
      view.summary.verified = true;
      delete view.script;
      touch(view);
    }
  }

  if (view.summary.status === "RUNNING") {
    // A run with nothing scripted stays open, as a slow real run would.
    const timer = setInterval(() => response.write(": keep-alive\n\n"), 1000);
    request.on("close", () => clearInterval(timer));
    return;
  }
  if (!closed) {
    sse(response, "status", view.summary);
    response.end();
  }
}

function decide(view, body) {
  if (view.summary.status !== "AWAITING_APPROVAL") {
    return [409, failure("CONFLICT", `Case ${view.summary.case_id} is not waiting for a decision.`)];
  }
  const kind = body?.kind;
  if (!["APPROVE", "EDIT_AND_APPROVE", "REJECT"].includes(kind)) {
    return [422, failure("VALIDATION_FAILED", "The request is not valid.", [{ field: "kind", message: "Input should be 'APPROVE', 'EDIT_AND_APPROVE' or 'REJECT'" }])];
  }
  if (kind === "REJECT" && !body.reason) {
    return [422, failure("VALIDATION_FAILED", "The request is not valid.", [{ field: null, message: "Value error, a reason is required when rejecting" }])];
  }
  const rejected = kind === "REJECT";
  view.state.human_decision = { kind, reason: body.reason ?? null, edited_summary: body.edited_summary ?? null };
  view.state.status = rejected ? "REJECTED" : "APPROVED";
  view.state.audit.push({ step: "approval", at: new Date().toISOString(), summary: `Reviewer decision: ${kind}.`, llm_call: null });
  touch(view);
  return [200, envelope(publicView(view))];
}

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", `http://127.0.0.1:${PORT}`);
  const parts = url.pathname.split("/").filter(Boolean).map(decodeURIComponent);
  try {
    if (request.method === "POST" && url.pathname === "/__reset") {
      reset();
      return send(response, 200, { ok: true });
    }
    if (request.method === "GET" && url.pathname === "/health/live") {
      return send(response, 200, envelope({ status: "ok" }));
    }
    if (request.method === "GET" && url.pathname === "/evaluations") {
      return send(response, 200, envelope(evaluations));
    }
    if (request.method === "GET" && url.pathname === "/samples") {
      return send(response, 200, envelope(samples));
    }
    if (parts[0] === "cases" && parts.length === 1) {
      if (request.method === "GET") {
        const page = Number(url.searchParams.get("page") ?? 1);
        const pageSize = Number(url.searchParams.get("page_size") ?? 20);
        const status = url.searchParams.get("status");
        const items = [...views.values()]
          .map((view) => view.summary)
          .filter((summary) => !status || summary.status === status)
          .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
        return send(response, 200, envelope({ items: items.slice((page - 1) * pageSize, page * pageSize), page, page_size: pageSize, total: items.length }));
      }
      if (request.method === "POST") {
        const body = await readJson(request);
        const missing = ["claim", "denial", "visit_note"].filter((key) => !body || typeof body[key] !== "object");
        if (missing.length > 0) {
          return send(response, 422, failure("VALIDATION_FAILED", "The request is not valid.", missing.map((field) => ({ field, message: "Field required" }))));
        }
        return send(response, 202, envelope(publicView(startCase(body))));
      }
    }
    if (parts[0] === "cases" && parts.length >= 2) {
      const view = views.get(parts[1]);
      if (!view) return send(response, 404, failure("NOT_FOUND", `Case ${parts[1]} does not exist.`));
      if (request.method === "GET" && parts.length === 2) return send(response, 200, envelope(publicView(view)));
      if (request.method === "GET" && parts[2] === "events") return follow(view, request, response);
      if (request.method === "POST" && parts[2] === "decision") {
        const [status, body] = decide(view, await readJson(request));
        return send(response, status, body);
      }
      if (request.method === "POST" && parts[2] === "retry") {
        if (view.summary.status !== "FAILED") {
          return send(response, 409, failure("CONFLICT", `Case ${view.summary.case_id} has no unfinished step to continue.`));
        }
        view.state.status = "RUNNING";
        touch(view);
        return send(response, 202, envelope(publicView(view)));
      }
    }
    send(response, 404, failure("NOT_FOUND", "No such endpoint."));
  } catch (error) {
    console.error(error);
    send(response, 500, failure("INTERNAL_ERROR", "Something went wrong."));
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`mock API listening on http://127.0.0.1:${PORT}`);
});
