const { test, expect } = require("@playwright/test");
const path = require("node:path");

test("browser connects through the same-origin health endpoint", async ({ page }, testInfo) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  const healthRequest = page.waitForRequest(request => request.url().endsWith("/api/health"));
  await page.goto("/");
  const request = await healthRequest;
  await expect(page.getByRole("status")).toHaveText("Connected");
  expect(new URL(request.url()).origin).toBe(new URL(page.url()).origin);
  expect(errors).toEqual([]);
  await expect(page.getByRole("button", { name: "Check again" })).toBeEnabled();
  if (process.env.CAPTURE_SCREENSHOTS === "1") {
    await page.screenshot({
      path: path.join(__dirname, "../../docs/screenshots", `${testInfo.project.name}.png`),
      fullPage: true,
    });
  }
});

test("unavailable service gives clear feedback and retry recovers", async ({ page }) => {
  await page.route("**/api/health", route => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ status: "unavailable" }),
  }));
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("Unavailable");
  await expect(page.getByRole("button", { name: "Check again" })).toBeEnabled();
  await page.unroute("**/api/health");
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(page.getByRole("status")).toHaveText("Connected");
});

test("invalid health payload is not reported as connected", async ({ page }) => {
  await page.route("**/api/health", route => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ status: "unexpected" }),
  }));
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("Unavailable");
});

test("network failure releases the retry button", async ({ page }) => {
  await page.route("**/api/health", route => route.abort("failed"));
  await page.goto("/");
  await expect(page.getByRole("status")).toHaveText("Unavailable");
  await expect(page.getByRole("button", { name: "Check again" })).toBeEnabled();
});
