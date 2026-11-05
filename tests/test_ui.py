import os
import unittest
from unittest.mock import patch

try:
    from PySide6.QtWidgets import QApplication
    from kowalski.app import Kowalski
except ImportError:
    QApplication=None

@unittest.skipIf(QApplication is None,"Qt not available")
class UISmoke(unittest.TestCase):
    def test_window(self):
        os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
        app=QApplication.instance() or QApplication([])
        with patch.object(Kowalski,"scan",lambda self: None):
            w=Kowalski()
        self.assertIn("Kowalski",w.windowTitle())
        self.assertGreaterEqual(w.pages.count(),4)
        w.close()
