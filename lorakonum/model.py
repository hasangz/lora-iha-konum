"""Log-mesafe modeli: kalibrasyon (Eş. 3.9 / 3.22), mesafe kestirimi (Eş. 3.8, 3.11) ve ağırlıklar (Eş. 3.18–3.19)."""
import math

import numpy as np

ISTASYONLAR = ("A1", "A2", "A3")


def egik_mesafe(h, k, S, anten_h):
    """Bekleme noktası ile istasyon arasındaki gerçek eğik mesafe."""
    return math.hypot(np.linalg.norm(np.array(h["P"]) - S[k]), h["agl"] - anten_h)


def kalibre_et(egitim, S, anten_h, mod="ortak n"):
    """A ve n parametrelerini en küçük kareler ile kestirir (d0 = 1 m).
    'ortak n': her istasyona ayrı A, tüm istasyonlara ortak n (Eş. 3.22).
    'ayrı'   : her istasyona ayrı A ve n (Eş. 3.9)."""
    cal = {}
    if mod == "ayrı":
        for k in ISTASYONLAR:
            x = np.array([10 * math.log10(egik_mesafe(h, k, S, anten_h)) for h in egitim if k in h["m"]])
            y = np.array([h["m"][k][0] for h in egitim if k in h["m"]])
            (A, n), *_ = np.linalg.lstsq(np.vstack([np.ones_like(x), -x]).T, y, rcond=None)
            cal[k] = (A, max(n, 1.0))
    else:
        R, Y = [], []
        for h in egitim:
            for j, k in enumerate(ISTASYONLAR):
                if k in h["m"]:
                    v = np.zeros(4)
                    v[j] = 1
                    v[3] = -10 * math.log10(egik_mesafe(h, k, S, anten_h))
                    R.append(v)
                    Y.append(h["m"][k][0])
        s, *_ = np.linalg.lstsq(np.array(R), np.array(Y), rcond=None)
        for j, k in enumerate(ISTASYONLAR):
            cal[k] = (s[j], s[3])
    return cal


def mesafe_kestir(rssi, A, n, dmax):
    """Eş. 3.8: d̂ = 10^((A − RSSI) / (10 n)), dmax ile sınırlı."""
    return min(10 ** ((A - rssi) / (10 * n)), dmax)


def yatay_mesafe(d, h_b, h_i):
    """Eş. 3.11: eğik mesafeden yatay mesafe; eğik mesafe yükseklik farkından küçükse 1 m."""
    return math.sqrt(max(d ** 2 - (h_b - h_i) ** 2, 1))


def snr_agirlik(snr, snr_min, snr_max, eps):
    """Eş. 3.19: g(SNR) = min(1, max(ε, (SNR − SNRmin) / (SNRmax − SNRmin)))."""
    return min(1, max(eps, (snr - snr_min) / (snr_max - snr_min)))
