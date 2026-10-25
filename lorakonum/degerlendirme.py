"""Doğrulama şemaları (LOO, çapraz uçuş) ve başarım ölçütleri (Eş. 3.24–3.26)."""
import math

import numpy as np

from .cozum import konum_kestir
from .model import ISTASYONLAR, egik_mesafe, kalibre_et, mesafe_kestir


def ozet(e):
    e = np.asarray(e, float)
    return dict(n=int(len(e)), ortalama=float(e.mean()), ortanca=float(np.median(e)),
                rmse=float(math.sqrt((e ** 2).mean())), p95=float(np.percentile(e, 95)))


def egitim_kumesi(H, i, sema):
    """LOO: değerlendirilen nokta hariç tüm noktalar. Çapraz uçuş: yalnızca diğer uçuşun noktaları."""
    if sema == "LOO":
        return [x for j, x in enumerate(H) if j != i]
    return [x for x in H if x["fl"] != H[i]["fl"]]


def degerlendir(H, S, mcfg, sema="LOO", mod="ortak n"):
    """Her bekleme noktasını kendi eğitim kümesiyle kalibre edilen modelle EKK ve AEKK yöntemleriyle çözer."""
    ah = mcfg["anten_yuksekligi_m"]
    sonuc = []
    for i, h in enumerate(H):
        cal = kalibre_et(egitim_kumesi(H, i, sema), S, ah, mod)
        r = dict(fl=h["fl"], P=h["P"], agl=h["agl"], m=h["m"], cal={k: [float(a), float(n)] for k, (a, n) in cal.items()})
        for y in ("EKK", "AEKK"):
            p = konum_kestir(h, cal, S, mcfg, y)
            r[y] = p.tolist()
            r["e_" + y] = float(np.linalg.norm(p - np.array(h["P"])))
        # istasyon bazında model sapması (ölçülen − model, dB) ve mesafe kestirim hatası (%)
        r["sapma_db"], r["mesafe_hata_yuzde"] = {}, {}
        for k in ISTASYONLAR:
            if k not in h["m"]:
                continue
            A, n = cal[k]
            d = egik_mesafe(h, k, S, ah)
            r["sapma_db"][k] = float(h["m"][k][0] - (A - 10 * n * math.log10(d)))
            r["mesafe_hata_yuzde"][k] = float(100 * (mesafe_kestir(h["m"][k][0], A, n, float("inf")) / d - 1))
        sonuc.append(r)
    return sonuc


def model_artiklari(H, cal, S, ah):
    """Tüm veriyle kalibre edilmiş modelin RSSI artıkları (gölgeleme σ hesabı için)."""
    return [h["m"][k][0] - (cal[k][0] - 10 * cal[k][1] * math.log10(egik_mesafe(h, k, S, ah))) for h in H for k in h["m"]]


def pdr(paketler):
    """Eş. 3.26: alınan farklı TXSAYAC sayısı / (son − ilk + 1)."""
    tx = sorted(set(p["tx"] for p in paketler))
    return 100 * len(tx) / (tx[-1] - tx[0] + 1), tx[0], tx[-1]
