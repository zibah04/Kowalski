"""Kowalski native Windows desktop interface using Qt."""
import os,sys
from datetime import datetime
from PySide6.QtCore import QObject,QThread,Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,
    QPushButton,QFrame,QStackedWidget,QScrollArea,QFileDialog,QMessageBox,QTextEdit,QLineEdit,
    QGridLayout,QProgressBar)
from . import diagnostics
from .repairs import TOOLS,launch_tool

CSS="""
QWidget { background:#10151d; color:#e8edf5; font:10pt 'Segoe UI'; }
QMainWindow { background:#10151d; }
QLabel#logo { color:#f4f7fb; font-size:23pt; font-weight:800; letter-spacing:1px; }
QLabel#heading { color:#f5f7fb; font-size:23pt; font-weight:750; }
QLabel#subheading { color:#9aa9ba; font-size:10pt; }
QLabel#muted { color:#91a0b2; font-size:9pt; }
QLabel#metric { color:#f6f8fc; font-size:27pt; font-weight:750; }
QFrame#sidebar { background:#171e29; border-right:1px solid #283342; }
QFrame#panel { background:#1a2330; border:1px solid #2a3748; border-radius:14px; }
QFrame#metricPanel { background:#1a2330; border:1px solid #2a3748; border-radius:14px; }
QPushButton { background:#222e3d; border:1px solid #344357; border-radius:9px; color:#e4ebf4; padding:10px 14px; text-align:left; }
QPushButton:hover { background:#2a394b; border-color:#6e91b8; }
QPushButton#navButton { background:transparent; border:0; border-radius:9px; color:#aebaca; padding:12px 14px; text-align:left; font-weight:600; }
QPushButton#navButton:hover { background:#222d3b; color:#ffffff; }
QPushButton#navButton:checked { background:#26394d; color:#ffffff; border-left:3px solid #78b7f4; padding-left:11px; }
QPushButton#primary { background:#78b7f4; color:#101923; border:0; border-radius:9px; padding:11px 18px; font-weight:750; text-align:center; }
QPushButton#primary:hover { background:#9acaff; }
QPushButton:disabled { color:#647386; background:#202a36; }
QTextEdit,QLineEdit { background:#131b26; color:#e0e8f1; border:1px solid #344357; border-radius:9px; padding:10px; selection-background-color:#426d98; }
QLineEdit:focus,QTextEdit:focus { border:1px solid #78b7f4; }
QProgressBar { background:#2a3544; border:0; border-radius:5px; height:9px; text-align:center; }
QProgressBar::chunk { background:#78b7f4; border-radius:5px; }
QScrollArea { border:0; background:transparent; }
QScrollArea QWidget { background:transparent; }
"""
def label(value,kind=None):
    w=QLabel(str(value));w.setWordWrap(True)
    if kind:w.setObjectName(kind)
    return w
def panel():
    p=QFrame();p.setObjectName("panel")
    box=QVBoxLayout(p);box.setContentsMargins(18,16,18,16);box.setSpacing(10)
    return p,box

class ScanWorker(QObject):
    completed=Signal(dict)
    failed=Signal(str)
    def run(self):
        try:self.completed.emit(diagnostics.snapshot())
        except Exception as e:self.failed.emit(str(e))

