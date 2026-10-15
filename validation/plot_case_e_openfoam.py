"""Validation figures for AIJ UWE Case E (Niigata district) solved with Eddy3D / OpenFOAM.

Two figures, each answering one question:

  figures/case-e-openfoam-agreement.png
      Does the model agree with the tunnel?  Measured velocity ratio against the modelled sqrt(|U|^2 +
      2k)/U_ref (filled) and |U|/U_ref (hollow), before and after construction, and the CHANGE the
      construction makes — the quantity in which inflow, closure and instrument biases largely cancel.
  figures/case-e-openfoam-bias-map.png
      WHERE does it agree?  log2(model / tunnel) of the scalar speed at the 80 points on the plan of the
      district, before and after construction.

U_ref is the solved approach speed at 15.9 m (the meteorological station height the benchmark
normalises by), read per state and direction by the fixture; the tunnel's ratios are as published.

Inputs: the measured table clean/cases/E/points.csv, and the per-state model tables the Eddy3D
fixture TestAijCaseEContainerE2E wrote under C:/Eddy3DVal/aij_E_{bc,ac}_realizableKE_L3/. The pairs
are snapshotted to validation/results/caseE_openfoam12_realizableKE_pairs.csv and the figures are
drawn from that snapshot, so they rebuild from this repository alone when C:/Eddy3DVal is absent.
Frame: full-scale metres, +x east, +y north, the frame of the workbook, the 3dm and points.csv.

Colours: slot 1 of the validated categorical palette (blue #2a78d6) is the OpenFOAM model, as in the
other figures; the map's diverging scale is the palette's blue <-> red pair around its neutral gray.
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
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
VAL = r"C:/Eddy3DVal"
RESULTS = os.path.join(HERE, "results")
PAIRS = os.path.join(RESULTS, "caseE_openfoam12_realizableKE_pairs.csv")
SCORES = os.path.join(RESULTS, "caseE_openfoam12_realizableKE.json")

BUILDING = "#d9d8d4"
NEW_BUILDING = "#a9a8a3"

DIRECTION = "SW"
STATES = [("bc", "before construction"), ("ac", "after construction")]


def export_pairs():
    meas = {}
    with io.open(os.path.join(REPO, "clean", "cases", "E", "points.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["wind_direction"] == DIRECTION:
                meas[(r["config"], round(float(r["x"]), 3), round(float(r["y"]), 3))] = r
    rows = []
    for state, _ in STATES:
        path = os.path.join(VAL, f"aij_E_{state}_realizableKE_L3", f"model_{DIRECTION}.csv")
        with io.open(path, encoding="utf-8") as f:
            for m in csv.DictReader(f):
                key = (state, round(float(m["x"]), 3), round(float(m["y"]), 3))
                r = meas[key]
                rows.append({"config": state, "wind_direction": DIRECTION, "point_id": int(r["point_id"]),
                             "x": float(m["x"]), "y": float(m["y"]), "z": float(m["z"]),
                             "measured_ratio": float(r["velocity_ratio"]),
                             "scalar_ratio": float(m["rms/Uref"]), "vector_ratio": float(m["Umag/Uref"])})
    assert len(rows) == 160, len(rows)
    with io.open(PAIRS, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"wrote {os.path.relpath(PAIRS, REPO)} ({len(rows)} rows)")


def read_pairs():
    out = {s: [] for s, _ in STATES}
    with io.open(PAIRS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["config"]].append({k: (v if k in ("config", "wind_direction") else float(v)) for k, v in r.items()})
    for s in out:
        out[s].sort(key=lambda p: p["point_id"])
    return out


def footprints(name):
    """Plan-view triangles of an ASCII STL: the roofs are what has area in plan."""
    tris, cur = [], []
    with io.open(os.path.join(REPO, "clean", "cases", "E", name), encoding="utf-8") as f:
        for line in f:
            t = line.split()
            if t and t[0] == "vertex":
                cur.append((float(t[1]), float(t[2]), float(t[3])))
                if len(cur) == 3:
                    (x1, y1, z1), (x2, y2, z2), (x3, y3, z3) = cur
                    if abs((x2 - x1) * (y3 - y1) - (x3 - x1) * (y2 - y1)) > 1e-6:
                        tris.append(((x1, y1), (x2, y2), (x3, y3), max(z1, z2, z3)))
                    cur = []
    return tris


if os.path.isdir(VAL):
    export_pairs()
pairs = read_pairs()
with io.open(SCORES, encoding="utf-8") as f:
    scores = json.load(f)

# ----------------------------------------------------------------------------- figure 1
style.apply()
fig, axs = uplt.subplots(nrows=1, ncols=3, refwidth=2.5, refaspect=1, share=False, wspace=(1.0, 6.0))
hi = 1.08 * max(max(max(p["measured_ratio"], p["scalar_ratio"]) for p in pairs[s]) for s, _ in STATES)
for i, (state, title) in enumerate(STATES):
    ax = axs[i]
    pts = pairs[state]
    o = np.array([p["measured_ratio"] for p in pts])
    scalar = np.array([p["scalar_ratio"] for p in pts])
    vector = np.array([p["vector_ratio"] for p in pts])
    style.one_to_one(ax, 0, hi)
    ax.scatter(o, vector, s=22, facecolor="none", edgecolor=style.OPENFOAM, linewidth=0.8, alpha=0.8, zorder=2)
    ax.scatter(o, scalar, s=22, color=style.OPENFOAM, edgecolor=style.SURFACE, linewidth=0.4, zorder=3)
    m = scores[f"vr.{state}.{DIRECTION}.rms"]
    style.stats(ax, f"R {m['R']:+.2f}\nFAC2 {m['Fac2']:.2f}\nFB {m['Fb']:+.2f}")
    ax.format(xlim=(0, hi), ylim=(0, hi), xlabel="Tunnel velocity ratio [–]",
              ylabel="Eddy3D speed/U$_{ref}$ [–]" if i == 0 else None, title=f"{title.capitalize()}, wind from {DIRECTION}")
    if i:
        ax.tick_params(labelleft=False)

ax = axs[2]
d_obs = np.array([a["measured_ratio"] - b["measured_ratio"] for a, b in zip(pairs["ac"], pairs["bc"])])
d_s = np.array([a["scalar_ratio"] - b["scalar_ratio"] for a, b in zip(pairs["ac"], pairs["bc"])])
d_v = np.array([a["vector_ratio"] - b["vector_ratio"] for a, b in zip(pairs["ac"], pairs["bc"])])
lim = 1.1 * float(max(np.abs(d_obs).max(), np.abs(d_s).max(), np.abs(d_v).max()))
ax.axhline(0, color=style.REFERENCE, lw=0.8, zorder=1)
ax.axvline(0, color=style.REFERENCE, lw=0.8, zorder=1)
ax.plot([-lim, lim], [-lim, lim], color=style.REFERENCE, lw=1.0, zorder=1)
ax.scatter(d_obs, d_v, s=22, facecolor="none", edgecolor=style.OPENFOAM, linewidth=0.8, alpha=0.8, zorder=2)
ax.scatter(d_obs, d_s, s=22, color=style.OPENFOAM, edgecolor=style.SURFACE, linewidth=0.4, zorder=3)
style.stats(ax, f"R {scores[f'delta.{DIRECTION}.R.rms']:+.2f}  √(|U|²+2k)\nR {scores[f'delta.{DIRECTION}.R']:+.2f}  |U|")
ax.format(xlim=(-lim, lim), ylim=(-lim, lim), xlabel="Tunnel: after − before [–]", ylabel="Eddy3D: after − before [–]",
          title="What the construction changes")
style.finish(fig, "AIJ UWE Case E — Eddy3D (OpenFOAM 12, realizable k-ε, tabulated inlet) vs wind tunnel, z = 2 m",
             handles=[style.marker(style.OPENFOAM, "Eddy3D √(|U|²+2k)"),
                      style.marker(style.OPENFOAM, "Eddy3D |U|", filled=False),
                      style.line(style.REFERENCE, "1:1", lw=1.0), style.line(style.REFERENCE, "factor of two", lw=0.8, ls=":")])
style.save(fig, "case-e-openfoam-agreement.png")

# ----------------------------------------------------------------------------- figure 2
cmap = LinearSegmentedColormap.from_list("aij_diverging", [style.SLOW, style.NEUTRAL, style.FAST])
fig2, axs2 = uplt.subplots(nrows=1, ncols=2, refwidth=3.6, refaspect=1, share=True)
xs = [p["x"] for p in pairs["bc"]]; ys = [p["y"] for p in pairs["bc"]]
pad = 30.0
xlim = (min(xs) - pad, max(xs) + pad); ylim = (min(ys) - pad, max(ys) + pad)
bc_tris = footprints("geometry_bc_3dm.stl")
ac_tris = footprints("geometry_ac_3dm.stl")
bc_keys = {tuple(sorted((round(a, 3), round(b, 3)) for a, b in t[:3])) for t in bc_tris}
for i, (state, title) in enumerate(STATES):
    ax = axs2[i]
    tris = bc_tris if state == "bc" else ac_tris
    old = [t[:3] for t in tris if state == "bc" or tuple(sorted((round(a, 3), round(b, 3)) for a, b in t[:3])) in bc_keys]
    new = [t[:3] for t in tris if state == "ac" and tuple(sorted((round(a, 3), round(b, 3)) for a, b in t[:3])) not in bc_keys]
    ax.add_collection(PolyCollection(old, facecolor=BUILDING, edgecolor="none", zorder=1))
    if new:
        ax.add_collection(PolyCollection(new, facecolor=NEW_BUILDING, edgecolor="none", zorder=1))
    pts = pairs[state]
    ratio = np.log2(np.array([p["scalar_ratio"] / p["measured_ratio"] for p in pts]))
    sc = ax.scatter([p["x"] for p in pts], [p["y"] for p in pts], c=np.clip(ratio, -1, 1), cmap=cmap,
                    vmin=-1, vmax=1, s=34, edgecolor=style.SURFACE, linewidth=0.5, zorder=3)
    # Wind FROM the south-west, blowing toward the north-east.
    d = np.array([math.sin(math.radians(45)), math.cos(math.radians(45))])
    tail = np.array([xlim[0] + 0.12 * (xlim[1] - xlim[0]), ylim[0] + 0.12 * (ylim[1] - ylim[0])])
    ax.add_patch(FancyArrowPatch(tuple(tail), tuple(tail + 30 * d), arrowstyle="-|>", mutation_scale=11,
                                 color=style.INK, lw=1.4, zorder=4))
    ax.format(xlim=xlim, ylim=ylim, aspect="equal", title=f"{title.capitalize()}, wind from {DIRECTION}")
style.outer_ticks(axs2, 1, 2)
fig2.colorbar(sc, loc="b", ticks=[-1, -0.5, 0, 0.5, 1], length=0.7,
              label="log$_2$(Eddy3D √(|U|²+2k) / tunnel) [–]:  −1 = half the tunnel's speed,  0 = equal,  +1 = twice")
style.finish(fig2, "AIJ UWE Case E — where the model is slow (red) or fast (blue), z = 2 m",
             xlabel="x, east [m]", ylabel="y, north [m]")
style.save(fig2, "case-e-openfoam-bias-map.png")
