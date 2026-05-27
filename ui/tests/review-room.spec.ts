import { expect, test } from "@playwright/test";

async function startDemo(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await page.getByRole("button", { name: /Explore demo/ }).click();
}

test("onboarding explains the paths into review room", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create with Codex/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Open a project/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore demo/ })).toBeVisible();
  await page.getByRole("button", { name: /Create with Codex/ }).click();
  await expect(page.getByRole("button", { name: "Copy Codex prompt" })).toBeVisible();

  await page.getByRole("button", { name: /Open a project/ }).click();
  await expect(page.getByLabel("Project directory")).toBeVisible();
});

test("review room exposes interactive visual inspector controls", async ({ page }) => {
  await startDemo(page);
  await page.getByRole("button", { name: "QA", exact: true }).click();

  await expect(page.getByRole("heading", { name: "Shoulder Kitten" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("heading", { name: "Qa" })).toBeVisible();
  await expect(page.getByLabel("Visual artifact canvas")).toBeVisible();
  await expect(page.getByRole("banner").getByText("Decision needed: visual QA")).toBeVisible();
  await expect(page.getByLabel("Project progress")).toContainText("Current step");
  await expect(page.getByLabel("Project progress")).toContainText("QA Review");

  await page.getByRole("button", { name: "Toggle compare mode" }).click();
  await expect(page.getByText("Reference overlay")).toBeVisible();

  await page.getByLabel("Zoom level").fill("1.25");
  await expect(page.getByText("125%")).toBeVisible();

  await page.getByRole("navigation", { name: "Review stages" }).getByRole("button", { name: "Style" }).click();
  await expect(page.getByRole("heading", { name: "Style Studio" })).toBeVisible();
  await page.getByRole("button", { name: "anime" }).click();
  await expect(page.getByRole("button", { name: "anime" })).toHaveClass(/active/);

  await page.getByRole("button", { name: "Toggle inspector" }).click();
  await expect(page.getByLabel("Inspector panel")).not.toBeVisible();
  await page.getByRole("button", { name: "Toggle inspector" }).click();
  await expect(page.getByLabel("Inspector panel")).toBeVisible();

  await page.getByRole("button", { name: "Back to start" }).first().click();
  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await page.getByRole("button", { name: /Explore demo/ }).click();
  await page.getByRole("button", { name: "QA", exact: true }).click();

  await page.keyboard.press("Meta+K");
  await expect(page.getByPlaceholder("Search Goodboy actions...")).toBeVisible();
  await page.getByText("Open QA Review").click();
  await expect(page.getByRole("heading", { name: "QA Review" })).toBeVisible();
});

test("demo refresh is safe and recorded without a backend", async ({ page }) => {
  await startDemo(page);

  await page.getByRole("button", { name: "Refresh project state" }).click();
  await page.getByRole("button", { name: "Toggle activity drawer" }).click();

  await expect(page.getByRole("complementary", { name: "Activity drawer" })).toContainText("Demo refreshed");
});

test("approval interaction updates gate and activity", async ({ page }) => {
  await startDemo(page);
  await page.getByRole("button", { name: "QA", exact: true }).click();

  await page.getByRole("button", { name: "Approve visual review" }).click();
  await expect(page.getByRole("banner").getByText("Ready to export")).toBeVisible();
  await expect(page.getByLabel("Inspector panel").getByText("Ready", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Toggle activity drawer" }).click();
  await expect(page.getByRole("complementary", { name: "Activity drawer" })).toContainText("Approval recorded");
});
