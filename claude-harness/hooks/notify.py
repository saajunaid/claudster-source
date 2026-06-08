"""Desktop notification when Claude finishes a task. Windows balloon tip."""
import subprocess
import sys

ps = (
    "Add-Type -AssemblyName System.Windows.Forms; "
    "$n = New-Object System.Windows.Forms.NotifyIcon; "
    "$n.Icon = [System.Drawing.SystemIcons]::Information; "
    "$n.Visible = $true; "
    "$n.ShowBalloonTip(6000, 'Claude Code', 'Task complete', 'Info'); "
    "Start-Sleep -Seconds 4; "
    "$n.Dispose()"
)
try:
    subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
except Exception:
    pass
sys.exit(0)
