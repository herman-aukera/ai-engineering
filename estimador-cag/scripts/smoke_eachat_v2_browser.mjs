import { chromium } from "playwright";

const baseUrl = process.env.EACHAT_BROWSER_BASE_URL || "http://127.0.0.1:8000";
const screenshotPath = process.env.EACHAT_BROWSER_SCREENSHOT || "/tmp/eachat-v2-browser.png";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
const consoleErrors = [];

page.on("console", message => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", error => consoleErrors.push(error.message));

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitForActivity(fragment) {
  await page.waitForFunction(
    expected => document.querySelector("#activity")?.textContent?.includes(expected),
    fragment,
    { timeout: 20_000 },
  );
}

try {
  await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
  assert(page.url().endsWith("/energy-chat/v2/demo"), "Root did not open the V2 product UI");
  await page.waitForSelector("#composerInput");

  await page.fill(
    "#composerInput",
    "Explain the safest first step for validating an Energy-Aware Chat release.",
  );
  await page.getByRole("button", { name: "Send to graph" }).click();
  await waitForActivity("Graph completed");
  await page.waitForSelector(".message.assistant");

  const answer = await page.locator(".message.assistant .bubble").last().textContent();
  const status = await page.locator("#statusPanel").textContent();
  const card = await page.locator("#energyPanel").textContent();
  assert(Boolean(answer?.trim()), "Deterministic graph returned no visible answer");
  assert(status?.includes("evaluated"), "Deterministic graph did not reach evaluated state");
  assert(card?.includes("Decision"), "Energy Card was not rendered");

  await page.getByRole("button", { name: "Inspect state" }).click();
  await waitForActivity("Safe checkpoint state loaded");
  const stateProjection = await page.locator("#statePanel").textContent();
  assert(stateProjection?.includes("checkpoint_id"), "Safe checkpoint state was not rendered");

  const assistantCountBeforeReplay = await page.locator(".message.assistant").count();
  await page.getByRole("button", { name: "Replay checkpoint" }).click();
  await waitForActivity("Checkpoint replayed without graph execution");
  const assistantCountAfterReplay = await page.locator(".message.assistant").count();
  assert(
    assistantCountAfterReplay === assistantCountBeforeReplay + 1,
    "Checkpoint replay did not append one replay projection",
  );

  const storage = await page.evaluate(() => ({
    threads: localStorage.getItem("eachat:v2:threads"),
    messageKeys: Object.keys(localStorage).filter(key => key.startsWith("eachat:v2:messages:")),
  }));
  assert(Boolean(storage.threads), "Browser thread history was not persisted");
  assert(storage.messageKeys.length >= 1, "Browser message history was not persisted");

  await page.getByRole("button", { name: "＋ New run" }).click();
  await page.fill("#composerInput", "Approve the production release.");
  await page.getByRole("button", { name: "Run with human gate" }).click();
  await waitForActivity("Human response required");
  await page.waitForSelector("#humanPanel.visible");
  const actionType = await page.locator("#humanActionType").textContent();
  assert(actionType === "escalate_response", "Expected an escalation human-action contract");

  await page.fill("#humanResponse", "Reviewed by the browser smoke operator.");
  await page.getByRole("button", { name: "Submit human response" }).click();
  await waitForActivity("Graph resumed from the authoritative checkpoint");
  const completedStatus = await page.locator("#statusPanel").textContent();
  assert(completedStatus?.includes("completed"), "Human-gated graph did not complete");

  await page.screenshot({ path: screenshotPath, fullPage: true });
  assert(consoleErrors.length === 0, `Browser console errors: ${consoleErrors.join(" | ")}`);
  console.log("EACHAT_V2_BROWSER_SMOKE_OK");
} finally {
  await browser.close();
}
