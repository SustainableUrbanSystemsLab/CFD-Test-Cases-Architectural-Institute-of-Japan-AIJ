"""Validation figure for AIJ UWE Case D (high-rise among city blocks) solved with Eddy3D / OpenFOAM.

  figures/case-d-openfoam-agreement.png
      Does the model agree with the tunnel? Measured thermistor Vs/U_H against the modelled sqrt(|U|^2 + 2k)/U_H
      (filled) and |U|/U_H (hollow), one panel per solved heading; and the 33 split-fibre points' |U| against the
      model's |U| at 0 deg, where both sides are the same quantity.

Inputs: the measured table clean/cases/D/points.csv; the fixture's probes under
C:/Eddy3DVal/aij_D_realizableKE_L3 (thermistor{0,22.5,45}.probe.csv, splitfibre.probe.csv), written by
TestAijCaseDContainerE2E in the case frame, which is the model frame rotated and scaled: case (X, Y, Z) =
400 (-y, x, z), with the model's +x (the wind at 0 deg) along case +Y. The per-point pairs are snapshotted to
validation/results/caseD_openfoam12_realizableKE_pairs.csv and the figure is drawn from the snapshot.
Scores come from the fixture's results.json (validation/results/caseD_openfoam12_realizableKE.json).
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

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STUDY = r"C:/Eddy3DVal/aij_D_realizableKE_L3"
RESULTS = os.path.join(HERE, "results")
PAIRS = os.path.join(RESULTS, "caseD_openfoam12_realizableKE_pairs.csv")
SCORES = os.path.join(RESULTS, "caseD_openfoam12_realizableKE.json")

SCALE = 400.0        # the fixture solves at full scale, 1:400
HEADINGS = [0.0, 22.5, 45.0]
FIELDS = ["instrument", "wind_direction_deg", "point_id", "x", "y", "z", "measured_over_UH", "scalar_over_UH",
          "vector_over_UH", "U_meas", "V_meas", "W_meas", "U_model", "V_model", "W_model"]


def uh():
    with io.open(SCORES, encoding="utf-8") as f:
        return float(json.load(f)["Uh"])


def read_probe(name):
    """The fixture's probe CSV keyed by model coordinates (case (X, Y, Z) / 400 -> model (Y, -X, Z))."""
    out = {}
    with io.open(os.path.join(STUDY, f"{name}.probe.csv"), encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(round(float(r["y"]) / SCALE, 6), round(-float(r["x"]) / SCALE, 6), round(float(r["z"]) / SCALE, 6))] = r
    return out


def export_pairs():
    u_h = uh()
    key = lambda r: (round(float(r["x"]), 6), round(float(r["y"]), 6), round(float(r["z"]), 6))  # noqa: E731
    with io.open(os.path.join(REPO, "clean", "cases", "D", "points.csv"), encoding="utf-8") as f:
        meas = list(csv.DictReader(f))
    rows = []
    for h in HEADINGS:
        name = f"thermistor{h:g}"
        if not os.path.isfile(os.path.join(STUDY, f"{name}.probe.csv")):
            continue
        probe = read_probe(name)
        for m in meas:
            if m["instrument"] != "thermistor" or float(m["wind_direction_deg"]) != h or m["Vs"] == "":
                continue
            p = probe[key(m)]
            um, k = float(p["U_mag"]), max(float(p["k"]), 0.0)
            rows.append({"instrument": "thermistor", "wind_direction_deg": h, "point_id": int(m["point_id"]),
                         "x": float(m["x"]), "y": float(m["y"]), "z": float(m["z"]),
                         "measured_over_UH": float(m["Vs"]) / u_h, "scalar_over_UH": math.sqrt(um * um + 2 * k) / u_h,
                         "vector_over_UH": um / u_h})
    probe = read_probe("splitfibre")
    for m in meas:
        if m["instrument"] != "split_fibre":
            continue
        p = probe[key(m)]
        um, k = float(p["U_mag"]), max(float(p["k"]), 0.0)
        U, V, W = (float(m[c]) for c in "UVW")
        rows.append({"instrument": "split_fibre", "wind_direction_deg": 0.0, "point_id": int(m["point_id"]),
                     "x": float(m["x"]), "y": float(m["y"]), "z": float(m["z"]),
                     "measured_over_UH": math.sqrt(U * U + V * V + W * W) / u_h,
                     "scalar_over_UH": math.sqrt(um * um + 2 * k) / u_h, "vector_over_UH": um / u_h,
                     "U_meas": U / u_h, "V_meas": V / u_h, "W_meas": W / u_h,
                     # model +x is case +Y, model +y is case -X
                     "U_model": float(p["U_y"]) / u_h, "V_model": -float(p["U_x"]) / u_h, "W_model": float(p["U_z"]) / u_h})
    with io.open(PAIRS, "w", encoding="utf-8", newline="\n") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (repr(v) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"wrote {os.path.relpath(PAIRS, REPO)} ({len(rows)} rows)")


