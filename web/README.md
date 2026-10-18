# AppealPilot web

The reviewer's interface: a case list, a page to start a case, and a case view where a
person checks the cited draft, source by source, and approves, edits or rejects it.

Next.js 16 (App Router, Cache Components), React 19, TypeScript, Tailwind CSS 4, Radix
primitives.

## Run

Requires Node 20.9 or later and the API running (see the repository README).

```
npm install
npm run dev            # http://localhost:3000
```

The app reads one setting, `API_URL`, on the server only (default
`http://127.0.0.1:8000`). The browser never calls the API directly.

To look at the app without the backend, run the mock API (`npm run mock-api`, port 8765)
and start the app with `API_URL=http://127.0.0.1:8765` (PowerShell:
`$env:API_URL = "http://127.0.0.1:8765"; npm run dev`).

## Scripts

| Script | Does |
|---|---|
| `npm run dev` | Development server |
| `npm run build` / `npm start` | Production build and server |
| `npm run lint` | ESLint |
| `npm run typecheck` | Generates route types, then `tsc --noEmit` |
| `npm test` | Unit and component tests (Vitest, Testing Library) |
| `npm run test:e2e` | End-to-end tests (Playwright) against a production build and a mock API |
| `npm run api:types` | Regenerates `src/lib/api/schema.d.ts` from `openapi.json` |
| `npm run check` | Lint, types and unit tests |

`E2E_DEV=1 npm run test:e2e` runs the end-to-end tests against `next dev` instead.

## When the API changes

The types and the test fixtures come from the API, never by hand. From the repository root:

```
uv run python -m scripts.export_openapi       # writes web/openapi.json
uv run python -m scripts.build_web_fixtures   # writes web/tests/fixtures/*.json
cd web && npm run api:types                   # writes src/lib/api/schema.d.ts
```

CI regenerates all three and fails if anything changed, so a schema change cannot reach
the web app unnoticed.

## Layout

```
src/
  app/                 routes: /cases, /cases/new, /cases/[id]; Server Actions; event relay
  components/          domain components (case/, cases/, samples/) and ui/ primitives
  lib/
    api/               server-only API client, generated types, error envelope
    labels.ts          wording for every code the API returns
    format.ts          money, dates, durations (fixed locale and UTC)
    quote.ts           finds a citation's quote in its source, as the API's check does
    sources.ts         resolves a citation to the clause or document it names
    progress.ts        where each workflow step stands
tests/
  unit/                Vitest: lib functions and components
  e2e/                 Playwright specs, accessibility checks, mock API
  fixtures/            API responses built from the API's schemas
```
