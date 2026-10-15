"""Validation figures for the AIJ UWE benchmark cases solved with Eddy3D / OpenFOAM.

Two figures, each answering one question:

  cases-ab-openfoam-agreement.png   Does the model agree with the tunnel?  Measured vs modelled, one panel
                      per quantity per case, with the 1:1 line and the factor-of-two band.
  cases-ab-openfoam-profiles.png    WHERE does it agree?  Centre-plane vertical profiles of U/U_H at the
                      measurement stations, measured points against the modelled line.

Colours are slots 1-2 of the validated categorical palette (blue #2a78d6, orange #eb6834);
reference geometry (1:1 line, FAC2 band, grid) is recessive grey so it never competes with data.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os

import numpy as np
import ultraplot as uplt

VAL = r"C:/Eddy3DVal"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

BLUE = "#2a78d6"     # slot 1 - the model
ORANGE = "#eb6834"   # slot 2 - the measurement
INK = "#2b2b2b"
MUTED = "#8a8a88"

CASES = [
    ("A", "aij_A", "RS-caseA.csv", 1.0, +1.0, "aij_A_realizableKE_L3",
     "Case A — 1:1:2 building", 0.16, 4.491, (-0.04, 0.04)),
    ("B", "aij_B", "RS_caseB.csv", 0.001, -1.0, "aij_B_realizableKE_L3",
     "Case B — 1:4:4 slab", 0.20, 5.133, (-0.025, 0.025)),
]


def read_reference(path, coord_scale, lateral_sign):
    """The benchmark table: coordinates in metres, velocities in m/s, -999.9 = not measured."""
    rows = []
    with io.open(path, encoding="utf-8-sig") as f:
        rd = csv.reader(f)
        header = [h.split("(")[0].split("[")[0].strip() for h in next(rd)]
        idx = {n: i for i, n in enumerate(header)}

        def val(r, name):
            try:
                v = float(r[idx[name]])
            except (KeyError, IndexError, ValueError):
                return math.nan
            return math.nan if abs(v + 999.9) < 1e-6 else v

        for r in rd:
            if not any(c.strip() for c in r):
                continue
            rows.append(dict(
                x=val(r, "x") * coord_scale, y=val(r, "y") * coord_scale, z=val(r, "z") * coord_scale,
                U=val(r, "U"), V=lateral_sign * val(r, "V"), W=val(r, "W"), k=val(r, "k")))
    return rows


def read_probe(path):
    """What the solve gave at those same points. Case frame: wind along +y, so U = U_y, V = -U_x."""
    rows = []
    with io.open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            def g(k):
                try:
                    return float(r[k])
                except (KeyError, TypeError, ValueError):
                    return math.nan
            rows.append(dict(U=g("U_y"), V=-g("U_x"), W=g("U_z"), k=g("k")))
    return rows


def metrics(case_dir, key):
    with io.open(os.path.join(VAL, case_dir, "results.json"), encoding="utf-8") as f:
        return json.load(f)[key]


# ----------------------------------------------------------------------------- figure 1
QUANTITIES = [("U", "U/U$_H$"), ("V", "V/U$_H$"), ("W", "W/U$_H$"), ("k", "k/U$_H^2$")]

fig, axs = uplt.subplots(nrows=2, ncols=4, refwidth=1.72, refaspect=1, share=False,
                         hspace=4.4, wspace=2.6)

for row, (tag, ref_id, ref_file, cscale, lsign, study, title, H, Uh, _bx) in enumerate(CASES):
    meas = read_reference(os.path.join(VAL, "reference", ref_id, ref_file), cscale, lsign)
    model = read_probe(os.path.join(VAL, study, "reference.probe.csv"))
    for col, (q, label) in enumerate(QUANTITIES):
        ax = axs[row, col]
        norm = Uh * Uh if q == "k" else Uh
        o = np.array([m[q] for m in meas]) / norm
        p = np.array([m[q] for m in model]) / norm
        ok = np.isfinite(o) & np.isfinite(p)
        o, p = o[ok], p[ok]

        lo = float(min(o.min(), p.min())); hi = float(max(o.max(), p.max()))
        pad = 0.08 * (hi - lo) if hi > lo else 0.1
        lo, hi = lo - pad, hi + pad
        line = np.array([lo, hi])

        # Reference geometry first, so data sits on top of it.
        ax.plot(line, line, color=MUTED, lw=1.0, zorder=1)
        if q == "k" or (o > 0).all():          # a factor-of-two band is meaningless across zero
            ax.plot(line, 2 * line, color=MUTED, lw=0.7, ls=":", zorder=1)
            ax.plot(line, 0.5 * line, color=MUTED, lw=0.7, ls=":", zorder=1)

        ax.scatter(o, p, s=9, color=BLUE, alpha=0.75, edgecolor="none", zorder=3)

        m = metrics(study, "k" if q == "k" else f"velocity.{q}")
        ax.text(0.05, 0.95, f"R {m['R']:+.2f}\nFAC2 {m['Fac2']:.2f}\nFB {m['Fb']:+.2f}",
                transform=ax.transAxes, va="top", ha="left", fontsize=6.5, color=INK)

        ax.format(xlim=(lo, hi), ylim=(lo, hi), xlabel="measured", ylabel="Eddy3D" if col == 0 else None,
                  title=label, titleloc="l", titlesize=8)

for row, (_t, _r, _f, _c, _l, _s, title, _H, _U, _b) in enumerate(CASES):
    axs[row, 0].text(-0.46, 0.5, title, transform=axs[row, 0].transAxes, rotation=90,
                     va="center", ha="center", fontsize=9, color=INK)

fig.format(suptitle="AIJ UWE benchmark — Eddy3D (OpenFOAM 12, realizable k-ε) vs wind tunnel",
           abc=False, gridcolor="#e3e3e0", gridlinewidth=0.6)
fig.save(os.path.join(OUT, "cases-ab-openfoam-agreement.png"), dpi=220)
print("wrote cases-ab-openfoam-agreement.png")


# ----------------------------------------------------------------------------- figure 2
fig2, axs2 = uplt.subplots(nrows=1, ncols=2, refwidth=3.0, refaspect=1.25, share=False, wspace=4.5)

for i, (tag, ref_id, ref_file, cscale, lsign, study, title, H, Uh, bx) in enumerate(CASES):
    ax = axs2[i]
    meas = read_reference(os.path.join(VAL, "reference", ref_id, ref_file), cscale, lsign)
    model = read_probe(os.path.join(VAL, study, "reference.probe.csv"))

    centre = [(m, p) for m, p in zip(meas, model)
              if abs(m["y"]) < 1e-6 and np.isfinite(m["U"]) and np.isfinite(p["U"])]
    stations = sorted({round(m["x"] / H, 3) for m, _ in centre})
    # The leeward face and the two nearest wake stations: where a closure is actually tested.
    stations = [s for s in stations if s >= bx[1] / H - 1e-6][:3]

    drawn = []
    lohi = []
    for j, s in enumerate(stations):
        sel = [(m, p) for m, p in centre if abs(m["x"] / H - s) < 1e-6]
        if len(sel) < 3:
            continue
        sel.sort(key=lambda t: t[0]["z"])
        z = np.array([m["z"] / H for m, _ in sel])
        um = np.array([m["U"] / Uh for m, _ in sel])
        up = np.array([p["U"] / Uh for _, p in sel])
        off = j * 1.0                      # offset each station so they do not overplot
        ax.plot(up + off, z, color=BLUE, lw=1.8, zorder=3)
        ax.scatter(um + off, z, s=16, color=ORANGE, zorder=4, edgecolor="none")
        # Label at the station's NOMINAL band centre (offset + 1, since U/U_H runs about 0..1.2
        # around each offset), not at the data mean: at the offset origin the text is clipped
        # outside the frame, and at the data mean two close stations collide.
        drawn.append((off + 1.0, f"x/H={s:+.2f}"))
        lohi.extend([float(np.nanmin(np.concatenate([up, um]))) + off,
                     float(np.nanmax(np.concatenate([up, um]))) + off])

    for xc, lab in drawn:
        ax.text(xc, 2.08, lab, ha="center", fontsize=6.5, color=MUTED)

    ax.axhline(1.0, color=MUTED, lw=0.7, ls="--", zorder=1)
    lo, hi = (min(lohi) - 0.28, max(lohi) + 0.28) if lohi else (0, 3)
    ax.format(title=title, titleloc="l", titlesize=9, xlabel="U/U$_H$  (offset per station)",
              ylabel="z/H" if i == 0 else None, ylim=(0, 2.25), xlim=(lo, hi))

axs2[0].plot([], [], color=BLUE, lw=1.8, label="Eddy3D")
axs2[0].scatter([], [], s=16, color=ORANGE, label="wind tunnel")
axs2[0].legend(loc="lr", ncols=1, frame=False, fontsize=7.5)

fig2.format(suptitle="AIJ UWE benchmark — centre-plane profiles behind the building (y = 0)",
            gridcolor="#e3e3e0", gridlinewidth=0.6)
fig2.save(os.path.join(OUT, "cases-ab-openfoam-profiles.png"), dpi=220)
print("wrote cases-ab-openfoam-profiles.png")
