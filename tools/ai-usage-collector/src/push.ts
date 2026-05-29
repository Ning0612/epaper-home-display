export interface AIUsagePayload {
  codex_5h_pct: number | null;
  codex_5h_reset: string | null;
  codex_weekly_pct: number | null;
  codex_weekly_reset: string | null;
  claude_5h_pct: number | null;
  claude_5h_reset: string | null;
}

export async function pushToDisplay(
  piUrl: string,
  payload: AIUsagePayload
): Promise<void> {
  const url = `${piUrl.replace(/\/$/, "")}/ai_usage`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) {
    throw new Error(`POST ${url} returned ${response.status}`);
  }
}
