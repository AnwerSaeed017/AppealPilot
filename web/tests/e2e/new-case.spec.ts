import { expect, expectAccessible, test } from "./support";

test.describe("new case", () => {
  test("offers the three Medicare samples", async ({ page }) => {
    await page.goto("/cases/new");

    const runButtons = page.getByRole("button", { name: /^Run sample:/ });
    await expect(runButtons).toHaveCount(3);
    await expect(page.getByText("Office visit bundled into a same-day knee injection")).toBeVisible();
    await expect(page.getByText("CO-97", { exact: true })).toBeVisible();
    await expectAccessible(page);
  });

  test("runs a sample and follows it live until it waits for a decision", async ({ page }) => {
    await page.goto("/cases/new");

    await page.getByRole("button", { name: "Run sample: Office visit bundled into a same-day knee injection" }).click();

    await expect(page).toHaveURL(/\/cases\/case-new-1$/);
    await expect(page.getByRole("heading", { name: /Claim MC-2026-0818-0457/ })).toBeVisible();
    // The steps stream in; the page re-renders until the draft is ready for review.
    await expect(page.getByRole("heading", { name: "Your decision" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByText("Needs review").first()).toBeVisible();
    const progress = page.getByRole("list", { name: "Workflow progress" });
    await expect(progress).toContainText("Draft: done");
    await expect(progress).toContainText("Decision: waiting for a reviewer");
  });

  test("rejects text that is not JSON before calling the API", async ({ page }) => {
    await page.goto("/cases/new");

    await page.getByLabel("Case JSON").fill("{ not json");
    await page.getByRole("button", { name: "Submit case" }).click();

    await expect(page.getByText("That is not valid JSON.", { exact: false })).toBeVisible();
    await expect(page.getByLabel("Case JSON")).toHaveAttribute("aria-invalid", "true");
  });

  test("shows the API's own messages for a case it does not accept", async ({ page }) => {
    await page.goto("/cases/new");

    await page.getByLabel("Case JSON").fill("{}");
    await page.getByRole("button", { name: "Submit case" }).click();

    const errors = page.getByRole("alert").filter({ hasText: "The API did not accept this case" });
    await expect(errors).toContainText("claim: Field required");
    await expect(errors).toContainText("visit_note: Field required");
  });
});
