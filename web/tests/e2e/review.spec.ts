import { expect, expectAccessible, test } from "./support";

test.describe("reviewing a case", () => {
  test("shows each cited quote highlighted in its source", async ({ page }) => {
    await page.goto("/cases/case-modifier-25");

    await page.getByRole("button", { name: "Open source MEDICARE-MOD-1.1" }).first().click();

    const panel = page.getByRole("dialog");
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("heading", { name: /§30.6.6.B CPT Modifier -25/ })).toBeVisible();
    await expect(panel.locator("mark")).toHaveText("Modifier -25 is added to the E/M code on the claim.");
    await expect(panel.getByRole("link", { name: /Read it at the source/ })).toHaveAttribute(
      "href",
      /cms\.gov\/.*clm104c12\.pdf$/,
    );
    await page.keyboard.press("Escape");
    await expect(panel).toBeHidden();
  });

  test("moves between the case's tabs", async ({ page }) => {
    await page.goto("/cases/case-modifier-25");

    await page.getByRole("tab", { name: /Findings/ }).click();
    await expect(page.getByText("Visit without modifier 25")).toBeVisible();

    await page.getByRole("tab", { name: /Claim/ }).click();
    await expect(page.getByRole("heading", { name: "Visit note" })).toBeVisible();
    await expect(page.getByRole("cell", { name: "99214" })).toBeVisible();

    await page.getByRole("tab", { name: /Audit/ }).click();
    await expect(page.getByText("2 attempts")).toBeVisible();
    await expectAccessible(page);
  });

  test("requires a reason to reject, then records the rejection", async ({ page }) => {
    await page.goto("/cases/case-modifier-25");

    await page.getByText("Reject", { exact: true }).click();
    await page.getByRole("button", { name: "Reject draft" }).click();
    // The browser keeps the form open until a reason is given.
    await expect(page.getByRole("heading", { name: "Your decision" })).toBeVisible();

    await page.getByLabel("Why the draft is rejected").fill("The diabetes review was routine follow-up only.");
    await page.getByRole("button", { name: "Reject draft" }).click();

    await expect(page.getByText("Rejected by the reviewer")).toBeVisible();
    await expect(page.getByText("The diabetes review was routine follow-up only.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Your decision" })).toBeHidden();
  });

  test("approves with the reviewer's own wording", async ({ page }) => {
    await page.goto("/cases/case-bone-density");

    await page.getByText("Edit and approve", { exact: true }).click();
    await page.getByLabel("Your wording of the summary").fill("File a redetermination citing 42 CFR 410.31(c)(2)(i).");
    await page.getByRole("button", { name: "Approve with my edits" }).click();

    await expect(page.getByText("Approved with edits")).toBeVisible();
    await expect(page.getByText("File a redetermination citing 42 CFR 410.31(c)(2)(i).")).toBeVisible();
  });

  test("warns before approving a draft that failed verification", async ({ page }) => {
    await page.goto("/cases/case-bone-density-unverified");

    await expect(page.getByText("1 assertion failed verification")).toBeVisible();
    await expect(page.getByText("3 of 4 assertions verified")).toBeVisible();
    await expect(page.getByText(/Quote not found in MEDICARE-COV-2.1/)).toBeVisible();
  });

  test("retries a failed case from its last step", async ({ page }) => {
    await page.goto("/cases/case-timely-filing");

    await expect(page.getByText("The run stopped on an error")).toBeVisible();
    await expect(page.getByRole("list", { name: "Workflow progress" })).toContainText("Record review: stopped here");

    await page.getByRole("button", { name: "Retry from the last step" }).click();

    await expect(page.getByRole("status")).toContainText(/Live|Connecting/);
    await expect(page.getByText("Working: Record review")).toBeVisible();
    await expect(page.getByText("Running").first()).toBeVisible();
  });
});
