"""Generate the static API under docs/api/ (and the generated site pages) from the cleaned data.

    python scripts/build_api.py            # build, then verify
    python scripts/build_api.py --check    # verify what is on disk; build nothing

Requirements: scripts/requirements.txt (xlrd, rhino3dm, jsonschema, openapi-spec-validator).

GitHub Pages serves docs/ at <site>/; every API file is a plain GET of a static file. The build is a pure
function of the repository: the same inputs give byte-identical outputs (no timestamps, no commit hashes),
so CI can rebuild and diff. Inputs:

- clean/                      the cleaned point tables (aijdata.load_points)
- the case folders            approach-flow profiles, Case D's STL, Case E's 3dm (aijdata)
- validation/results/         snapshots of the Eddy3D fixtures' results.json and per-point pairs, one entry
                              per run in RUNS below
- validation/figures/         the figures and geometry renders the site shows

Outputs: docs/api/** (the API), docs/assets/{figures,geometry}/, docs/cases/*.md, docs/_includes/
{case-gallery.md, dataset-jsonld.html} and docs/llms.txt. Every JSON document names its JSON Schema in
`$schema`; the schemas are in scripts/api_schemas.py and are enforced here before anything is reported OK.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aijdata as D  # noqa: E402
import api_schemas as S  # noqa: E402

REPO = D.REPO
DOCS = os.path.join(REPO, "docs")
API = os.path.join(DOCS, "api")
ASSETS = os.path.join(DOCS, "assets")
FIGURES = os.path.join(REPO, "validation", "figures")
RESULTS_DIR = os.path.join(REPO, "validation", "results")

REPO_URL = "https://github.com/SustainableUrbanSystemsLab/CFD-Test-Cases-Architectural-Institute-of-Japan-AIJ"
SITE = "https://sustainableurbansystems.com/CFD-Test-Cases-Architectural-Institute-of-Japan-AIJ"
API_BASE = SITE + "/api"
RAW_BASE = "https://raw.githubusercontent.com/SustainableUrbanSystemsLab/CFD-Test-Cases-Architectural-Institute-of-Japan-AIJ/main/docs/api"
SCHEMA_VERSION = "2.0.0"

CHANGELOG = [
    {"version": "2.0.0", "date": "2026-10-15", "changes": [
        "Breaking: cases/{id}.json `gotchas` is renamed `known_issues`.",
        "Breaking: `licence` is replaced by `license`, the SPDX identifier CC-BY-4.0; index.json `licence_detail` is `license_detail`.",
        "Breaking: `generated_from` and `generated_at` are removed. `data_version`, a SHA-256 over every served measurement, "
        "geometry and score file, changes when, and only when, the data does; the build is reproducible byte for byte.",
        "Breaking: links to JSON resources are named `url` (was `file`, `endpoint`, `endpoint_json`); file downloads are objects "
        "with `url`, `path`, `media_type`, `bytes` and `sha256` (points `csv`, approach-flow `csv`, run `pairs`, geometry files, "
        "the archive, and every entry of index.json `files`).",
        "Breaking: a validation result's `figures` is a list of {url, caption}.",
        "Added: validation.json, every case and engine in one table with each run's headline scores.",
        "Added: cases/{id}/pairs/{engine}.csv, the per-point measured and modelled values behind every scored run, so any score "
        "can be recomputed; linked from each result as `pairs`.",
        "Added: cases/{id}/approach_flow.csv, the measured approach-flow profile in SI units.",
        "Added: schemas/{name}.schema.json, the JSON Schema (draft 2020-12) of every document, named by its `$schema` and "
        "embedded in openapi.json.",
        "Added: `run_id` on every validation result; geometry renders and captions in geometry.json.",
        "Added: download URLs carry ?v=<SHA-256 prefix>, so a changed file has a new URL and no cache serves a stale copy.",
        "Added: /llms.txt at the site root, and schema.org Dataset metadata on the home page.",
    ]},
    {"version": "1.0.0", "date": "2026-10-14", "changes": ["First release."]},
]
COMPATIBILITY = ("Semantic versioning. Within a major version the API only adds: new fields, new endpoints, new runs. "
                 "Clients must ignore fields they do not know. A field is renamed or removed only in a new major "
                 "version, and the changelog says which.")
CACHING = ("GitHub Pages sends JSON with a 10-minute max-age and CSV and ZIP files with a 186-day max-age. Every "
           "download URL therefore carries ?v=<first 12 hex digits of the file's SHA-256>: the server ignores the "
           "query, and a changed file gets a new URL. Fetch the JSON documents for the current URLs; check "
           "downloads against `sha256`.")

ENGINES = [
    {"id": "openfoam12-realizableKE", "name": "OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor)", "kind": "RANS"},
    {"id": "openlb", "name": "OpenLB (Eddy3D LBM)", "kind": "LBM"},
    {"id": "fluidx3d", "name": "FluidX3D (Eddy3D GPU LBM)", "kind": "LBM"},
    {"id": "ml-surrogate", "name": "Eddy3D ML wind surrogate (pedestrian height)", "kind": "surrogate"},
]
# "scored" says a run exists and its scores are served, NOT that it agrees; how well it agrees is in the numbers.
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

# ----------------------------------------------------------------------------- runs
# Every validation run snapshotted in validation/results/: its case, engine and configuration, the scores
# to quote (label -> key in its results.json), its per-point pairs and what their columns are, the
# figures that show it, and how to reproduce it. A results file that is not listed here is an error.

PAIRS_AB = ("point_id; x, y, z in m (case frame); U, V, W measured (_meas) and modelled (_model), each divided by U_H; "
            "V in the unified sign (positive toward +y)")
PAIRS_ML = ("set (the scored subset); x_tunnel, y_tunnel in m (case frame); x_scene, y_scene in m (the scaled scene the "
            "surrogate was given); observed_over_UH and predicted_over_UH, the speeds divided by U_H (Case E: by U at 15.9 m)")


def run(case, engine, configuration, results, headline, figures, reproduce, pairs, pairs_columns):
    return {"case": case, "engine": engine, "configuration": configuration, "results": results, "headline": headline,
            "figures": figures, "reproduce": reproduce, "pairs": pairs, "pairs_columns": pairs_columns,
            "run_id": f"{case}.{engine}" + (f".{configuration}" if configuration else "")}


_FOAM_A_B = {"U": "velocity.U", "V": "velocity.V", "W": "velocity.W", "k": "k"}
_FOAM_C = {f"WD {wd} {q}": f"vs.{lab}.{key}" for wd, lab in (("0°", "wd-0"), ("22.5°", "wd22_5"), ("45°", "wd45"))
           for q, key in (("√(|U|²+2k)", "scalar"), ("|U|", "vector"))}
_ML_REPRO = "Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py"
RUNS = [
    *[run(c, "openfoam12-realizableKE", None, f"case{c}_openfoam12_realizableKE.json", _FOAM_A_B,
          ["cases-ab-openfoam-agreement.png", "cases-ab-openfoam-profiles.png"],
          f"Eddy3D fixture TestAijCase{c}ContainerE2E; figures validation/plot_cases_ab_openfoam.py",
          f"case{c}_openfoam12_realizableKE_pairs.csv", PAIRS_AB) for c in ("A", "B")],
    *[run("C", "openfoam12-realizableKE", cb, f"caseC_openfoam12_realizableKE_{cb}.json", _FOAM_C,
          ["case-c-openfoam-agreement.png", "case-c-openfoam-bias-map.png"],
          f"Eddy3D fixture TestAijCaseC{cb}ContainerE2E; figures validation/plot_case_c_openfoam.py",
          "caseC_openfoam12_realizableKE_pairs.csv",
          "config (0D/1D/2D), wind_direction_deg, point_id; x, y, z in m (case frame); measured_over_UH, the thermistor "
          "Vs/U_H; scalar_over_UH, the modelled sqrt(|U|^2 + 2k)/U_H; vector_over_UH, the modelled |U|/U_H (all nine "
          "configurations in one file)") for cb in ("0D", "1D", "2D")],
    *[run(c, "openlb", None, f"case{c}_openlb.json",
          {"U": "velocity.U", "U, points ≥ 2 dx": "velocity.U.aboveTwoCells", "V": "velocity.V", "W": "velocity.W",
           "k (resolved)": "k.resolved", "V, lateral sign flipped (control)": "control.V.lateralSignFlipped"},
          ["cases-ab-engine-comparison.png"],
          f"Eddy3D fixture TestAijCase{c}OpenLbContainerE2E (OpenLB eddy3dWind, CPU image, dx = 1.6 m); "
          "figure validation/plot_cases_ab_engines.py", f"case{c}_openlb_pairs.csv", PAIRS_AB) for c in ("A", "B")],
    run("E", "openfoam12-realizableKE", "SW", "caseE_openfoam12_realizableKE.json",
        {"before, √(|U|²+2k)": "vr.bc.SW.rms", "before, |U|": "vr.bc.SW.Umag", "after, √(|U|²+2k)": "vr.ac.SW.rms",
         "after, |U|": "vr.ac.SW.Umag", "no-construction ceiling control": "noConstruction.SW"},
        ["case-e-openfoam-agreement.png", "case-e-openfoam-bias-map.png"],
        "Eddy3D fixture TestAijCaseEContainerE2E (EDDY3D_AIJ_E_DIRECTIONS=SW, tabulated inlet); figures "
        "validation/plot_case_e_openfoam.py", "caseE_openfoam12_realizableKE_pairs.csv",
        "config (bc before / ac after construction), wind_direction, point_id; x, y, z in full-scale m (+x east, +y north); "
        "measured_ratio, the tunnel's velocity ratio; scalar_ratio and vector_ratio, the modelled sqrt(|U|^2 + 2k) and |U| "
        "over the model's own U at 15.9 m"),
    run("A", "ml-surrogate", None, "caseA_ml.json",
        {"|U| (z = 0.01 m plane)": "speed.vectorMagnitude", "|U|, lattice cut at ±250 m": "halfExtent250.forward",
         "wind reversed (control)": "negativeControl.reversedWind"},
        ["ml-surrogate-agreement.png"], _ML_REPRO, "caseA_ml_pairs.csv", PAIRS_ML),
    run("B", "ml-surrogate", None, "caseB_ml.json",
        {"|U| (z = H/16 plane)": "speed.vectorMagnitude", "|U|, lattice cut at ±250 m": "halfExtent250.forward",
         "wind reversed (control)": "negativeControl.reversedWind"},
        ["ml-surrogate-agreement.png"], _ML_REPRO, "caseB_ml_pairs.csv", PAIRS_ML),
    run("C", "ml-surrogate", None, "caseC_ml.json",
        {"Vs, 9 configurations": "speed.thermistor", "Vs, 2D WD 0, lattice cut at ±250 m": "halfExtent250.forward",
         "wind reversed (control)": "negativeControl.reversedWind"},
        ["ml-surrogate-agreement.png"], _ML_REPRO, "caseC_ml_pairs.csv", PAIRS_ML),
    run("D", "ml-surrogate", None, "caseD_ml.json",
        {"Vs, thermistor, 3 WD": "speed.thermistor", "|U|, split fibre, WD 0": "speed.vectorMagnitude",
         "Vs, WD 0, lattice cut at ±250 m": "halfExtent250.forward", "wind reversed (control)": "negativeControl.reversedWind"},
        ["ml-surrogate-agreement.png"], _ML_REPRO, "caseD_ml_pairs.csv", PAIRS_ML),
    run("E", "ml-surrogate", None, "caseE_ml.json",
        {"Vs/U(15.9 m), 16 WD, bc + ac": "speed.thermistor", "after construction": "speed.thermistor.after",
         "after − before": "delta.afterMinusBefore", "after, lattice cut at ±250 m": "halfExtent250.forward",
         "wind reversed (control)": "negativeControl.reversedWind"},
        ["ml-surrogate-agreement.png"], _ML_REPRO, "caseE_ml_pairs.csv", PAIRS_ML),
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

# (path, media type, schema name or None, description); the order is the order of index.json and openapi.json.
ENDPOINTS = [
    ("index.json", "application/json", "index", "every endpoint and file with its size and SHA-256, versions, compatibility policy, changelog, licence, citation"),
    ("cases.json", "application/json", "cases", "the five cases: id, title, frame, units, counts, engine status, links"),
    ("cases/{id}.json", "application/json", "case", "one case in full: configurations, frame, units, inflow fit and approach-flow profile, point-table summary, geometry files, validation status, known data issues, attribution"),
    ("cases/{id}/points.json", "application/json", "points", "the cleaned measurement table: SI units, one frame, null where not measured"),
    ("cases/{id}/points.csv", "text/csv", None, "the same table as CSV (empty cell = not measured)"),
    ("cases/{id}/approach_flow.csv", "text/csv", None, "the measured approach-flow profile: z (m), U (m/s), and k (m^2/s^2) or u_rms (m/s) where published"),
    ("cases/{id}/geometry.json", "application/json", "geometry", "the case's STL files with statistics, renders, and the boxes where the geometry is boxes"),
    ("cases/{id}/geometry.stl", "model/stl", None, "cleaned ASCII STL of the default configuration: metres, case frame, outward normals"),
    ("cases/{id}/geometry_{configuration}.stl", "model/stl", None, "the other configurations' STLs (C: 0D, 1D; E: bc, before construction)"),
    ("cases/{id}/validation.json", "application/json", "validation", "Eddy3D's scores per engine and run, with figures and the per-point pairs"),
    ("cases/{id}/pairs/{engine}.csv", "text/csv", None, "per-point measured and modelled values of one engine's runs on the case (columns described by the result's pairs_columns)"),
    ("validation.json", "application/json", "validation-summary", "every case and engine in one table: status, runs, headline scores"),
    ("geometry.json", "application/json", "geometry-index", "every STL of every case in one list: case, configuration, units, frame, bounding box, size, SHA-256"),
    ("geometry.zip", "application/zip", None, "every STL in one archive (each keeps its own case's frame and units: they are not one scene)"),
    ("schemas/{name}.schema.json", "application/schema+json", None, "the JSON Schema (draft 2020-12) of each JSON document"),
    ("openapi.json", "application/json", None, "OpenAPI 3.1 description of every endpoint"),
    ("llms.txt", "text/plain", None, "plain-text entry point for agents"),
]
MEDIA_TYPES = {".json": "application/json", ".csv": "text/csv", ".stl": "model/stl", ".zip": "application/zip", ".txt": "text/plain"}

WRITTEN = set()          # every file this build wrote under docs/api/ (relative); anything else there is stale
DATA_VERSION = None      # set once the data files are written


# ----------------------------------------------------------------------------- files and URLs

def url(rel):
    return f"{API_BASE}/{rel}"


def schema_url(name):
    return f"{API_BASE}/schemas/{name}.schema.json"


def render_url(case, configuration=None):
    """The site URL of a configuration's render (the case's default configuration if None)."""
    return f"{SITE}/assets/geometry/{D.render_file(case, configuration)}"


def _sha256(rel):
    with io.open(os.path.join(API, rel), "rb") as f:
        body = f.read()
    return hashlib.sha256(body).hexdigest(), len(body)


def media_type(rel):
    if rel.startswith("schemas/"):
        return "application/schema+json"
    return MEDIA_TYPES[os.path.splitext(rel)[1]]


def download(rel):
    """A file to fetch: versioned URL, path, media type, size and SHA-256 of the bytes on disk."""
    sha, n = _sha256(rel)
    return {"url": f"{url(rel)}?v={sha[:12]}", "path": rel, "media_type": media_type(rel), "bytes": n, "sha256": sha}


def _target(rel):
    path = os.path.join(API, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    WRITTEN.add(rel)
    return path


def write_text(rel, text):
    with io.open(_target(rel), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return rel


def write_csv(rel, header, rows):
    with io.open(_target(rel), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        for r in rows:
            w.writerow(["" if v is None else v for v in r])
    return rel


def copy_file(src, rel):
    shutil.copyfile(src, _target(rel))
    return rel


def dump(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False, allow_nan=False) + "\n"


def write_json(rel, schema, obj):
    """A JSON document: the four header keys, then the body."""
    body = {"$schema": schema_url(schema), "schema_version": SCHEMA_VERSION, "data_version": DATA_VERSION,
            "license": D.LICENSE["spdx"]}
    body.update(obj)
    return write_text(rel, dump(body))


# ----------------------------------------------------------------------------- phase 1: data files

def points_summary(rows):
    cols = [c for c in D.POINT_COLUMNS if any(r[c] not in (None, "") for r in rows)]
    by = lambda key: sorted({str(r[key]) for r in rows})  # noqa: E731
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


def stl_rel(case, cfg):
    return f"cases/{case}/geometry.stl" if cfg == D.DEFAULT_CONFIGURATION[case] else f"cases/{case}/geometry_{cfg}.stl"


def write_data(case):
    """Points CSV, approach-flow CSV, STLs and pairs of one case; returns what the JSON phase needs."""
    rows, src = D.load_points(case)
    summ = points_summary(rows)
    write_csv(f"cases/{case}/points.csv", summ["columns"], ([r[c] for c in summ["columns"]] for r in rows))

    af, af_src = D.load_approach_flow(case)
    af_cols = [c for c in ("z", "U", "k", "u_rms") if any(c in r for r in af)]
    write_csv(f"cases/{case}/approach_flow.csv", af_cols, ([r.get(c) for c in af_cols] for r in af))

    geometry = []
    for cfg, tris, boxes, note in D.case_geometry(case):
        stats = D.stl_stats(tris)
        rel = stl_rel(case, cfg)
        D.write_ascii_stl(_target(rel), tris, f"AIJ_case{case}_{cfg}")
        lo, hi = expected_bbox(case, cfg)
        ok = None
        if lo is not None:
            ok = all(abs(a - b) < 1e-6 for a, b in zip(stats["bbox_min"], lo)) and all(abs(a - b) < 1e-6 for a, b in zip(stats["bbox_max"], hi))
            if not ok:
                raise SystemExit(f"geometry check failed for {case}/{cfg}: bbox {stats['bbox_min']}..{stats['bbox_max']} != {lo}..{hi}")
        if boxes is not None and not stats["watertight"]:
            raise SystemExit(f"geometry check failed for {case}/{cfg}: box geometry is not edge-manifold")
        geometry.append({"configuration": cfg, "rel": rel, "stats": stats, "boxes": boxes, "note": note, "bbox_ok": ok})
    geometry.sort(key=lambda g: g["configuration"] != D.DEFAULT_CONFIGURATION[case])

    for r in RUNS:
        if r["case"] == case:
            copy_file(os.path.join(RESULTS_DIR, r["pairs"]), f"cases/{case}/pairs/{r['engine']}.csv")
    return {"rows": rows, "src": src, "summ": summ, "af": af, "af_src": af_src, "af_cols": af_cols, "geometry": geometry}


def write_archive(data):
    """geometry.zip: every STL under a self-describing name, with fixed timestamps and order.

    Deflate output depends on the zlib version (1.2.13 and 1.3.1 encode the same bytes differently), so an
    archive whose members already equal the current STLs is kept as it is: its bytes then depend on the
    geometry alone, and a rebuild on any platform reproduces the committed file."""
    rel = "geometry.zip"
    members = []
    for case in D.CASE_IDS:
        for g in data[case]["geometry"]:
            with io.open(os.path.join(API, g["rel"]), "rb") as f:
                members.append((archive_name(case, g["configuration"]), f.read()))
    path = _target(rel)
    if os.path.isfile(path):
        try:
            with zipfile.ZipFile(path) as z:
                infos = z.infolist()
                if ([i.filename for i in infos] == [n for n, _ in members]
                        and all(i.date_time == (1980, 1, 1, 0, 0, 0) and i.compress_type == zipfile.ZIP_DEFLATED for i in infos)
                        and all(z.read(n) == body for n, body in members)):
                    return rel
        except zipfile.BadZipFile:
            pass
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, body in members:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, body)
    return rel


def archive_name(case, cfg):
    return f"AIJ_case{case}_{cfg}.stl"


def compute_data_version():
    """SHA-256 over (path, SHA-256) of every data file served and every score snapshot behind validation.json.

    The served files are written here with LF endings, so their bytes are their content. The score snapshots
    are hashed as canonical JSON (sorted keys, no whitespace), so a checkout's line endings cannot move it."""
    entries = []
    for rel in sorted(WRITTEN):
        if rel.endswith((".csv", ".stl")):
            entries.append(f"api/{rel}\t{_sha256(rel)[0]}")
    for r in sorted({r["results"] for r in RUNS}):
        with io.open(os.path.join(RESULTS_DIR, r), encoding="utf-8") as f:
            canonical = json.dumps(json.load(f), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        entries.append(f"validation/results/{r}\t{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}")
    return hashlib.sha256("\n".join(entries).encode("utf-8")).hexdigest()


# ----------------------------------------------------------------------------- phase 2: JSON documents

def check_runs_registry():
    """Every snapshot is registered and every registered snapshot exists: nothing is served by accident."""
    on_disk = {n for n in os.listdir(RESULTS_DIR) if n.endswith(".json")}
    listed = {r["results"] for r in RUNS}
    if on_disk != listed:
        raise SystemExit(f"validation/results/ and RUNS disagree: unregistered {sorted(on_disk - listed)}, "
                         f"missing {sorted(listed - on_disk)}")
    missing = sorted({r["pairs"] for r in RUNS if not os.path.isfile(os.path.join(RESULTS_DIR, r["pairs"]))})
    if missing:
        raise SystemExit(f"RUNS names pairs files that are not in validation/results/: {missing}")


def is_metric(v):
    return isinstance(v, dict) and "Fb" in v and "R" in v


def validation_entries(case):
    out = []
    for r in RUNS:
        if r["case"] != case:
            continue
        with io.open(os.path.join(RESULTS_DIR, r["results"]), encoding="utf-8") as f:
            res = json.load(f)
        for label, key in r["headline"].items():
            if not is_metric(res.get(key)):
                raise SystemExit(f"{r['results']}: headline '{label}' -> '{key}' is not a score in the file")
        out.append({
            "run_id": r["run_id"],
            "engine": r["engine"],
            "configuration": r["configuration"],
            "solver": res.get("engine") or res.get("turbulenceModel"), "numerics_level": res.get("numericsLevel"),
            "scale": res.get("scale"), "solved_time": res.get("solvedTime"), "iterations": res.get("iterations"),
            "points_measured": res.get("points.measured"),
            "lateral_sign_applied_in_fixture": res.get("lateralSign"),
            "recirculation_Lr_over_H": res.get("recirculation.LrOverH"),
            "quantity": res.get("quantity"),
            "normalisation": ("velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, "
                              "as it is published); hit rate D = 0.25, W = 0.05 in those units"),
            "metric_meaning": METRIC_MEANING,
            "headline": dict(r["headline"]),
            "scores": {k: v for k, v in res.items() if is_metric(v)},
            "figures": [{"url": f"{SITE}/assets/figures/{fig}", "caption": FIGURE_CAPTIONS[fig]} for fig in r["figures"]],
            "pairs": download(f"cases/{case}/pairs/{r['engine']}.csv"),
            "pairs_columns": r["pairs_columns"],
            "reproduce": r["reproduce"],
            "source_file": f"validation/results/{r['results']}",
            "source_url": f"{REPO_URL}/blob/main/validation/results/{r['results']}",
            # The benchmark's citation from one place, not the fixture's free-text reference line.
            "cite": D.CITATION["benchmark"],
        })
    return out


def configurations(case, rows):
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
    return configs


def write_case_documents(case, d):
    meta = D.CASES[case]
    summ = d["summ"]
    cols = summ["columns"]
    units_label = "metres" + (" (full scale)" if case == "E" else " (model scale)")

    write_json(f"cases/{case}/points.json", "points", {
        "case": case, "title": meta["title"],
        "points_source": d["src"],
        "units": meta["units"], "frame": meta["frame"],
        "columns": cols,
        "column_meaning": {c: COLUMN_MEANING[c] for c in cols},
        "n": len(d["rows"]),
        "csv": download(f"cases/{case}/points.csv"),
        "points": [{c: r[c] for c in cols} for r in d["rows"]],
    })

    files = []
    for g in d["geometry"]:
        entry = {"configuration": g["configuration"], **download(g["rel"]), "format": "ASCII STL, LF line endings, outward normals",
                 "source": g["note"], "stats": g["stats"], "bbox_matches_stated_dimensions": g["bbox_ok"],
                 "render": render_url(case, g["configuration"]), "render_caption": D.RENDER_CAPTIONS[(case, g["configuration"])]}
        if g["boxes"] is not None:
            b = g["boxes"]
            entry.update({"boxes": b, "box_count": len(b), "analytic_volume": round(sum(
                (x["max"][0] - x["min"][0]) * (x["max"][1] - x["min"][1]) * (x["max"][2] - x["min"][2]) for x in b), 9)})
        files.append(entry)
    write_json(f"cases/{case}/geometry.json", "geometry", {
        "case": case, "title": meta["title"], "units": units_label, "frame": meta["frame"],
        "default_configuration": D.DEFAULT_CONFIGURATION[case],
        "configurations": [f["configuration"] for f in files],
        "is_boxes": files[0].get("boxes") is not None,
        "files": files,
        "render": render_url(case),
    })

    results = validation_entries(case)
    write_json(f"cases/{case}/validation.json", "validation", {
        "case": case, "title": meta["title"],
        "status": "scored" if results else "pending",
        "status_meaning": STATUS_MEANING,
        "engines": [{"engine": e["id"], "status": ENGINE_STATUS[case][e["id"]]} for e in ENGINES],
        "results": results,
        "note": (None if results else "No validation has been run for this case yet; results is an empty list. "
                 "Nothing on this page is a claim about this case."),
    })

    configs = configurations(case, d["rows"])
    write_json(f"cases/{case}.json", "case", {
        "id": case, "slug": meta["slug"], "title": meta["title"], "summary": meta["short"],
        "configuration": meta["configuration"],
        "configurations": configs,
        "quantities": meta["quantities"],
        "units": meta["units"], "frame": meta["frame"],
        "inflow_fit": meta["inflow_fit"],
        "approach_flow": {"source": d["af_src"], "units": {c: {"z": "m", "U": "m/s", "k": "m^2/s^2", "u_rms": "m/s"}[c] for c in d["af_cols"]},
                          "rows": d["af"], "csv": download(f"cases/{case}/approach_flow.csv")},
        "points": {"url": url(f"cases/{case}/points.json"), "csv": download(f"cases/{case}/points.csv"), "source": d["src"], **summ},
        "geometry": {"url": url(f"cases/{case}/geometry.json"),
                     "files": [{"configuration": f["configuration"], "url": f["url"], "triangles": f["stats"]["triangles"],
                                "watertight": f["stats"]["watertight"]} for f in files]},
        "validation": {"url": url(f"cases/{case}/validation.json"), "status": "scored" if results else "pending",
                       "engines": ENGINE_STATUS[case]},
        "known_issues": meta["known_issues"],
        "people": meta["people"], "doi": meta["doi"], "doi_note": meta.get("doi_note"),
        "citation_requested": meta["citation_requested"],
        "files_in_repository": {"folder": f"{REPO_URL}/tree/main/{meta['folder']}", "reference": meta["reference_file"],
                                "approach_flow": meta["approach_flow_file"], "readme": meta["readme"]},
        "render": render_url(case),
        "page": f"{SITE}/cases/{meta['slug']}/",
    })
    return {"summ": summ, "configs": configs, "results": results, "files": files}


def write_cases_index(percase):
    items = []
    for case in D.CASE_IDS:
        meta = D.CASES[case]
        p = percase[case]
        items.append({
            "id": case, "slug": meta["slug"], "title": meta["title"], "summary": meta["short"],
            "configuration": meta["configuration"],
            "quantities": meta["quantities"], "units": meta["units"],
            "frame": {k: meta["frame"][k] for k in ("origin", "x", "y", "z")},
            "counts": {"rows": p["summ"]["rows"], "distinct_points": p["summ"]["distinct_points"], "configurations": len(p["configs"])},
            "engines": ENGINE_STATUS[case],
            "doi": meta["doi"],
            "links": {"case": url(f"cases/{case}.json"), "points": url(f"cases/{case}/points.json"),
                      "points_csv": download(f"cases/{case}/points.csv")["url"],
                      "geometry": url(f"cases/{case}/geometry.json"), "geometry_stl": p["files"][0]["url"],
                      "validation": url(f"cases/{case}/validation.json"), "page": f"{SITE}/cases/{meta['slug']}/",
                      "render": render_url(case)},
        })
    write_json("cases.json", "cases", {"cases": items})


def write_geometry_index(data):
    """One index of every STL. The STLs are NOT merged into one scene: each case has its own origin, A-D are
    model scale while E is full scale (about 1000 times larger), and C's three centre-block variants and E's
    before/after states are alternatives that cannot share one CFD domain."""
    items = []
    for case in D.CASE_IDS:
        meta = D.CASES[case]
        for g in data[case]["geometry"]:
            items.append({
                "case": case, "configuration": g["configuration"], **download(g["rel"]),
                "archive_name": archive_name(case, g["configuration"]),
                "units": "metres" + (" (full scale)" if case == "E" else " (model scale)"),
                "frame": {k: meta["frame"][k] for k in ("origin", "x", "y", "z")},
                "bbox_min": g["stats"]["bbox_min"], "bbox_max": g["stats"]["bbox_max"],
                "triangles": g["stats"]["triangles"], "watertight": g["stats"]["watertight"],
                "render": render_url(case, g["configuration"]),
            })
    write_json("geometry.json", "geometry-index", {
        "description": ("Every cleaned STL, one entry per case and configuration. Each file is in its own case's frame "
                        "and units — points.json of the same case lives in that frame — so they are deliberately not one "
                        "scene: overlaid, the cases would stack at the origin, and Case E is full scale while A-D are "
                        "model scale. geometry.zip holds the same files under archive_name."),
        "archive": download("geometry.zip"),
        "files": items,
    })


def write_validation_summary(percase):
    cases = []
    for case in D.CASE_IDS:
        engines = []
        for e in ENGINES:
            runs = []
            for res in percase[case]["results"]:
                if res["engine"] != e["id"]:
                    continue
                runs.append({"run_id": res["run_id"], "configuration": res["configuration"], "headline": [
                    {"label": label, "score": key, **{m: res["scores"][key].get(m) for m in ("Count", "R", "Fac2", "Fb", "HitRate")}}
                    for label, key in res["headline"].items()]})
            engines.append({"engine": e["id"], "status": ENGINE_STATUS[case][e["id"]], "runs": runs})
        cases.append({"case": case, "title": D.CASES[case]["title"], "url": url(f"cases/{case}/validation.json"), "engines": engines})
    write_json("validation.json", "validation-summary", {
        "description": ("Every case and engine in one table. 'scored' means a run exists, not that it agrees: read the "
                        "scores. Headline scores are the ones to quote; every score, the figures and the per-point pairs "
                        "are in each case's validation.json."),
        "engines": ENGINES, "status_meaning": STATUS_MEANING, "metric_meaning": METRIC_MEANING, "cases": cases,
    })


def write_schemas():
    for name, schema in S.published(API_BASE).items():
        write_text(f"schemas/{name}.schema.json", dump(schema))


def write_openapi():
    ids = D.CASE_IDS
    variants = sorted({g for case in ids for (c, g) in D.RENDER_CAPTIONS if c == case and g != D.DEFAULT_CONFIGURATION[case]})
    params = {
        "id": {"name": "id", "in": "path", "required": True, "description": "case id", "schema": {"type": "string", "enum": ids}},
        "configuration": {"name": "configuration", "in": "path", "required": True, "schema": {"type": "string", "enum": variants},
                          "description": "a non-default geometry configuration: C 0D or 1D (2D is geometry.stl); E bc (ac is geometry.stl)"},
        "engine": {"name": "engine", "in": "path", "required": True, "description": "an engine with a scored run on the case",
                   "schema": {"type": "string", "enum": [e["id"] for e in ENGINES]}},
        "name": {"name": "name", "in": "path", "required": True, "description": "a document schema",
                 "schema": {"type": "string", "enum": list(S.DOCUMENTS)}},
        "v": {"name": "v", "in": "query", "required": False, "schema": {"type": "string", "pattern": "^[0-9a-f]{12}$"},
              "description": "the file's SHA-256 prefix, as in the URLs the JSON documents give; ignored by the server, it keeps caches from serving a stale copy"},
    }
    op_ids = {
        "index.json": ("getIndex", "discovery"), "cases.json": ("listCases", "cases"), "cases/{id}.json": ("getCase", "cases"),
        "cases/{id}/points.json": ("getPoints", "points"), "cases/{id}/points.csv": ("getPointsCsv", "points"),
        "cases/{id}/approach_flow.csv": ("getApproachFlowCsv", "points"),
        "cases/{id}/geometry.json": ("getGeometry", "geometry"), "cases/{id}/geometry.stl": ("getGeometryStl", "geometry"),
        "cases/{id}/geometry_{configuration}.stl": ("getGeometryVariantStl", "geometry"),
        "cases/{id}/validation.json": ("getValidation", "validation"), "cases/{id}/pairs/{engine}.csv": ("getPairsCsv", "validation"),
        "validation.json": ("getValidationSummary", "validation"), "geometry.json": ("listGeometry", "geometry"),
        "geometry.zip": ("getGeometryArchive", "geometry"), "schemas/{name}.schema.json": ("getSchema", "discovery"),
        "openapi.json": ("getOpenApi", "discovery"), "llms.txt": ("getLlmsTxt", "discovery"),
    }
    names = {n: "".join(w.capitalize() for w in n.split("-")) for n in S.DOCUMENTS}
    stl_note = (" GitHub Pages labels .stl responses `application/vnd.ms-pki.stl` (a certificate type); the body is "
                "ASCII STL whatever the header says.")
    not_found = {"description": "No such case, configuration, engine or file. GitHub Pages answers with an HTML page, not JSON."}
    paths = {}
    for path, media, schema, desc in ENDPOINTS:
        op_id, tag = op_ids[path]
        if schema:
            body = {"schema": {"$ref": f"#/components/schemas/{names[schema]}"}}
        elif media == "application/zip":
            body = {"schema": {"type": "string", "format": "binary"}}
        elif media == "application/schema+json":
            body = {"schema": {"type": "object"}}
        else:
            body = {"schema": {"type": "string"}}
        op = {"operationId": op_id, "tags": [tag], "summary": desc[0].upper() + desc[1:].split(":")[0],
              "description": desc + (stl_note if media == "model/stl" else ""),
              "responses": {"200": {"description": "OK", "content": {media: body}}, "404": not_found}}
        ps = [params[p] for p in ("id", "configuration", "engine", "name") if "{" + p + "}" in path]
        if not path.endswith(".json") and path != "llms.txt" or path.endswith(".schema.json"):
            ps.append(params["v"])
        if ps:
            op["parameters"] = ps
        paths["/" + path] = {"get": op}
    components = {names[n]: {k: v for k, v in s.items() if k not in ("$schema", "$id")} for n, s in S.DOCUMENTS.items()}
    doc = {
        "openapi": "3.1.0",
        "jsonSchemaDialect": S.DRAFT,
        "info": {"title": "AIJ UWE benchmark — cleaned data API", "version": SCHEMA_VERSION,
                 "summary": "Wind-tunnel reference data of the AIJ UWE benchmark (Cases A-E), cleaned, with Eddy3D's validation against it.",
                 "description": ("Static files, one GET each; nothing is computed on request. Lengths in metres, velocities in "
                                 "m/s, variances and k in m^2/s^2, in one frame per case. " + COMPATIBILITY + " " + CACHING),
                 "license": {"name": D.LICENSE["name"], "identifier": D.LICENSE["spdx"]}},
        "servers": [{"url": API_BASE}, {"url": RAW_BASE, "description": "the same files, raw from the repository (fallback)"}],
        "tags": [{"name": "discovery", "description": "where everything is"}, {"name": "cases", "description": "the five cases"},
                 {"name": "points", "description": "measurement tables"}, {"name": "geometry", "description": "STL geometry"},
                 {"name": "validation", "description": "Eddy3D's scores and the per-point pairs behind them"}],
        "paths": paths,
        "components": {"schemas": components},
    }
    write_text("openapi.json", dump(doc))


def llms_text(percase):
    walk = [
        "# AIJ UWE benchmark — cleaned data API",
        "",
        "> Wind-tunnel reference data from the Architectural Institute of Japan Urban Wind Environment (UWE)",
        "> benchmark, Cases A-E, cleaned into one schema, plus Eddy3D's validation against it. Static files, plain GET.",
        "",
        f"Base URL: {API_BASE}",
        f"Fallback (raw files from the repository): {RAW_BASE}",
        f"Repository: {REPO_URL}",
        f"API version: {SCHEMA_VERSION}. Data version (SHA-256 of the served data): {DATA_VERSION}.",
        "Licence: CC-BY-4.0 — the data belongs to its collectors; cite the benchmark and the per-case papers.",
        "",
        "## How to use this",
        "",
        "1. GET index.json — every endpoint and file (with size and SHA-256), versions, changelog, citation.",
        "2. GET cases.json — the five cases with their frame, units, counts and links. Pick an id (A, B, C, D, E).",
        "3. GET cases/{id}.json — read `frame`, `units` and `known_issues` BEFORE the numbers; they differ per case.",
        "4. GET cases/{id}/points.json (or points.csv) — every value is SI (m, m/s, m^2/s^2) in ONE frame per case;",
        "   unmeasured values are null. Case E's quantity is a dimensionless velocity ratio.",
        "5. GET cases/{id}/geometry.stl — ASCII STL in metres, outward normals, origin at the building / array centre,",
        "   +x along the wind at WD = 0 (Cases A-D). Case E keeps its geographic frame (+x east, +y north, full-scale metres).",
        "   geometry.json lists the boxes where the geometry IS boxes (A, B, C, D), so you need not parse the STL at all.",
        "6. GET validation.json for every case and engine at once, or cases/{id}/validation.json for one case in full.",
        "   Quote the `headline` scores. An engine whose status is not \"scored\" has NO result for that case: do not",
        "   infer one. \"scored\" means a run exists, not that it agrees — read the numbers. Each result's `pairs` is",
        "   the per-point measured and modelled values, so any score can be recomputed. Status today: "
        + "; ".join(f"{c}: " + ", ".join(f"{e} {s}" for e, s in ENGINE_STATUS[c].items()) for c in D.CASE_IDS) + ".",
        "7. All geometry at once: GET geometry.json (every STL with its case, configuration, units, frame and SHA-256)",
        "   or geometry.zip. Each STL stays in its own case's frame and units; they are NOT one scene.",
        "8. Every JSON document names its JSON Schema in `$schema` (schemas/{name}.schema.json); openapi.json describes",
        "   every endpoint. Download URLs carry ?v=<SHA-256 prefix>: use the URLs the documents give, not hand-built ones.",
        "9. Send a descriptive User-Agent: the site's CDN answers HTTP 403 to Python urllib's default one and to some AI",
        "   crawlers. If you are refused, the fallback URL above serves byte-identical files from the repository.",
        "",
        "## Endpoints",
        "",
    ]
    for p, _, _, d in ENDPOINTS:
        walk.append(f"- {API_BASE}/{p} — {d}")
    walk += ["", "## Cases", ""]
    for case in D.CASE_IDS:
        meta = D.CASES[case]
        summ = percase[case]["summ"]
        walk.append(f"- {case}: {meta['title']}. {meta['short']} {summ['rows']} rows, {summ['distinct_points']} points, "
                    f"columns {', '.join(summ['columns'])}. Engines: " + ", ".join(f"{k} {v}" for k, v in ENGINE_STATUS[case].items()) + ".")
    walk += ["", "## Known data issues", "", "Each of these changes the result of a comparison if it is not accounted for.", ""]
    for case in D.CASE_IDS:
        for g in D.CASES[case]["known_issues"]:
            walk.append(f"- [{case}] {g}")
    walk += [
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
    return "\n".join(walk)


def write_dataset_jsonld(percase):
    """schema.org Dataset metadata for the home page (docs/_includes/dataset-jsonld.html), so search engines
    that index datasets (Google Dataset Search among them) find the data, its licence and its downloads."""
    editors = sorted({p for c in D.CASE_IDS for p in D.CASES[c]["people"]["editors_distributors"]})
    dataset = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "name": "AIJ Urban Wind Environment benchmark, Cases A-E — cleaned wind-tunnel data",
        "description": ("Wind-tunnel reference data of the Architectural Institute of Japan Urban Wind Environment (UWE) "
                        "benchmark, Cases A-E — an isolated 1:1:2 building, an isolated 1:4:4 slab, a 3 x 3 block array, a "
                        "high-rise among city blocks, and a district of Niigata before and after a high-rise — cleaned into "
                        "SI units and one frame per case, with cleaned STL geometry and Eddy3D's CFD validation scores."),
        "url": SITE + "/",
        "sameAs": REPO_URL,
        "license": D.LICENSE["url"],
        "isAccessibleForFree": True,
        "keywords": ["computational fluid dynamics", "CFD validation", "wind tunnel", "urban wind environment",
                     "pedestrian wind", "Architectural Institute of Japan", "benchmark"],
        "creator": [{"@type": "Person", "name": n.split(" (")[0]} for n in editors],
        "citation": D.CITATION["benchmark"],
        "isBasedOn": [f"https://doi.org/{D.CASES[c]['doi']}" for c in D.CASE_IDS if D.CASES[c]["doi"]],
        "measurementTechnique": ["hot-wire anemometry (split-fibre probes)", "thermistor anemometry"],
        "variableMeasured": ["mean velocity components U, V, W", "velocity variances", "turbulent kinetic energy k",
                             "mean scalar wind speed", "velocity ratio"],
        "distribution": [
            {"@type": "DataDownload", "name": f"{D.CASES[c]['title']}, measurement table",
             "encodingFormat": "text/csv", "contentUrl": download(f"cases/{c}/points.csv")["url"]} for c in D.CASE_IDS
        ] + [
            {"@type": "DataDownload", "name": "Geometry of every case (STL, metres)", "encodingFormat": "application/zip",
             "contentUrl": download("geometry.zip")["url"]},
            {"@type": "DataDownload", "name": "API index", "encodingFormat": "application/json", "contentUrl": url("index.json")},
        ],
    }
    body = json.dumps(dataset, indent=1, ensure_ascii=False).replace("</", "<\\/")
    os.makedirs(os.path.join(DOCS, "_includes"), exist_ok=True)
    with io.open(os.path.join(DOCS, "_includes", "dataset-jsonld.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write("<!-- Generated by scripts/build_api.py (write_dataset_jsonld). -->\n"
                f'<script type="application/ld+json">\n{body}\n</script>\n')


def write_changelog_include():
    """docs/_includes/api-changelog.md: the changelog index.json serves, as Markdown for the API page."""
    L = ["<!-- Generated by scripts/build_api.py from CHANGELOG. -->", ""]
    for entry in CHANGELOG:
        L += [f"### {entry['version']} ({entry['date']})", ""] + [f"- {c}" for c in entry["changes"]] + [""]
    with io.open(os.path.join(DOCS, "_includes", "api-changelog.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L))


def write_index():
    """Last: index.json lists every other file under docs/api/ with its size and SHA-256."""
    files = sorted(WRITTEN - {"index.json"})
    write_json("index.json", "index", {
        "name": "AIJ UWE benchmark — cleaned data API",
        "description": ("Static JSON/CSV/STL endpoints for the Architectural Institute of Japan Urban Wind Environment "
                        "benchmark (Cases A-E) and Eddy3D's validation against it. Every file is a plain HTTP GET; nothing is computed on request."),
        "base_url": API_BASE,
        "fallback_base_url": RAW_BASE,
        "fallback_note": "the same files, served raw from the repository's main branch (use when the Pages site is not reachable)",
        "repository": REPO_URL, "site": SITE,
        "versions": {"schema": SCHEMA_VERSION, "data": DATA_VERSION, "clean_manifest": (D.clean_manifest() or {}).get("version")},
        "compatibility": COMPATIBILITY,
        "caching": CACHING,
        "changelog": CHANGELOG,
        "endpoints": [{"path": p, "url": url(p), "method": "GET", "media_type": m, "description": d,
                       "schema": schema_url(s) if s else None} for p, m, s, d in ENDPOINTS],
        "case_ids": D.CASE_IDS,
        "files": [download(rel) for rel in files],
        "license_detail": D.LICENSE,
        "cite": D.CITATION,
        "agents": {
            "start_here": url("llms.txt"),
            "walk": ["GET index.json", "GET cases.json and pick an id", "GET cases/{id}.json for frame, units and known_issues",
                     "GET cases/{id}/points.json (SI units, one frame) and cases/{id}/geometry.stl (metres)",
                     "GET validation.json or cases/{id}/validation.json before quoting any Eddy3D score; an engine that is not 'scored' has no result"],
        },
    })


def remove_stale():
    """Delete anything under docs/api/ this build did not write (a renamed or retired file)."""
    for root, _, names in os.walk(API):
        for n in names:
            rel = os.path.relpath(os.path.join(root, n), API).replace(os.sep, "/")
            if rel not in WRITTEN:
                os.remove(os.path.join(root, n))
                print("removed stale", rel)
    for root, dirs, _ in sorted(os.walk(API), key=lambda t: -len(t[0])):
        for d in dirs:
            p = os.path.join(root, d)
            if not os.listdir(p):
                os.rmdir(p)


# ----------------------------------------------------------------------------- assets

def copy_assets():
    """docs/assets/geometry/ = every render, docs/assets/figures/ = every figure a run names; nothing else."""
    wanted = {
        "geometry": {D.render_file(c, cfg) for (c, cfg) in D.RENDER_CAPTIONS},
        "figures": {fig for r in RUNS for fig in r["figures"]},
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
        summ = percase[case]["summ"]
        cap = GALLERY_CAPTIONS[case].format(points=f"{summ['distinct_points']:,}", rows=f"{summ['rows']:,}")
        cells.append((f"/assets/geometry/{D.render_file(case)}", meta["title"], f"<strong>{meta['title']}</strong><br>{cap}",
                      f"/cases/{meta['slug']}/"))
    os.makedirs(os.path.join(DOCS, "_includes"), exist_ok=True)
    with io.open(os.path.join(DOCS, "_includes", "case-gallery.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(["<!-- Generated by scripts/build_api.py; edit GALLERY_CAPTIONS there. -->", ""] + figure_table(cells, 2)))


def build_pages(percase):
    """docs/cases/<slug>.md, one per case, from the same facts the API serves."""
    out_dir = os.path.join(DOCS, "cases")
    os.makedirs(out_dir, exist_ok=True)
    build_gallery(percase)
    for n, case in enumerate(D.CASE_IDS, start=1):
        meta = D.CASES[case]
        summ, configs, ventries = percase[case]["summ"], percase[case]["configs"], percase[case]["results"]
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
        for g in meta["known_issues"]:
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
                        "—" if s.get(m) is None else str(s[m]) if m == "Count" else f"{s[m]:+.3f}" if m in ("R", "Fb") else f"{s[m]:.3f}"
                        for s in scores.values()) + " |")
                pairs_rel = e["pairs"]["path"]
                L += ["", f"{e['normalisation']}. Per-point values: [`/api/{pairs_rel}`]({_asset('/api/' + pairs_rel)}). "
                      f"Reproduce: {e['reproduce']}.", ""]
                figures += [f for f in e["figures"] if f not in figures]
            for fig in figures:
                name = fig["url"].rsplit("/", 1)[-1]
                L += figure(f"/assets/figures/{name}", name, f"<strong>Figure {fig_no}.</strong> {fig['caption']}")
                fig_no += 1
            L += ["How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page."]
        else:
            L.append("**No validation has been run for this case yet.** Nothing on this page is a claim about it. Engine status: "
                     + ", ".join(f"{k} {v}" for k, v in ENGINE_STATUS[case].items()) + ".")
        L += ["", "## API", "", "| Resource | Endpoint |", "|---|---|"]
        for name, rel in (("Case", f"cases/{case}.json"), ("Points (JSON)", f"cases/{case}/points.json"),
                          ("Points (CSV)", f"cases/{case}/points.csv"), ("Approach flow (CSV)", f"cases/{case}/approach_flow.csv"),
                          ("Geometry", f"cases/{case}/geometry.json"), ("Geometry (STL)", f"cases/{case}/geometry.stl"),
                          ("Validation", f"cases/{case}/validation.json")):
            L.append(f"| {name} | [`/api/{rel}`]({_asset('/api/' + rel)}) |")
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

def _strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)
    elif isinstance(obj, str):
        yield obj


def verify():
    """Everything a client relies on, checked against the files on disk."""
    problems = []
    try:
        import jsonschema
        from openapi_spec_validator import validate as validate_openapi
    except ImportError as e:  # the contract is not optional
        return [f"{e.name} is not installed: pip install -r scripts/requirements.txt"]

    def load(rel):
        with io.open(os.path.join(API, rel), encoding="utf-8") as f:
            return json.load(f)

    on_disk = set()
    for root, _, names in os.walk(API):
        for n in names:
            on_disk.add(os.path.relpath(os.path.join(root, n), API).replace(os.sep, "/"))

    # index.json: lists every other file, with the right size and hash
    index = load("index.json")
    listed = {f["path"]: f for f in index["files"]}
    for rel in sorted(on_disk - {"index.json"} - set(listed)):
        problems.append(f"{rel} is served but not listed in index.json")
    for rel, f in listed.items():
        if rel not in on_disk:
            problems.append(f"index.json lists {rel}, which does not exist")
            continue
        sha, n = _sha256(rel)
        if (sha, n) != (f["sha256"], f["bytes"]):
            problems.append(f"index.json size/hash of {rel} disagree with the file")

    # schemas: valid themselves, and every document valid against the one it names
    schemas = {}
    for rel in sorted(r for r in on_disk if r.startswith("schemas/")):
        s = load(rel)
        jsonschema.Draft202012Validator.check_schema(s)
        schemas[s["$id"]] = s
    versions = set()
    for rel in sorted(r for r in on_disk if r.endswith(".json") and not r.startswith("schemas/") and r != "openapi.json"):
        doc = load(rel)
        s = schemas.get(doc.get("$schema"))
        if s is None:
            problems.append(f"{rel}: $schema {doc.get('$schema')} is not a published schema")
            continue
        for err in jsonschema.Draft202012Validator(s).iter_errors(doc):
            problems.append(f"{rel}: {'/'.join(str(p) for p in err.absolute_path)}: {err.message[:160]}")
        versions.add((doc.get("schema_version"), doc.get("data_version")))
        # every link into the API resolves, and a ?v= is the file's current hash prefix
        for sv in _strings(doc):
            if not sv.startswith(API_BASE + "/") or "{" in sv:
                continue
            rel_t, _, query = sv[len(API_BASE) + 1:].partition("?v=")
            if rel_t not in on_disk:
                problems.append(f"{rel}: link to {rel_t}, which does not exist")
            elif query and _sha256(rel_t)[0][:12] != query:
                problems.append(f"{rel}: link to {rel_t} carries a stale ?v={query}")
            if sv.startswith(SITE + "/assets/"):
                pass
        for sv in _strings(doc):
            if sv.startswith(SITE + "/assets/") and not os.path.isfile(os.path.join(DOCS, sv[len(SITE) + 1:])):
                problems.append(f"{rel}: link to site asset {sv[len(SITE) + 1:]}, which does not exist")
    if len(versions) != 1:
        problems.append(f"documents disagree on schema/data version: {sorted(versions)}")

    # openapi.json: a valid OpenAPI 3.1 document whose paths exist
    oa = load("openapi.json")
    try:
        validate_openapi(oa)
    except Exception as e:  # noqa: BLE001 — report whatever the validator found
        problems.append(f"openapi.json is not valid OpenAPI: {str(e)[:300]}")
    for p in oa["paths"]:
        pattern = p.lstrip("/")
        if "{" not in pattern:
            if pattern not in on_disk:
                problems.append(f"openapi path {p} has no file")
            continue
        import re
        rx = re.compile("^" + re.sub(r"\\\{[a-z]+\\\}", "[^/]+", re.escape(pattern)) + "$")
        if not any(rx.match(r) for r in on_disk):
            problems.append(f"openapi path {p} matches no file")

    # content checks
    for case in D.CASE_IDS:
        pj = load(f"cases/{case}/points.json")
        with io.open(os.path.join(API, f"cases/{case}/points.csv"), encoding="utf-8", newline="") as f:
            n_csv = sum(1 for _ in csv.reader(f)) - 1
        if pj["n"] != len(pj["points"]) or pj["n"] != n_csv:
            problems.append(f"case {case}: points.json n={pj['n']} rows={len(pj['points'])} csv={n_csv}")
        gj = load(f"cases/{case}/geometry.json")
        for g in gj["files"]:
            if D.stl_stats(D.read_ascii_stl(os.path.join(API, g["path"])))["triangles"] != g["stats"]["triangles"]:
                problems.append(f"case {case}: {g['path']} triangle count disagrees with geometry.json")
    gall = load("geometry.json")
    with zipfile.ZipFile(os.path.join(API, "geometry.zip")) as z:
        names = set(z.namelist())
        for it in gall["files"]:
            if it["archive_name"] not in names or hashlib.sha256(z.read(it["archive_name"])).hexdigest() != it["sha256"]:
                problems.append(f"geometry.zip lacks {it['archive_name']} or holds different bytes")
        if len(names) != len(gall["files"]):
            problems.append(f"geometry.zip holds {len(names)} files, geometry.json lists {len(gall['files'])}")
    with io.open(os.path.join(DOCS, "llms.txt"), encoding="utf-8") as a, io.open(os.path.join(API, "llms.txt"), encoding="utf-8") as b:
        if a.read() != b.read():
            problems.append("docs/llms.txt and docs/api/llms.txt differ")
    return problems


# ----------------------------------------------------------------------------- main

def build():
    global DATA_VERSION
    os.makedirs(API, exist_ok=True)
    check_runs_registry()
    copy_assets()
    # Phase 1: the data files. Their hashes define data_version, which every JSON document carries.
    data = {case: write_data(case) for case in D.CASE_IDS}
    write_archive(data)
    DATA_VERSION = compute_data_version()
    # Phase 2: the JSON documents, the site's generated pages, and the index of it all.
    percase = {}
    for case in D.CASE_IDS:
        percase[case] = write_case_documents(case, data[case])
        g = data[case]["geometry"]
        print(f"case {case}: {percase[case]['summ']['rows']} rows from {data[case]['src']}; geometry "
              f"{[(x['configuration'], x['stats']['triangles'], x['stats']['watertight']) for x in g]}; "
              f"{len(percase[case]['results'])} validation result(s)")
    write_cases_index(percase)
    write_geometry_index(data)
    write_validation_summary(percase)
    write_schemas()
    write_openapi()
    text = llms_text(percase)
    write_text("llms.txt", text)
    with io.open(os.path.join(DOCS, "llms.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    write_dataset_jsonld(percase)
    write_changelog_include()
    build_pages(percase)
    write_index()
    remove_stale()
    print("data_version", DATA_VERSION)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="verify the files on disk; build nothing")
    args = ap.parse_args()
    if not args.check:
        build()
    problems = verify()
    for p in problems:
        print("PROBLEM:", p)
    print("verify:", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
