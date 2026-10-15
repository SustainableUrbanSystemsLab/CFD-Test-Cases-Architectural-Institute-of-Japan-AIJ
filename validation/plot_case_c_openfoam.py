"""Validation figures for AIJ UWE Case C (3 x 3 block array) solved with Eddy3D / OpenFOAM.

Two figures, each answering one question:

  figures/case-c-openfoam-agreement.png
      Does the model agree with the tunnel?  Measured Vs/U_H against the modelled scalar speed
      sqrt(|U|^2 + 2k)/U_H (filled) and the vector |U|/U_H (hollow), one panel per configuration (centre
      block x WD).
  figures/case-c-openfoam-bias-map.png
      WHERE does it agree?  log2(model / tunnel) of the scalar speed at each of the 120 points, on the
      plan of the array, per configuration.

The thermistor reads an omnidirectional scalar speed, so the honest comparison is the bracket
|U| <= Vs <= sqrt(|U|^2 + 2k): the filled and hollow marks of one point should straddle the 1:1 line.

Inputs: the measured table clean/cases/C/points.csv, and the probe files the Eddy3D fixtures
TestAijCaseC{0D,1D,2D}ContainerE2E wrote under C:/Eddy3DVal. The pairs are snapshotted to
validation/results/caseC_openfoam12_realizableKE_pairs.csv, and the figures are drawn from that
snapshot, so they rebuild from this repository alone when C:/Eddy3DVal is absent.

Probe frame: the fixtures solve the CSV frame turned so that the WD = 0 wind blows along world +y
(meteorological 180 deg), at 1:100: world = 100 * (-y, x, z). WD rotates the wind from +x toward -y
in the CSV frame (the data's own mirror symmetry; see the README).

Colours: slot 1 of the validated categorical palette (blue #2a78d6) is the OpenFOAM model, as in
cases-ab-openfoam-agreement.png; the map's diverging scale is the palette's blue <-> red pair around its neutral
gray (#f0efec). Reference geometry (1:1 line, FAC2 band, blocks) is recessive grey.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os

import numpy as np
import ultraplot as uplt

import plotstyle as style
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
VAL = r"C:/Eddy3DVal"
RESULTS = os.path.join(HERE, "results")
PAIRS = os.path.join(RESULTS, "caseC_openfoam12_realizableKE_pairs.csv")

BLUE = "#2a78d6"     # slot 1 - the OpenFOAM model
RED = "#e34948"      # diverging pole: model slower than the tunnel
MID = "#f0efec"      # diverging neutral midpoint
BLOCK = "#d9d8d4"

UH = 3.654           # U(z = D) from AF_caseC.csv, the case's normalising speed [m/s]
SCALE = 100.0        # the fixtures solve at 1:100
CONFIGS = ["0D", "1D", "2D"]
WDS = [0.0, 22.5, 45.0]
CB_TITLE = {"0D": "centre block absent (0D)", "1D": "centre block 1D", "2D": "centre block 2D"}


def label(wd):
    """The fixtures' file label for a wind direction: wd-0, wd22_5, wd45."""
    return "wd-0" if wd == 0 else f"wd{wd:g}".replace(".", "_")


