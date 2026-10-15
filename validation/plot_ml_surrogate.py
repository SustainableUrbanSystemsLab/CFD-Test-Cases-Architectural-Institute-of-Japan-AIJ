"""Validation figure for the Eddy3D ML wind surrogate (Yel-2.0) against AIJ UWE Cases A-E.

  figures/ml-surrogate-agreement.png
      Does the surrogate agree with the tunnel?  Measured against predicted pedestrian-height speed, one
      panel per case, with the 1:1 line and the factor-of-two band.

The model predicts |U_mean|/U_ref at one height (1.8 m), so each tunnel case was scaled until its
measurement plane sits there (A x180, B x144, C x90, D x360, E x0.9) and the prediction was read at
the tunnel's own sensor coordinates; every value is divided by the case's U_H (Case E: U at 15.9 m).
What is plotted per case is the set the fixture scores as its headline: A and B |U| at the lowest
horizontal plane, C all nine configurations, D the thermistor plane at three directions, E all 16
directions before and after construction.

Inputs: validation/results/case{A..E}_ml_pairs.csv and case{A..E}_ml.json, snapshots of the Eddy3D
fixture Outdoor.ML.Tests/TestAijSurrogateE2E's pairs.csv and results.json (C:/Eddy3DVal/ml_*); the
snapshot is refreshed from there when that folder exists.

Colour: slot 3 of the validated categorical palette (aqua #1baf7a) is the ML surrogate in every
figure here, as slot 1 (blue) is OpenFOAM; aqua sits below 3:1 contrast on the light surface, so
every panel carries its scores as visible text (the palette's relief rule).
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import shutil

import numpy as np
import ultraplot as uplt

HERE = os.path.dirname(os.path.abspath(__file__))
VAL = r"C:/Eddy3DVal"
RESULTS = os.path.join(HERE, "results")

AQUA = "#1baf7a"     # slot 3 - the ML surrogate
INK = "#2b2b2b"
MUTED = "#8a8a88"
SURFACE = "#fcfcfb"

PANELS = [
    ("A", "Case A — |U|/U$_H$, z = 0.01 m plane", "speed.vectorMagnitude"),
    ("B", "Case B — |U|/U$_H$, z = H/16 plane", "speed.vectorMagnitude"),
    ("C", "Case C — Vs/U$_H$, 9 configurations", None),
    ("D", "Case D — Vs/U$_H$, thermistor, 3 WD", "speed.thermistor"),
    ("E", "Case E — Vs/U(15.9 m), 16 WD, bc + ac", "speed.thermistor"),
]


def snapshot():
    os.makedirs(RESULTS, exist_ok=True)
    for case, _, _ in PANELS:
        src = os.path.join(VAL, f"ml_{case}")
        shutil.copyfile(os.path.join(src, "results.json"), os.path.join(RESULTS, f"case{case}_ml.json"))
        # LF on every platform, like the rest of the served data.
        with io.open(os.path.join(src, "pairs.csv"), encoding="utf-8") as f:
            text = f.read().replace("\r\n", "\n")
        with io.open(os.path.join(RESULTS, f"case{case}_ml_pairs.csv"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)


def pairs(case):
    o, p = [], []
    with io.open(os.path.join(RESULTS, f"case{case}_ml_pairs.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["set"].endswith("_splitFibre_Umag"):     # D's 33 split-fibre points are a different instrument
                continue
            o.append(float(r["observed_over_UH"])); p.append(float(r["predicted_over_UH"]))
    return np.array(o), np.array(p)


def metrics(o, p, d=0.25, w=0.05):
    """Chang & Hanna FB / FAC2 / R and the VDI 3783-9 hit rate, as DispersionMetrics computes them."""
    mo, mp = o.mean(), p.mean()
    fac2 = float(np.mean([(a > 0) and (0.5 <= b / a <= 2) for a, b in zip(o, p)]))
    hit = float(np.mean((np.abs(p - o) <= w) | (np.abs(p - o) <= d * np.abs(o))))
    return {"Count": len(o), "Fb": 2 * (mo - mp) / (mo + mp), "Fac2": fac2,
            "R": float(np.corrcoef(o, p)[0, 1]), "HitRate": hit}


if os.path.isdir(VAL):
    snapshot()

fig, axs = uplt.subplots(nrows=1, ncols=5, refwidth=1.75, refaspect=1, share=False, wspace=2.6)
for i, (case, title, key) in enumerate(PANELS):
    ax = axs[i]
    o, p = pairs(case)
    m = metrics(o, p)
    if key:   # the fixture's own numbers must be what this figure says
        with io.open(os.path.join(RESULTS, f"case{case}_ml.json"), encoding="utf-8") as f:
            ref = json.load(f)[key]
        for k in ("Count", "Fb", "Fac2", "R", "HitRate"):
            assert abs(m[k] - ref[k]) < 1e-9, (case, k, m[k], ref[k])
    lo = min(0.0, float(min(o.min(), p.min())))
    hi = 1.05 * float(max(o.max(), p.max()))
    line = np.array([max(lo, 1e-6), hi])
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1.0, zorder=1)
    ax.plot(line, 2 * line, color=MUTED, lw=0.7, ls=":", zorder=1)
    ax.plot(line, 0.5 * line, color=MUTED, lw=0.7, ls=":", zorder=1)
    ax.scatter(o, p, s=7 if len(o) > 500 else 11, color=AQUA, edgecolor=SURFACE, linewidth=0.25,
               alpha=0.8, zorder=3)
    ax.text(0.05, 0.95, f"n {m['Count']}\nR {m['R']:+.2f}\nFAC2 {m['Fac2']:.2f}\nFB {m['Fb']:+.2f}\nq {m['HitRate']:.2f}",
            transform=ax.transAxes, va="top", ha="left", fontsize=6.5, color=INK)
    ax.format(xlim=(lo, hi), ylim=(lo, hi), xlabel="tunnel", ylabel="ML surrogate" if i == 0 else None,
              title=title, titleloc="l", titlesize=7.5)
    print(f"{case}: n={m['Count']} FB={m['Fb']:+.3f} FAC2={m['Fac2']:.3f} R={m['R']:+.3f} q={m['HitRate']:.3f}")

fig.format(suptitle="AIJ UWE benchmark — Eddy3D ML wind surrogate (Yel-2.0) vs wind tunnel, pedestrian height",
           abc=False, gridcolor="#e3e3e0", gridlinewidth=0.6)
fig.save(os.path.join(HERE, "figures", "ml-surrogate-agreement.png"), dpi=220)
print("wrote ml-surrogate-agreement.png")
