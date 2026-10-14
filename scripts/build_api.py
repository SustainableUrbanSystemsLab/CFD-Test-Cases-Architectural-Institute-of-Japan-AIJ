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
# What the README's "What is not validated yet" table says. n/a = the engine cannot predict the
# quantity the case measures (the ML surrogate predicts pedestrian-height wind; A and B do not measure it).
ENGINE_STATUS = {
    "A": {"openfoam12-realizableKE": "validated", "openlb": "pending", "fluidx3d": "pending", "ml-surrogate": "n/a"},
    "B": {"openfoam12-realizableKE": "validated", "openlb": "pending", "fluidx3d": "pending", "ml-surrogate": "n/a"},
    "C": {"openfoam12-realizableKE": "pending", "openlb": "pending", "fluidx3d": "pending", "ml-surrogate": "pending"},
    "D": {"openfoam12-realizableKE": "pending", "openlb": "pending", "fluidx3d": "pending", "ml-surrogate": "pending"},
    "E": {"openfoam12-realizableKE": "pending", "openlb": "pending", "fluidx3d": "pending", "ml-surrogate": "pending"},
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
    default_cfg = {"A": "default", "B": "default", "C": "2D", "D": "default", "E": "ac"}[case]
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
                 "source": note, "stats": stats, "bbox_matches_stated_dimensions": ok if lo is not None else None}
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
        "render": f"{SITE}/assets/geom_case{case}.png",
    })
    return files, rel, checks


# ----------------------------------------------------------------------------- validation

def validation_entries(case):
    out = []
    rdir = os.path.join(REPO, "validation", "results")
    if not os.path.isdir(rdir):
        return out
    for name in sorted(os.listdir(rdir)):
        if not (name.startswith(f"case{case}_") and name.endswith(".json")):
            continue
        with io.open(os.path.join(rdir, name), encoding="utf-8") as f:
            res = json.load(f)
        engine = name[len(f"case{case}_"):-5]
        engine_id = {"openfoam12_realizableKE": "openfoam12-realizableKE"}.get(engine, engine)
        scores = {k: v for k, v in res.items() if isinstance(v, dict)}
        out.append({
            "engine": engine_id,
            "solver": res.get("turbulenceModel"), "numerics_level": res.get("numericsLevel"),
            "scale": res.get("scale"), "solved_time": res.get("solvedTime"),
            "points_measured": res.get("points.measured"),
            "lateral_sign_applied_in_fixture": res.get("lateralSign"),
            "recirculation_Lr_over_H": res.get("recirculation.LrOverH"),
            "normalisation": "U by U_H, k by U_H^2 (the benchmark's own convention); hit rate D = 0.25, W = 0.05 U_H",
            "metric_meaning": METRIC_MEANING,
            "scores": scores,
            "figures": [f"{SITE}/assets/aij_agreement.png", f"{SITE}/assets/aij_profiles.png"],
            "reproduce": "validation/plot_aij.py; Eddy3D fixtures TestAijCaseAContainerE2E / TestAijCaseBContainerE2E",
            "source_file": f"validation/results/{name}",
            "reference_string": res.get("reference"),
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
        "status": "validated" if entries else "pending",
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
        "validation": {"endpoint": url(rel_val), "status": "validated" if ventries else "pending", "engines": ENGINE_STATUS[case]},
        "gotchas": meta["gotchas"],
        "people": meta["people"], "doi": meta["doi"], "doi_note": meta.get("doi_note"),
        "citation_requested": meta["citation_requested"],
        "files_in_repository": {"folder": f"{REPO_URL}/tree/main/{meta['folder'].replace(' ', '%20')}", "reference": meta["reference_file"], "approach_flow": meta["approach_flow_file"], "readme": meta["readme"]},
        "render": f"{SITE}/assets/geom_case{case}.png",
        "page": f"{SITE}/cases/{meta['slug']}/",
    })
    return rel, summ, configs


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
                      "validation": url(f"cases/{case}/validation.json"), "page": f"{SITE}/cases/{meta['slug']}/", "render": f"{SITE}/assets/geom_case{case}.png"},
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
                            + extra_stl + ["index.json", "cases.json", "openapi.json", "llms.txt"])),
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
        "6. GET cases/{id}/validation.json — Eddy3D scores per engine. An EMPTY results list means no validation exists",
        "   for that case: do not infer one. Today only Cases A and B carry results (OpenFOAM 12, realizable k-epsilon).",
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
        "## Validation method (Cases A and B)",
        "",
        "Each case is solved through Eddy3D's production case writer (build-case -> run -> probe), not a hand-built",
        "OpenFOAM case; the probe sits at exactly the tunnel's measurement coordinates. Scores are normalised by U_H",
        "(k by U_H^2); hit rate uses D = 0.25, W = 0.05 U_H. FAC2 is harsh by construction on sign-changing V and W;",
        "read R and hit rate there. The lateral sign of Case B is corrected before scoring.",
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
    os.makedirs(ASSETS, exist_ok=True)
    for case in D.CASE_IDS:
        shutil.copyfile(os.path.join(REPO, "validation", "geometry", f"geom_case{case}.png"), os.path.join(ASSETS, f"geom_case{case}.png"))
    for name in ("aij_agreement.png", "aij_profiles.png"):
        shutil.copyfile(os.path.join(REPO, "validation", name), os.path.join(ASSETS, name))


