"""Generate the static API under docs/api/ from the cleaned data.

    python scripts/build_api.py            # build + verify
    python scripts/build_api.py --check    # verify what is on disk, build nothing

Served by GitHub Pages at <site>/api/… ; every file is a plain GET. The point tables come from
`clean/` when `clean/manifest.json` names them and from the raw case folders otherwise (see
aijdata.load_points); re-run this script whenever either changes. Validation scores are read from
validation/results/*.json, which are snapshots of the Eddy3D fixtures' results.json files.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aijdata as D  # noqa: E402

REPO = D.REPO
DOCS = os.path.join(REPO, "docs")
API = os.path.join(DOCS, "api")
ASSETS = os.path.join(DOCS, "assets")
FIGURES = os.path.join(REPO, "validation", "figures")

REPO_URL = "https://github.com/SustainableUrbanSystemsLab/CFD-Test-Cases-Architectural-Institute-of-Japan-AIJ"
SITE = "https://sustainableurbansystems.com/CFD-Test-Cases-Architectural-Institute-of-Japan-AIJ"
API_BASE = SITE + "/api"
RAW_BASE = "https://raw.githubusercontent.com/SustainableUrbanSystemsLab/CFD-Test-Cases-Architectural-Institute-of-Japan-AIJ/main/docs/api"
SCHEMA_VERSION = "1.0.0"

ENGINES = [
    {"id": "openfoam12-realizableKE", "name": "OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor)", "kind": "RANS"},
    {"id": "openlb", "name": "OpenLB (Eddy3D LBM)", "kind": "LBM"},
    {"id": "fluidx3d", "name": "FluidX3D (Eddy3D GPU LBM)", "kind": "LBM"},
    {"id": "ml-surrogate", "name": "Eddy3D ML wind surrogate (pedestrian height)", "kind": "surrogate"},
]
# What the README's validation matrix says, per case and engine. "scored" says a run exists and its
# scores are in validation.json — NOT that it agrees; how well it agrees is in the numbers.
STATUS_MEANING = {
    "scored": "a validation run exists and its scores are in cases/{id}/validation.json; whether it agrees is in the numbers",
    "running": "the solve is in progress; no scores yet",
    "pending": "not run yet",
    "not comparable": ("the engine cannot produce the measured quantity at the measured location at a resolution this "
                       "hardware runs; the measurement behind that is in the README"),
}
ENGINE_STATUS = {
    "A": {"openfoam12-realizableKE": "scored", "openlb": "scored", "fluidx3d": "running", "ml-surrogate": "scored"},
    "B": {"openfoam12-realizableKE": "scored", "openlb": "scored", "fluidx3d": "running", "ml-surrogate": "scored"},
    "C": {"openfoam12-realizableKE": "scored", "openlb": "not comparable", "fluidx3d": "pending", "ml-surrogate": "scored"},
    "D": {"openfoam12-realizableKE": "running", "openlb": "not comparable", "fluidx3d": "pending", "ml-surrogate": "scored"},
    "E": {"openfoam12-realizableKE": "scored", "openlb": "not comparable", "fluidx3d": "pending", "ml-surrogate": "scored"},
}

# Every validation run whose results.json is snapshotted in validation/results/: which case, engine and
# configuration it is, which of its scores are the headline (label -> key), the figures that show it,
# and how to reproduce it. A file in validation/results/ that is not listed here is an error.
_FOAM_A_B = {"U": "velocity.U", "V": "velocity.V", "W": "velocity.W", "k": "k"}
_FOAM_C = {f"WD {wd} {q}": f"vs.{lab}.{key}" for wd, lab in (("0°", "wd-0"), ("22.5°", "wd22_5"), ("45°", "wd45"))
           for q, key in (("√(|U|²+2k)", "scalar"), ("|U|", "vector"))}
RUNS = [
    ("A", "openfoam12-realizableKE", None, "caseA_openfoam12_realizableKE.json", _FOAM_A_B,
     ["cases-ab-openfoam-agreement.png", "cases-ab-openfoam-profiles.png"], "Eddy3D fixture TestAijCaseAContainerE2E; figures validation/plot_cases_ab_openfoam.py"),
    ("B", "openfoam12-realizableKE", None, "caseB_openfoam12_realizableKE.json", _FOAM_A_B,
     ["cases-ab-openfoam-agreement.png", "cases-ab-openfoam-profiles.png"], "Eddy3D fixture TestAijCaseBContainerE2E; figures validation/plot_cases_ab_openfoam.py"),
    *[("C", "openfoam12-realizableKE", cb, f"caseC_openfoam12_realizableKE_{cb}.json", _FOAM_C,
       ["case-c-openfoam-agreement.png", "case-c-openfoam-bias-map.png"],
       f"Eddy3D fixture TestAijCaseC{cb}ContainerE2E; figures validation/plot_case_c_openfoam.py "
       "(per-point pairs in validation/results/caseC_openfoam12_realizableKE_pairs.csv)") for cb in ("0D", "1D", "2D")],
    *[(case, "openlb", None, f"case{case}_openlb.json",
       {"U": "velocity.U", "U, points ≥ 2 dx": "velocity.U.aboveTwoCells", "V": "velocity.V", "W": "velocity.W",
        "k (resolved)": "k.resolved", "V, lateral sign flipped (control)": "control.V.lateralSignFlipped"},
       ["cases-ab-engine-comparison.png"],
       f"Eddy3D fixture TestAijCase{case}OpenLbContainerE2E (OpenLB eddy3dWind, CPU image, dx = 1.6 m); "
       "figure validation/plot_cases_ab_engines.py") for case in ("A", "B")],
    ("E", "openfoam12-realizableKE", "SW", "caseE_openfoam12_realizableKE.json",
     {"before, √(|U|²+2k)": "vr.bc.SW.rms", "before, |U|": "vr.bc.SW.Umag", "after, √(|U|²+2k)": "vr.ac.SW.rms",
      "after, |U|": "vr.ac.SW.Umag", "no-construction ceiling control": "noConstruction.SW"},
     ["case-e-openfoam-agreement.png", "case-e-openfoam-bias-map.png"],
     "Eddy3D fixture TestAijCaseEContainerE2E (EDDY3D_AIJ_E_DIRECTIONS=SW, tabulated inlet); figures "
     "validation/plot_case_e_openfoam.py (per-point pairs in validation/results/caseE_openfoam12_realizableKE_pairs.csv)"),
    ("A", "ml-surrogate", None, "caseA_ml.json",
     {"|U| (z = 0.01 m plane)": "speed.vectorMagnitude", "|U|, lattice cut at ±250 m": "halfExtent250.forward",
      "wind reversed (control)": "negativeControl.reversedWind"},
     ["ml-surrogate-agreement.png"], "Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py"),
    ("B", "ml-surrogate", None, "caseB_ml.json",
     {"|U| (z = H/16 plane)": "speed.vectorMagnitude", "|U|, lattice cut at ±250 m": "halfExtent250.forward",
      "wind reversed (control)": "negativeControl.reversedWind"},
     ["ml-surrogate-agreement.png"], "Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py"),
    ("C", "ml-surrogate", None, "caseC_ml.json",
     {"Vs, 9 configurations": "speed.thermistor", "Vs, 2D WD 0, lattice cut at ±250 m": "halfExtent250.forward",
      "wind reversed (control)": "negativeControl.reversedWind"},
     ["ml-surrogate-agreement.png"], "Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py"),
    ("D", "ml-surrogate", None, "caseD_ml.json",
     {"Vs, thermistor, 3 WD": "speed.thermistor", "|U|, split fibre, WD 0": "speed.vectorMagnitude",
      "Vs, WD 0, lattice cut at ±250 m": "halfExtent250.forward", "wind reversed (control)": "negativeControl.reversedWind"},
     ["ml-surrogate-agreement.png"], "Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py"),
    ("E", "ml-surrogate", None, "caseE_ml.json",
     {"Vs/U(15.9 m), 16 WD, bc + ac": "speed.thermistor", "after construction": "speed.thermistor.after",
      "after − before": "delta.afterMinusBefore", "after, lattice cut at ±250 m": "halfExtent250.forward",
      "wind reversed (control)": "negativeControl.reversedWind"},
     ["ml-surrogate-agreement.png"], "Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py"),
]

# One caption per validation figure, used on the case pages and served with each result.
FIGURE_CAPTIONS = {
    "cases-ab-openfoam-agreement.png": ("Cases A and B, OpenFOAM 12 (realizable k-ε): measured against modelled U, V, W and k at "
                                        "every measured point, normalised by U_H, with the 1:1 line and the factor-of-two band."),
    "cases-ab-openfoam-profiles.png": ("Cases A and B, OpenFOAM 12: centre-plane vertical profiles of U/U_H at the measurement "
                                       "stations, measured points against the modelled line."),
    "case-c-openfoam-agreement.png": ("Case C, OpenFOAM 12: measured Vs/U_H against the modelled √(|U|²+2k)/U_H (filled) and "
                                      "|U|/U_H (hollow), one panel per configuration (centre block × wind direction)."),
    "case-c-openfoam-bias-map.png": ("Case C, OpenFOAM 12: log₂(model / tunnel) of the scalar speed at each of the 120 points "
                                     "on the plan of the array, per configuration — where the model is slow and where it is fast."),
    "case-e-openfoam-agreement.png": ("Case E, OpenFOAM 12, wind from SW: measured velocity ratio against the modelled "
                                      "√(|U|²+2k)/U_ref (filled) and |U|/U_ref (hollow), before and after construction, and the "
                                      "change the construction makes."),
    "case-e-openfoam-bias-map.png": ("Case E, OpenFOAM 12, wind from SW: log₂(model / tunnel) of the scalar speed at the 80 "
                                     "points on the plan of the district, before and after construction."),
    "cases-ab-engine-comparison.png": ("Cases A and B, every engine on the same points: measured against modelled U/U_H and "
                                       "V/U_H, one row per engine."),
    "ml-surrogate-agreement.png": ("Eddy3D ML surrogate (Yel-2.0): measured against predicted pedestrian-height speed, one "
                                   "panel per case, with the 1:1 line and the factor-of-two band."),
}

HEAD = D.git_head()
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def header():
    return {"schema_version": SCHEMA_VERSION, "generated_from": HEAD, "generated_at": NOW, "licence": D.LICENCE["data"]}


def write_json(rel, obj):
    path = os.path.join(API, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = dict(header())
    body.update(obj)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(body, f, indent=1, ensure_ascii=False, allow_nan=False)
        f.write("\n")
    return rel


def url(rel):
    return f"{API_BASE}/{rel}"


def render_url(case, configuration=None):
    """The site URL of a configuration's render (the case's default configuration if None)."""
    return f"{SITE}/assets/geometry/{D.render_file(case, configuration)}"


# ----------------------------------------------------------------------------- points

def points_summary(rows):
    cols = [c for c in D.POINT_COLUMNS if any(r[c] not in (None, "") for r in rows)]
    by = lambda key: sorted({str(r[key]) for r in rows})
    counts = {}
    for key in ("config", "instrument", "wind_direction_deg"):
        if key in cols:
            counts[key] = {k: sum(1 for r in rows if str(r[key]) == k) for k in by(key)}
    nulls = {c: sum(1 for r in rows if r[c] is None) for c in cols if c not in ("config", "instrument", "wind_direction")}
    xyz = [(r["x"], r["y"], r["z"]) for r in rows if None not in (r["x"], r["y"], r["z"])]
    return {
        "rows": len(rows),
        "distinct_points": len({r["point_id"] for r in rows}),
        "columns": cols,
        "counts": counts,
        "nulls": {k: v for k, v in nulls.items() if v},
        "bbox_min": [round(min(p[i] for p in xyz), 6) for i in range(3)],
        "bbox_max": [round(max(p[i] for p in xyz), 6) for i in range(3)],
    }


def build_points(case):
    rows, src = D.load_points(case)
    meta = D.CASES[case]
    summ = points_summary(rows)
    cols = summ["columns"]
    rel_json = write_json(f"cases/{case}/points.json", {
        "case": case, "title": meta["title"],
        "points_source": src,
        "units": meta["units"], "frame": meta["frame"],
        "columns": cols,
        "column_meaning": {c: COLUMN_MEANING[c] for c in cols},
        "n": len(rows),
        "points": [{c: r[c] for c in cols} for r in rows],
    })
    rel_csv = f"cases/{case}/points.csv"
    with io.open(os.path.join(API, rel_csv), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r[c] is None else r[c] for c in cols])
    return rows, src, summ, rel_json, rel_csv


COLUMN_MEANING = {
    "point_id": "the tunnel's own measurement point number",
    "config": "configuration key: 'default', Case C centre building '0D'/'1D'/'2D', Case E state 'bc' (before) / 'ac' (after construction)",
    "instrument": "'split_fibre' (vector components) or 'thermistor' (omnidirectional scalar speed)",
    "wind_direction": "compass name of the direction the wind comes FROM (Case E)",
    "wind_direction_deg": "AIJ wind direction in degrees; 0 is the case's reference direction (see frame)",
    "x": "m, case frame", "y": "m, case frame", "z": "m above ground, case frame",
    "U": "m/s, mean velocity along +x", "V": "m/s, mean velocity along +y (sign unified: positive toward +y)", "W": "m/s, mean velocity along +z",
    "uu": "m^2/s^2, variance of u", "vv": "m^2/s^2, variance of v", "ww": "m^2/s^2, variance of w",
    "k": "m^2/s^2, turbulent kinetic energy",
    "Vs": "m/s, mean omnidirectional scalar wind speed (thermistor); Case D also lists |U| of the split-fibre probe under Vs for its 33 vector points",
    "velocity_ratio": "dimensionless, Vs / U(15.9 m) with U(15.9 m) = 3.935 m/s (Case E)",
}


# ----------------------------------------------------------------------------- geometry

def expected_bbox(case, cfg):
    c = D.CASES[case]["configuration"]
    if case == "A":
        return [-c["b_m"] / 2, -c["b_m"] / 2, 0.0], [c["b_m"] / 2, c["b_m"] / 2, c["H_m"]]
    if case == "B":
        return [-c["depth_m"] / 2, -c["width_m"] / 2, 0.0], [c["depth_m"] / 2, c["width_m"] / 2, c["H_m"]]
    if case == "C":
        return [-0.5, -0.5, 0.0], [0.5, 0.5, 0.4 if cfg == "2D" else 0.2]
    if case == "D":
        e = c["array_extent_m"]
        return [e["x"][0], e["y"][0], e["z"][0]], [e["x"][1], e["y"][1], e["z"][1]]
    return None, None


def build_geometry(case):
    meta = D.CASES[case]
    entries = D.case_geometry(case)
    default_cfg = D.DEFAULT_CONFIGURATION[case]
    files, checks = [], []
    for cfg, tris, boxes, note in entries:
        stats = D.stl_stats(tris)
        rel = f"cases/{case}/geometry.stl" if cfg == default_cfg else f"cases/{case}/geometry_{cfg}.stl"
        D.write_ascii_stl(os.path.join(API, rel), tris, f"AIJ_case{case}_{cfg}")
        lo, hi = expected_bbox(case, cfg)
        ok = True
        if lo is not None:
            ok = all(abs(a - b) < 1e-6 for a, b in zip(stats["bbox_min"], lo)) and all(abs(a - b) < 1e-6 for a, b in zip(stats["bbox_max"], hi))
            if not ok:
                raise SystemExit(f"geometry check failed for {case}/{cfg}: bbox {stats['bbox_min']}..{stats['bbox_max']} != {lo}..{hi}")
        if boxes is not None and not stats["watertight"]:
            raise SystemExit(f"geometry check failed for {case}/{cfg}: box geometry is not edge-manifold")
        entry = {"configuration": cfg, "file": url(rel), "path": rel, "format": "ASCII STL, LF line endings, outward normals",
                 "source": note, "stats": stats, "bbox_matches_stated_dimensions": ok if lo is not None else None,
                 "render": render_url(case, cfg), "render_caption": D.RENDER_CAPTIONS[(case, cfg)]}
        if boxes is not None:
            entry["boxes"] = boxes
            entry["box_count"] = len(boxes)
            entry["analytic_volume"] = round(sum((b["max"][0] - b["min"][0]) * (b["max"][1] - b["min"][1]) * (b["max"][2] - b["min"][2]) for b in boxes), 9)
        if cfg == default_cfg:
            files.insert(0, entry)
        else:
            files.append(entry)
        checks.append((cfg, stats, ok))
    rel = write_json(f"cases/{case}/geometry.json", {
        "case": case, "title": meta["title"],
        "units": "metres" + (" (full scale)" if case == "E" else " (model scale)"),
        "frame": meta["frame"],
        "default_configuration": default_cfg,
        "configurations": [e["configuration"] for e in files],
        "is_boxes": files[0].get("boxes") is not None,
        "files": files,
        "render": render_url(case),
    })
    return files, rel, checks


# ----------------------------------------------------------------------------- validation

RESULTS_DIR = os.path.join(REPO, "validation", "results")


def check_runs_registry():
    """Every snapshot is registered and every registered snapshot exists: nothing is served by accident."""
    on_disk = {n for n in os.listdir(RESULTS_DIR) if n.endswith(".json")} if os.path.isdir(RESULTS_DIR) else set()
    listed = {r[3] for r in RUNS}
    if on_disk != listed:
        raise SystemExit(f"validation/results/ and RUNS disagree: unregistered {sorted(on_disk - listed)}, "
                         f"missing {sorted(listed - on_disk)}")


def is_metric(v):
    return isinstance(v, dict) and "Fb" in v and "R" in v


def validation_entries(case):
    out = []
    for run_case, engine, config, name, headline, figures, reproduce in RUNS:
        if run_case != case:
            continue
        with io.open(os.path.join(RESULTS_DIR, name), encoding="utf-8") as f:
            res = json.load(f)
        for label, key in headline.items():
            if not is_metric(res.get(key)):
                raise SystemExit(f"{name}: headline '{label}' -> '{key}' is not a score in the file")
        out.append({
            "engine": engine,
            "configuration": config,
            "solver": res.get("engine") or res.get("turbulenceModel"), "numerics_level": res.get("numericsLevel"),
            "scale": res.get("scale"), "solved_time": res.get("solvedTime"), "iterations": res.get("iterations"),
            "points_measured": res.get("points.measured"),
            "lateral_sign_applied_in_fixture": res.get("lateralSign"),
            "recirculation_Lr_over_H": res.get("recirculation.LrOverH"),
            "quantity": res.get("quantity"),
            "normalisation": ("velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, "
                              "as it is published); hit rate D = 0.25, W = 0.05 in those units"),
            "metric_meaning": METRIC_MEANING,
            "headline": {label: key for label, key in headline.items()},
            "scores": {k: v for k, v in res.items() if is_metric(v)},
            "figures": [f"{SITE}/assets/figures/{fig}" for fig in figures],
            "reproduce": reproduce,
            "source_file": f"validation/results/{name}",
            "source_url": f"{REPO_URL}/blob/main/validation/results/{name}",
            # The benchmark's citation from one place, not the fixture's free-text reference line.
            "cite": D.CITATION["benchmark"],
        })
    return out


METRIC_MEANING = {
    "Count": "number of measured points scored",
    "MeanObserved": "mean of the measured, normalised quantity", "MeanPredicted": "mean of the modelled, normalised quantity",
    "Fb": "fractional bias, 2 (mean_obs - mean_pred) / (mean_obs + mean_pred); positive = model low",
    "Nmse": "normalised mean square error", "Nad": "normalised absolute difference",
    "Fac2": "fraction of points within a factor of two (harsh near zero for sign-changing V and W)",
    "HitRate": "fraction of points within D = 0.25 relative or W = 0.05 U_H absolute",
    "Mg": "geometric mean bias", "Vg": "geometric variance", "GeometricPairs": "pairs with both values positive (used for Mg/Vg)",
    "R": "Pearson correlation coefficient",
}


def build_validation(case):
    entries = validation_entries(case)
    status = ENGINE_STATUS[case]
    rel = write_json(f"cases/{case}/validation.json", {
        "case": case, "title": D.CASES[case]["title"],
        "status": "scored" if entries else "pending",
        "status_meaning": STATUS_MEANING,
        "engines": [{"engine": e["id"], "status": status[e["id"]]} for e in ENGINES],
        "results": entries,
        "note": (None if entries else "No validation has been run for this case yet; results is an empty list. "
                 "Nothing on this page is a claim about this case."),
    })
    return entries, rel


# ----------------------------------------------------------------------------- cases

def build_case(case, points, geometry, validation):
    rows, src, summ, rel_points, rel_csv = points
    gfiles, rel_geom, _ = geometry
    ventries, rel_val = validation
    meta = D.CASES[case]
    af, af_src = D.load_approach_flow(case)
    configs = []
    if case == "C":
        for cb in ("0D", "1D", "2D"):
            for wd in (0.0, 22.5, 45.0):
                configs.append({"config": cb, "wind_direction_deg": wd, "points": sum(1 for r in rows if r["config"] == cb and r["wind_direction_deg"] == wd)})
    elif case == "D":
        for inst in ("thermistor", "split_fibre"):
            for wd in sorted({r["wind_direction_deg"] for r in rows if r["instrument"] == inst}):
                sel = [r for r in rows if r["instrument"] == inst and r["wind_direction_deg"] == wd]
                configs.append({"instrument": inst, "wind_direction_deg": wd, "points": len(sel),
                                "measured": sum(1 for r in sel if (r["Vs"] if inst == "thermistor" else r["U"]) is not None)})
    elif case == "E":
        for st in ("bc", "ac"):
            configs.append({"config": st, "wind_directions": D.COMPASS, "points_per_direction": sum(1 for r in rows if r["config"] == st and r["wind_direction"] == "N")})
    else:
        configs.append({"config": "default", "wind_direction_deg": 0.0, "points": len(rows)})
    rel = write_json(f"cases/{case}.json", {
        "id": case, "slug": meta["slug"], "title": meta["title"], "summary": meta["short"],
        "configuration": meta["configuration"],
        "configurations": configs,
        "quantities": meta["quantities"],
        "units": meta["units"], "frame": meta["frame"],
        "inflow_fit": meta["inflow_fit"],
        "approach_flow": {"source": af_src, "units": {"z": "m", "U": "m/s", "k": "m^2/s^2", "u_rms": "m/s"}, "rows": af},
        "points": {"endpoint_json": url(rel_points), "endpoint_csv": url(rel_csv), "source": src, **summ},
        "geometry": {"endpoint": url(rel_geom), "files": [{"configuration": g["configuration"], "file": g["file"], "triangles": g["stats"]["triangles"], "watertight": g["stats"]["watertight"]} for g in gfiles]},
        "validation": {"endpoint": url(rel_val), "status": "scored" if ventries else "pending", "engines": ENGINE_STATUS[case]},
        "gotchas": meta["gotchas"],
        "people": meta["people"], "doi": meta["doi"], "doi_note": meta.get("doi_note"),
        "citation_requested": meta["citation_requested"],
        "files_in_repository": {"folder": f"{REPO_URL}/tree/main/{meta['folder'].replace(' ', '%20')}", "reference": meta["reference_file"], "approach_flow": meta["approach_flow_file"], "readme": meta["readme"]},
        "render": render_url(case),
        "page": f"{SITE}/cases/{meta['slug']}/",
    })
    return rel, summ, configs


def build_geometry_all(files_by_case):
    """One index of every STL, and one archive of them. The STLs are NOT merged into one scene: each case
    has its own origin, and A-D are model scale while E is full scale (about 1000 times larger), so a merged
    file would stack them at the origin, and C's three centre-block variants and E's before/after states
    are alternatives that cannot share one CFD domain."""
    import hashlib
    import zipfile
    items = []
    for case in D.CASE_IDS:
        meta = D.CASES[case]
        for g in files_by_case[case]:
            with io.open(os.path.join(API, g["path"]), "rb") as f:
                body = f.read()
            items.append({
                "case": case, "configuration": g["configuration"], "url": g["file"], "path": g["path"],
                "archive_name": f"AIJ_case{case}_{g['configuration']}.stl",
                "units": "metres" + (" (full scale)" if case == "E" else " (model scale)"),
                "frame": {k: meta["frame"][k] for k in ("origin", "x", "y", "z")},
                "bbox_min": g["stats"]["bbox_min"], "bbox_max": g["stats"]["bbox_max"],
                "triangles": g["stats"]["triangles"], "watertight": g["stats"]["watertight"],
                "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
            })
    write_json("geometry.json", {
        "description": ("Every cleaned STL, one entry per case and configuration. Each file is in its own case's frame "
                        "and units — points.json of the same case lives in that frame — so they are deliberately not one "
                        "scene: overlaid, the cases would stack at the origin, and Case E is full scale while A-D are "
                        "model scale. geometry.zip holds the same files under archive_name."),
        "archive": url("geometry.zip"),
        "files": items,
    })
    # Deterministic archive: fixed timestamps and order, so an unchanged geometry gives an unchanged zip.
    with zipfile.ZipFile(os.path.join(API, "geometry.zip"), "w", compression=zipfile.ZIP_DEFLATED) as z:
        for it in items:
            info = zipfile.ZipInfo(it["archive_name"], date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with io.open(os.path.join(API, it["path"]), "rb") as f:
                z.writestr(info, f.read())
    return ["geometry.json", "geometry.zip"]


def build_cases_index(percase):
    items = []
    for case in D.CASE_IDS:
        meta = D.CASES[case]
        summ, configs = percase[case]
        items.append({
            "id": case, "slug": meta["slug"], "title": meta["title"], "summary": meta["short"],
            "configuration": meta["configuration"],
            "quantities": meta["quantities"], "units": meta["units"],
            "frame": {k: meta["frame"][k] for k in ("origin", "x", "y", "z")},
            "counts": {"rows": summ["rows"], "distinct_points": summ["distinct_points"], "configurations": len(configs)},
            "engines": ENGINE_STATUS[case],
            "doi": meta["doi"],
            "links": {"case": url(f"cases/{case}.json"), "points": url(f"cases/{case}/points.json"), "points_csv": url(f"cases/{case}/points.csv"),
                      "geometry": url(f"cases/{case}/geometry.json"), "geometry_stl": url(f"cases/{case}/geometry.stl"),
                      "validation": url(f"cases/{case}/validation.json"), "page": f"{SITE}/cases/{meta['slug']}/", "render": render_url(case)},
        })
    return write_json("cases.json", {"cases": items})


# ----------------------------------------------------------------------------- index / openapi / llms

ENDPOINTS = [
    ("index.json", "every endpoint, versions, licence, how to cite"),
    ("cases.json", "the five cases: id, title, configuration facts, units, frame, counts, engine status, links"),
    ("cases/{id}.json", "one case in full: configurations, inflow fit and approach-flow profile, point-table summary, geometry files, validation status, gotchas"),
    ("cases/{id}/points.json", "the cleaned measurement table, SI units, one frame, null for unmeasured"),
    ("cases/{id}/points.csv", "the same table as CSV"),
    ("cases/{id}/geometry.json", "geometry description: frame, configurations, box lists where the geometry is boxes, STL statistics"),
    ("cases/{id}/geometry.stl", "cleaned ASCII STL of the default configuration, metres, outward normals"),
    ("cases/{id}/geometry_{configuration}.stl", "the other configurations' STLs (C: 0D, 1D; E: bc)"),
    ("cases/{id}/validation.json", "Eddy3D validation scores per engine (empty list where none has been run) with figure URLs"),
    ("geometry.json", "every STL of every case in one list: case, configuration, units, frame, bounding box, triangles, sha256, URL"),
    ("geometry.zip", "every STL in one archive (each file stays in its own case's frame and units: they are not one scene)"),
    ("openapi.json", "OpenAPI 3.1 description of these GETs"),
    ("llms.txt", "plain-text entry point for agents"),
]


def build_index(extra_stl):
    return write_json("index.json", {
        "name": "AIJ UWE benchmark — cleaned data API",
        "description": ("Static JSON/CSV/STL endpoints for the Architectural Institute of Japan Urban Wind Environment "
                        "benchmark (Cases A-E) and Eddy3D's validation against it. Every file is a plain HTTP GET; nothing is computed on request."),
        "base_url": API_BASE,
        "fallback_base_url": RAW_BASE,
        "fallback_note": "the same files, served raw from the repository's main branch (use when the Pages site is not reachable)",
        "repository": REPO_URL, "site": SITE,
        "versions": {"schema": SCHEMA_VERSION, "data_commit": HEAD, "clean_manifest": (D.clean_manifest() or {}).get("version")},
        "endpoints": [{"path": p, "url": url(p), "method": "GET", "description": d} for p, d in ENDPOINTS],
        "case_ids": D.CASE_IDS,
        "files": sorted(set([f"cases/{c}.json" for c in D.CASE_IDS]
                            + [f"cases/{c}/{n}" for c in D.CASE_IDS for n in ("points.json", "points.csv", "geometry.json", "geometry.stl", "validation.json")]
                            + extra_stl + ["index.json", "cases.json", "openapi.json", "llms.txt", "geometry.json", "geometry.zip"])),
        "licence_detail": D.LICENCE,
        "cite": D.CITATION,
        "agents": {
            "start_here": url("llms.txt"),
            "walk": ["GET index.json", "GET cases.json and pick an id", "GET cases/{id}.json for frame, units and gotchas",
                     "GET cases/{id}/points.json (SI units, one frame) and cases/{id}/geometry.stl (metres)",
                     "GET cases/{id}/validation.json before quoting any Eddy3D score; an empty results list means no validation exists"],
        },
    })


def build_openapi():
    ids = D.CASE_IDS
    def op(summary, media, schema=None, params=None):
        o = {"summary": summary, "responses": {"200": {"description": "OK", "content": {media: ({"schema": schema} if schema else {})}}}}
        if params:
            o["parameters"] = params
        return o
    case_param = [{"name": "id", "in": "path", "required": True, "schema": {"type": "string", "enum": ids}}]
    cfg_param = case_param + [{"name": "configuration", "in": "path", "required": True, "schema": {"type": "string", "enum": ["0D", "1D", "bc"]},
                               "description": "C: 0D or 1D (2D is geometry.stl); E: bc (ac is geometry.stl)"}]
    stamped = {"type": "object", "required": ["schema_version", "generated_from", "licence"],
               "properties": {"schema_version": {"type": "string"}, "generated_from": {"type": ["string", "null"], "description": "git commit of the data"},
                              "generated_at": {"type": "string", "format": "date-time"}, "licence": {"type": "string"}}}
    point = {"type": "object", "properties": {
        "point_id": {"type": "integer"}, "config": {"type": "string"}, "instrument": {"type": "string"}, "wind_direction": {"type": "string"},
        "wind_direction_deg": {"type": "number"}, "x": {"type": "number"}, "y": {"type": "number"}, "z": {"type": "number"},
        **{q: {"type": ["number", "null"]} for q in ("U", "V", "W", "uu", "vv", "ww", "k", "Vs", "velocity_ratio")}}}
    doc = {
        "openapi": "3.1.0",
        "info": {"title": "AIJ UWE benchmark — cleaned data API", "version": SCHEMA_VERSION,
                 "description": "Static GET endpoints generated by scripts/build_api.py. Lengths in metres, velocities in m/s, variances and k in m^2/s^2.",
                 "license": {"name": "CC BY 4.0", "url": D.LICENCE["data_url"]}},
        "servers": [{"url": API_BASE}, {"url": RAW_BASE, "description": "raw files from the repository (fallback)"}],
        "paths": {
            "/index.json": {"get": op("Endpoint directory, versions, licence, citation", "application/json", {"allOf": [stamped, {"type": "object"}]})},
            "/cases.json": {"get": op("The five cases", "application/json", {"allOf": [stamped, {"type": "object", "properties": {"cases": {"type": "array"}}}]})},
            "/cases/{id}.json": {"get": op("One case in full", "application/json", {"allOf": [stamped, {"type": "object"}]}, case_param)},
            "/cases/{id}/points.json": {"get": op("Cleaned measurement table", "application/json",
                                                   {"allOf": [stamped, {"type": "object", "properties": {"columns": {"type": "array", "items": {"type": "string"}}, "n": {"type": "integer"}, "points": {"type": "array", "items": point}}}]}, case_param)},
            "/cases/{id}/points.csv": {"get": op("Cleaned measurement table as CSV", "text/csv", {"type": "string"}, case_param)},
            "/cases/{id}/geometry.json": {"get": op("Geometry description and box lists", "application/json", {"allOf": [stamped, {"type": "object"}]}, case_param)},
            "/cases/{id}/geometry.stl": {"get": op("Cleaned ASCII STL, default configuration, metres", "model/stl", {"type": "string"}, case_param)},
            "/cases/{id}/geometry_{configuration}.stl": {"get": op("Cleaned ASCII STL of another configuration", "model/stl", {"type": "string"}, cfg_param)},
            "/cases/{id}/validation.json": {"get": op("Eddy3D validation scores per engine", "application/json", {"allOf": [stamped, {"type": "object", "properties": {"results": {"type": "array"}}}]}, case_param)},
            "/geometry.json": {"get": op("Every STL of every case, with frame, units, bounding box and sha256", "application/json", {"allOf": [stamped, {"type": "object", "properties": {"files": {"type": "array"}}}]})},
            "/geometry.zip": {"get": op("Every STL in one archive (each in its own case's frame and units)", "application/zip", {"type": "string", "format": "binary"})},
            "/openapi.json": {"get": op("This document", "application/json")},
            "/llms.txt": {"get": op("Plain-text entry point for agents", "text/plain", {"type": "string"})},
        },
        "components": {"schemas": {"Stamped": stamped, "Point": point}},
    }
    path = os.path.join(API, "openapi.json")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
        f.write("\n")
    return "openapi.json"


def build_llms(percase):
    lines = [
        "# AIJ UWE benchmark — cleaned data API",
        "",
        "> Wind-tunnel reference data from the Architectural Institute of Japan Urban Wind Environment (UWE)",
        "> benchmark, Cases A-E, cleaned into one schema, plus Eddy3D's validation against it. Static files, plain GET.",
        "",
        f"Base URL: {API_BASE}",
        f"Fallback (raw files from the repository): {RAW_BASE}",
        f"Repository: {REPO_URL}",
        f"Schema version: {SCHEMA_VERSION}. Data commit: {HEAD}. Generated: {NOW}.",
        "Licence: CC BY 4.0 — the data belongs to its collectors; cite the benchmark and the per-case papers.",
        "",
        "## How to use this",
        "",
        "1. GET index.json — endpoint list, versions, licence, citation.",
        "2. GET cases.json — the five cases with their frame, units, counts and links. Pick an id (A, B, C, D, E).",
        "3. GET cases/{id}.json — read `frame`, `units` and `gotchas` BEFORE the numbers; they differ per case.",
        "4. GET cases/{id}/points.json (or points.csv) — every value is SI (m, m/s, m^2/s^2) in ONE frame per case;",
        "   unmeasured values are null. Case E's quantity is a dimensionless velocity ratio.",
        "5. GET cases/{id}/geometry.stl — ASCII STL in metres, outward normals, origin at the building / array centre,",
        "   +x along the wind at WD = 0 (Cases A-D). Case E keeps its geographic frame (+x east, +y north, full-scale metres).",
        "   geometry.json lists the boxes where the geometry IS boxes (A, B, C, D), so you need not parse the STL at all.",
        "6. GET cases/{id}/validation.json — Eddy3D scores per engine and configuration, with a `headline` map naming",
        "   the scores to quote. An engine whose status is not \"scored\" has NO result for that case: do not infer one.",
        "   \"scored\" means a run exists, not that it agrees — read the numbers. Status today: "
        + "; ".join(f"{c}: " + ", ".join(f"{e} {s}" for e, s in ENGINE_STATUS[c].items()) for c in D.CASE_IDS) + ".",
        "7. All geometry at once: GET geometry.json (every STL with its case, configuration, units, frame and sha256)",
        "   or geometry.zip. Each STL stays in its own case's frame and units; they are NOT one scene.",
        "",
        "## Endpoints",
        "",
    ]
    for p, d in ENDPOINTS:
        lines.append(f"- {API_BASE}/{p} — {d}")
    lines += ["", "## Cases", ""]
    for case in D.CASE_IDS:
        meta = D.CASES[case]
        summ, configs = percase[case]
        lines.append(f"- {case}: {meta['title']}. {meta['short']} {summ['rows']} rows, {summ['distinct_points']} points, "
                     f"columns {', '.join(summ['columns'])}. Engines: " + ", ".join(f"{k} {v}" for k, v in ENGINE_STATUS[case].items()) + ".")
    lines += ["", "## Gotchas that silently corrupt a comparison", ""]
    for case in D.CASE_IDS:
        for g in D.CASES[case]["gotchas"]:
            lines.append(f"- [{case}] {g}")
    lines += [
        "",
        "## Validation method",
        "",
        "Each case is solved through Eddy3D's production case writer (build-case -> run -> probe), not a hand-built",
        "OpenFOAM case; the probe sits at exactly the tunnel's measurement coordinates. Scores are normalised by U_H",
        "(k by U_H^2; Case E by U at 15.9 m); hit rate uses D = 0.25, W = 0.05 in those units. FAC2 is harsh by",
        "construction on sign-changing V and W; read R and hit rate there. The lateral sign of Case B is corrected",
        "before scoring. Cases C-E measure an omnidirectional SCALAR speed (thermistor): the model is scored as",
        "sqrt(|U|^2 + 2k) and as |U|, the two ends of the bracket the measurement must fall in.",
        "The ML surrogate predicts |U|/U_ref at 1.8 m; each case is scaled so its measurement plane lands there.",
        "On the full prediction window it does not respond to the wind direction at all (reversing the wind changes",
        "the field by < 1e-4 U_ref) — its scores grade the geometry it was given, not a wind it was told.",
        "",
        "## Cite",
        "",
        f"- {D.CITATION['benchmark']}",
        f"- {D.CITATION['guidelines']}",
        "- Each case's own requested citation and Zenodo DOI are in cases/{id}.json.",
        "",
    ]
    path = os.path.join(API, "llms.txt")
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    return "llms.txt"


# ----------------------------------------------------------------------------- assets

def copy_assets():
    """docs/assets/geometry/ = every render, docs/assets/figures/ = every figure a run names; nothing else."""
    wanted = {
        "geometry": {D.render_file(c, cfg) for c in D.CASE_IDS for (cc, cfg) in D.RENDER_CAPTIONS if cc == c},
        "figures": {fig for run in RUNS for fig in run[5]},
    }
    for sub_dir, names in wanted.items():
        src = os.path.join(FIGURES, "geometry") if sub_dir == "geometry" else FIGURES
        dst = os.path.join(ASSETS, sub_dir)
        os.makedirs(dst, exist_ok=True)
        for stale in set(os.listdir(dst)) - names:
            os.remove(os.path.join(dst, stale))
        for name in sorted(names):
            shutil.copyfile(os.path.join(src, name), os.path.join(dst, name))


# ----------------------------------------------------------------------------- site pages

# Row labels for the case pages' tables: the API keeps its snake_case keys, the pages read as prose.
LABELS = {
    "D_m": "Block size D (m)", "H_m": "Height H (m)", "Re": "Reynolds number", "Re_D": "Reynolds number Re_D",
    "Re_H": "Reynolds number Re_H", "U_H_m_s": "U_H (m/s)", "U_H_note": "U_H, note", "array": "Array",
    "array_extent_m": "Array extent (m)", "b_m": "Width b (m)", "blocks": "Blocks", "building": "Building",
    "centre_building": "Centre building", "configurations": "Configurations", "configurations_note": "Configurations, note",
    "depth_m": "Depth (m)", "district": "District", "instrument": "Instrument", "measurement_height_m": "Measurement height (m)",
    "measurement_height_note": "Measurement height, note", "measurement_planes": "Measurement planes",
    "new_buildings": "New buildings", "normalisation": "Normalisation", "pitch_note": "Pitch, note", "points": "Points",
    "roads": "Roads", "scale": "Scale", "scale_note": "Scale, note", "states": "States", "tower": "Tower",
    "tunnel": "Wind tunnel", "values": "Values", "width_m": "Width (m)", "wind_directions": "Wind directions",
    "wind_directions_deg": "Wind directions (°)",
    "coordinate_scale_applied": "Coordinate scale applied", "lateral_sign_applied": "Lateral sign applied",
    "origin": "Origin", "wind_direction_rotation": "Wind direction convention",
    "U_H_measured_m_s": "U_H, measured (m/s)", "U_ref_15_9m_m_s": "U_ref at 15.9 m (m/s)", "log_law": "Log law",
    "log_law_error_at_H": "Log-law error at H", "method": "Method", "note": "Note", "power_law_exponent": "Power-law exponent",
    "power_law_exponent_fitted": "Power-law exponent, fitted", "power_law_exponent_paper": "Power-law exponent, data paper",
    "turbulence_intensity_at_D": "Turbulence intensity at D", "u_star_m_s": "Friction velocity u* (m/s)",
    "z0_mm": "Roughness length z₀ (mm)", "length": "Length", "variance": "Variance", "velocity": "Velocity",
    "velocity_ratio": "Velocity ratio",
}


def _label(k):
    return LABELS.get(k, k.replace("_", " "))


def _config_part(k, v):
    """'2D', 'WD 22.5°', 'split fibre', 'before construction': one part of a configuration's name."""
    if k == "wind_direction_deg":
        return f"WD {v:g}°"
    if k == "config":
        return {"bc": "before construction", "ac": "after construction", "default": "default"}.get(v, v)
    return str(v).replace("_", " ")


