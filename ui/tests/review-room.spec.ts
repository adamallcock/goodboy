import { expect, test } from "@playwright/test";

async function startDemo(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await page.getByRole("button", { name: /Explore companion demo/ }).click();
}

test("onboarding explains the paths into review room", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Create with Codex/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Open a project/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Explore companion demo/ })).toBeVisible();
  await page.getByRole("button", { name: /Create with Codex/ }).click();
  await expect(page.getByRole("button", { name: "Copy Codex prompt" })).toBeVisible();

  await page.getByRole("button", { name: /Open a project/ }).click();
  await expect(page.getByLabel("Project directory")).toBeVisible();
});

test("review room defaults to a focused decision surface", async ({ page }) => {
  await startDemo(page);
  await page.getByRole("button", { name: /Baselines/ }).click();
  await page.getByRole("button", { name: /Style/ }).click();
  await page.getByRole("button", { name: /Generate/ }).click();
  await page.getByRole("button", { name: /QA Review/ }).click();

  await expect(page.getByRole("heading", { name: "Companion Demo" })).toBeVisible();
  await expect(page.getByRole("main").getByRole("heading", { name: "QA Review" })).toBeVisible();
  await expect(page.getByRole("banner").getByText("Decision needed: visual QA")).toBeVisible();
  await expect(page.getByLabel("Project progress")).toContainText("Current step");
  await expect(page.getByLabel("Project progress")).toContainText("QA Review");

  await expect(page.getByTestId("sprite-state-viewer")).toBeVisible();
  await expect(page.getByTestId("sprite-state-viewer")).toContainText("Idle");
  await expect(page.getByTestId("sprite-state-viewer")).toContainText("6 frames");
  await expect(page.getByLabel("Generated files")).not.toBeVisible();
  await expect(page.getByLabel("Review Room walkthrough guide")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Toggle compare mode" })).not.toBeVisible();
  await expect(page.getByLabel("Zoom level")).not.toBeVisible();

  await page.getByRole("button", { name: "Run Right Row 1, 8 frames" }).click();
  await expect(page.getByTestId("sprite-state-viewer")).toContainText("Run Right");
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute("data-state", "running-right");
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute("data-row", "1");
  await expect(page.getByTestId("sprite-state-animation")).toHaveAttribute("data-frame-count", "8");
  await expect(page.getByTestId("sprite-state-animation")).toHaveCSS("animation-timing-function", "steps(8)");

  await page.getByRole("button", { name: "Open large preview" }).click();
  await expect(page.getByRole("dialog", { name: "Large artifact preview" })).toBeVisible();
  await page.getByRole("button", { name: "Toggle compare mode" }).click();
  await expect(page.getByText("Reference overlay")).toBeVisible();

  await page.getByLabel("Zoom level").fill("1.25");
  await expect(page.getByText("125%")).toBeVisible();
  await page.getByRole("button", { name: "Close preview" }).click();

  await page.keyboard.press("Meta+K");
  await page.getByText("Open Style Studio").click();
  await expect(page.getByRole("heading", { name: "Style Studio" })).toBeVisible();
  await page.getByRole("button", { name: "anime" }).click();
  await expect(page.getByRole("button", { name: "anime" })).toHaveClass(/active/);

  await page.getByRole("button", { name: "Open details" }).click();
  await expect(page.getByLabel("Generated files")).toBeVisible();
  await expect(page.getByLabel("Generated files")).toContainText("contact-sheet.png");
  await page.getByRole("button", { name: "Close details" }).click();
  await expect(page.getByLabel("Generated files")).not.toBeVisible();

  await page.getByRole("button", { name: "Back to start" }).first().click();
  await expect(page.getByRole("heading", { name: "Goodboy Review Room" })).toBeVisible();
  await page.getByRole("button", { name: /Explore companion demo/ }).click();

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
  await page.keyboard.press("5");

  await page.getByRole("button", { name: "Approve visual review" }).click();
  await expect(page.getByRole("banner").getByText("Ready to export")).toBeVisible();
  await page.getByRole("button", { name: "Open details" }).click();
  await expect(page.getByLabel("Details drawer").getByText("Ready", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Close details" }).click();

  await page.getByRole("button", { name: "Toggle activity drawer" }).click();
  await expect(page.getByRole("complementary", { name: "Activity drawer" })).toContainText("Approval recorded");
});
