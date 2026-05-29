import * as pty from "node-pty";
import stripAnsi from "strip-ansi";

const IS_WINDOWS = process.platform === "win32";

export async function runTuiCommand(
  cliCommand: string,
  slashCommand: string,
  startupMs = 1500,
  waitMs = 9000
): Promise<string> {
  return new Promise((resolve, reject) => {
    let output = "";

    // On Windows, spawn via cmd.exe to resolve PATH correctly;
    // on macOS/Linux, spawn directly so the shell profile is not re-sourced.
    const spawnArgs = IS_WINDOWS
      ? { name: "xterm-color", cols: 120, rows: 40, env: process.env as Record<string, string>, useConpty: false }
      : { name: "xterm-color", cols: 120, rows: 40, env: process.env as Record<string, string> };

    let shell: pty.IPty;
    try {
      shell = pty.spawn(cliCommand, [], spawnArgs as pty.IWindowsPtyForkOptions);
    } catch (err) {
      reject(new Error(`Failed to spawn '${cliCommand}': ${err}`));
      return;
    }

    const killAndResolve = () => {
      try { shell.kill(); } catch { /* already dead */ }
      resolve(stripAnsi(output));
    };

    const timeout = setTimeout(killAndResolve, waitMs);

    shell.onData((data: string) => {
      output += data;
    });

    shell.onExit(() => {
      clearTimeout(timeout);
      resolve(stripAnsi(output));
    });

    // Wait for TUI to finish loading before sending the slash command
    setTimeout(() => {
      try {
        shell.write(`${slashCommand}\r`);
      } catch {
        // shell may have already exited
      }
    }, startupMs);

    // Send Ctrl+C shortly before the timeout to trigger graceful exit
    setTimeout(() => {
      try {
        shell.write("\x03");
      } catch { /* ignore */ }
    }, waitMs - 1000);
  });
}
