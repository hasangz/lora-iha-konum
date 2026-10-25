"""Bekleme (hover) noktalarının kayıtlardan otomatik tespiti."""
import numpy as np


def bekleme_noktalari(satirlar, istasyonlar, cfg_b, ucus):
    """Yatay hızı eşiğin altında ve yüksekliği eşiğin üzerinde olan ardışık paketleri bekleme noktası olarak gruplar.
    Her istasyon için RSSI ve SNR ortancası alınır (m[k] = (RSSI, SNR, paket sayısı))."""
    tx_bazli = {}
    for r in satirlar:
        tx_bazli.setdefault(r["tx"], {})[r["st"]] = r
    segler, cur = [], []
    for t in sorted(tx_bazli):
        r = next(iter(tx_bazli[t].values()))
        if r["agl"] > cfg_b["yukseklik_esik_m"] and r["sp"] < cfg_b["hiz_esik_ms"]:
            if cur and t - cur[-1] > cfg_b["max_bosluk_paket"]:
                segler.append(cur)
                cur = []
            cur.append(t)
        elif cur:
            segler.append(cur)
            cur = []
    if cur:
        segler.append(cur)
    segler = [s for s in segler if len(s) >= cfg_b["min_paket"]]
    H = []
    for s in segler:
        pts = [next(iter(tx_bazli[t].values())) for t in s]
        m = {}
        for k in istasyonlar:
            v = [tx_bazli[t][k] for t in s if k in tx_bazli[t]]
            if len(v) >= cfg_b["istasyon_min_paket"]:
                m[k] = (float(np.median([x["rssi"] for x in v])), float(np.median([x["snr"] for x in v])), len(v))
        H.append(dict(P=[float(np.mean([p["x"] for p in pts])), float(np.mean([p["y"] for p in pts]))],
                      agl=float(np.mean([p["agl"] for p in pts])), m=m, tx=(s[0], s[-1]), fl=ucus))
    return H
