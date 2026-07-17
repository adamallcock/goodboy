import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/launch-context", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ project_id: null, project_dir: null })
    });
  });
});

test("primary review controls are keyboard reachable and named", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: /Explore companion demo/ }).click();

  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Back to start" }).first()).toBeFocused();

  await page.getByRole("button", { name: "Open command palette" }).focus();
  await expect(page.getByRole("button", { name: "Open command palette" })).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(page.getByPlaceholder("Search Goodboy actions...")).toBeVisible();

  await page.keyboard.press("Escape");
  const nextStep = page.getByRole("button", { name: /Identity/ });
  await nextStep.focus();
  await expect(nextStep).toBeFocused();

  await page.keyboard.press("6");
  await expect(page.getByTestId("sprite-state-viewer")).toBeVisible();
  await page.getByRole("button", { name: "Open details" }).focus();
  await expect(page.getByRole("button", { name: "Open details" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("complementary", { name: "Details drawer" })).toBeVisible();
});
