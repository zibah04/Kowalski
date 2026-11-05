"""Local PC diagnostics and export."""
import json,os,platform,psutil,socket,subprocess
from datetime import datetime
from pathlib import Path
from . import crashes

def disk_data():
    result=[]
    for p in psutil.disk_partitions(all=False):
        try:
            u=psutil.disk_usage(p.mountpoint)
            if u.total:result.append({"mount":p.mountpoint,"filesystem":p.fstype,"total_gb":round(u.total/2**30,1),"free_gb":round(u.free/2**30,1),"used_percent":round(u.percent,1)})
        except (OSError,PermissionError):pass
    return result

def win_event_errors(limit=12):
    if os.name!="nt":return []
    script="Get-WinEvent -FilterHashtable @{LogName='System';Level=1,2;StartTime=(Get-Date).AddDays(-7)} -MaxEvents "+str(min(int(limit),40))+" -ErrorAction SilentlyContinue | Select-Object TimeCreated,Id,ProviderName,Message | ConvertTo-Json -Depth 3 -Compress"
    try:
        p=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script],capture_output=True,text=True,encoding="utf-8-sig",errors="replace",timeout=25,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        data=json.loads(p.stdout) if p.stdout.strip() else []
        if isinstance(data,dict):data=[data]
        return [{"time":str(e.get("TimeCreated","")),"id":e.get("Id"),"source":str(e.get("ProviderName","")),"message":str(e.get("Message",""))[:380]} for e in data]
    except (OSError,subprocess.TimeoutExpired,ValueError,TypeError):return []

def snapshot(include_events=True):
    m=psutil.virtual_memory();cpu=psutil.cpu_percent(interval=0.25);disks=disk_data()
    warnings=[]
    if cpu>=90:warnings.append({"severity":"warning","title":"High CPU use","detail":f"CPU is {cpu:.0f}% busy. Check Task Manager."})
    if m.percent>=85:warnings.append({"severity":"warning","title":"Memory pressure","detail":f"RAM usage is {m.percent:.0f}%. Close unneeded applications."})
    for d in disks:
        if d["used_percent"]>=90:warnings.append({"severity":"warning","title":"Low disk space on "+d["mount"],"detail":f"Only {d['free_gb']} GB is free."})
    if not warnings:warnings.append({"severity":"ok","title":"No immediate resource warnings","detail":"Current CPU, RAM and disk thresholds look normal. This does not prove all hardware is healthy."})
    return {"captured_at":datetime.now().astimezone().isoformat(timespec="seconds"),"computer":socket.gethostname(),"os":platform.platform(),"architecture":platform.machine(),"processor":platform.processor() or "Unknown","cpu_cores":psutil.cpu_count(logical=False),"cpu_threads":psutil.cpu_count(),"cpu_percent":cpu,"ram_total_gb":round(m.total/2**30,1),"ram_used_percent":round(m.percent,1),"ram_available_gb":round(m.available/2**30,1),"boot_time":datetime.fromtimestamp(psutil.boot_time()).isoformat(timespec="seconds"),"disks":disks,"warnings":warnings,"events":win_event_errors() if include_events else [],"crashes":crashes.crash_report() if include_events else crashes.analyze_records([]),"windows":os.name=="nt"}

def export_json(report,path):
    Path(path).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
def export_text(report,path):
    lines=["KOWALSKI | PC DIAGNOSTICS REPORT","="*45,"Captured: "+report["captured_at"],"PC: "+report["computer"],"OS: "+report["os"],"CPU: "+report["processor"],f"RAM: {report['ram_total_gb']} GB ({report['ram_used_percent']}% used)","","DRIVES"]
    lines += [f"{d['mount']}: {d['free_gb']} GB free of {d['total_gb']} GB" for d in report["disks"]]
    lines += ["","RESOURCE FINDINGS"]
    lines += [f"{w['title']}: {w['detail']}" for w in report["warnings"]]
    lines += ["","CRASH DIAGNOSTICS (POSSIBLE CAUSES, NOT PROVEN)"]
    for f in report.get("crashes",{}).get("findings",[]):
        lines += [f["title"]+" "+f["code"],"Meaning: "+f["meaning"],"Possible causes: "+f["possible_causes"],"Suggested step: "+f["next_steps"],""]
    lines += ["Minidumps found: "+str(len(report.get("crashes",{}).get("dumps",[])))+" (not analyzed)","Review reports before sharing: they may contain PC information."]
    Path(path).write_text("\n".join(lines),encoding="utf-8")
