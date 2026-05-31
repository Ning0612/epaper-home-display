export interface ClaudeSessionInfo {
  used_pct: number;
  reset_text: string;
}

export interface ClaudeUsage {
  five_hour: ClaudeSessionInfo | null;
  raw_ok: boolean;
}

function to24h(raw: string): string {
  // Strip trailing timezone parenthetical: "6:40pm (Asia/Taipei)" → "6:40pm"
  const stripped = raw.replace(/\s*\([^)]+\)\s*$/, "").trim();
  const m = stripped.match(/^(\d{1,2}):(\d{2})\s*(am|pm)$/i);
  if (!m) return stripped;
  let h = parseInt(m[1], 10);
  const min = m[2];
  const period = m[3].toLowerCase();
  if (period === "am") {
    if (h === 12) h = 0;
  } else {
    if (h !== 12) h += 12;
  }
  return `${h.toString().padStart(2, "0")}:${min}`;
}

export function parseClaudeUsage(text: string): ClaudeUsage {
  // TUI strips spaces, so "34% used" and "34%used" both occur
  const usedMatch = text.match(/(\d+)%\s*used/i);
  // Capture only the time token after "Resets", not the rest of the collapsed line
  const resetsMatch = text.match(/Resets\s*(\d{1,2}:\d{2}\s*(?:am|pm)\s*(?:\([^)]+\))?)/i);

  if (!usedMatch) {
    return { five_hour: null, raw_ok: false };
  }

  const used_pct = Math.max(0, Math.min(100, Number(usedMatch[1])));
  const reset_text = resetsMatch ? to24h(resetsMatch[1].trim()) : "";

  return {
    five_hour: { used_pct, reset_text },
    raw_ok: true,
  };
}
