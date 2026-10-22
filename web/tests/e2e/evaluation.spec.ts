import { evaluations } from "../fixtures";
import { expect, expectAccessible, test } from "./support";

const latest = evaluations().run;

test.describe("evaluation", () => {
  test("compares the workflow with the baseline on the latest run", async ({ page }) => {
    await page.goto("/evaluation");

    await expect(page.getByRole("heading", { name: "Evaluation", level: 1 })).toBeVisible();
    await expect(page.getByRole("heading", { name: latest.title })).toBeVisible();
    const headlines = page.getByRole("region", { name: "Headline results" });
    await expect(headlines.getByRole("heading", { name: "Right action" })).toBeVisible();
    await expect(headlines).toContainText(
      `${latest.correct.workflow.value} of ${latest.correct.workflow.total}`,
    );
    await expect(headlines).toContainText(
      `${latest.unsafe.baseline.value} of ${latest.unsafe.baseline.total}`,
    );
    await expect(page.getByText(/exact McNemar test/)).toBeVisible();
    await expect(page.getByRole("heading", { name: "Cases either system got wrong" })).toBeVisible();
    await expect(page.getByRole("cell", { name: latest.misses[0].case_id })).toBeVisible();
  });

  test("is reachable from the main navigation and accessible", async ({ page }) => {
    await page.goto("/cases");

    await page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Evaluation" }).click();

    await expect(page).toHaveURL(/\/evaluation$/);
    await expect(page.getByRole("region", { name: "Headline results" })).toBeVisible();
    await expectAccessible(page);
  });
});
