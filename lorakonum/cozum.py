"""Trilaterasyon: EKK (Eş. 3.16) ve SNR ağırlıklı AEKK (Eş. 3.17), sönümlü Gauss-Newton (Eş. 3.23)."""
import numpy as np

from .model import ISTASYONLAR, mesafe_kestir, snr_agirlik, yatay_mesafe


def lm_coz(P, r, w, p0, maks_yineleme=300, tol=1e-4):
    """Levenberg–Marquardt: Δp = −(JᵀWJ + λI)⁻¹ JᵀWe. Maliyeti düşüren adım kabul edilir (λ/2), aksi halde λ·4."""
    w = np.asarray(w, float) / np.sum(w)
    p, lam = np.array(p0, float), 1.0
    for _ in range(maks_yineleme):
        d = np.linalg.norm(P - p, axis=1) + 1e-6
        e = d - r
        J = (p - P) / d[:, None]
        dp = -np.linalg.solve(J.T @ (w[:, None] * J) + lam * np.eye(2), J.T @ (w * e))
        pn = p + dp
        if (w * (np.linalg.norm(P - pn, axis=1) - r) ** 2).sum() < (w * e ** 2).sum():
            p, lam = pn, lam * 0.5
        else:
            lam *= 4
        if np.linalg.norm(dp) < tol:
            break
    return p


def konum_kestir(h, cal, S, mcfg, yontem="AEKK"):
    """Bekleme noktasının ortanca RSSI/SNR değerlerinden konum kestirir.
    Başlangıç noktası istasyonların ağırlık merkezidir (doğrusal çözüm yerel minimuma götürebilir)."""
    st = [k for k in ISTASYONLAR if k in h["m"]]
    r, snr = [], []
    for k in st:
        A, n = cal[k]
        d = mesafe_kestir(h["m"][k][0], A, n, mcfg["dmax_m"])
        r.append(yatay_mesafe(d, h["agl"], mcfg["anten_yuksekligi_m"]))
        snr.append(h["m"][k][1])
    r = np.array(r)
    P = np.array([S[k] for k in st])
    if yontem == "EKK":
        w = np.ones(len(r))
    else:
        w = np.array([snr_agirlik(s, mcfg["snr_min_db"], mcfg["snr_max_db"], mcfg["eps"]) for s in snr]) / r ** 2
    merkez = np.mean([S[k] for k in ISTASYONLAR], axis=0)
    return lm_coz(P, r, w, merkez)
