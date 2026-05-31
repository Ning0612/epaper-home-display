Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = "F:\WorkSpace\epaper-home-display\tools\ai-usage-collector"
shell.Run """C:\WINDOWS\System32\WindowsPowerShell\v1.0\powershell.exe"" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""F:\WorkSpace\epaper-home-display\tools\ai-usage-collector\scripts\run.ps1""", 0, True
Set shell = Nothing
