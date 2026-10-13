const { test, expect } = require("@playwright/test");

test("login page is responsive and shows validation errors", async ({ page }) => {
  await page.goto("/accounts/login/");
  await expect(page.getByRole("heading", { name: "Log in", exact: true })).toBeVisible();
  await page.getByLabel("Username:", { exact: true }).fill("unknown-user");
  await page.getByLabel("Password:", { exact: true }).fill("wrong-password");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.locator(".errorlist")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: test.info().outputPath("login.png"), fullPage: true });
});

test("password reset gives a generic confirmation", async ({ page }) => {
  await page.goto("/accounts/login/");
  await page.getByRole("link", { name: "Forgot your password?" }).click();
  await page.getByLabel("Email:", { exact: true }).fill("missing@example.test");
  await page.getByRole("button", { name: "Send reset link" }).click();
  await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible();
  await page.goto("/accounts/reset/bad/bad/");
  await expect(page.getByText("This reset link is invalid or has expired.")).toBeVisible();
});

for (const role of ["student", "manager", "admin"]) {
  test(`${role} can log in, sees permitted pages, and logs out`, async ({ page }) => {
    test.skip(!process.env.AUTH_TEST_PASSWORD, "Run verify-stack.py for disposable test accounts.");
    await page.goto("/accounts/dashboard/");
    await expect(page).toHaveURL(/\/accounts\/login\//);
    await page.getByLabel("Username:", { exact: true }).fill(`browser-${role}`);
    await page.getByLabel("Password:", { exact: true }).fill(process.env.AUTH_TEST_PASSWORD);
    await page.getByRole("button", { name: "Log in", exact: true }).click();
    await expect(page.getByRole("heading", { name: "My account", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Laboratory manager area" })).toHaveCount(role === "student" ? 0 : 1);
    await expect(page.getByRole("link", { name: "Administrator area" })).toHaveCount(role === "admin" ? 1 : 0);
    const me = await page.request.get("/accounts/me/");
    expect(await me.json()).toEqual({ username: `browser-${role}`, role });
    for (const [path, allowed] of [["manager", role !== "student"], ["administrator", role === "admin"]]) {
      const response = await page.goto(`/accounts/${path}/`);
      expect(response.status()).toBe(allowed ? 200 : 403);
    }
    await page.goto("/accounts/dashboard/");
    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page).toHaveURL(/\/accounts\/login\//);
    expect((await page.request.get("/accounts/me/")).status()).toBe(401);
  });
}
