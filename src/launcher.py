import sys, os, subprocess, time, json, signal
from pathlib import Path

# Proje kökü = bu dosyanın olduğu yer
BASE = Path(__file__).resolve().parent
PY = sys.executable  # venv içindeki python

# Dosya yolları
COLLECTOR = BASE / "collector.py"
PROCESSOR = BASE / "processor_txt.py"
DASHBOARD = BASE / "dashboard_txt.py"
PID_DIR = BASE / ".pids"
LOG_DIR = BASE / "logs"

PID_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

def _pid_file(name: str) -> Path:
    return PID_DIR / f"{name}.pid"

def _is_running(pid: int) -> bool:
    try:
        # Windows/Linux uyumlu kaba kontrol
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def _spawn(name: str, cmd: list[str], cwd: Path | None = None) -> int:
    """Süreci başlat, stdout/stderr log dosyasına yönlendir, PID kaydet."""
    log_path = LOG_DIR / f"{name}.log"
    log_f = open(log_path, "a", buffering=1, encoding="utf-8")  # line-buffered
    # Yeni konsol penceresi istersen: creationflags=subprocess.CREATE_NEW_CONSOLE (Windows)
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_CONSOLE  # ayrı pencere
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd or BASE),
        stdout=log_f,
        stderr=log_f,
        creationflags=creationflags
    )
    _pid_file(name).write_text(str(p.pid), encoding="utf-8")
    print(f"[OK] {name} started (pid={p.pid}) | logs/{name}.log")
    return p.pid

def start():
    # 1) collector
    _spawn(
        "collector",
        [PY, str(COLLECTOR)]
    )
    time.sleep(0.3)

    # 2) processor
    _spawn(
        "processor",
        [PY, str(PROCESSOR)]
    )
    time.sleep(0.3)

    # 3) dashboard (streamlit run)
    _spawn(
        "dashboard",
        [PY, "-m", "streamlit", "run", str(DASHBOARD)]
    )

def stop():
    for name in ["dashboard","processor","collector"]:
        pf = _pid_file(name)
        if not pf.exists():
            print(f"[i] {name}: pid yok")
            continue
        pid = int(pf.read_text(encoding="utf-8").strip() or "0")
        if pid <= 0:
            print(f"[i] {name}: geçersiz pid")
            pf.unlink(missing_ok=True)
            continue
        print(f"[-] stopping {name} (pid={pid}) ...")
        if os.name == "nt":
            # Windows: taskkill ile çocukları da öldür
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        pf.unlink(missing_ok=True)
    print("[OK] stopped")

def status():
    any_running = False
    for name in ["collector","processor","dashboard"]:
        pf = _pid_file(name)
        if not pf.exists():
            print(f"[ ] {name}: not running")
            continue
        pid = int(pf.read_text(encoding="utf-8").strip() or "0")
        running = _is_running(pid)
        print(f"[{'✓' if running else 'x'}] {name}: pid={pid} {'(running)' if running else '(dead pid)'}")
        if not running:
            pf.unlink(missing_ok=True)
        any_running = any_running or running
    if any_running:
        print("\nLoglar: logs/collector.log, logs/processor.log, logs/dashboard.log")

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"start","stop","status"}:
        print("Kullanım: python launcher.py [start|stop|status]")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    else:
        status()

if __name__ == "__main__":
    main()
