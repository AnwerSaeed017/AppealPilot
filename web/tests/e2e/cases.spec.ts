import { expect, expectAccessible, test } from "./support";

test.describe("case list", () => {
  test("lists every case with its status, action and verification", async ({ page }) => {
    await page.goto("/cases");

    await expect(page.getByRole("heading", { name: "Cases", level: 1 })).toBeVisible();
    const rows = page.getByRole("row");
    await expect(rows).toHaveCount(9); // header + 8 fixture cases
    await expect(page.getByRole("cell", { name: /MC-2026-0818-0457/ }).first()).toBeVisible();
    await expect(page.getByText("Needs review").first()).toBeVisible();
    await expect(page.getByText("Unverified").first()).toBeVisible();
  });

  test("filters by status through the URL", async ({ page }) => {
    await page.goto("/cases");

    await page.getByRole("navigation", { name: "Filter by status" }).getByRole("link", { name: "Failed" }).click();

    await expect(page).toHaveURL(/status=FAILED/);
    await expect(page.getByRole("row")).toHaveCount(2);
    await expect(
      page.getByRole("navigation", { name: "Filter by status" }).getByRole("link", { name: "Failed" }),
    ).toHaveAttribute("aria-current", "page");
  });

  test("counts the queue and opens the next case waiting for review", async ({ page }) => {
    await page.goto("/cases");

    const queue = page.getByRole("region", { name: "Queue" });
    await expect(queue).toContainText(/Needs review\D*4/);
    await expect(queue).toContainText(/Failed\D*1/);

    await queue.getByRole("link", { name: /Review next/ }).click();

    await expect(page.getByRole("heading", { name: "Your decision" })).toBeVisible();
  });

  test("opens a case from its row", async ({ page }) => {
    await page.goto("/cases?status=AWAITING_APPROVAL");

    await page.getByRole("link", { name: "MC-2026-0818-0457" }).click();

    await expect(page).toHaveURL(/\/cases\/case-modifier-25$/);
    await expect(page.getByRole("heading", { name: /Claim MC-2026-0818-0457/ })).toBeVisible();
  });

  test("has no serious accessibility problems", async ({ page }) => {
    await page.goto("/cases");
    await expect(page.getByRole("table")).toBeVisible();
    await expectAccessible(page);
  });

  test("fits a phone screen @mobile", async ({ page }) => {
    await page.goto("/cases");
    await expect(page.getByRole("table")).toBeVisible();

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });

  test("explains a case that has no saved workflow state instead of waiting for it", async ({ page }) => {
    await page.goto("/cases/case-without-state");

    await expect(page.getByText("No workflow record for this case")).toBeVisible();
    await expect(page.getByText("Starting the workflow…")).toBeHidden();
  });

  test("shows a clear page for an unknown case", async ({ page }) => {
    await page.goto("/cases/does-not-exist");

    await expect(page.getByRole("heading", { name: "Case not found" })).toBeVisible();
  });
});
