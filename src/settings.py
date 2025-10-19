from pathlib import Path

# Proje kökü (değiştirmek istersen burayı düzenle)
BASE_DIR = Path(__file__).resolve().parent

# Dosya yolları
READINGS_TXT = BASE_DIR / "readings.txt"
MINUTE_AGG_CSV = BASE_DIR / "minute_agg.csv"
HOUR_AGG_CSV = BASE_DIR / "hour_agg.csv"
LOG_FILE = BASE_DIR / "app.log"

# Tesseract (Windows) — kurulum yolunu doğrula ve yolunu gir
# Örn: r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_EXE = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# OCR örnekleme aralığı (saniye)
SAMPLE_PERIOD_SEC = 1.0

# Processor çalışma periyodu (saniye)
PROCESSOR_PERIOD_SEC = 60

# Streamlit dashboard'ında ham veri penceresi (dakika)
DASH_LIVE_WINDOW_MIN = 30
