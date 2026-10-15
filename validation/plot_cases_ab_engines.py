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
U = U_y, V = -U_x; OpenLB: aij_{A,B}_openlb_dx1.6/case/results/probes.csv, identity frame; FluidX3D:
aij_{A,B}_fluidx3d_H64/model-lattice.csv, identity frame, already divided by U_H). The pairs are snapshotted
to validation/results/case{A,B}_<engine>_pairs.csv and the figure is drawn from the snapshots, so it rebuilds
from this repository alone. Scores come from each engine's results.json snapshot
(validation/results/case{A,B}_<engine>.json).

FluidX3D is scored on the heights where its own empty-domain control reproduces the imposed log law within
5 % (its bounce-back ground carries no roughness wall function, so the flow just above it is slower than the
tunnel's approach flow). Its panels draw those points filled and the excluded near-ground points hollow, and
print the scores of the filled ones.
"""
from __future__ import annotations

import csv
import io
import json
import os

import numpy as np
import ultraplot as uplt

import plotstyle as style

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
VAL = r"C:/Eddy3DVal"
RESULTS = os.path.join(HERE, "results")

UH = {"A": 4.491, "B": 5.133}
SCALE = 100.0

# engine id (file stem), label, colour
ENGINES = [
    ("openfoam12_realizableKE", "OpenFOAM 12, realizable k-ε", style.OPENFOAM),
    ("openlb", "OpenLB, dx = 1.6 m", style.OPENLB),
    ("fluidx3d", "FluidX3D", style.FLUIDX3D),
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
    out = {}
    with io.open(os.path.join(VAL, f"aij_{case}_fluidx3d_H64", "model-lattice.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(round(float(r["x"]), 5), round(float(r["y"]), 5), round(float(r["z"]), 5))] = tuple(
                float(r[f"{q}/Uh"]) * UH[case] for q in "UVW")
    return [out[(round(p["x"], 5), round(p["y"], 5), round(p["z"], 5))] for p in pts]


def scores(case, engine, q):
    """(score, comparable heights or None): FluidX3D's headline is its comparable-heights subset."""
    with io.open(os.path.join(RESULTS, f"case{case}_{engine}.json"), encoding="utf-8") as f:
        res = json.load(f)
    if f"velocity.{q}" in res:
        return res[f"velocity.{q}"], None
    return res[f"velocity.{q}.comparable"]["score"], set(res["control.comparableHeights"]["heights"])


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

style.apply()
engines = [e for e in ENGINES if all(os.path.exists(pairs_path(c, e[0])) for c in ("A", "B"))]
cols = [("A", "U"), ("A", "V"), ("B", "U"), ("B", "V")]
# One range per column, shared by every engine, so a row compares with the row above it at a glance.
limits = {}
for case, q in cols:
    vals = [v for e, _, _ in engines for p in read_pairs(case, e) for v in (p[f"{q}_meas"], p[f"{q}_model"])]
    lo, hi = min(vals), max(vals)
    pad = 0.06 * (hi - lo)
    limits[(case, q)] = (lo - pad, hi + pad)
fig, axs = uplt.subplots(nrows=len(engines), ncols=4, refwidth=2.0, refaspect=1, share=False, wspace=4.2, hspace=1.2)
axs = np.asarray(axs).reshape(len(engines), 4)
for r, (engine, label, colour) in enumerate(engines):
    for c, (case, q) in enumerate(cols):
        ax = axs[r, c]
        pr = read_pairs(case, engine)
        o = np.array([p[f"{q}_meas"] for p in pr]); m = np.array([p[f"{q}_model"] for p in pr])
        lo, hi = limits[(case, q)]
        style.one_to_one(ax, lo, hi, factor_two=(q == "U"))
        s, heights = scores(case, engine, q)
        keep = np.array([heights is None or round(p["z"], 5) in heights for p in pr])
        ax.scatter(o[keep], m[keep], s=15, color=colour, edgecolor=style.SURFACE, linewidth=0.35, zorder=3)
        if not keep.all():
            ax.scatter(o[~keep], m[~keep], s=15, facecolor="none", edgecolor=colour, linewidth=0.8, zorder=2)
        note = f"\nn {s['Count']} filled" if heights is not None else ""
        style.stats(ax, f"R {s['R']:+.2f}\nFAC2 {s['Fac2']:.2f}{note}")
        last = r == len(engines) - 1
        ax.format(xlim=(lo, hi), ylim=(lo, hi), xlabel="Tunnel [–]" if last else None,
                  ylabel="Model [–]" if c == 0 else None)
        ax.tick_params(labelbottom=last)
style.finish(fig, "AIJ UWE Cases A and B — every engine on the same measured points",
             handles=[style.marker(colour, label) for _, label, colour in engines]
             + [style.marker(style.FLUIDX3D, "FluidX3D, excluded near-ground point", filled=False),
                style.line(style.REFERENCE, "1:1", lw=1.0), style.line(style.REFERENCE, "factor of two", lw=0.8, ls=":")],
             ncols=3, toplabels=[f"Case {case} · {q}/U$_H$" for case, q in cols],
             leftlabels=[label.split(",")[0] for _, label, _ in engines])
style.save(fig, "cases-ab-engine-comparison.png")
print("engines", [e[0] for e in engines])
