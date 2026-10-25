"""Alıcı istasyon kayıtlarının (Excel) okunması, paketlerin ayrıştırılması ve temizlenmesi."""
import collections
import datetime as dt
import re

import openpyxl


def nmea_gecerli(s):
    """NMEA sağlama toplamını (XOR) denetler."""
    if not s or "$" not in s:
        return False
    s = s[s.find("$"):]
    if "*" not in s:
        return False
    govde, cs = s[1:].split("*", 1)
    x = 0
    for ch in govde:
        x ^= ord(ch)
    try:
        return x == int(cs[:2], 16)
    except ValueError:
        return False


def nmea_derece(deger, yon):
    """NMEA ddmm.mmmm biçimini ondalık dereceye çevirir."""
    r = float(deger)
    d = int(r / 100)
    x = d + (r - d * 100) / 60
    return -x if yon in "SW" else x


def kayit_oku(yol):
    """Bilgisayar yazılımının kaydettiği .xlsx dosyasından (zaman, satır) listesi döndürür.
    Her istasyon dosyasında ilgili kartın sütun çifti doludur (A/B, C/D veya E/F)."""
    ws = openpyxl.load_workbook(yol).active  # read_only kullanılmaz (ClosedXML boyut bilgisi)
    satirlar = list(ws.iter_rows(min_row=2, values_only=True))
    tc = [c for c in (0, 2, 4) if any(r[c + 1] is not None for r in satirlar)][0]
    return [(r[tc], str(r[tc + 1])) for r in satirlar if r[tc + 1] is not None]


def paketleri_ayir(satirlar):
    """LORA| TXSAYAC / RSSI / SNR satırlarını tek pakette birleştirir; hemen önceki LORA GGA satırını pakete ekler."""
    paketler, cur, son_gga = [], None, None
    for t, v in satirlar:
        if v.startswith("LORA| $") or v.startswith("LORA| NOFIX"):
            son_gga = (t, v)
        m = re.match(r"LORA\| TXSAYAC:(\d+)$", v)
        if m:
            gga = son_gga[1] if son_gga and (t - son_gga[0]).total_seconds() < 0.5 else None
            cur = {"T": t, "tx": int(m.group(1)), "gga": gga}
            paketler.append(cur)
            continue
        m = re.match(r"LORA\| RSSI: (-?\d+) dBm", v)
        if m and cur and "rssi" not in cur:
            cur["rssi"] = int(m.group(1))
            continue
        m = re.match(r"LORA\| SNR: ([+-]?\d+\.\d+) dB", v)
        if m and cur and "snr" not in cur:
            cur["snr"] = float(m.group(1))
    return [p for p in paketler if "rssi" in p and "snr" in p]


def epok_temizle(paketler, periyot, esik, min_paket):
    """Sayaç alanı bozulmuş paketleri ayıklar: geçerli paketlerde (alım zamanı − TXSAYAC·periyot) sabittir."""
    ofs = [p["T"] - dt.timedelta(seconds=p["tx"] * periyot) for p in paketler]
    kumeler = collections.Counter(o.replace(microsecond=0, second=o.second // 10 * 10) for o in ofs).most_common(4)
    return [p for p, o in zip(paketler, ofs)
            if any(n > min_paket and abs((o - a).total_seconds()) < esik for a, n in kumeler)]


def beacon_konumlari(paketler, tarih, yerel, merkez, esik):
    """Paketlerdeki geçerli beacon GGA cümlelerinden {TXSAYAC: (UTC zamanı, enlem, boylam, irtifa)} üretir."""
    B = {}
    for p in paketler:
        s = p["gga"]
        if not nmea_gecerli(s):
            continue
        f = s[s.find("$"):].split("*")[0].split(",")
        if not f[0].endswith("GGA") or f[6] in ("", "0"):
            continue
        try:
            hh = f[1]
            u = dt.datetime(tarih.year, tarih.month, tarih.day, int(hh[:2]), int(hh[2:4])) + dt.timedelta(seconds=float(hh[4:]))
            la, lo = nmea_derece(f[2], f[3]), nmea_derece(f[4], f[5])
            if abs(la - merkez[0]) > esik or abs(lo - merkez[1]) > esik:
                continue  # sağlama toplamını tesadüfen geçen bozuk cümle
            B.setdefault(p["tx"], (u, la, lo, float(f[9])))
        except (ValueError, IndexError):
            pass
    return B
