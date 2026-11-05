import unittest
from kowalski.crashes import normalize_hex, explain_event, analyze_records
from kowalski import diagnostics

class CrashTests(unittest.TestCase):
    def test_decimal_exception(self):
        self.assertEqual(normalize_hex("3221225477"), "0xc0000005")
    def test_game_crash(self):
        r=explain_event({"log":"Application","source":"Application Error","id":1000,"message":"Faulting application name: MyGame.exe, version: 1.0\nException code: 0xc0000005"})
        self.assertEqual(r["category"],"app")
        self.assertIn("MyGame.exe",r["title"])
    def test_blue_screen(self):
        r=explain_event({"log":"System","source":"BugCheck","id":1001,"message":"The computer has rebooted from a bugcheck. The bugcheck was: 0x00000116"})
        self.assertEqual(r["category"],"bsod")
        self.assertIn("graphics",r["meaning"].lower())
    def test_app_1001_is_not_bsod(self):
        self.assertEqual(explain_event({"log":"Application","source":"Windows Error Reporting","id":1001,"message":"APPCRASH"})["category"],"app")
    def test_kernel_power_not_proof(self):
        r=explain_event({"log":"System","source":"Microsoft-Windows-Kernel-Power","id":41,"message":"Unexpected restart"})
        self.assertEqual(r["category"],"unexpected_shutdown")
        self.assertIn("not prove",r["meaning"])
    def test_repeated(self):
        e={"log":"Application","source":"Application Error","id":1000,"message":"Faulting application name: Game.exe\nException code: 0xc0000005"}
        r=analyze_records([e,e],[])
        self.assertEqual(r["findings"][0]["repeat_count"],2)
    def test_machine_snapshot(self):
        r=diagnostics.snapshot(include_events=False)
        self.assertGreater(r["ram_total_gb"],0)
        self.assertIn("disks",r)

if __name__=="__main__": unittest.main()
