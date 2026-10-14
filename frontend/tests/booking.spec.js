const { test, expect } = require("@playwright/test");

async function expectFits(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

async function login(page, role) {
  await page.goto("/accounts/login/");
  await page.getByLabel("Username:", { exact: true }).fill(`browser-${role}`);
  await page.getByLabel("Password:", { exact: true }).fill(process.env.AUTH_TEST_PASSWORD);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "My account", exact: true })).toBeVisible();
  await expectFits(page);
}

test("administrator setup, manager equipment and student booking lifecycle", async ({ page }, info) => {
  test.skip(!process.env.AUTH_TEST_PASSWORD, "Run verify-stack.py for disposable test accounts.");
  const suffix = info.project.name;
  const equipment = `Test scope ${suffix}`;
  const purpose = `Practical class ${suffix}`;
  await login(page, "admin");
  await page.goto("/workspace/admin/laboratories/new/");
  await expectFits(page);
  await page.getByLabel("Code:", { exact: true }).fill(`FLOW-${suffix}`);
  await page.getByLabel("Name:", { exact: true }).fill(`Test laboratory ${suffix}`);
  await page.getByLabel("Location:", { exact: true }).fill("Building C");
  await page.getByLabel("Managers:", { exact: true }).selectOption({ label: "browser-manager" });
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Manage laboratories" })).toBeVisible();
  await expectFits(page);

  await page.goto("/workspace/admin/users/new/");
  await expectFits(page);
  await page.getByLabel("Username:", { exact: true }).fill(`new-${suffix}`);
  await page.getByLabel("Email:", { exact: true }).fill(`new-${suffix}@example.test`);
  await page.getByLabel("Role:", { exact: true }).selectOption("student");
  await page.getByLabel("Password:", { exact: true }).fill("Browser-new-password-53!");
  await page.getByLabel("Password confirmation:", { exact: true }).fill("Browser-new-password-53!");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Manage users" })).toBeVisible();
  await expectFits(page);
  await page.getByRole("row").filter({ hasText: `new-${suffix}@example.test` }).getByRole("link", { name: "Edit", exact: true }).click();
  await expectFits(page);
  await page.getByLabel("Active:", { exact: true }).uncheck();
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: `new-${suffix}@example.test` })).toContainText("No");

  await login(page, "manager");
  await page.goto("/workspace/manage/equipment/new/");
  await expectFits(page);
  await page.getByLabel("Laboratory:", { exact: true }).selectOption({ label: `FLOW-${suffix}` });
  await page.getByLabel("Asset tag:", { exact: true }).fill(`SCOPE-${suffix}`);
  await page.getByLabel("Name:", { exact: true }).fill(equipment);
  await page.getByLabel("Category:", { exact: true }).fill("Measurement");
  await page.getByLabel("Status:", { exact: true }).selectOption("available");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Manage equipment" })).toBeVisible();
  await expectFits(page);

  await login(page, "student");
  await page.locator("strong").evaluate(element => { element.textContent = "u".repeat(150); });
  await expectFits(page);
  await page.goto("/workspace/laboratories/");
  await expectFits(page);
  await page.goto("/workspace/equipment/");
  await page.getByLabel("Name or asset tag:", { exact: true }).fill(equipment);
  await page.getByRole("button", { name: "Filter", exact: true }).click();
  await expect(page.locator("tbody tr")).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath("equipment.png"), fullPage: true });
  await page.getByRole("link", { name: equipment, exact: true }).click();
  const detailUrl = page.url();
  const day = new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10);
  async function reserve() {
    await page.goto(detailUrl);
    await page.getByRole("link", { name: "Reserve this equipment" }).click();
    await expectFits(page);
    await page.getByLabel("Purpose:", { exact: true }).fill(purpose);
    await page.getByLabel("Start:", { exact: true }).fill(`${day}T10:00`);
    await page.getByLabel("End:", { exact: true }).fill(`${day}T11:00`);
    await page.getByRole("button", { name: "Request reservation" }).click();
  }
  await reserve();
  await expect(page.getByRole("row").filter({ hasText: purpose })).toContainText("pending");
  await expectFits(page);
  await reserve();
  await expect(page.locator(".errorlist")).toContainText("overlaps");

  await login(page, "admin");
  await page.goto("/workspace/manage/reservations/");
  await expectFits(page);
  const actions = page.getByRole("row").filter({ hasText: purpose }).locator(".reservation-actions button");
  await expect(actions).toHaveCount(3);
  const boxes = await actions.evaluateAll(buttons => buttons.map(button => {
    const box = button.getBoundingClientRect();
    return { x: box.x, y: box.y, width: box.width, height: box.height };
  }));
  for (let i = 1; i < boxes.length; i++) {
    expect(boxes[i].x).toBe(boxes[0].x);
    expect(boxes[i].width).toBe(boxes[0].width);
    expect(boxes[i].y - boxes[i - 1].y - boxes[i - 1].height).toBeGreaterThanOrEqual(8);
  }
  await page.screenshot({ path: info.outputPath("review-actions.png"), fullPage: true });

  await login(page, "manager");
  await page.goto("/workspace/manage/reservations/");
  await page.getByRole("row").filter({ hasText: purpose }).getByRole("button", { name: "Approve", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: purpose })).toContainText("approved");
  await page.screenshot({ path: info.outputPath("review.png"), fullPage: true });

  await login(page, "student");
  await page.goto("/workspace/reservations/");
  await page.getByRole("row").filter({ hasText: purpose }).getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: purpose })).toContainText("cancelled");
  await reserve();
  await expect(page.getByRole("row").filter({ hasText: purpose }).filter({ hasText: "pending" })).toHaveCount(1);

  await login(page, "manager");
  await page.goto("/workspace/manage/reservations/");
  await page.getByRole("row").filter({ hasText: purpose }).filter({ hasText: "pending" }).getByRole("button", { name: "Reject", exact: true }).click();
  await expect(page.getByRole("row").filter({ hasText: purpose }).filter({ hasText: "rejected" })).toHaveCount(1);
});
