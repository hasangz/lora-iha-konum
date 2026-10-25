"""Referans konum: uzaktan kumanda (RC) kaydı, beacon GNSS ile zaman hizalaması ve paket bazında referans."""
import bisect
import datetime as dt
import math

import numpy as np


def _sayi(s):
    """RC kaydındaki '397.704.334' biçimini 39.7704334'e çevirir."""
    s = s.replace(".", "")
    return float(s[:2] + "." + s[2:])


def rc_oku(yol, utc_ofset):
    """RC kaydını okur. Zaman damgası dakika çözünürlüklü olabildiğinden saniye ekseni satır sırasından (1 Hz) kurulur:
    ms çözünürlüklü ilk damga varsa çapa olarak kullanılır, yoksa ilk dakika değişimi çapadır."""
    ham = [l.strip().split(";") for l in open(yol, encoding="utf-8-sig")][1:]
    ham = [r for r in ham if len(r) == 4]
    capa = None
    for i, r in enumerate(ham):
        if "-" in r[0] and r[0].count(":") == 2:
            capa = (i, dt.datetime.fromisoformat(r[0]))
            break
    if capa:
        T0 = capa[1] - dt.timedelta(seconds=capa[0])
    else:
        i7 = next(i for i, r in enumerate(ham) if r[0] != ham[0][0])
        T0 = dt.datetime.strptime(ham[i7][0], "%d.%m.%Y %H:%M") - dt.timedelta(seconds=i7)
    return [(T0 + dt.timedelta(seconds=i) - dt.timedelta(hours=utc_ofset), _sayi(r[1]), _sayi(r[2]), float(r[3]))
            for i, r in enumerate(ham)]


class RC:
    """RC kaydından zaman -> (konum, yerden yükseklik, yatay hız) aradeğerlemesi."""

    def __init__(self, kayit, yerel):
        self.k, self.y = kayit, yerel
        self.t = [r[0] for r in kayit]
        self.zemin = float(np.median([r[3] for r in kayit[:20]]))

    def __call__(self, t):
        rc, i = self.k, bisect.bisect_left(self.t, t)
        if i <= 0 or i >= len(rc):
            return None
        a, b = rc[i - 1], rc[i]
        w = (t - a[0]).total_seconds() / (b[0] - a[0]).total_seconds()
        j0, j1 = max(0, i - 2), min(len(rc) - 1, i + 2)
        hiz = np.linalg.norm(self.y.enu(rc[j1][1], rc[j1][2]) - self.y.enu(rc[j0][1], rc[j0][2])) / max(1e-3, (rc[j1][0] - rc[j0][0]).total_seconds())
        p = self.y.enu(a[1] + (b[1] - a[1]) * w, a[2] + (b[2] - a[2]) * w)
        return p, a[3] + (b[3] - a[3]) * w - self.zemin, hiz


def kayma_bul(beacon, rc, yerel, aralik):
    """Eş. 3.21: beacon GNSS konumu ile RC konumu arasındaki ortanca farkı en küçükleyen zaman kayması."""
    en_iyi = None
    for sh in np.arange(aralik[0], aralik[1] + aralik[2], aralik[2]):
        e = [np.linalg.norm(yerel.enu(la, lo) - q[0]) for t, (u, la, lo, al) in beacon.items()
             if (q := rc(u + dt.timedelta(seconds=float(sh))))]
        if e and (en_iyi is None or np.median(e) < en_iyi[1]):
            en_iyi = (float(sh), float(np.median(e)), len(e))
    return en_iyi


def paket_referanslari(C, beacon, rc, kayma, S, periyot, anten_h):
    """Her istasyonun her paketine gönderim anındaki referans konum, yükseklik, hız ve mesafeleri ekler."""
    ref = "A3" if "A3" in C else "A1"
    ep = sorted(p["T"] - dt.timedelta(seconds=p["tx"] * periyot) for p in C[ref])
    E0 = ep[len(ep) // 2]
    d = [(p["T"] - beacon[p["tx"]][0]).total_seconds() for p in C[ref] if p["tx"] in beacon]
    pc_ofset = float(np.median(d))  # PC saati − GNSS saati
    satirlar = []
    for k in C:
        for p in C[k]:
            tu = E0 + dt.timedelta(seconds=p["tx"] * periyot - pc_ofset)
            q = rc(tu + dt.timedelta(seconds=kayma))
            if not q:
                continue
            pos, agl, hiz = q
            h = float(np.linalg.norm(pos - S[k]))
            satirlar.append(dict(st=k, tx=p["tx"], rssi=p["rssi"], snr=p["snr"], agl=float(agl), sp=float(hiz),
                                 dh=h, ds=math.hypot(h, agl - anten_h), x=float(pos[0]), y=float(pos[1])))
    return satirlar, pc_ofset