def render_stl_check(case="D"):
    """Draw one cleaned STL with matplotlib so a human can look at it."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    tris = D.read_ascii_stl(os.path.join(API, f"cases/{case}/geometry.stl"))
    fig = plt.figure(figsize=(8, 5.5), dpi=130)
    ax = fig.add_subplot(111, projection="3d")
    coll = Poly3DCollection(tris, facecolor="#9aa3ad", edgecolor="#3a3f45", linewidths=0.25, alpha=0.95)
    ax.add_collection3d(coll)
    s = D.stl_stats(tris)
    lo, hi = s["bbox_min"], s["bbox_max"]
    span = max(h - l for h, l in zip(hi, lo))
    mid = [(h + l) / 2 for h, l in zip(hi, lo)]
    ax.set_xlim(mid[0] - span / 2, mid[0] + span / 2)
    ax.set_ylim(mid[1] - span / 2, mid[1] + span / 2)
    ax.set_zlim(0, span / 4)
    ax.set_box_aspect((1, 1, 0.25))
    ax.view_init(elev=28, azim=-55)
    ax.set_xlabel("x (m)"); ax.set_ylabel("y (m)"); ax.set_zlabel("z (m)")
    ax.set_title(f"api/cases/{case}/geometry.stl — {s['triangles']} triangles, watertight = {s['watertight']}, volume {s['signed_volume']:.6g} m³", fontsize=9)
    out = os.path.join(REPO, "validation", "geometry", f"stl_check_case{case}.png")
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


# ----------------------------------------------------------------------------- site pages

def _md_value(v):
    if isinstance(v, dict):
        return "<br>".join(f"**{k}**: {_md_value(x)}" for k, x in v.items())
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def build_pages(percase, validations):
    """docs/cases/<slug>.md, one per case, from the same facts the API serves."""
    out_dir = os.path.join(DOCS, "cases")
    os.makedirs(out_dir, exist_ok=True)
    for n, case in enumerate(D.CASE_IDS, start=1):
        meta = D.CASES[case]
        summ, configs = percase[case]
        ventries = validations[case]
        L = ["---", f"title: \"{meta['title']}\"", "parent: Cases", f"nav_order: {n}", "---", "",
             f"# {meta['title']}", "", meta["short"], "",
             f"![{meta['title']}]({{{{ '/assets/geom_case{case}.png' | relative_url }}}})", "",
             "## Configuration", "", "| | |", "|---|---|"]
        for k, v in meta["configuration"].items():
            L.append(f"| {k} | {_md_value(v)} |")
        L += ["", "## Frame and units", "", "| | |", "|---|---|"]
        for k, v in meta["frame"].items():
            L.append(f"| {k} | {_md_value(v)} |")
        for k, v in meta["units"].items():
            L.append(f"| unit: {k} | {v} |")
        L += ["", "## Reference data", "",
              f"Source in this repository: `{meta['reference_file']}`" + (f" (approach flow: `{meta['approach_flow_file']}`)" if meta["approach_flow_file"] else "") + ".",
              "", f"The cleaned table has **{summ['rows']} rows** over **{summ['distinct_points']} distinct points**; columns `{'`, `'.join(summ['columns'])}`.", ""]
        if summ["nulls"]:
            L.append("Unmeasured cells (null): " + ", ".join(f"{k} {v}" for k, v in summ["nulls"].items()) + ".")
            L.append("")
        L += ["| configuration | points |", "|---|---|"]
        for c in configs:
            key = ", ".join(f"{k} {v}" for k, v in c.items() if k not in ("points", "measured", "points_per_direction", "wind_directions"))
            val = c.get("points", c.get("points_per_direction"))
            if "measured" in c:
                val = f"{val} ({c['measured']} measured)"
            if "wind_directions" in c:
                key += f", 16 directions"
                val = f"{val} per direction"
            L.append(f"| {key} | {val} |")
        L += ["", "### Inflow", "", "| | |", "|---|---|"]
        for k, v in meta["inflow_fit"].items():
            if k == "windows":
                for w in v:
                    L.append("| window | " + "; ".join(f"{a} {b}" for a, b in w.items()) + " |")
            else:
                L.append(f"| {k} | {_md_value(v)} |")
        L += ["", "## Things to know before comparing", ""]
        for g in meta["gotchas"]:
            L.append(f"- {g}")
        L += ["", "## Validation", ""]
        if ventries:
            for e in ventries:
                L += [f"**{e['engine']}** — solved time {e['solved_time']}, scale 1:{e['scale']}, {e['points_measured']} points; "
                      f"reattachment length L_r/H = {e['recirculation_Lr_over_H']:.2f}. {e['normalisation']}.", "",
                      "| | " + " | ".join(e["scores"].keys()) + " |", "|---|" + "---|" * len(e["scores"])]
                for m, label in (("R", "R"), ("Fac2", "FAC2"), ("Fb", "FB"), ("HitRate", "hit rate")):
                    L.append(f"| **{label}** | " + " | ".join(f"{s[m]:+.3f}" if m in ("R", "Fb") else f"{s[m]:.3f}" for s in e["scores"].values()) + " |")
                L += ["", f"![agreement]({{{{ '/assets/aij_agreement.png' | relative_url }}}})", "", f"![profiles]({{{{ '/assets/aij_profiles.png' | relative_url }}}})", "",
                      "How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page."]
        else:
            L.append("**No validation has been run for this case yet.** Nothing on this page is a claim about it. Engine status: "
                     + ", ".join(f"{k} {v}" for k, v in ENGINE_STATUS[case].items()) + ".")
        L += ["", "## API", "", "| endpoint | |", "|---|---|"]
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
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify the files on disk; build nothing")
    args = ap.parse_args()
    if not args.check:
        os.makedirs(API, exist_ok=True)
        copy_assets()
        percase, validations, extra = {}, {}, []
        for case in D.CASE_IDS:
            pts = build_points(case)
            geo = build_geometry(case)
            val = build_validation(case)
            _, summ, configs = build_case(case, pts, geo, val)
            percase[case] = (summ, configs)
            validations[case] = val[0]
            extra += [g["path"] for g in geo[0][1:]]
            print(f"case {case}: {summ['rows']} rows from {pts[1]}; geometry {[(c, s['triangles'], s['watertight']) for c, s, _ in geo[2]]}; validation {len(val[0])} result(s)")
        build_cases_index(percase)
        build_index(extra)
        build_openapi()
        build_llms(percase)
        build_pages(percase, validations)
        print("rendered", render_stl_check("D"))
    problems = verify()
    for p in problems:
        print("PROBLEM:", p)
    print("verify:", "OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
