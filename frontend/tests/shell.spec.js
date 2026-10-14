const { test, expect } = require("@playwright/test");

test("foundation shell loads without horizontal overflow", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle("LabReserve · Laboratory workspace");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByText("Log in to browse equipment and manage your reservations.")).toBeVisible();
  const fits = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);
  expect(fits).toBe(true);
});
