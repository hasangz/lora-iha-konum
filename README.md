# LoRa Tabanlı Çok Alıcılı Sistem ile İHA Konum Kestirimi – Saha Testi Analizi

Bu depo, "LoRa Tabanlı Çok Alıcılı Sistem ile İHA Konum Tespiti" başlıklı yüksek lisans tezinde kullanılan saha testi verilerini ve analiz yazılımını içerir. Yazılım, İHA'ya monte edilmiş bir LoRa vericinin (beacon) paketlerinin yerdeki üç alıcı istasyonda ölçülen RSSI ve SNR değerlerinden İHA'nın yatay konumunu kestirir ve kestirimleri referans konumla karşılaştırır.

Analiz tezin 3.5. bölümünde (Deneysel Yöntem) anlatılan adımları izler. Kod içindeki eşitlik numaraları tezdeki numaralara karşılık gelir.

## Kurulum

Python 3.9 veya üzeri gereklidir.

```bash
pip install -r requirements.txt
```

## Çalıştırma

```bash
python analiz.py
```

Analiz `config.json` dosyasındaki ayarlarla tüm adımları çalıştırır, sonuçları `sonuclar/` klasörüne yazar ve özet tabloyu ekrana basar. Farklı bir yapılandırma veya çıktı klasörü için:

```bash
python analiz.py --config config.json --cikti sonuclar
```

## Klasör yapısı

```
lora-iha-konum/
├── analiz.py              Ana betik: tüm analizi uçtan uca çalıştırır
├── config.json            Test tarihi, orijin, istasyon koordinatları, dosya yolları ve eşik değerleri
├── requirements.txt
├── LICENSE
├── data/ham/              Ham saha kayıtları
│   ├── ucusN_aliciK.xlsx  N. uçuşta K. alıcı istasyonun bilgisayar yazılımıyla aldığı kayıt
│   └── ucusN_rc.csv       N. uçuşta İHA uzaktan kumandasının (RC) konum/yükseklik kaydı
├── lorakonum/             Analiz modülleri
│   ├── geo.py             Coğrafi → yerel Doğu-Kuzey dönüşümü, istasyon konumları
│   ├── kayitlar.py        Kayıt okuma, paket ayrıştırma, NMEA sağlama toplamı, bozuk paket ayıklama
│   ├── referans.py        RC kaydı, RC–beacon zaman hizalaması (Eş. 3.21), paket bazında referans konum
│   ├── bekleme.py         Bekleme (hover) noktalarının otomatik tespiti ve ortanca RSSI/SNR
│   ├── model.py           Log-mesafe modeli kalibrasyonu (Eş. 3.9, 3.22), mesafe kestirimi (Eş. 3.8, 3.11), SNR ağırlığı (Eş. 3.19)
│   ├── cozum.py           EKK ve AEKK trilaterasyonu, sönümlü Gauss-Newton (Eş. 3.16, 3.17, 3.23)
│   ├── degerlendirme.py   Birini dışarıda bırakma ve çapraz uçuş doğrulaması, başarım ölçütleri (Eş. 3.24–3.26)
│   └── grafik.py          Sonuç grafikleri
└── sonuclar/              analiz.py tarafından üretilir
```

## Analiz adımları

1. **Kayıtların okunması ve temizlenmesi:** Her istasyonun kaydındaki `LORA| TXSAYAC`, `RSSI` ve `SNR` satırları paketlerde birleştirilir. Sayaç alanı bozulmuş paketler, (alım zamanı − TXSAYAC × paket periyodu) değerinin sabit kalmasından yararlanılarak ayıklanır. Beacon GNSS cümleleri sağlama toplamı ve konum aralığıyla denetlenir.
2. **Referans konum:** Beacon'ın paketlerde gönderdiği GNSS konumu ile RC kaydı arasındaki zaman kayması, iki kaynak arasındaki ortanca konum farkını en küçükleyecek şekilde bulunur. Her paketin gönderim anındaki konum, yerden yükseklik ve yatay hız RC kaydından aradeğerlenir.
3. **Bekleme noktaları:** Yatay hızı 0,8 m/s'nin altında ve yüksekliği 15 m'nin üzerinde olan en az 6 ardışık paket bir bekleme noktasıdır. Her istasyon için RSSI ve SNR ortancası alınır. Üç istasyonun da ölçümünün bulunduğu noktalar değerlendirilir.
4. **Kalibrasyon:** Her istasyona ayrı A, tüm istasyonlara ortak n kestirilir (karşılaştırma için her istasyona ayrı n seçeneği de hesaplanır).
5. **Konum kestirimi:** RSSI'dan eğik ve yatay mesafeler hesaplanır; konum ağırlıksız EKK ve SNR ağırlıklı AEKK ile, istasyonların ağırlık merkezinden başlayan sönümlü Gauss-Newton yinelemesiyle bulunur.
6. **Doğrulama:** Her nokta kendisi dışındaki noktalarla (LOO) ve yalnızca diğer uçuşun verisiyle (çapraz uçuş) kalibre edilen modelle çözülür.

## Çıktılar

| Dosya | İçerik |
|---|---|
| `paket_istatistikleri.csv` | Uçuş ve istasyon başına geçerli paket sayısı, TXSAYAC aralığı, PDR, ortalama RSSI/SNR |
| `zaman_hizalama.csv` | RC–beacon zaman kayması, iki kaynak arasındaki ortanca fark, PC–GNSS saat farkı |
| `kalibrasyon.json` | Tüm veriyle kestirilen A ve n değerleri, model artıklarının standart sapması |
| `bekleme_noktalari.csv` | Değerlendirilen bekleme noktaları: referans konum, ortanca RSSI/SNR, modelden sapma, EKK/AEKK kestirimleri ve hataları (LOO, ortak n) |
| `ozet.json` | Tüm doğrulama/kalibrasyon/yöntem bileşimleri için ortalama, ortanca, RMSE ve 95. yüzdelik hata |
| `*.png` | Test düzeni, RSSI–mesafe ilişkisi, uçuş başına kestirim haritaları, hata dağılımı |

## Veri hakkında

- Testler 16 Ekim 2026'da 39°46′13″ K, 32°02′54″ D yakınındaki açık bir alanda yapılmıştır. Kayıtlardaki zamanlar UTC'dir; RC kaydı yerel saattedir (UTC+3).
- Alıcı 1 ve Alıcı 3'ün konumları kendi GNSS kayıtlarından, Alıcı 2'nin konumu harita okumasından alınmış ve okuma kayması diğer iki istasyon üzerinden düzeltilmiştir (`config.json`).
- Alıcı kayıtları, tezin 3.4.2. bölümünde anlatılan bilgisayar yazılımının ürettiği Excel biçimindedir; her satırda bilgisayarın UTC zaman damgası ve karttan gelen satır bulunur.

## Lisans

Kod MIT lisansıyla, veriler CC BY 4.0 lisansıyla paylaşılmaktadır (bkz. `LICENSE`). Çalışmada kullanılması durumunda teze atıf yapılması rica olunur.
