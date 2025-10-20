import os
import re
import time
import logging
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytesseract

from settings import (
    READINGS_TXT, LOG_FILE, TESSERACT_EXE,
    SAMPLE_PERIOD_SEC, CAMERA_INDEX_CANDIDATES
)

# ---------- Logging ----------
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8")
        ],
    )
setup_logging()
log = logging.getLogger("collector")

# ---------- OCR helpers ----------
def ensure_tesseract_path():
    if os.name == "nt":
        if TESSERACT_EXE and Path(TESSERACT_EXE).exists():
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
            log.info("Tesseract path set (Windows): %s", TESSERACT_EXE)
        else:
            raise SystemExit(
                "Windows ortamında Tesseract yolunu bulamadım. "
                "settings.TESSERACT_EXE değerini kurulum yoluyla güncelleyin."
            )
    else:
        if TESSERACT_EXE and Path(TESSERACT_EXE).exists():
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE
            log.info("Tesseract path set: %s", TESSERACT_EXE)
        else:
            system_cmd = shutil.which("tesseract")
            if system_cmd:
                pytesseract.pytesseract.tesseract_cmd = system_cmd
                log.info("Tesseract PATH üzerinden bulundu: %s", system_cmd)
            else:
                raise SystemExit(
                    "Linux ortamında Tesseract bulunamadı. 'sudo apt install tesseract-ocr' "
                    "komutuyla kurulum yapın veya settings.TESSERACT_EXE yolunu güncelleyin."
                )

def preprocess_for_digits(img_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    white_ratio = cv2.countNonZero(th) / th.size
    if white_ratio < 0.45:
        th = cv2.bitwise_not(th)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((3,3), np.uint8), iterations=1)
    th = cv2.resize(th, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    return th

def ocr_text(img_bin: np.ndarray) -> str:
    cfg = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789:.,'
    try:
        return pytesseract.image_to_string(img_bin, config=cfg).strip()
    except Exception as e:
        log.exception("Tesseract okuyamadı: %s", e)
        return ""

def extract_floats(raw_text: str) -> list[float]:
    clean = raw_text.replace(':', '.').replace(',', '.')
    nums = re.findall(r'\d+(?:\.\d+)?', clean)
    vals = []
    for n in nums:
        try:
            vals.append(float(n))
        except ValueError:
            log.debug("float parse hata: %s", n)
    return vals

def append_to_txt(path: Path, floats: list[float]) -> None:
    ts = datetime.now().isoformat(timespec="seconds")
    line = f"{ts}\t" + ", ".join(map(str, floats)) + "\n"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line)
            # İstersen tam garanti için:
            # f.flush(); os.fsync(f.fileno())
    except Exception as e:
        log.exception("TXT'ye yazılamadı: %s", e)

def assert_gui_available():
    try:
        cv2.namedWindow("test")
        cv2.destroyAllWindows()
    except cv2.error as e:
        raise SystemExit(
            "GUI açılamıyor. Muhtemelen headless OpenCV kurulu.\n"
            "Çözüm: 'pip uninstall -y opencv-python-headless' ve 'pip install opencv-python'."
        ) from e

# ---------- Main loop ----------
def main():
    ensure_tesseract_path()
    assert_gui_available()

    READINGS_TXT.touch(exist_ok=True)  # dosya yoksa oluştur
    log.info("Kayıt dosyası: %s", READINGS_TXT)

    # Kamera açma (retry ile)
    cam_index_candidates = CAMERA_INDEX_CANDIDATES
    cap = None
    for idx in cam_index_candidates:
        cap_try = cv2.VideoCapture(idx)
        if cap_try.isOpened():
            cap = cap_try
            log.info("Kamera açıldı: index=%s", idx)
            break
        cap_try.release()

    if cap is None:
        raise SystemExit("Kamera açılamadı. Başka index deneyin (0/1/2) veya "
                         "kamerayı kullanan uygulamayı kapatın.")

    WINDOW_MAIN = "Canli OCR"
    WINDOW_PROC = "ROI - islenmis"
    cv2.namedWindow(WINDOW_MAIN, cv2.WINDOW_NORMAL)
    roi = None
    next_time = time.monotonic()
    last_values: list[float] = []

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                log.warning("Kare alınamadı. 100ms bekle.")
                time.sleep(0.1)
                continue

            disp = frame.copy()
            if roi is None:
                cv2.putText(disp, "ROI icin 'r', cikis icin 'q'.",
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,255), 2)
            else:
                x, y, w, h = roi
                cv2.rectangle(disp, (x, y), (x+w, y+h), (0,255,0), 2)
                now = time.monotonic()
                if now >= next_time:
                    try:
                        crop = frame[y:y+h, x:x+w]
                        proc = preprocess_for_digits(crop)
                        raw = ocr_text(proc)
                        vals = extract_floats(raw)
                        last_values = vals
                        if vals:
                            append_to_txt(READINGS_TXT, vals)
                        cv2.imshow(WINDOW_PROC, proc)
                    except Exception:
                        log.exception("OCR döngüsünde hata.")
                    finally:
                        next_time += SAMPLE_PERIOD_SEC

                show = " | ".join(map(str, last_values)) if last_values else "(yok)"
                cv2.putText(disp, f"Values: {show}",
                            (x, max(y-10, 30)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

            cv2.imshow(WINDOW_MAIN, disp)
            k = cv2.waitKey(1) & 0xFF
            if k == ord('q'):
                break
            if k == ord('r'):
                try:
                    r = cv2.selectROI(WINDOW_MAIN, frame, fromCenter=False, showCrosshair=True)
                    roi = tuple(map(int, r)) if r and sum(r) > 0 else None
                    cv2.waitKey(1)
                except cv2.error:
                    log.exception("ROI seçiminde hata.")

    except KeyboardInterrupt:
        log.info("Kullanıcı durdurdu (Ctrl+C).")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        log.info("Collector kapandı.")

if __name__ == "__main__":
    main()
