import pandas as pd
import streamlit as st
from pathlib import Path

from settings import (
    READINGS_TXT, MINUTE_AGG_CSV, HOUR_AGG_CSV,
    DASH_LIVE_WINDOW_MIN
)

# ---------- Sayfa ----------
st.set_page_config(page_title="OCR Dashboard", layout="wide")
st.title("📊 OCR Dashboard")

# ---------- Üst bilgi / Yardım ----------
with st.expander("ℹ️ Sistem Durumu & Hızlı Başlangıç", expanded=True):
    st.markdown("""
**Amaç:** Kameradan OCR ile okunan **sayısal değerleri** canlı ve geçmişe dönük olarak izlemek.

**Çalışma Şekli:**
1. **collector.py** her saniye `readings.txt` dosyasına *zaman damgası + değerler* yazar.
2. **processor_txt.py** periyodik olarak `readings.txt`’yi işler → `minute_agg.csv` ve `hour_agg.csv`.
3. **Bu dashboard** dosyaları okuyup **grafik/tablolar** oluşturur.

**Kısayol:**
- ROI seçmek için collector penceresinde **R**, çıkmak için **Q**.
- Bu panel: `python -m streamlit run dashboard_txt.py` ile açılır.
""")

# ---------- Sidebar ----------
st.sidebar.header("Ayarlar")
live_window_min = st.sidebar.slider("Ham veri penceresi (dakika)", 5, 240, DASH_LIVE_WINDOW_MIN, 5)
show_tables = st.sidebar.checkbox("Tabloları göster", value=True)
use_threshold = st.sidebar.checkbox("Eşik/uyarı kullan", value=False)
threshold = st.sidebar.number_input("Uyarı eşiği", value=100.0, step=1.0, format="%.3f")
auto_refresh = st.sidebar.checkbox("Otomatik yenile (5 sn)", value=False)
if st.sidebar.button("Yenile"):
    st.cache_data.clear()
    st.rerun()
if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=5000, key="auto_refresh_key")
    except Exception:
        st.sidebar.warning("Oto-yenile için: pip install streamlit-autorefresh")

# ---------- Veri Yükleme ----------
def _safe_float(s: str):
    try: return float(s)
    except: return None

@st.cache_data(ttl=5)
def load_raw_last_minutes(minutes: int) -> pd.DataFrame:
    rows = []
    if not READINGS_TXT.exists():
        return pd.DataFrame(columns=["ts","value"])
    with open(READINGS_TXT, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or "\t" not in line: continue
            ts_str, vals = line.split("\t", 1)
            try:
                ts = pd.to_datetime(ts_str)
            except: continue
            for p in vals.split(","):
                p = p.strip()
                v = _safe_float(p)
                if v is not None: rows.append((ts, v))
    df = pd.DataFrame(rows, columns=["ts","value"])
    if df.empty: return df
    df = df.sort_values("ts")
    cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(minutes=minutes)
    df = df[df["ts"] >= cutoff]
    return df

@st.cache_data(ttl=5)
def load_agg(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["bucket_start","cnt","avg","min","max"])
    try:
        df = pd.read_csv(path)
        if "bucket_start" in df.columns:
            df["bucket_start"] = pd.to_datetime(df["bucket_start"])
        return df
    except:
        return pd.DataFrame(columns=["bucket_start","cnt","avg","min","max"])

def kpis_for_raw(df: pd.DataFrame):
    if df.empty: return 0, None, None
    return len(df), df["value"].iloc[-1], df["value"].mean()

def download_df_button(df: pd.DataFrame, filename: str, label: str):
    if df.empty:
        st.caption("İndirilecek veri yok.")
        return
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), filename, "text/csv")

# ---------- Sekmeler ----------
tab1, tab2, tab3 = st.tabs(["🔴 Canlı/Anlık", "🕒 Dakika Özeti", "🗓 Saat Özeti"])

with tab1:
    st.subheader("Ham Değerler (son N dakika)")
    df = load_raw_last_minutes(live_window_min)
    if df.empty:
        st.warning("readings.txt yok veya içinde uygun veri bulunamadı. collector.py çalışıyor mu?")
    else:
        df["ts"] = pd.to_datetime(df["ts"])
        count, last_val, mean_val = kpis_for_raw(df)
        c1, c2, c3 = st.columns(3)
        c1.metric("Kayıt sayısı", count)
        c2.metric("Son değer", f"{last_val:.3f}" if last_val is not None else "-")
        c3.metric("Ortalama", f"{mean_val:.3f}" if mean_val is not None else "-")

        # Eşik uyarısı
        if use_threshold and last_val is not None:
            if last_val > threshold:
                st.error(f"⚠️ Son değer eşiği aştı: {last_val:.3f} > {threshold:.3f}")
            else:
                st.success(f"✓ Son değer eşik altında: {last_val:.3f} ≤ {threshold:.3f}")

        st.line_chart(df.set_index("ts")["value"])
        if show_tables:
            st.dataframe(df.tail(200), width='stretch')
        download_df_button(df, "raw_window.csv", "Ham veriyi indir (CSV)")

with tab2:
    st.subheader("Dakika Bazlı Özet")
    m = load_agg(MINUTE_AGG_CSV).sort_values("bucket_start")
    if m.empty:
        st.info("minute_agg.csv henüz oluşmadı. processor_txt.py çalışıyor mu?")
    else:
        last = m.iloc[-1]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Adet", int(last["cnt"]))
        k2.metric("Ortalama", f"{last['avg']:.3f}")
        k3.metric("Min", f"{last['min']:.3f}")
        k4.metric("Max", f"{last['max']:.3f}")

        st.area_chart(m.set_index("bucket_start")[["avg"]])
        st.line_chart(m.set_index("bucket_start")[["min","max"]])
        if show_tables:
            st.dataframe(m.tail(200), width='stretch')
        download_df_button(m, "minute_agg.csv", "Dakika özetini indir (CSV)")

with tab3:
    st.subheader("Saat Bazlı Özet")
    h = load_agg(HOUR_AGG_CSV).sort_values("bucket_start")
    if h.empty:
        st.info("hour_agg.csv henüz oluşmadı.")
    else:
        st.line_chart(h.set_index("bucket_start")[["avg"]])
        if show_tables:
            st.dataframe(h.tail(200), width='stretch')
        download_df_button(h, "hour_agg.csv", "Saat özetini indir (CSV)")

# ---------- Sorun Giderme ----------
with st.expander("🛠 Sorun Giderme İpuçları"):
    st.markdown(f"""
- **Collector çalışmıyor** → `python collector.py` (pencerede **R** ile ROI seç, **Q** ile çık).
- **Processor çalışmıyor** → `python processor_txt.py` (her {DASH_LIVE_WINDOW_MIN} sn’de CSV günceller).
- **`readings.txt` yok/boş** → collector çalışmıyordur veya ROI’nin içi boş/okunamıyordur.
- **Tesseract bulunamadı** → `settings.py` içindeki `TESSERACT_EXE` yolunu kontrol et.
- **CSV yarım yükleniyor** → processor atomik yazıyor; birkaç saniye sonra yeniden dene.
""")