def _md_value(v):
    if isinstance(v, dict):
        return "<br>".join(f"**{_label(k)}**: {_md_value(x)}" for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def _asset(rel):
    return f"{{{{ '{rel}' | relative_url }}}}"


def figure(src, alt, caption):
    """One image with its caption, as HTML (<figure>), so the caption stays attached to the image."""
    return ['<figure class="figure">', f'<img src="{_asset(src)}" alt="{alt}">', f"<figcaption>{caption}</figcaption>", "</figure>", ""]


def figure_table(cells, columns, caption=None):
    """Images side by side in a Markdown table marked {: .figures } (see docs/_sass/custom/custom.scss):
    cells are (src, alt, caption, link or None); the header row is blank and hidden by the stylesheet."""
    L = ["|" + " |" * columns, "|" + "---|" * columns]
    for i in range(0, len(cells), columns):
        row = []
        for src, alt, cap, link in cells[i:i + columns]:
            img = f"![{alt}]({_asset(src)})"
            if link:
                img = f"[{img}]({_asset(link)})"
            row.append(f"{img}<br><span class=\"caption\">{cap.replace('|', '&#124;')}</span>")
        row += [" "] * (columns - len(row))
        L.append("| " + " | ".join(row) + " |")
    L += ["{: .figures }", ""]
    if caption:
        L += [f'<p class="caption">{caption}</p>', ""]
    return L


GALLERY_CAPTIONS = {
    "A": "Isolated building · {points} points · U, V, W and k",
    "B": "Isolated slab · {points} points · U, V, W and k",
    "C": "Centre block at 0D, 1D or 2D (2D shown) · {rows} scalar speeds at pedestrian height, 3 wind directions",
    "D": "A tower among 82 low blocks · {rows} measurements: scalar speed at 3 wind directions, velocity at 33 points",
    "E": "Before and after a 60 m high-rise (after shown) · {rows} velocity ratios over 16 wind directions",
}


def build_gallery(percase):
    """docs/_includes/case-gallery.md: the five cases, two to a row, each render linked to its page."""
    cells = []
    for case in D.CASE_IDS:
        meta = D.CASES[case]
        summ, _ = percase[case]
        cap = GALLERY_CAPTIONS[case].format(points=f"{summ['distinct_points']:,}", rows=f"{summ['rows']:,}")
        cells.append((f"/assets/geometry/{D.render_file(case)}", meta["title"], f"<strong>{meta['title']}</strong><br>{cap}",
                      f"/cases/{meta['slug']}/"))
    os.makedirs(os.path.join(DOCS, "_includes"), exist_ok=True)
    with io.open(os.path.join(DOCS, "_includes", "case-gallery.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(["<!-- Generated by scripts/build_api.py; edit GALLERY_CAPTIONS there. -->", ""] + figure_table(cells, 2)))


def build_pages(percase, validations):
    """docs/cases/<slug>.md, one per case, from the same facts the API serves."""
    out_dir = os.path.join(DOCS, "cases")
    os.makedirs(out_dir, exist_ok=True)
    build_gallery(percase)
    for n, case in enumerate(D.CASE_IDS, start=1):
        meta = D.CASES[case]
        summ, configs = percase[case]
        ventries = validations[case]
        L = ["---", f"title: \"{meta['title']}\"", "parent: Cases", f"nav_order: {n}", "---", "",
             f"# {meta['title']}", "", meta["short"], ""]
        fig_no = 1
        cfgs = [cfg for (c, cfg) in D.RENDER_CAPTIONS if c == case]
        if len(cfgs) == 1:
            L += figure(f"/assets/geometry/{D.render_file(case)}", meta["title"],
                        f"<strong>Figure {fig_no}.</strong> {D.RENDER_CAPTIONS[(case, cfgs[0])]}")
        else:
            label = {"C": "The three configurations of the centre block, on one scale; 120 measurement points each, "
                          "at three wind directions.",
                     "E": "The two states, on one scale (full-scale metres, +x east, +y north); the arrow marks SW, the "
                          "direction Eddy3D is scored at."}[case]
            L += figure_table([(f"/assets/geometry/{D.render_file(case, cfg)}", f"{meta['title']}, {cfg}",
                                D.RENDER_CAPTIONS[(case, cfg)], None) for cfg in cfgs],
                              3 if case == "C" else 1,  # C's three states side by side; E's are wide, so they stack
                              f"<strong>Figure {fig_no}.</strong> {label}")
        fig_no += 1
        L += ["## Configuration", "", "| Parameter | Value |", "|---|---|"]
        for k, v in meta["configuration"].items():
            L.append(f"| {_label(k)} | {_md_value(v)} |")
        L += ["", "## Frame and units", "", "| Property | Definition |", "|---|---|"]
        for k, v in meta["frame"].items():
            L.append(f"| {_label(k)} | {_md_value(v)} |")
        for k, v in meta["units"].items():
            L.append(f"| Unit of {'k' if k == 'k' else _label(k).lower()} | {v} |")
        L += ["", "## Reference data", "",
              f"Source in this repository: `{meta['reference_file']}`" + (f" (approach flow: `{meta['approach_flow_file']}`)" if meta["approach_flow_file"] else "") + ".",
              "", f"The cleaned table has **{summ['rows']} rows** over **{summ['distinct_points']} distinct points**; columns `{'`, `'.join(summ['columns'])}`.", ""]
        if summ["nulls"]:
            L.append("Unmeasured cells (null): " + ", ".join(f"{k} {v}" for k, v in summ["nulls"].items()) + ".")
            L.append("")
        L += ["| Configuration | Points |", "|---|---|"]
        for c in configs:
            key = ", ".join(_config_part(k, v) for k, v in c.items() if k not in ("points", "measured", "points_per_direction", "wind_directions"))
            val = c.get("points", c.get("points_per_direction"))
            if "measured" in c:
                val = f"{val} ({c['measured']} measured)"
            if "wind_directions" in c:
                key += ", 16 wind directions"
                val = f"{val} per direction"
            L.append(f"| {key} | {val} |")
        L += ["", "### Inflow", "", "| Property | Value |", "|---|---|"]
        for k, v in meta["inflow_fit"].items():
            if k == "windows":
                for w in v:
                    L.append("| Fit window | " + "; ".join(f"{_label(a)} {b}" for a, b in w.items()) + " |")
            else:
                L.append(f"| {_label(k)} | {_md_value(v)} |")
        L += ["", "## Known data issues", ""]
        for g in meta["gotchas"]:
            L.append(f"- {g}")
        L += ["", "## Validation", ""]
        if ventries:
            names = {e["id"]: e["name"] for e in ENGINES}
            figures = []
            for e in ventries:
                title = names[e["engine"]] + (f" — configuration {e['configuration']}" if e["configuration"] else "")
                L += [f"### {title}", ""]
                if e["quantity"]:
                    L += [f"Quantity: {e['quantity']}.", ""]
                if e["recirculation_Lr_over_H"] is not None:
                    L += [f"Reattachment length L_r/H = {e['recirculation_Lr_over_H']:.2f}.", ""]
                scores = {label: e["scores"][key] for label, key in e["headline"].items()}
                # A bare '|' in a label (|U|) would split the Markdown table's column: escape it.
                L += ["| Metric | " + " | ".join(lab.replace("|", "\\|") for lab in scores) + " |", "|---|" + "---|" * len(scores)]
                for m, label in (("R", "R"), ("Fac2", "FAC2"), ("Fb", "FB"), ("HitRate", "hit rate"), ("Count", "n")):
                    L.append(f"| **{label}** | " + " | ".join(
                        str(s[m]) if m == "Count" else f"{s[m]:+.3f}" if m in ("R", "Fb") else f"{s[m]:.3f}"
                        for s in scores.values()) + " |")
                L += ["", f"{e['normalisation']}. Reproduce: {e['reproduce']}.", ""]
                figures += [f for f in e["figures"] if f not in figures]
            for fig in figures:
                name = fig.rsplit("/", 1)[-1]
                L += figure(f"/assets/figures/{name}", name, f"<strong>Figure {fig_no}.</strong> {FIGURE_CAPTIONS[name]}")
                fig_no += 1
            L += ["How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page."]
        else:
            L.append("**No validation has been run for this case yet.** Nothing on this page is a claim about it. Engine status: "
                     + ", ".join(f"{k} {v}" for k, v in ENGINE_STATUS[case].items()) + ".")
        L += ["", "## API", "", "| Resource | Endpoint |", "|---|---|"]
        for name, rel in (("case", f"cases/{case}.json"), ("points (JSON)", f"cases/{case}/points.json"), ("points (CSV)", f"cases/{case}/points.csv"),
                          ("geometry", f"cases/{case}/geometry.json"), ("geometry STL", f"cases/{case}/geometry.stl"), ("validation", f"cases/{case}/validation.json")):
            L.append(f"| {name} | [`/api/{rel}`]({{{{ '/api/{rel}' | relative_url }}}}) |")
        L += ["", "## Attribution", "", f"- Data collectors: {', '.join(meta['people']['data_collectors'])}",
              f"- Editors and distributors: {', '.join(meta['people']['editors_distributors'])}"]
        if meta["doi"]:
            L.append(f"- DOI: [{meta['doi']}](https://doi.org/{meta['doi']})")
        elif meta.get("doi_note"):
            L.append(f"- DOI: {meta['doi_note']}")
        L += [f"- Citation requested: {meta['citation_requested']}", "- Licence: CC BY 4.0", ""]
        with io.open(os.path.join(out_dir, f"{meta['slug']}.md"), "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(L))


# ----------------------------------------------------------------------------- verify

def verify():
    problems = []
    with io.open(os.path.join(API, "index.json"), encoding="utf-8") as f:
        index = json.load(f)
    for rel in index["files"]:
        if not os.path.isfile(os.path.join(API, rel)):
            problems.append(f"index.json lists {rel} but it is not on disk")
    for e in index["endpoints"]:
        if "{" not in e["path"] and not os.path.isfile(os.path.join(API, e["path"])):
            problems.append(f"endpoint {e['path']} missing")
    with io.open(os.path.join(API, "openapi.json"), encoding="utf-8") as f:
        oa = json.load(f)
    if not oa.get("openapi", "").startswith("3.1"):
        problems.append("openapi.json is not 3.1")
    for p in oa["paths"]:
        if "{" in p:
            continue
        if not os.path.isfile(os.path.join(API, p.lstrip("/"))):
            problems.append(f"openapi path {p} missing on disk")
    for p, item in oa["paths"].items():
        if "get" not in item or "200" not in item["get"]["responses"]:
            problems.append(f"openapi path {p} lacks a GET 200")
    for root, _, files in os.walk(API):
        for name in files:
            if name.endswith(".json"):
                with io.open(os.path.join(root, name), encoding="utf-8") as f:
                    body = json.load(f)
                if name != "openapi.json":
                    for key in ("schema_version", "generated_from", "licence"):
                        if key not in body:
                            problems.append(f"{name} lacks {key}")
    for case in D.CASE_IDS:
        with io.open(os.path.join(API, f"cases/{case}/points.json"), encoding="utf-8") as f:
            pj = json.load(f)
        with io.open(os.path.join(API, f"cases/{case}/points.csv"), encoding="utf-8", newline="") as f:
            n_csv = sum(1 for _ in csv.reader(f)) - 1
        if pj["n"] != len(pj["points"]) or pj["n"] != n_csv:
            problems.append(f"case {case}: points.json n={pj['n']} rows={len(pj['points'])} csv={n_csv}")
        tris = D.read_ascii_stl(os.path.join(API, f"cases/{case}/geometry.stl"))
        s = D.stl_stats(tris)
        with io.open(os.path.join(API, f"cases/{case}/geometry.json"), encoding="utf-8") as f:
            gj = json.load(f)
        if gj["files"][0]["stats"]["triangles"] != s["triangles"]:
            problems.append(f"case {case}: geometry.json triangle count disagrees with the STL on disk")
    import hashlib
    import zipfile
    with io.open(os.path.join(API, "geometry.json"), encoding="utf-8") as f:
        gall = json.load(f)
    with zipfile.ZipFile(os.path.join(API, "geometry.zip")) as z:
        names = set(z.namelist())
        for it in gall["files"]:
            with io.open(os.path.join(API, it["path"]), "rb") as f:
                on_disk = hashlib.sha256(f.read()).hexdigest()
            if on_disk != it["sha256"]:
                problems.append(f"geometry.json sha256 of {it['path']} disagrees with the file on disk")
            if it["archive_name"] not in names or hashlib.sha256(z.read(it["archive_name"])).hexdigest() != it["sha256"]:
                problems.append(f"geometry.zip lacks {it['archive_name']} or holds different bytes")
        if len(names) != len(gall["files"]):
            problems.append(f"geometry.zip holds {len(names)} files, geometry.json lists {len(gall['files'])}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the files on disk; build nothing")
    args = ap.parse_args()
    if not args.check:
        os.makedirs(API, exist_ok=True)
        check_runs_registry()
        copy_assets()
        percase, validations, extra, geometry = {}, {}, [], {}
        for case in D.CASE_IDS:
            pts = build_points(case)
            geo = build_geometry(case)
            val = build_validation(case)
            _, summ, configs = build_case(case, pts, geo, val)
            percase[case] = (summ, configs)
            validations[case] = val[0]
            geometry[case] = geo[0]
            extra += [g["path"] for g in geo[0][1:]]
            print(f"case {case}: {summ['rows']} rows from {pts[1]}; geometry {[(c, s['triangles'], s['watertight']) for c, s, _ in geo[2]]}; validation {len(val[0])} result(s)")
        build_geometry_all(geometry)
        build_cases_index(percase)
        build_index(extra)
        build_openapi()
        build_llms(percase)
        build_pages(percase, validations)
    problems = verify()
    for p in problems:
        print("PROBLEM:", p)
    print("verify:", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
