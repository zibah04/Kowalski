"""Cautious, offline Windows game/app/BSOD event analysis. Never executes a dump."""
import os, json, re, subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter

STOP_CODES = {
 "0x0000000a":("IRQL_NOT_LESS_OR_EQUAL","A driver or Windows component accessed restricted memory.","Drivers, unstable RAM or overclocking.","Review recent driver changes; test memory; undo overclocks."),
 "0x0000001a":("MEMORY_MANAGEMENT","Windows detected a memory management problem.","RAM instability, drivers or system file corruption.","Run a memory test and review recent changes."),
 "0x0000003b":("SYSTEM_SERVICE_EXCEPTION","Windows encountered an error while running a system service.","Drivers, system files or unstable memory.","Review recent drivers and Windows integrity."),
 "0x00000050":("PAGE_FAULT_IN_NONPAGED_AREA","Windows accessed a memory address it could not use.","RAM, drivers, storage or security software.","Check RAM and storage and recent drivers."),
 "0x0000007b":("INACCESSIBLE_BOOT_DEVICE","Windows could not read the boot drive.","Storage hardware, controllers or firmware settings.","Back up data, check drive detection and firmware settings."),
 "0x0000009f":("DRIVER_POWER_STATE_FAILURE","A driver did not respond correctly to a sleep or power transition.","Device drivers, USB, Wi-Fi or graphics.","Check updates or rollbacks for drivers; note if sleep triggers it."),
 "0x000000d1":("DRIVER_IRQL_NOT_LESS_OR_EQUAL","A driver accessed memory incorrectly.","Faulty or incompatible device driver or RAM.","Review driver changes and analyze a minidump in WinDbg."),
 "0x000000ef":("CRITICAL_PROCESS_DIED","A critical Windows process unexpectedly stopped.","Corrupted files, storage, drivers or malware.","Back up important files and check Windows integrity."),
 "0x00000116":("VIDEO_TDR_FAILURE","The graphics card stopped responding and Windows could not recover it.","GPU driver, overheating, graphics instability or hardware.","Check temperature, remove overclocks, and update or roll back GPU driver."),
 "0x00000124":("WHEA_UNCORRECTABLE_ERROR","Windows reported a serious hardware-level error.","CPU, RAM, motherboard, power or unstable tuning.","Undo overclocks, inspect temperatures and WHEA events."),
 "0x00000133":("DPC_WATCHDOG_VIOLATION","A driver or hardware operation took too long.","Storage, chipset, GPU drivers or firmware.","Update trusted drivers and firmware; check storage health."),
 "0x00000139":("KERNEL_SECURITY_CHECK_FAILURE","Windows detected damaged critical data.","Drivers, memory instability or system corruption.","Inspect minidump, drivers and RAM.")
}
EXCEPTIONS = {
 "0xc0000005":("Memory access violation","The program tried to access memory that was not permitted.","A software bug, mod, incompatible overlay, graphics driver or unstable RAM.","Verify game files, disable mods/overlays, update driver, test RAM if multiple apps crash."),
 "0xc0000409":("Security check failure","The app detected damaged or invalid data and stopped.","App bugs, plugins or memory corruption.","Update the app and disable add-ons."),
 "0xe06d7363":("C++ exception","The app did not handle a C++ exception.","App error, dependent component or add-ons.","Update the app and inspect its own log."),
 "0xc000001d":("Illegal instruction","The application tried a CPU instruction the processor cannot execute.","Unsupported processor or incompatible app build.","Check minimum CPU requirements."),
 "0xc0000135":("Dependency missing","A component needed to launch the application could not be found.","Missing runtimes or application files.","Repair the application using official installers."),
 "0xc000007b":("Invalid program format","Windows could not load a program or library.","32/64-bit mismatch or corrupted libraries.","Reinstall the appropriate version; do not download random DLLs."),
 "0x887a0005":("Graphics device removed","The game lost access to the GPU.","Driver reset, overheating or graphics instability.","Check GPU temperatures and drivers; remove overclocks."),
 "0x887a0006":("Graphics device hung","The GPU stopped responding to the game.","GPU drivers, overlays, load or hardware instability.","Reduce graphics settings and disable overlays; check temperatures.")
}

