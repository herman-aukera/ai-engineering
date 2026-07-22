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
    "Remember that the release-validation keyword is ORBIT-17.",
  );
  await page.getByRole("button", { name: "Send turn" }).click();
  await waitForActivity("Durable graph turn completed");

  let userCount = await page.locator(".message.user").count();
  let assistantCount = await page.locator(".message.assistant").count();
  let status = await page.locator("#statusPanel").textContent();
  let card = await page.locator("#energyPanel").textContent();
  assert(userCount === 1, "First durable turn did not render one user message");
  assert(assistantCount === 1, "First durable turn did not render one assistant message");
  assert(status?.includes("evaluated"), "First durable turn did not reach evaluated state");
  assert(status?.includes("Context profilebalanced"), "Balanced context profile was not recorded");
  assert(status?.includes("Memory messages0"), "First turn unexpectedly received prior memory");
  assert(card?.includes("Decision"), "First turn Energy Card was not rendered");

  await page.selectOption("#contextProfile", "minimal");
  await page.selectOption("#orchestrationMode", "adaptive");
  await page.fill(
    "#composerInput",
    "What release-validation keyword did I give you in the previous visible turn?",
  );
  await page.getByRole("button", { name: "Send turn" }).click();
  await waitForActivity("Durable graph turn completed");

  userCount = await page.locator(".message.user").count();
  assistantCount = await page.locator(".message.assistant").count();
  status = await page.locator("#statusPanel").textContent();
  assert(userCount === 2, "Second durable turn did not retain ordered user history");
  assert(assistantCount === 2, "Second durable turn did not retain ordered assistant history");
  assert(status?.includes("Context profileminimal"), "Minimal context snapshot was not applied");
  assert(status?.includes("Requested orchestrationadaptive"), "Adaptive orchestration was not requested");
  assert(status?.includes("Resolved orchestrationcritic"), "Low-risk adaptive turn did not stay on critic");
  assert(status?.includes("Context snapshotconversation-"), "Context snapshot identity was not rendered");
  assert(status?.includes("Memory messages2"), "Second turn did not receive bounded prior context");

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
    index: localStorage.getItem("eachat:v2:conversation-index"),
    messageKeys: Object.keys(localStorage).filter(key => key.includes("messages")),
    serializedStorage: JSON.stringify(localStorage),
  }));
  assert(Boolean(storage.index), "Browser conversation index was not persisted");
  assert(storage.messageKeys.length === 0, "Browser retained message-body storage keys");
  assert(!storage.serializedStorage.includes("ORBIT-17"), "Browser persisted conversation bodies locally");

  await page.reload({ waitUntil: "networkidle" });
  await waitForActivity("Server history loaded");
  userCount = await page.locator(".message.user").count();
  assistantCount = await page.locator(".message.assistant").count();
  assert(userCount === 2, "Reload did not recover two user turns from server memory");
  assert(assistantCount === 2, "Reload did not recover two assistant turns from server memory");
  assert(await page.locator("#contextProfile").inputValue() === "minimal", "Context profile did not survive server-history reload");

  await page.getByRole("button", { name: "Delete conversation" }).click();
  await waitForActivity("Conversation deleted from the server");
  assert(await page.locator(".message").count() === 0, "Deleted conversation remained visible");

  await page.fill("#composerInput", "Approve the production release.");
  await page.getByRole("button", { name: "Run protected one-off" }).click();
  await waitForActivity("Human decision required");
  await page.waitForSelector("#humanPanel.visible");
  const actionType = await page.locator("#humanActionType").textContent();
  assert(actionType === "escalate_response", "Expected an escalation human-action contract");

  await page.selectOption("#humanDecision", "reject");
  await page.fill("#humanDecisionReason", "Release evidence is insufficient in the browser canary.");
  await page.getByRole("button", { name: "Apply human decision" }).click();
  await waitForActivity("Authoritative human decision applied");
  const completedStatus = await page.locator("#statusPanel").textContent();
  card = await page.locator("#energyPanel").textContent();
  assert(completedStatus?.includes("completed"), "Human-gated graph did not complete");
  assert(completedStatus?.includes("Human decisionreject"), "Human reject authority was not rendered");
  assert(card?.includes("Decisionreject"), "Rejected Energy Card was not rendered");

  await page.screenshot({ path: screenshotPath, fullPage: true });
  assert(consoleErrors.length === 0, `Browser console errors: ${consoleErrors.join(" | ")}`);
  console.log("EACHAT_V2_BROWSER_SMOKE_OK");
} finally {
  await browser.close();
}
