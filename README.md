# Bigbang OCR İzleme Paketi

Bu proje, canlı bir kamera akışından sayısal veriler toplar, Tesseract kullanarak OCR işlemi gerçekleştirir, elde edilen değerleri toplar ve sonuçları bir Streamlit panosu aracılığıyla sunar.
Windows için tasarlanmıştır ve görüntü yakalama ile ön işleme adımlarında OpenCV kullanır.

## ⚙️ Temel Özellikler
- İlgi alanı (ROI) seçmenize olanak tanıyan ve tanınan sayısal değerleri her saniye kaydeden canlı OCR döngüsü.
- Okumaları dakikalık ve saatlik CSV özetlerine dönüştüren periyodik işlemci.
- Canlı izleme, trend grafikleri ve CSV indirme seçenekleri sunan kullanıcı dostu Streamlit panosu.
- Tüm servisleri (toplayıcı, işlemci, pano) tek komutla başlatıp durduran, PID ve günlükleri yöneten başlatıcı betik.
- Sistem yeniden başlatılsa bile veri kaybını önleyen dosya tabanlı kalıcılık.

## 📁 Proje Dizini
```
src/
  collector.py        # Kamera yakalama, OCR işlemi ve readings.txt yazımı
  proccessor_txt.py   # Okumaları CSV özetlerine dönüştürür
  dashboard_txt.py    # Canlı ve geçmiş veriler için Streamlit arayüzü
  launcher.py         # Servisleri başlatır/durdurur ve PID/günlük yönetimini yapar
  settings.py         # Yollar, zamanlama sabitleri ve Tesseract konumu
  readings.txt        # Ham zaman damgalı okumalar (otomatik oluşturulur)
  minute_agg.csv      # Dakikalık özetler (otomatik oluşturulur)
  hour_agg.csv        # Saatlik özetler (otomatik oluşturulur)
  logs/               # Her servis için günlük dosyaları
  .pids/              # launcher.py tarafından oluşturulan PID dosyaları
requirements.txt      # Temel bağımlılıklar (gerekirse genişletilebilir)
venv/                 # İsteğe bağlı sanal ortam klasörü
```

## 🧩 Gereksinimler
1. Python 3.10+ (proje Python 3.12 ile test edilmiştir).
2. Windows üzerinde Tesseract OCR kurulu olmalıdır. `src/settings.py` dosyasındaki `TESSERACT_EXE` değişkenini doğru şekilde güncelleyin.
   Örnek:
   ```
   TESSERACT_EXE = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```
3. Python paketleri (`requirements.txt` içinde listelenmiştir, gerekirse ekleme yapabilirsiniz):
   ```
   opencv-python
   pytesseract
   numpy
   pandas
   streamlit
   streamlit-autorefresh   # Opsiyonel: Panoda otomatik yenilemeyi etkinleştirir
   ```

## 💻 Kurulum Adımları
```powershell
cd C:\Users\Talha Keskin\Documents\Projects\Bigbang
python -m venv venv
.\venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
# Eğer requirements.txt tüm bağımlılıkları içermiyorsa:
pip install numpy pandas streamlit streamlit-autorefresh
```

## 🚀 Servisleri Tek Tek Çalıştırma
> Öncelikle sanal ortamı etkinleştirin: `.\venv\Scripts\activate`

### 1. Toplayıcı (Collector)
```powershell
cd src
python collector.py
```
- Sayısal ekranın etrafındaki ROI alanını seçmek için `r` tuşuna basın.
- Çıkmak için `q` tuşuna basın.
- Çıktılar, zaman damgası ve sayısal değerler ile `src/readings.txt` dosyasına kaydedilir.

### 2. İşlemci (Processor)
```powershell
cd src
python proccessor_txt.py
```
- Sürekli çalışır ve her `PROCESSOR_PERIOD_SEC` (varsayılan 60 saniye) aralıkta uyanır.
- Atomik yazım yöntemiyle `minute_agg.csv` ve `hour_agg.csv` dosyalarını oluşturur.

