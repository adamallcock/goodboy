import { expect, test } from "@playwright/test";

test("primary inspector controls are keyboard reachable and named", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: /Explore demo/ }).click();

  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Back to start" }).first()).toBeFocused();

  await page.getByRole("button", { name: "Open command palette" }).focus();
  await expect(page.getByRole("button", { name: "Open command palette" })).toBeFocused();

  await page.keyboard.press("Enter");
  await expect(page.getByPlaceholder("Search Goodboy actions...")).toBeVisible();

  await page.keyboard.press("Escape");
  const nextStep = page.getByRole("button", { name: /Baselines/ });
  await nextStep.focus();
  await expect(nextStep).toBeFocused();
});