def normalize_hex(code):
    if code is None:return ""
    s=str(code).strip().lower()
    try:
        if s.startswith("0x"): n=int(s,16)
        elif re.fullmatch(r"[+-]?\d+",s): n=int(s,10)
        elif re.fullmatch(r"[0-9a-f]{1,8}",s): n=int(s,16)
        else:return ""
        return f"0x{n & 0xffffffff:08x}"
    except ValueError:return ""

def extract_code(message,kind="app"):
    pattern=r"(?:bugcheck(?: was)?|stop code)\s*(?:is|of|:)?\s*(0x[0-9a-f]{1,8})" if kind=="bsod" else r"(?:exception code|error code|fault code)\s*:\s*(0x[0-9a-f]{1,8})"
    m=re.search(pattern,message or "",re.I)
    return normalize_hex(m.group(1)) if m else ""

def explain_event(event):
    provider=str(event.get("source",event.get("provider","")))
    log=str(event.get("log",""))
    msg=str(event.get("message") or "")[:5000]
    try:event_id=int(event.get("id") or 0)
    except (TypeError,ValueError):event_id=0
    m=re.search(r"(?:Faulting application name|Faulting application path|AppName)\s*[:=]\s*([^,\r\n]+)",msg,re.I)
    app=Path(m.group(1).strip().replace("\\","/")).name[:100] if m else ""
    low=(provider+" "+msg).lower()
    out=dict(time=str(event.get("time","")),source=provider,event_id=event_id,application=app,evidence=msg[:700],severity="info",category="other",code="",title="",meaning="",possible_causes="",next_steps="",certainty="Possible causes, not a confirmed diagnosis")
    if event_id==1001 and ("bugcheck" in low or (log.lower()=="system" and provider.lower()=="bugcheck")):
        code=normalize_hex(event.get("code")) or extract_code(msg,"bsod")
        name,meaning,causes,steps=STOP_CODES.get(code,("Unknown BSOD stop code","Windows stopped after a serious error.","Hardware, Windows or a device driver.","Analyze the dump with Microsoft WinDbg to investigate further."))
        out.update(category="bsod",severity="critical",code=code,title="Blue screen: "+name,meaning=meaning,possible_causes=causes,next_steps=steps)
    elif event_id==41 and "kernel-power" in low:
        out.update(category="unexpected_shutdown",severity="warning",title="Unexpected restart",meaning="The computer restarted without a clean shutdown; this does not prove what caused it.",possible_causes="Power loss, freeze, forced restart, overheating or BSOD.",next_steps="Look for related BugCheck or WHEA events near the same time.")
    elif event_id==6008 and "eventlog" in low:
        out.update(category="unexpected_shutdown",severity="warning",title="Unclean shutdown",meaning="Windows detected an unexpected previous shutdown.",possible_causes="Power issue, freeze, manual restart or BSOD.",next_steps="Compare nearby power, hardware and BugCheck events.")
    elif event_id in (17,18,19,46,47) and "whea" in low:
        out.update(category="hardware",severity="critical" if event_id in (18,46) else "warning",title="Hardware error report",meaning="Windows recorded a hardware-level error. Some errors are corrected automatically.",possible_causes="CPU, memory, PCIe devices or unstable firmware settings.",next_steps="Back up important files, inspect cooling and review the complete WHEA record.")
    elif event_id==4101 and "display" in low:
        out.update(category="gpu",severity="warning",title="Graphics driver timeout",meaning="The GPU driver stopped responding and Windows attempted recovery.",possible_causes="Driver, overheating or graphics instability.",next_steps="Check GPU temperature, clocks, overlays and graphics drivers.")
    elif event_id in (1000,1001,1002) and (log.lower()=="application" or "application error" in low or "windows error reporting" in low or "application hang" in low):
        code=normalize_hex(event.get("code")) or extract_code(msg)
        label,meaning,causes,steps=EXCEPTIONS.get(code,("Application crash","Windows recorded an unexpected app shutdown.","Software bug, missing files, drivers, compatibility or hardware instability.","Update and verify app files and investigate the app logs."))
        if event_id==1002 or "application hang" in low:
            label,meaning,causes,steps=("Application unresponsive","The app froze and did not respond to Windows.","Software bugs, memory pressure, disk delay or drivers.","Check resource usage and try without add-ons.")
        out.update(category="app",severity="warning",code=code,title=(app or "Application")+": "+label,meaning=meaning,possible_causes=causes,next_steps=steps)
    return out

