const path = require("node:path");

async function reportScreenshot(page, info, name) {
  if (process.env.REPORT_SCREENSHOTS !== "1") return;
  if (info.project.name === "mobile" && name === "equipment") {
    name = "equipment-mobile";
  } else if (info.project.name !== "desktop") {
    return;
  }
  await page.screenshot({
    path: path.join(__dirname, "../../docs/screenshots", `${name}.png`),
    fullPage: true,
  });
}

module.exports = { reportScreenshot };