class Kowalski(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kowalski | Windows PC Diagnostics")
        self.resize(1170,760);self.setMinimumSize(860,570)
        self.report=None;self.thread=None;self.worker=None
        root=QWidget();self.setCentralWidget(root)
        shell=QHBoxLayout(root);shell.setContentsMargins(0,0,0,0);shell.setSpacing(0)
        side=QFrame();side.setObjectName("sidebar");side.setFixedWidth(228)
        menu=QVBoxLayout(side);menu.setContentsMargins(18,30,18,24);menu.setSpacing(7)
        menu.addWidget(label("KOWALSKI","logo"));menu.addWidget(label("PC CARE, WITHOUT THE GUESSWORK.","muted"));menu.addSpacing(28)
        menu.addWidget(label("WORKSPACE","muted"))
        self.pages=QStackedWidget();self.nav_buttons=[]
        for i,name in enumerate(["Dashboard","Diagnostics","Windows errors","Crash investigator","Maintenance","About"]):
            b=QPushButton(name);b.setObjectName("navButton");b.setCheckable(True);b.setChecked(i==0)
            b.clicked.connect(lambda checked,n=i:self.navigate(n));menu.addWidget(b);self.nav_buttons.append(b)
        menu.addStretch()
        menu.addWidget(label("●  LOCAL-FIRST DIAGNOSTICS","muted"))
        menu.addWidget(label("No account. No telemetry.","muted"))
        shell.addWidget(side)
        main=QWidget();content=QVBoxLayout(main);content.setContentsMargins(30,26,30,22);content.setSpacing(15)
        head=QHBoxLayout()
        titles=QVBoxLayout();titles.setSpacing(3)
        titles.addWidget(label("PC HEALTH CENTER","heading"))
        titles.addWidget(label("A clearer picture of what is happening on your Windows PC.","subheading"))
        head.addLayout(titles);head.addStretch()
        self.scan_btn=QPushButton("↻   Run full scan");self.scan_btn.setObjectName("primary")
        self.scan_btn.clicked.connect(self.scan);head.addWidget(self.scan_btn);content.addLayout(head)
        self.status=label("●  Ready to scan","muted");content.addWidget(self.status)
        content.addWidget(self.pages);shell.addWidget(main,1)
        self.make_pages();self.scan()

    def navigate(self,index):
        self.pages.setCurrentIndex(index)
        for i,button in enumerate(self.nav_buttons):
            button.setChecked(i==index)

    def page(self):
        scroll=QScrollArea();scroll.setWidgetResizable(True)
        base=QWidget();layout=QVBoxLayout(base);layout.setContentsMargins(2,8,8,16);layout.setSpacing(14)
        scroll.setWidget(base);self.pages.addWidget(scroll);return layout

    def make_pages(self):
        dash=self.page();dash.addWidget(label("LIVE RESOURCE OVERVIEW","muted"))
        grid=QGridLayout();grid.setSpacing(12);self.metrics={}
        for i,(key,title) in enumerate([("cpu","CPU USAGE"),("ram","RAM USED"),("disk","SYSTEM DISK"),("health","RESOURCE STATUS")]):
            p,body=panel();p.setObjectName("metricPanel");body.addWidget(label(title,"muted"));w=label("—","metric")
            body.addWidget(w);grid.addWidget(p,i//2,i%2);self.metrics[key]=w
        dash.addLayout(grid);p,body=panel();body.addWidget(label("HEALTH FINDINGS","muted"))
        self.findings=label("Scanning…");body.addWidget(self.findings);dash.addWidget(p);dash.addStretch()

        diag=self.page();p,body=panel();body.addWidget(label("SYSTEM INFORMATION","muted"))
        self.system_box=label("Scanning…");body.addWidget(self.system_box);diag.addWidget(p)
        p,body=panel();body.addWidget(label("STORAGE","muted"))
        self.drive_layout=QVBoxLayout();body.addLayout(self.drive_layout);diag.addWidget(p)
        for ext in ("json","txt"):
            b=QPushButton("Export "+ext.upper()+" report");b.clicked.connect(lambda _,x=ext:self.export(x));diag.addWidget(b)
        diag.addStretch()

        errors=self.page();errors.addWidget(label("RECENT WINDOWS SYSTEM ERRORS","muted"))
        p,body=panel();self.event_box=QTextEdit();self.event_box.setReadOnly(True)
        self.event_box.setMinimumHeight(380);body.addWidget(self.event_box);errors.addWidget(p)
        b=QPushButton("Open Reliability Monitor");b.clicked.connect(lambda:self.open_tool("reliability"));errors.addWidget(b);errors.addStretch()

        crash=self.page();crash.addWidget(label("GAME, APP & BLUE SCREEN CRASH INVESTIGATOR","muted"))
        crash.addWidget(label("Read-only Windows Event Log evidence. Stop codes suggest possibilities, not confirmed causes. Dump files are discovered, not debugged.","muted"))
        p,body=panel();self.crash_summary=label("Scanning…");body.addWidget(self.crash_summary);crash.addWidget(p)
        self.crash_filter=QLineEdit();self.crash_filter.setPlaceholderText("Search game name, application or stop code")
        self.crash_filter.textChanged.connect(self.refresh_crash_view);crash.addWidget(self.crash_filter)
        p,body=panel();self.crash_box=QTextEdit();self.crash_box.setReadOnly(True);self.crash_box.setMinimumHeight(420)
        body.addWidget(self.crash_box);crash.addWidget(p)
        crash.addWidget(label("For detailed dump debugging, use Microsoft WinDbg and symbols.","muted"))
        crash.addStretch()

        maintenance=self.page()
        maintenance.addWidget(label("SAFE WINDOWS TOOLS","muted"))
        maintenance.addWidget(label("These buttons only open built-in tools after confirmation. Kowalski never silently deletes files or edits the registry.","muted"))
        for key,(name,description,_) in TOOLS.items():
            p,body=panel();body.addWidget(label(name));body.addWidget(label(description,"muted"))
            b=QPushButton("Open "+name);b.clicked.connect(lambda _,k=key:self.open_tool(k));body.addWidget(b)
            maintenance.addWidget(p)
        maintenance.addStretch()

        about=self.page();p,body=panel()
        body.addWidget(label("KOWALSKI","logo"))
        body.addWidget(label("Windows PC health, crash investigation and plain-English troubleshooting."))
        body.addWidget(label("Version 1.1.0 • Offline • Read-only diagnosis • No telemetry","muted"))
        body.addWidget(label("Crash evidence may be incomplete. App error codes and BSOD stop codes do not, on their own, prove why something failed.","muted"))
        about.addWidget(p);about.addStretch()

    def scan(self):
        if self.thread is not None:return
        self.scan_btn.setEnabled(False);self.status.setText("●  Scanning resources, Windows crashes and hardware reports…")
        t=QThread(self);w=ScanWorker();w.moveToThread(t)
        self.thread=t;self.worker=w
        t.started.connect(w.run)
        w.completed.connect(self.scan_done)
        w.failed.connect(self.scan_failed)
        w.completed.connect(t.quit);w.failed.connect(t.quit)
        t.finished.connect(w.deleteLater);t.finished.connect(self.scan_finished)
        t.start()

    def scan_finished(self):
        self.thread=None;self.worker=None;self.scan_btn.setEnabled(True)
    def scan_failed(self,message):
        self.status.setText("Scan failed: "+message)
        QMessageBox.warning(self,"Scan failed",message)

    def scan_done(self,r):
        self.report=r;self.status.setText("●  Scan complete  ·  "+r["captured_at"]+"  ·  All data stays on this PC")
        self.metrics["cpu"].setText(f"{r['cpu_percent']:.0f}%")
        self.metrics["ram"].setText(f"{r['ram_used_percent']:.0f}%")
        d=next((x for x in r["disks"] if os.environ.get("SystemDrive","C:").lower() in x["mount"].lower()),None)
        d=d or next(iter(r["disks"]),None)
        self.metrics["disk"].setText(f"{d['used_percent']:.0f}%" if d else "N/A")
        issues=[x for x in r["warnings"] if x["severity"]!="ok"]
        self.metrics["health"].setText("CHECK" if issues else "NORMAL")
        self.findings.setText("\n\n".join(w["title"]+": "+w["detail"] for w in r["warnings"]))
        self.system_box.setText("\n\n".join((f"PC: {r['computer']}",f"OS: {r['os']}",f"CPU: {r['processor']}",f"Cores / threads: {r['cpu_cores']} / {r['cpu_threads']}",f"RAM: {r['ram_total_gb']} GB",f"RAM available: {r['ram_available_gb']} GB",f"Boot time: {r['boot_time']}")))
        while self.drive_layout.count():
            item=self.drive_layout.takeAt(0)
            if item.widget():item.widget().deleteLater()
        for d in r["disks"]:
            self.drive_layout.addWidget(label(f"{d['mount']}: {d['free_gb']} GB free of {d['total_gb']} GB"))
            bar=QProgressBar();bar.setRange(0,100);bar.setValue(round(d["used_percent"]))
            self.drive_layout.addWidget(bar)
        self.event_box.setPlainText("\n\n".join(f"{e['time']} | {e['source']} ID {e['id']}\n{e['message']}" for e in r["events"]) or "No recent errors available.")
        self.refresh_crash_view()

    def refresh_crash_view(self,*_):
        if not self.report:return
        data=self.report.get("crashes",{});summary=data.get("summary",{})
        self.crash_summary.setText("App crashes: {application_crashes}   |   BSODs: {blue_screens}   |   Hardware errors: {hardware_reports}   |   Unexpected shutdowns: {unexpected_shutdowns}   |   Dumps: {dump_files_found}".format(**summary))
        term=self.crash_filter.text().casefold().strip();sections=[]
        for f in data.get("findings",[]):
            item=(f"{f['time']}   •   {f['category'].upper()}\n{f['title']} {f['code']}\n"
                f"IN SIMPLE ENGLISH: {f['meaning']}\nPOSSIBLE CAUSES: {f['possible_causes']}\n"
                f"WHAT TO TRY: {f['next_steps']}\nEVIDENCE: {f['source']} / Event {f['event_id']}\n{f['evidence']}")
            if not term or term in item.casefold():sections.append(item)
        if data.get("dumps") and not term:
            sections.append("DUMP FILES FOUND (contents NOT analyzed)\n"+"\n".join(d["name"]+" • "+str(d["size_mb"])+" MB" for d in data["dumps"]))
        self.crash_box.setPlainText(("\n"+"—"*40+"\n\n").join(sections) or "No matching crash evidence found. Logs may be unavailable or incomplete.")

    def open_tool(self,key):
        name,description,_=TOOLS[key]
        if QMessageBox.question(self,"Open Windows tool",description+"\n\nOpen "+name+"?",QMessageBox.Yes|QMessageBox.No)!=QMessageBox.Yes:return
        try:launch_tool(key)
        except Exception as e:QMessageBox.warning(self,"Tool unavailable",str(e))

    def export(self,ext):
        if not self.report:
            QMessageBox.information(self,"No report","Run a scan first.");return
        filename="kowalski-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"."+ext
        path,_=QFileDialog.getSaveFileName(self,"Save report",filename,"JSON (*.json)" if ext=="json" else "Text (*.txt)")
        if path:
            try:
                if ext=="json":diagnostics.export_json(self.report,path)
                else:diagnostics.export_text(self.report,path)
                QMessageBox.information(self,"Saved","Report saved. Review personal system details before sharing.")
            except OSError as e:QMessageBox.warning(self,"Export error",str(e))

def main():
    app=QApplication(sys.argv);app.setStyle("Fusion");app.setStyleSheet(CSS);app.setApplicationName("Kowalski")
    w=Kowalski();w.show();return app.exec()
if __name__=="__main__":raise SystemExit(main())
