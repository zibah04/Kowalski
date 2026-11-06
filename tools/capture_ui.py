"""Capture genuine Kowalski Qt windows as PNG screenshots on a Windows runner."""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from kowalski.app import CSS, Kowalski


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(CSS)
    window = Kowalski()
    window.resize(1280, 800)
    window.show()

    # Capture the real app, after its normal read-only diagnostic scan finishes.
    deadline = time.monotonic() + 50
    while window.report is None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.08)

    if window.report is None:
        raise RuntimeError("Kowalski's initial scan did not finish; no screenshots saved.")

    folder = Path("docs/screenshots")
    folder.mkdir(parents=True, exist_ok=True)
    for index, filename in [
        (0, "kowalski-dashboard.png"),
        (3, "kowalski-crash-investigator.png"),
    ]:
        window.pages.setCurrentIndex(index)
        for _ in range(8):
            app.processEvents()
            time.sleep(0.06)
        path = folder / filename
        if not window.grab().save(str(path), "PNG"):
            raise RuntimeError(f"Qt failed to save screenshot: {path}")
        print(f"Captured {path} ({path.stat().st_size} bytes)")
    window.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
