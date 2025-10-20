import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2


@dataclass
class CameraInfo:
    index: int
    name: str | None = None
    path: str | None = None


def probe_indices(max_index: int, backend: int) -> list[int]:
    """Return indices that can be opened with OpenCV."""
    found: list[int] = []
    for idx in range(max_index + 1):
        cap = cv2.VideoCapture(idx, backend)
        if not cap.isOpened():
            cap.release()
            continue
        ok, _ = cap.read()
        cap.release()
        if ok:
            found.append(idx)
    return found


def iter_linux_devices() -> Iterator[tuple[int, str]]:
    """Yield (index, name) pairs for Linux video devices."""
    base = Path("/sys/class/video4linux")
    if not base.exists():
        return iter(())
    devices: list[tuple[int, str]] = []
    for node in base.glob("video*"):
        try:
            idx = int(node.name.replace("video", ""))
        except ValueError:
            continue
        name_file = node / "name"
        if name_file.exists():
            try:
                name = name_file.read_text(encoding="utf-8").strip()
            except OSError:
                continue
            devices.append((idx, name))
    return iter(devices)


def list_windows_devices() -> list[str]:
    """Return a best-effort list of camera names on Windows."""
    if os.name != "nt":
        return []
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-CimInstance Win32_PnPEntity | "
        "Where-Object { $_.PNPClass -in @('Camera','Image') } | "
        "Select-Object -ExpandProperty Name"
    ]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            text=True,
            capture_output=True,
            timeout=5
        )
    except OSError:
        return []
    output = result.stdout.strip()
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def gather_info(max_index: int, backend: int) -> list[CameraInfo]:
    indices = probe_indices(max_index, backend)
    infos: list[CameraInfo] = [CameraInfo(index=i) for i in indices]
    if sys.platform.startswith("linux"):
        name_map = dict(iter_linux_devices())
        for info in infos:
            info.path = f"/dev/video{info.index}"
            if info.index in name_map:
                info.name = name_map[info.index]
    elif os.name == "nt":
        names = list_windows_devices()
        for idx, info in enumerate(infos):
            info.name = names[idx] if idx < len(names) else None
    return infos


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sistemde kullanılabilir kamera indekslerini listeler."
    )
    parser.add_argument(
        "--max-index",
        type=int,
        default=10,
        help="Taranacak en yüksek kamera indeksi (varsayılan: 10)."
    )
    parser.add_argument(
        "--backend",
        type=int,
        default=cv2.CAP_ANY,
        help="OpenCV backend sabiti (varsayılan: CAP_ANY)."
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    infos = gather_info(args.max_index, args.backend)
    if not infos:
        print("Kamera bulunamadı.")
        return 1

    print("Bulunan kameralar:")
    for info in infos:
        details = [f"index={info.index}"]
        if info.path:
            details.append(f"path={info.path}")
        if info.name:
            details.append(f"name={info.name}")
        print(" - " + ", ".join(details))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
