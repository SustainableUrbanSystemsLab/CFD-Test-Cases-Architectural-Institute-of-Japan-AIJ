"""Cases A and B, solver against solver: the same measured points scored for every engine that solved them.

  figures/cases-ab-engine-comparison.png
      Measured against modelled U/U_H and V/U_H, Cases A and B, one ROW per engine (small multiples:
      each panel carries one engine, in that engine's colour, with its scores printed beside it).

Engines and their colours (fixed across every figure in this repository): OpenFOAM 12 realizable k-epsilon
slot 1 blue; OpenLB slot 4 yellow; FluidX3D slot 5 magenta. Yellow and magenta sit below 3:1 contrast on
the light surface, so every panel prints its scores (the palette's relief rule), and no panel carries two
engines (only slots 1-3 are validated against each other for overlapping marks).

Inputs: the measured tables clean/cases/{A,B}/points.csv; each engine's probes at those points under
C:/Eddy3DVal (OpenFOAM: aij_{A,B}_realizableKE_L3/reference.probe.csv, case frame wind along +y, so
U = U_y, V = -U_x; OpenLB: aij_{A,B}_openlb_dx1.6/case/results/probes.csv, identity frame; FluidX3D: see
FLUIDX3D below). The pairs are snapshotted to validation/results/case{A,B}_<engine>_pairs.csv and the
figure is drawn from the snapshots, so it rebuilds from this repository alone. Scores come from each
engine's results.json snapshot (validation/results/case{A,B}_<engine>.json).
"""
from __future__ import annotations

import csv
import io
import json
import os

import numpy as np
import ultraplot as uplt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
VAL = r"C:/Eddy3DVal"
RESULTS = os.path.join(HERE, "results")
INK = "#2b2b2b"
MUTED = "#8a8a88"
SURFACE = "#fcfcfb"

UH = {"A": 4.491, "B": 5.133}
SCALE = 100.0

# engine id (file stem), label, colour, probe reader
ENGINES = [
    ("openfoam12_realizableKE", "OpenFOAM 12, realizable k-ε", "#2a78d6"),
    ("openlb", "OpenLB, dx = 1.6 m", "#eda100"),
    ("fluidx3d", "FluidX3D", "#e87ba4"),
]


def measured(case):
    rows = []
    with io.open(os.path.join(REPO, "clean", "cases", case, "points.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({k: float(r[k]) for k in ("x", "y", "z", "U", "V", "W")} | {"point_id": int(r["point_id"])})
    return rows


def probe_openfoam(case, pts):
    out = {}
    with io.open(os.path.join(VAL, f"aij_{case}_realizableKE_L3", "reference.probe.csv"), encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[(round(float(r["x"]), 4), round(float(r["y"]), 4), round(float(r["z"]), 4))] = (
                float(r["U_y"]), -float(r["U_x"]), float(r["U_z"]))
    return [out[(round(-p["y"] * SCALE, 4) + 0.0, round(p["x"] * SCALE, 4), round(p["z"] * SCALE, 4))] for p in pts]


def probe_openlb(case, pts):
    out = {}
    with io.open(os.path.join(VAL, f"aij_{case}_openlb_dx1.6", "case", "results", "probes.csv"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or line.startswith("x,"):
                continue
            x, y, z, ux, uy, uz = map(float, line.split(","))
            out[(round(x, 4), round(y, 4), round(z, 4))] = (ux, uy, uz)
    return [out[(round(p["x"] * SCALE, 4), round(p["y"] * SCALE, 4), round(p["z"] * SCALE, 4))] for p in pts]


def probe_fluidx3d(case, pts):
    raise FileNotFoundError  # wired up when the FluidX3D strand's probe format is known


PROBES = {"openfoam12_realizableKE": probe_openfoam, "openlb": probe_openlb, "fluidx3d": probe_fluidx3d}


def pairs_path(case, engine):
    return os.path.join(RESULTS, f"case{case}_{engine}_pairs.csv")


def export(case, engine):
    pts = measured(case)
    try:
        model = PROBES[engine](case, pts)
    except (FileNotFoundError, KeyError):
        return False
    with io.open(pairs_path(case, engine), "w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["point_id", "x", "y", "z", "U_meas", "V_meas", "W_meas", "U_model", "V_model", "W_model"])
        for p, (u, v, ww) in zip(pts, model):
            w.writerow([p["point_id"], repr(p["x"]), repr(p["y"]), repr(p["z"]),
                        repr(p["U"] / UH[case]), repr(p["V"] / UH[case]), repr(p["W"] / UH[case]),
                        repr(u / UH[case]), repr(v / UH[case]), repr(ww / UH[case])])
    print(f"wrote {os.path.relpath(pairs_path(case, engine), REPO)}")
    return True


def read_pairs(case, engine):
    with io.open(pairs_path(case, engine), encoding="utf-8") as f:
        return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]


if os.path.isdir(VAL):
    for e, _, _ in ENGINES:
        for c in ("A", "B"):
            export(c, e)

engines = [e for e in ENGINES if all(os.path.exists(pairs_path(c, e[0])) for c in ("A", "B"))]
cols = [("A", "U"), ("A", "V"), ("B", "U"), ("B", "V")]
fig, axs = uplt.subplots(nrows=len(engines), ncols=4, refwidth=1.55, refaspect=1, share=False, hspace=3.6, wspace=3.8)
axs = np.asarray(axs).reshape(len(engines), 4)
for r, (engine, label, colour) in enumerate(engines):
    for c, (case, q) in enumerate(cols):
        ax = axs[r, c]
        pr = read_pairs(case, engine)
        o = np.array([p[f"{q}_meas"] for p in pr]); m = np.array([p[f"{q}_model"] for p in pr])
        lo = float(min(o.min(), m.min())); hi = float(max(o.max(), m.max()))
        pad = 0.08 * (hi - lo); lo, hi = lo - pad, hi + pad
        ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1.0, zorder=1)
        if q == "U":
            line = np.array([max(lo, 1e-6), hi])
            ax.plot(line, 2 * line, color=MUTED, lw=0.7, ls=":", zorder=1)
            ax.plot(line, 0.5 * line, color=MUTED, lw=0.7, ls=":", zorder=1)
        ax.scatter(o, m, s=9, color=colour, edgecolor=SURFACE, linewidth=0.25, zorder=3)
        with io.open(os.path.join(RESULTS, f"case{case}_{engine}.json"), encoding="utf-8") as f:
            s = json.load(f)[f"velocity.{q}"]
        ax.text(0.05, 0.95, f"R {s['R']:+.2f}\nFAC2 {s['Fac2']:.2f}\nq {s['HitRate']:.2f}", transform=ax.transAxes,
                va="top", ha="left", fontsize=6.3, color=INK)
        ax.format(xlim=(lo, hi), ylim=(lo, hi), xlabel="tunnel" if r == len(engines) - 1 else None,
                  ylabel="model" if c == 0 else None, title=f"Case {case} — {q}/U$_H$" if r == 0 else None,
                  titleloc="l", titlesize=8)
    axs[r, 0].text(-0.5, 0.5, label, transform=axs[r, 0].transAxes, rotation=90, va="center", ha="center",
                   fontsize=8, color=INK)
fig.format(suptitle="AIJ UWE Cases A and B — every engine on the same measured points", abc=False,
           gridcolor="#e3e3e0", gridlinewidth=0.6)
fig.save(os.path.join(HERE, "figures", "cases-ab-engine-comparison.png"), dpi=220)
print("wrote cases-ab-engine-comparison.png with", [e[0] for e in engines])
