"""Sonuç grafikleri."""
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .model import ISTASYONLAR, egik_mesafe

plt.rcParams["font.size"] = 11
RENK = {"A1": "#b5452f", "A2": "#2f5d8a", "A3": "#3d7a4a"}


def _ucgen(ax, S):
    tri = np.array([S["A1"], S["A2"], S["A3"], S["A1"]])
    ax.fill(tri[:, 0], tri[:, 1], color="#eef3f8", zorder=0)
    ax.plot(tri[:, 0], tri[:, 1], color="#2f5d8a", lw=1.3)
    yer = {"A1": (4, 4, "left"), "A2": (5, 4, "left"), "A3": (-3, -9, "right")}
    for k, v in S.items():
        ax.plot(*v, "^", ms=13, color="#2f5d8a", zorder=5)
        o = yer[k]
        ax.text(v[0] + o[0], v[1] + o[1], "Alıcı " + k[1], fontsize=11, fontweight="bold", ha=o[2])


def test_duzeni(H, S, yol):
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 5.9))
    for ax, fl in zip(axs, (1, 2)):
        P = np.array([h["P"] for h in H if h["fl"] == fl])
        _ucgen(ax, S)
        ax.plot(P[:, 0], P[:, 1], "-", color="#3d7a4a", lw=1.1, alpha=.7)
        ax.plot(0, 0, "s", color="k", ms=7)
        ax.text(-3, -9, "Kalkış", fontsize=9.5, ha="right")
        for i, p in enumerate(P):
            ax.plot(*p, "o", ms=15, mfc="white", mec="#b5452f", mew=1.8, zorder=6)
            ax.text(*p, str(i + 1), ha="center", va="center", fontsize=8.5, color="#b5452f", fontweight="bold", zorder=7)
        ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_title(f"{fl}. uçuş")
        ax.set_xlabel("Doğu (m)"); ax.set_ylabel("Kuzey (m)")
    fig.tight_layout(); fig.savefig(yol, dpi=200); plt.close(fig)


def rssi_mesafe(H, cal, S, ah, yol):
    fig, ax = plt.subplots(figsize=(9, 5.6))
    for k in ISTASYONLAR:
        for fl, mk in ((1, "o"), (2, "s")):
            x = [egik_mesafe(h, k, S, ah) for h in H if h["fl"] == fl]
            y = [h["m"][k][0] for h in H if h["fl"] == fl]
            ax.scatter(x, y, marker=mk, color=RENK[k], s=45, alpha=.85, edgecolor="white", lw=.5)
        A, n = cal[k]
        d = np.linspace(20, 190, 100)
        ax.plot(d, A - 10 * n * np.log10(d), color=RENK[k], lw=1.6, label=f"Alıcı {k[1]}: A = {A:.1f} dBm, n = {n:.2f}")
    ax.set_xscale("log"); ax.set_xlabel("Eğik mesafe (m)"); ax.set_ylabel("Ortanca RSSI (dBm)")
    ax.grid(alpha=.3, which="both"); ax.legend(fontsize=9.5, loc="lower left")
    fig.tight_layout(); fig.savefig(yol, dpi=200); plt.close(fig)


def kestirim_haritasi(R, S, fl, yol):
    RR = [r for r in R if r["fl"] == fl]
    fig, ax = plt.subplots(figsize=(9.5, 7.8))
    _ucgen(ax, S)
    for i, r in enumerate(RR):
        T, E = np.array(r["P"]), np.array(r["AEKK"])
        ax.annotate("", xy=E, xytext=T, arrowprops=dict(arrowstyle="-|>", color="#b5452f", lw=1.2, alpha=.75, shrinkA=7, shrinkB=4))
        ax.plot(*E, "s", ms=8, color="#b5452f", zorder=5)
        ax.plot(*T, "o", ms=13, color="k", zorder=6)
        ax.text(*T, str(i + 1), color="white", fontsize=8, ha="center", va="center", zorder=7, fontweight="bold")
        ax.text(T[0] + 6, T[1] - 5, f"{r['e_AEKK']:.0f} m", fontsize=9.5, color="#b5452f")
    e = np.array([r["e_AEKK"] for r in RR])
    ax.set_title(f"{fl}. uçuş – AEKK  (ortalama {e.mean():.1f} m, ortanca {np.median(e):.1f} m, RMSE {math.sqrt((e**2).mean()):.1f} m)")
    ax.set_aspect("equal"); ax.grid(alpha=.3); ax.set_xlabel("Doğu (m)"); ax.set_ylabel("Kuzey (m)")
    fig.tight_layout(); fig.savefig(yol, dpi=200); plt.close(fig)


def hata_dagilimi(R, yol):
    fig, ax = plt.subplots(figsize=(8, 4.8))
    for key, lab, c, ls in (("e_EKK", "EKK", "#7f7f7f", "--"), ("e_AEKK", "AEKK", "#b5452f", "-")):
        e = np.sort([r[key] for r in R])
        ax.step(np.r_[0, e], np.r_[0, np.arange(1, len(e) + 1) / len(e)], where="post", color=c, ls=ls, lw=2,
                label=f"{lab} (ortanca {np.median(e):.1f} m)")
    ax.set_xlabel("Konum hatası (m)"); ax.set_ylabel("Kümülatif oran"); ax.grid(alpha=.3); ax.legend(loc="lower right")
    fig.tight_layout(); fig.savefig(yol, dpi=200); plt.close(fig)
