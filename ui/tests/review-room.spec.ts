import { expect, test } from "@playwright/test";

test("review room exposes interactive visual inspector controls", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Shoulder Kitten" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("heading", { name: "Qa" })).toBeVisible();
  await expect(page.getByLabel("Visual artifact canvas")).toBeVisible();
  await expect(page.getByLabel("Project directory")).toBeVisible();

  await page.getByRole("button", { name: "Toggle compare mode" }).click();
  await expect(page.getByText("Reference overlay")).toBeVisible();

  await page.getByLabel("Zoom level").fill("1.25");
  await expect(page.getByText("125%")).toBeVisible();

  await page.getByRole("button", { name: "Style" }).click();
  await expect(page.getByRole("heading", { name: "Style Studio" })).toBeVisible();
  await page.getByRole("button", { name: "anime" }).click();
  await expect(page.getByRole("button", { name: "anime" })).toHaveClass(/active/);

  await page.getByRole("button", { name: "Toggle inspector" }).click();
  await expect(page.getByLabel("Inspector panel")).not.toBeVisible();
  await page.getByRole("button", { name: "Toggle inspector" }).click();
  await expect(page.getByLabel("Inspector panel")).toBeVisible();

  await page.keyboard.press("Meta+K");
  await expect(page.getByPlaceholder("Search Goodboy actions...")).toBeVisible();
  await page.getByText("Open QA Review").click();
  await expect(page.getByRole("heading", { name: "QA Review" })).toBeVisible();
});

test("demo refresh is safe and recorded without a backend", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Refresh project state" }).click();
  await page.getByRole("button", { name: "Toggle activity drawer" }).click();

  await expect(page.getByRole("complementary", { name: "Activity drawer" })).toContainText("Demo refreshed");
});

test("approval interaction updates gate and activity", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Approve visual review" }).click();
  await expect(page.getByRole("banner").getByText("Export Or Install")).toBeVisible();
  await expect(page.getByLabel("Inspector panel").getByText("Ready", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Toggle activity drawer" }).click();
  await expect(page.getByRole("complementary", { name: "Activity drawer" })).toContainText("Approval recorded");
});
