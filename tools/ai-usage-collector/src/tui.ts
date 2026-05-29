import * as pty from "node-pty";
import stripAnsi from "strip-ansi";

const IS_WINDOWS = process.platform === "win32";

export async function runTuiCommand(
  cliCommand: string,
  slashCommand: string,
  startupMs = 1500,
  waitMs = 12000
): Promise<string> {
  return new Promise((resolve, reject) => {
    let output = "";
    let commandSent = false;

    const baseArgs = {
      name: "xterm-color",
      cols: 120,
      rows: 40,
      env: process.env as Record<string, string>,
    };

    let shell: pty.IPty;
    try {
      shell = IS_WINDOWS
        ? pty.spawn("cmd.exe", [], { ...baseArgs, useConpty: false } as pty.IWindowsPtyForkOptions)
        : pty.spawn(cliCommand, [], baseArgs);
    } catch (err) {
      reject(new Error(`Failed to spawn PTY for '${cliCommand}': ${err}`));
      return;
    }

    const sendSlashCommand = () => {
      if (commandSent) return;
      commandSent = true;
      try { shell.write(`${slashCommand}\r`); } catch { /* shell may have exited */ }
    };

    const killAndResolve = () => {
      try { shell.kill(); } catch { /* already dead */ }
      resolve(stripAnsi(output));
    };

    const hardTimeout = setTimeout(killAndResolve, waitMs);

    shell.onData((data: string) => {
      output += data;
      // Send slash command as soon as the TUI reports "Ready" — more reliable
      // than a fixed startup delay because MCP server load time varies.
      if (!commandSent && stripAnsi(output).includes(" · Ready · ")) {
        setTimeout(sendSlashCommand, 300);
      }
    });

    shell.onExit(() => {
      clearTimeout(hardTimeout);
      resolve(stripAnsi(output));
    });

    if (IS_WINDOWS) {
      // On Windows: type the CLI command into cmd.exe after the shell prompt appears
      setTimeout(() => {
        try { shell.write(`${cliCommand}\r`); } catch { /* ignore */ }
      }, 500);
    }

    // Fallback: if "Ready" never appears, send the command at startupMs anyway
    const fallbackDelay = IS_WINDOWS ? 500 + startupMs : startupMs;
    setTimeout(() => {
      if (!commandSent) sendSlashCommand();
    }, fallbackDelay);

    // Ctrl+C for graceful exit before hard timeout
    setTimeout(() => {
      try { shell.write("\x03"); } catch { /* ignore */ }
    }, waitMs - 1000);
  });
}