def export_pairs():
    """Measured Vs beside the modelled speeds at the same point, for all nine configurations."""
    meas = {}
    with io.open(os.path.join(REPO, "clean", "cases", "C", "points.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            meas.setdefault((r["config"], float(r["wind_direction_deg"])), []).append(r)
    rows = []
    for cb in CONFIGS:
        study = os.path.join(VAL, f"aij_C_{cb}_realizableKE_L3")
        for wd in WDS:
            probe = {}
            with io.open(os.path.join(study, f"ref_{label(wd)}.probe.csv"), encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    probe[(round(float(r["x"]), 6), round(float(r["y"]), 6), round(float(r["z"]), 6))] = r
            for m in meas[(cb, wd)]:
                x, y, z = float(m["x"]), float(m["y"]), float(m["z"])
                p = probe[(round(-y * SCALE, 6), round(x * SCALE, 6), round(z * SCALE, 6))]
                um, k = float(p["U_mag"]), max(float(p["k"]), 0.0)
                rows.append({"config": cb, "wind_direction_deg": wd, "point_id": int(m["point_id"]),
                             "x": x, "y": y, "z": z, "measured_over_UH": float(m["Vs"]) / UH,
                             "scalar_over_UH": math.sqrt(um * um + 2 * k) / UH, "vector_over_UH": um / UH})
    os.makedirs(RESULTS, exist_ok=True)
    with io.open(PAIRS, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"wrote {os.path.relpath(PAIRS, REPO)} ({len(rows)} rows)")


def read_pairs():
    out = {}
    with io.open(PAIRS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (r["config"], float(r["wind_direction_deg"]))
            out.setdefault(key, []).append({k: (v if k == "config" else float(v)) for k, v in r.items()})
    return out


def scores(cb, wd, kind):
    with io.open(os.path.join(RESULTS, f"caseC_openfoam12_realizableKE_{cb}.json"), encoding="utf-8") as f:
        return json.load(f)[f"vs.{label(wd)}.{kind}"]


def blocks(cb):
    """The nine D = 0.2 m cubes on a 0.4 m pitch; the centre one per configuration."""
    out = []
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            centre = i == 0 and j == 0
            if centre and cb == "0D":
                continue
            out.append((0.4 * i - 0.1, 0.4 * j - 0.1, centre and cb == "2D"))
    return out


if os.path.isdir(VAL):
    export_pairs()
pairs = read_pairs()

# ----------------------------------------------------------------------------- figure 1
style.apply()
fig, axs = uplt.subplots(nrows=3, ncols=3, refwidth=2.1, refaspect=1, share=True)
lo, hi = 0.0, 1.25
for r, cb in enumerate(CONFIGS):
    for c, wd in enumerate(WDS):
        ax = axs[r, c]
        pts = pairs[(cb, wd)]
        o = np.array([p["measured_over_UH"] for p in pts])
        scalar = np.array([p["scalar_over_UH"] for p in pts])
        vector = np.array([p["vector_over_UH"] for p in pts])
        style.one_to_one(ax, lo, hi)
        ax.scatter(o, vector, s=16, facecolor="none", edgecolor=style.OPENFOAM, linewidth=0.7, alpha=0.75, zorder=2)
        ax.scatter(o, scalar, s=16, color=style.OPENFOAM, edgecolor=style.SURFACE, linewidth=0.35, zorder=3)
        m = scores(cb, wd, "scalar")
        style.stats(ax, f"R {m['R']:+.2f}\nFAC2 {m['Fac2']:.2f}\nFB {m['Fb']:+.2f}")
        ax.format(xlim=(lo, hi), ylim=(lo, hi))
style.outer_ticks(axs, 3, 3)
style.finish(fig, "AIJ UWE Case C — Eddy3D (OpenFOAM 12, realizable k-ε) vs wind tunnel, z = 0.1 D",
             handles=[style.marker(style.OPENFOAM, "Eddy3D √(|U|²+2k)"),
                      style.marker(style.OPENFOAM, "Eddy3D |U|", filled=False),
                      style.line(style.REFERENCE, "1:1", lw=1.0), style.line(style.REFERENCE, "factor of two", lw=0.8, ls=":")],
             toplabels=[f"WD = {wd:g}°" for wd in WDS], leftlabels=[CB_TITLE[cb] for cb in CONFIGS],
             xlabel="Tunnel Vs/U$_H$ [–]", ylabel="Eddy3D speed/U$_H$ [–]")
style.save(fig, "case-c-openfoam-agreement.png")

# ----------------------------------------------------------------------------- figure 2
cmap = LinearSegmentedColormap.from_list("aij_diverging", [style.SLOW, style.NEUTRAL, style.FAST])
fig2, axs2 = uplt.subplots(nrows=3, ncols=3, refwidth=2.1, refaspect=1, share=True)
for r, cb in enumerate(CONFIGS):
    for c, wd in enumerate(WDS):
        ax = axs2[r, c]
        for bx, by, tall in blocks(cb):
            ax.add_patch(Rectangle((bx, by), 0.2, 0.2, facecolor="#9f9e99" if tall else BLOCK,
                                   edgecolor="none", zorder=1))
        pts = pairs[(cb, wd)]
        x = np.array([p["x"] for p in pts]); y = np.array([p["y"] for p in pts])
        ratio = np.log2(np.array([p["scalar_over_UH"] / p["measured_over_UH"] for p in pts]))
        sc = ax.scatter(x, y, c=np.clip(ratio, -1, 1), cmap=cmap, vmin=-1, vmax=1, s=26,
                        edgecolor=style.SURFACE, linewidth=0.4, zorder=3)
        # The wind: from upstream, rotating from +x toward -y with WD (the CSV frame).
        t = math.radians(wd)
        d = np.array([math.cos(t), -math.sin(t)])
        tail = -0.52 * d
        ax.add_patch(FancyArrowPatch(tuple(tail), tuple(tail + 0.14 * d), arrowstyle="-|>",
                                     mutation_scale=11, color=style.INK, lw=1.4, zorder=4))
        ax.format(xlim=(-0.58, 0.58), ylim=(-0.58, 0.58), aspect="equal")
style.outer_ticks(axs2, 3, 3)
fig2.colorbar(sc, loc="b", ticks=[-1, -0.5, 0, 0.5, 1], length=0.7,
              label="log$_2$(Eddy3D √(|U|²+2k) / tunnel Vs) [–]:  −1 = half the tunnel's speed,  0 = equal,  +1 = twice")
style.finish(fig2, "AIJ UWE Case C — where the model is slow (red) or fast (blue), z = 0.1 D",
             toplabels=[f"WD = {wd:g}°" for wd in WDS], leftlabels=[CB_TITLE[cb] for cb in CONFIGS],
             xlabel="x [m]", ylabel="y [m]")
style.save(fig2, "case-c-openfoam-bias-map.png")