### 3. Pano (Dashboard)
```powershell
cd src
streamlit run dashboard_txt.py
```
- Varsayılan sayfa başlığı: `dys OCR Dashboard`
- Kenar çubuğu kontrolleri:
  - Canlı veri penceresi boyutu
  - Eşik alarmı
  - Tablo görünümü seçenekleri
  - Otomatik yenileme (gerektirir `streamlit-autorefresh`)
- Sekmeler: Canlı veriler, dakikalık ve saatlik özetler (CSV indirme butonları dahil)

## 🧠 Başlatıcıyı Kullanma
`launcher.py`, her bileşeni kendi konsolunda (Windows üzerinde) başlatır ve PID dosyalarını `src/.pids` altında saklar.

```powershell
cd src
python launcher.py start   # Collector, Processor ve Dashboard başlatılır
python launcher.py status  # Çalışan süreçleri listeler
python launcher.py stop    # Tüm süreçleri durdurur (Windows'ta taskkill kullanır)
```

> Günlükler `src/logs/{collector,processor,dashboard}.log` dosyalarına kaydedilir. Sorun durumunda bu dosyaları kontrol edin.

## ⚙️ Yapılandırma Notları
- Tüm çalışma zamanı sabitleri `settings.py` dosyasında yer alır.
  - `SAMPLE_PERIOD_SEC`: Toplayıcının ne sıklıkta veri kaydedeceğini belirler.
- Dosya yollarını değiştirirseniz, tüm modüllerin senkron kalması için `settings.py` içinde güncellemeler yapın.
- Kodlama: Dosyalar UTF-8 ile yazılır. Türkçe karakterlerde bozulma görüyorsanız, düzenleyicinizin ve terminalinizin UTF-8 kullandığından emin olun.

## 🔄 Veri Akışı
1. Toplayıcı: Kamera karelerini alır, ön işler (gri tonlama, bilateral filtre, adaptif eşikleme, morfoloji, yeniden boyutlandırma), Tesseract ile yalnızca sayısal karakterleri tanır ve sonuçları kaydeder.
2. İşlemci: `readings.txt` dosyasını okur, verileri DataFrame’e aktarır ve toplulaştırır.
3. Pano: Ham verileri ve özet CSV’leri okuyarak Streamlit grafikleri üzerinden canlı olarak görüntüler.

## 🧩 Sorun Giderme
- **Kamera açılamıyor:** Farklı kamera indekslerini deneyin (0/1/2) veya çakışan uygulamaları kapatın.
- **Tesseract bulunamadı:** `TESSERACT_EXE` yolunu doğrulayın ve Tesseract’ın kurulu olduğundan emin olun.
- **Pano veri göstermiyor:** Toplayıcının çalıştığını ve ROI alanının doğru ayarlandığını kontrol edin; `src/readings.txt` dosyasını inceleyin.
- **CSV dosyaları eksik:** İşlemci çalışmaya başladığında otomatik olarak oluşturur; birkaç saniye bekleyin veya `proccessor_txt.py`'yi manuel olarak çalıştırın.
- **Otomatik yenileme uyarısı:** `streamlit-autorefresh` kütüphanesini yükleyin veya bu özelliği devre dışı bırakın.
- **Headless OpenCV:** GUI desteği yoksa collector çıkış yapar; `opencv-python-headless` yerine `opencv-python` yükleyin.

## 🧭 GitHub README için Önerilen Sonraki Adımlar
- Bu taslak halihazırda Markdown uyumlu olduğu için doğrudan README.md olarak kullanılabilir.
- Varsa, pano ve kamera yakalama işlemini gösteren ekran görüntüleri veya GIF’ler ekleyin.
- Gelecek geliştirmeleri (ör. alarm entegrasyonları, veritabanı kaydı, Docker kurulumu) bir “Yol Haritası (Roadmap)” bölümünde belgeleyin.
