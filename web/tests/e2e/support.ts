import AxeBuilder from "@axe-core/playwright";
import { expect, test as base, type Page } from "@playwright/test";

const MOCK_API = "http://127.0.0.1:8765";

/** Every test starts from the fixtures, whatever the test before it changed. */
export const test = base.extend<{ resetApi: void }>({
  resetApi: [
    async ({ request }, use) => {
      await request.post(`${MOCK_API}/__reset`);
      await use();
    },
    { auto: true },
  ],
});

export { expect };

/** Fails on any serious or critical WCAG A/AA violation on the page as it stands. */
export async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const serious = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  const report = serious.map(
    (violation) =>
      `${violation.id}: ${violation.help} -> ${violation.nodes
        .slice(0, 4)
        .map((node) => node.target.join(" "))
        .join(" | ")}`,
  );
  expect(report).toEqual([]);
}
