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
        self.assertEqual(w.pages.count(),6)
        self.assertEqual(len(w.nav_buttons),6)
        self.assertTrue(w.nav_buttons[0].isChecked())
        w.navigate(3)
        self.assertEqual(w.pages.currentIndex(),3)
        self.assertTrue(w.nav_buttons[3].isChecked())
        self.assertFalse(w.nav_buttons[0].isChecked())
        w.close()
