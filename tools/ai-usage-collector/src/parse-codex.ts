export interface CodexLimitInfo {
  used_pct: number;
  reset_text: string;
}

export interface CodexStatus {
  five_hour: CodexLimitInfo | null;
  weekly: CodexLimitInfo | null;
  raw_ok: boolean;
}

export function parseCodexStatus(text: string): CodexStatus {
  // "5h limit:      99% left (resets 21:58)"
  const fiveHourMatch = text.match(
    /5h\s+limit\s*:.*?(\d+)%\s+left\s+\(resets\s+([^)]+)\)/i
  );

  // "Weekly limit: 75% left (resets 17:38 on 1 Jun)"
  const weeklyMatch = text.match(
    /weekly\s+limit\s*:.*?(\d+)%\s+left\s+\(resets\s+([^)]+)\)/i
  );

  const parseLimitInfo = (
    match: RegExpMatchArray | null
  ): CodexLimitInfo | null => {
    if (!match) return null;
    const leftPct = Number(match[1]);
    if (Number.isNaN(leftPct)) return null;
    return {
      used_pct: Math.max(0, Math.min(100, 100 - leftPct)),
      reset_text: match[2].trim(),
    };
  };

  const five_hour = parseLimitInfo(fiveHourMatch);
  const weekly = parseLimitInfo(weeklyMatch);

  return {
    five_hour,
    weekly,
    raw_ok: five_hour !== null || weekly !== null,
  };
}
