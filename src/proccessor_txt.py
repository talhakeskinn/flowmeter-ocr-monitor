import os
import time
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from settings import (
    READINGS_TXT, MINUTE_AGG_CSV, HOUR_AGG_CSV,
    LOG_FILE, PROCESSOR_PERIOD_SEC
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
log = logging.getLogger("processor")

# ---------- IO helpers ----------
def safe_write_csv(df: pd.DataFrame, target: Path):
    tmp = target.with_suffix(target.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, target)  # atomik

def load_readings(limit_minutes: int | None = None) -> pd.DataFrame:
    """
    readings.txt -> DataFrame(ts: datetime64, value: float)
    Satır formatı: ISO_TS \t "v1, v2, ..."
    """
    if not READINGS_TXT.exists():
        return pd.DataFrame(columns=["ts", "value"])

    rows: list[tuple[datetime, float]] = []
    with open(READINGS_TXT, "r", encoding="utf-8", errors="ignore") as f:
        for i, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or "\t" not in line:
                continue
            ts_str, values_str = line.split("\t", 1)
            try:
                ts = pd.to_datetime(ts_str)
            except Exception:
                log.debug("Zaman parse atlandı (satır %s): %s", i, ts_str)
                continue
            for p in values_str.split(","):
                p = p.strip()
                if not p:
                    continue
                try:
                    v = float(p)
                    rows.append((ts, v))
                except Exception:
                    log.debug("Float parse atlandı (satır %s): %s", i, p)

    df = pd.DataFrame(rows, columns=["ts", "value"])
    if df.empty:
        return df
    df = df.sort_values("ts")
    if limit_minutes:
        cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(minutes=limit_minutes)
        df = df[df["ts"] >= cutoff]
    return df

def aggregate_and_write(df: pd.DataFrame):
    # Boşsa başlık dosyalarını hazırla
    if df.empty:
        for path in (MINUTE_AGG_CSV, HOUR_AGG_CSV):
            if not path.exists():
                safe_write_csv(pd.DataFrame(columns=["bucket_start","cnt","avg","min","max"]), path)
        return

    # dakika
    m = df.copy()
    m["bucket_start"] = m["ts"].dt.floor("min")
    g = m.groupby("bucket_start")["value"].agg(["count", "mean", "min", "max"]).reset_index()
    g.rename(columns={"count": "cnt", "mean": "avg"}, inplace=True)
    safe_write_csv(g, MINUTE_AGG_CSV)

    # saat
    h = df.copy()
    h["bucket_start"] = h["ts"].dt.floor("H")
    gh = h.groupby("bucket_start")["value"].agg(["count", "mean", "min", "max"]).reset_index()
    gh.rename(columns={"count": "cnt", "mean": "avg"}, inplace=True)
    safe_write_csv(gh, HOUR_AGG_CSV)

def run_once():
    df = load_readings()
    aggregate_and_write(df)
    log.info("Aggregates updated → %s , %s", MINUTE_AGG_CSV.name, HOUR_AGG_CSV.name)

def run_forever(period_sec: int):
    while True:
        try:
            run_once()
        except Exception:
            log.exception("Processor döngü hatası.")
        time.sleep(period_sec)

def main():
    log.info("Processor başlıyor. Source: %s", READINGS_TXT)
    run_forever(PROCESSOR_PERIOD_SEC)

if __name__ == "__main__":
    main()
