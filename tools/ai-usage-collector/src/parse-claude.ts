export interface ClaudeSessionInfo {
  used_pct: number;
  reset_text: string;
}

export interface ClaudeUsage {
  five_hour: ClaudeSessionInfo | null;
  raw_ok: boolean;
}

export function parseClaudeUsage(text: string): ClaudeUsage {
  // Match "0% used" or "25% used" (anywhere in the output)
  const usedMatch = text.match(/(\d+)%\s+used/i);

  // Match "Resets 6:40pm (Asia/Taipei)" or "Resets 6:40pm"
  // Capture everything on that line up to a newline or end of string
  const resetsMatch = text.match(/Resets\s+([^\n\r]+)/i);

  if (!usedMatch) {
    return { five_hour: null, raw_ok: false };
  }

  const used_pct = Math.max(0, Math.min(100, Number(usedMatch[1])));
  // Strip trailing whitespace and parenthetical timezone if desired — keep raw for now
  const reset_text = resetsMatch ? resetsMatch[1].trim() : "";

  return {
    five_hour: { used_pct, reset_text },
    raw_ok: true,
  };
}
