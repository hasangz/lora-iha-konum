"""LoRa tabanlı çok alıcılı İHA konum kestirimi – saha testi analizi.

Kullanım:
    python analiz.py                 # config.json ile tüm analizi çalıştırır
    python analiz.py --config X.json --cikti sonuclar/

Çıktılar (sonuclar/):
    paket_istatistikleri.csv   istasyon ve uçuş başına geçerli paket, TXSAYAC aralığı, PDR, ortalama RSSI/SNR
    zaman_hizalama.csv         RC–beacon zaman kayması ve PC–GNSS saat farkı
    bekleme_noktalari.csv      değerlendirilen bekleme noktaları, ortanca RSSI/SNR, kestirimler ve hatalar (LOO, ortak n)
    kalibrasyon.json           tüm veriyle A ve n, model artıklarının standart sapması
    ozet.json                  tüm doğrulama şeması / kalibrasyon modu / yöntem bileşimleri için hata özetleri
    *.png                      grafikler
"""
import argparse
import csv
import datetime as dt
import json
import os

import numpy as np

from lorakonum import bekleme, degerlendirme, geo, grafik, kayitlar, model, referans


def ucus_isle(no, ucfg, cfg, yerel, S, log):
    oi = cfg["on_isleme"]
    tarih = dt.date.fromisoformat(cfg["test_tarihi"])
    C, istat = {}, []
    for k, yol in ucfg["alicilar"].items():
        satirlar = kayitlar.kayit_oku(yol)
        paket = kayitlar.paketleri_ayir(satirlar)
        temiz = kayitlar.epok_temizle(paket, oi["paket_periyodu_s"], oi["epok_esik_s"], oi["epok_kume_min_paket"])
        oran, ilk, son = degerlendirme.pdr(temiz)
        istat.append(dict(ucus=no, istasyon=k, gecerli=len(temiz), kayitli=len(paket), tx_ilk=ilk, tx_son=son, pdr=round(oran, 1),
                          ort_rssi=round(float(np.mean([p["rssi"] for p in temiz])), 1), ort_snr=round(float(np.mean([p["snr"] for p in temiz])), 1)))
        C[k] = temiz
    B = {}
    for k in C:
        for tx, v in kayitlar.beacon_konumlari(C[k], tarih, yerel, oi["alan_merkez"], oi["alan_esik_derece"]).items():
            B.setdefault(tx, v)
    rc = referans.RC(referans.rc_oku(ucfg["rc"], cfg["utc_ofset_saat"]), yerel)
    kayma, fark, n = referans.kayma_bul(B, rc, yerel, oi["rc_kayma_arama_s"])
    satirlar, pc = referans.paket_referanslari(C, B, rc, kayma, S, oi["paket_periyodu_s"], cfg["model"]["anten_yuksekligi_m"])
    H = bekleme.bekleme_noktalari(satirlar, model.ISTASYONLAR, cfg["bekleme"], int(no))
    log(f"{no}. uçuş: {len(B)} konumlu beacon paketi, RC kayması {kayma:+.1f} s (ortanca fark {fark:.1f} m), "
        f"PC–GNSS {pc:+.2f} s, {len(H)} bekleme noktası tespit edildi")
    return H, istat, dict(ucus=no, rc_kayma_s=kayma, ortanca_fark_m=round(fark, 2), eslesen_paket=n, pc_gnss_s=round(pc, 2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--cikti", default="sonuclar")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8"))
    os.makedirs(a.cikti, exist_ok=True)
    yerel = geo.Yerel(cfg["orijin"]["enlem"], cfg["orijin"]["boylam"])
    S, kayma = geo.istasyon_konumlari(cfg, yerel)
    print("İstasyonlar (Doğu, Kuzey m):", {k: np.round(v, 2).tolist() for k, v in S.items()}, "harita düzeltmesi:", np.round(kayma, 2).tolist())

    tum_H, istat, hiz = [], [], []
    for no, ucfg in cfg["ucuslar"].items():
        H, ist, z = ucus_isle(no, ucfg, cfg, yerel, S, print)
        tum_H += H; istat += ist; hiz.append(z)

    gerekli = cfg["bekleme"]["gerekli_istasyon"]
    H = [h for h in tum_H if len(h["m"]) >= gerekli]
    print(f"Değerlendirilen bekleme noktası: {len(H)} / {len(tum_H)} (en az {gerekli} istasyonun ölçümü bulunan noktalar)")

    mcfg, ah = cfg["model"], cfg["model"]["anten_yuksekligi_m"]
    cal = model.kalibre_et(H, S, ah, "ortak n")
    sigma = float(np.std(degerlendirme.model_artiklari(H, cal, S, ah)))
    json.dump(dict(ortak_n={k: dict(A=float(A), n=float(n)) for k, (A, n) in cal.items()},
                   ayri={k: dict(A=float(A), n=float(n)) for k, (A, n) in model.kalibre_et(H, S, ah, "ayrı").items()},
                   sigma_db=sigma, olcum_sayisi=sum(len(h["m"]) for h in H)),
              open(os.path.join(a.cikti, "kalibrasyon.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    ozet, ana = {}, None
    for sema in ("LOO", "Çapraz uçuş"):
        for mod in ("ortak n", "ayrı"):
            R = degerlendirme.degerlendir(H, S, mcfg, sema, mod)
            if sema == "LOO" and mod == "ortak n":
                ana = R
            for y in ("EKK", "AEKK"):
                e = np.array([r["e_" + y] for r in R]); fl = np.array([r["fl"] for r in R])
                ozet[f"{sema} | {mod} | {y}"] = dict(tumu=degerlendirme.ozet(e), ucus1=degerlendirme.ozet(e[fl == 1]), ucus2=degerlendirme.ozet(e[fl == 2]))
    json.dump(ozet, open(os.path.join(a.cikti, "ozet.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    with open(os.path.join(a.cikti, "paket_istatistikleri.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(istat[0])); w.writeheader(); w.writerows(istat)
    with open(os.path.join(a.cikti, "zaman_hizalama.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(hiz[0])); w.writeheader(); w.writerows(hiz)
    with open(os.path.join(a.cikti, "bekleme_noktalari.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ucus", "nokta", "enlem", "boylam", "dogu_m", "kuzey_m", "yukseklik_m"]
                   + [f"{k}_{x}" for k in model.ISTASYONLAR for x in ("rssi", "snr", "paket", "sapma_db")]
                   + ["ekk_dogu", "ekk_kuzey", "ekk_hata_m", "aekk_dogu", "aekk_kuzey", "aekk_hata_m"])
        sayac = {}
        for r in ana:
            sayac[r["fl"]] = sayac.get(r["fl"], 0) + 1
            la, lo = yerel.coğrafi(r["P"])
            w.writerow([r["fl"], sayac[r["fl"]], f"{la:.7f}", f"{lo:.7f}", f"{r['P'][0]:.2f}", f"{r['P'][1]:.2f}", f"{r['agl']:.2f}"]
                       + sum([[r["m"][k][0], r["m"][k][1], r["m"][k][2], f"{r['sapma_db'][k]:.2f}"] for k in model.ISTASYONLAR], [])
                       + [f"{r['EKK'][0]:.2f}", f"{r['EKK'][1]:.2f}", f"{r['e_EKK']:.2f}", f"{r['AEKK'][0]:.2f}", f"{r['AEKK'][1]:.2f}", f"{r['e_AEKK']:.2f}"])

    grafik.test_duzeni(H, S, os.path.join(a.cikti, "test_duzeni.png"))
    grafik.rssi_mesafe(H, cal, S, ah, os.path.join(a.cikti, "rssi_mesafe.png"))
    for fl in (1, 2):
        grafik.kestirim_haritasi(ana, S, fl, os.path.join(a.cikti, f"ucus{fl}_aekk.png"))
    grafik.hata_dagilimi(ana, os.path.join(a.cikti, "hata_dagilimi.png"))

    print("\nKalibrasyon (ortak n):", {k: (round(float(A), 2), round(float(n), 3)) for k, (A, n) in cal.items()}, f"σ = {sigma:.2f} dB")
    print("\nKonum hatası (m)         ortalama  ortanca   RMSE   95.yüzdelik")
    for k, v in ozet.items():
        t = v["tumu"]
        print(f"{k:28s} {t['ortalama']:7.1f} {t['ortanca']:8.1f} {t['rmse']:7.1f} {t['p95']:8.1f}")


if __name__ == "__main__":
    main()
