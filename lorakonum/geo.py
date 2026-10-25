"""Koordinat dönüşümleri ve istasyon konumları."""
import math
import numpy as np


def dms(d, m, s):
    """Derece-dakika-saniye -> ondalık derece."""
    return d + m / 60 + s / 3600


class Yerel:
    """Coğrafi koordinatları orijine göre yerel Doğu-Kuzey (m) düzlemine çevirir (Eş. 3.x / Bölüm 3.4.2.3)."""

    def __init__(self, enlem0, boylam0):
        self.lat0, self.lon0 = enlem0, boylam0
        self.kx = 111320 * math.cos(math.radians(enlem0))
        self.ky = 110540

    def enu(self, enlem, boylam):
        return np.array([(boylam - self.lon0) * self.kx, (enlem - self.lat0) * self.ky])

    def coğrafi(self, p):
        return self.lat0 + p[1] / self.ky, self.lon0 + p[0] / self.kx


def istasyon_konumlari(cfg, yerel):
    """A1 ve A3 GNSS konumlarını kullanır; A2'yi harita okuması + ortalama okuma kaymasıyla düzeltir."""
    ist = cfg["istasyonlar"]
    harita = {k: yerel.enu(dms(*v["harita_dms"][0]), dms(*v["harita_dms"][1])) for k, v in ist.items() if not k.startswith("_")}
    gnss = {k: yerel.enu(*v["gnss"]) for k, v in ist.items() if not k.startswith("_") and v["gnss"]}
    kayma = np.mean([gnss[k] - harita[k] for k in gnss], axis=0)
    S = {}
    for k in ("A1", "A2", "A3"):
        S[k] = gnss[k] if k in gnss else harita[k] + kayma
    return S, kayma
