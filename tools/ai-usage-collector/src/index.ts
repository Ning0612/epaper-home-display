import * as fs from "node:fs";
import * as path from "node:path";
import * as dotenv from "dotenv";

import { runTuiCommand } from "./tui";
import { parseCodexStatus } from "./parse-codex";
import { parseClaudeUsage } from "./parse-claude";
import { pushToDisplay, type AIUsagePayload } from "./push";

dotenv.config();

const PI_URL = process.env.PI_URL;
const CODEX_CMD = process.env.CODEX_CMD ?? "codex";
const CLAUDE_CMD = process.env.CLAUDE_CMD ?? "claude";
const STARTUP_MS = Number(process.env.TUI_STARTUP_MS ?? 1500);
const WAIT_MS = Number(process.env.TUI_WAIT_MS ?? 9000);

const DATA_DIR = path.resolve(__dirname, "..", "data");
const LATEST_PATH = path.join(DATA_DIR, "latest.json");

function saveCache(payload: AIUsagePayload): void {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(
    LATEST_PATH,
    JSON.stringify({ ...payload, updated_at: new Date().toISOString() }, null, 2)
  );
}

async function main(): Promise<void> {
  if (!PI_URL) {
    console.error("[ai-usage-collector] PI_URL is not set. Copy .env.example → .env and configure.");
    process.exit(1);
  }

  console.log("[ai-usage-collector] Collecting Codex and Claude usage...");

  // Run both TUI captures in parallel
  const [codexText, claudeText] = await Promise.all([
    runTuiCommand(CODEX_CMD, "/status", STARTUP_MS, WAIT_MS).catch((err: Error) => {
      console.warn("[codex] TUI capture failed:", err.message);
      return "";
    }),
    runTuiCommand(CLAUDE_CMD, "/usage", STARTUP_MS, WAIT_MS).catch((err: Error) => {
      console.warn("[claude] TUI capture failed:", err.message);
      return "";
    }),
  ]);

  const codex = parseCodexStatus(codexText);
  const claude = parseClaudeUsage(claudeText);

  if (!codex.raw_ok) console.warn("[codex] Parse failed — raw output may have changed format.");
  if (!claude.raw_ok) console.warn("[claude] Parse failed — raw output may have changed format.");

  const payload: AIUsagePayload = {
    codex_5h_pct:       codex.five_hour?.used_pct ?? null,
    codex_5h_reset:     codex.five_hour?.reset_text ?? null,
    codex_weekly_pct:   codex.weekly?.used_pct ?? null,
    codex_weekly_reset: codex.weekly?.reset_text ?? null,
    claude_5h_pct:      claude.five_hour?.used_pct ?? null,
    claude_5h_reset:    claude.five_hour?.reset_text ?? null,
  };

  console.log("[ai-usage-collector] Parsed:", JSON.stringify(payload, null, 2));
  saveCache(payload);

  try {
    await pushToDisplay(PI_URL, payload);
    console.log("[ai-usage-collector] Pushed to Pi successfully.");
  } catch (err) {
    console.error("[ai-usage-collector] Push failed (cached locally):", err);
  }

  process.exit(0);
}

main();
