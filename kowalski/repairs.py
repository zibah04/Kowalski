"""Read-only launchers for official Windows maintenance utilities."""
import os
import subprocess

TOOLS = {
    "storage": ("Storage Settings", "Review disk cleanup recommendations.", ["explorer.exe", "ms-settings:storagesense"]),
    "updates": ("Windows Update", "Review driver and security updates.", ["explorer.exe", "ms-settings:windowsupdate"]),
    "security": ("Windows Security", "Run a malware scan using Windows Security.", ["explorer.exe", "windowsdefender:"]),
    "taskmgr": ("Task Manager", "Review demanding applications and background processes.", ["taskmgr.exe"]),
    "reliability": ("Reliability Monitor", "Examine Windows crash and stability history.", ["perfmon.exe", "/rel"]),
    "network": ("Network Settings", "Open Windows network troubleshooting settings.", ["explorer.exe", "ms-settings:network-status"]),
}
def launch_tool(key):
    if os.name != "nt":
        raise RuntimeError("Windows is required.")
    if key not in TOOLS:
        raise ValueError("Unknown tool")
    subprocess.Popen(TOOLS[key][2], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