def analyze_records(records,dumps=None):
    findings=[explain_event(e) for e in records]
    findings=[f for f in findings if f["category"]!="other"]
    counts=Counter((f["category"],f["application"],f["code"],f["title"]) for f in findings)
    for f in findings:f["repeat_count"]=counts[(f["category"],f["application"],f["code"],f["title"])]
    dumps=dumps or []
    return {"findings":findings,"dumps":dumps,"summary":{"application_crashes":sum(f["category"]=="app" for f in findings),"blue_screens":sum(f["category"]=="bsod" for f in findings),"hardware_reports":sum(f["category"]=="hardware" for f in findings),"unexpected_shutdowns":sum(f["category"]=="unexpected_shutdown" for f in findings),"dump_files_found":len(dumps)},"notice":"Event logs are clues, not confirmed diagnoses; minidumps are listed but not parsed."}

def get_windows_crash_events(days=14,max_events=160):
    if os.name!="nt":return []
    days=max(1,min(int(days),90));max_events=max(1,min(int(max_events),400))
    script=("$since=(Get-Date).AddDays(-"+str(days)+");$out=@();foreach($log in @('Application','System')){try{$events=Get-WinEvent -FilterHashtable @{LogName=$log;StartTime=$since} -MaxEvents 1200 -ErrorAction Stop;foreach($e in $events){if(($log -eq 'Application' -and $e.Id -in @(1000,1001,1002)) -or ($log -eq 'System' -and $e.Id -in @(41,6008,1001,4101,17,18,19,46,47))){$out += [pscustomobject]@{time=$e.TimeCreated.ToString('o');id=$e.Id;source=$e.ProviderName;log=$log;message=$e.Message};if($out.Count -ge "+str(max_events)+"){break}}}}catch{}};$out | Sort-Object time -Descending | ConvertTo-Json -Depth 4 -Compress")
    try:
        result=subprocess.run(["powershell.exe","-NoProfile","-NonInteractive","-Command",script],capture_output=True,text=True,encoding="utf-8-sig",errors="replace",timeout=50,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        data=json.loads(result.stdout) if result.stdout.strip() else []
        return [data] if isinstance(data,dict) else data if isinstance(data,list) else []
    except (OSError,subprocess.TimeoutExpired,ValueError):return []

def find_minidumps(max_files=30):
    if os.name!="nt":return []
    windir=Path(os.environ.get("SystemRoot",r"C:\Windows"))
    folder=windir/"Minidump"
    paths=list(folder.glob("*.dmp")) if folder.is_dir() else []
    if (windir/"MEMORY.DMP").is_file():paths.append(windir/"MEMORY.DMP")
    results=[]
    for p in paths:
        try:
            st=p.stat()
            results.append({"name":p.name,"path":str(p),"size_mb":round(st.st_size/1048576,2),"modified":datetime.fromtimestamp(st.st_mtime).astimezone().isoformat(timespec="seconds")})
        except OSError:pass
    return sorted(results,key=lambda x:x["modified"],reverse=True)[:max_files]

def crash_report(days=14):
    return analyze_records(get_windows_crash_events(days),find_minidumps())
