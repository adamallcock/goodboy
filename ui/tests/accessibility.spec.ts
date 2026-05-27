import { expect, test } from "@playwright/test";

test("primary inspector controls are keyboard reachable and named", async ({ page }) => {
  await page.goto("/");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Refresh project state" })).toBeFocused();

  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Open command palette" })).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(page.getByPlaceholder("Search Goodboy actions...")).toBeVisible();

  await page.keyboard.press("Escape");
  const qaStage = page.getByRole("navigation", { name: "Review stages" }).getByRole("button", { name: "QA", exact: true });
  await qaStage.focus();
  await expect(qaStage).toBeFocused();
});