def read_pairs():
    with io.open(PAIRS, encoding="utf-8") as f:
        return [{k: (v if k == "instrument" else float(v) if v != "" else None) for k, v in r.items()} for r in csv.DictReader(f)]


if os.path.isdir(STUDY):
    export_pairs()
pairs = read_pairs()
with io.open(SCORES, encoding="utf-8") as f:
    res = json.load(f)

style.apply()
solved = [h for h in HEADINGS if any(p["instrument"] == "thermistor" and p["wind_direction_deg"] == h for p in pairs)]
fig, axs = uplt.subplots(ncols=len(solved) + 1, refwidth=2.5, refaspect=1, share=True)
lo, hi = 0.0, 1.2
for c, h in enumerate(solved + ["split"]):
    ax = axs[c]
    if h == "split":
        pts = [p for p in pairs if p["instrument"] == "split_fibre"]
        title, score, xlabel = "Split fibre, WD = 0°", res["splitfibre.speed"], "Tunnel |U|/U$_H$ [–]"
    else:
        pts = [p for p in pairs if p["instrument"] == "thermistor" and p["wind_direction_deg"] == h]
        title, score, xlabel = f"Thermistor, WD = {h:g}°", res[f"vs.{h:g}.corrected"], "Tunnel Vs/U$_H$ [–]"
    o = np.array([p["measured_over_UH"] for p in pts])
    scalar = np.array([p["scalar_over_UH"] for p in pts])
    vector = np.array([p["vector_over_UH"] for p in pts])
    style.one_to_one(ax, lo, hi)
    if h == "split":
        # the instrument measures |U| itself: compare the model's |U|, filled
        ax.scatter(o, vector, s=22, color=style.OPENFOAM, edgecolor=style.SURFACE, linewidth=0.4, zorder=3)
    else:
        ax.scatter(o, vector, s=22, facecolor="none", edgecolor=style.OPENFOAM, linewidth=0.8, alpha=0.8, zorder=2)
        ax.scatter(o, scalar, s=22, color=style.OPENFOAM, edgecolor=style.SURFACE, linewidth=0.4, zorder=3)
    style.stats(ax, f"R {score['R']:+.2f}\nFAC2 {score['Fac2']:.2f}\nFB {score['Fb']:+.2f}\nn {score['Count']}")
    ax.format(xlim=(lo, hi), ylim=(lo, hi), title=title)
style.outer_ticks(axs, 1, len(solved) + 1)
style.finish(fig, "AIJ UWE Case D — Eddy3D (OpenFOAM 12, realizable k-ε) vs wind tunnel, z/H = 0.02",
             handles=[style.marker(style.OPENFOAM, "Eddy3D √(|U|²+2k)"),
                      style.marker(style.OPENFOAM, "Eddy3D |U|", filled=False),
                      style.line(style.REFERENCE, "1:1", lw=1.0), style.line(style.REFERENCE, "factor of two", lw=0.8, ls=":")],
             xlabel="Tunnel speed/U$_H$ [–]  (thermistor Vs; split fibre |U|)", ylabel="Eddy3D speed/U$_H$ [–]")
style.save(fig, "case-d-openfoam-agreement.png")
print("headings", solved)
