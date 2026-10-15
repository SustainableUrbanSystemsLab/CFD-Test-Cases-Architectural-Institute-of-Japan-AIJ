#!/usr/bin/env python
"""Regenerate clean/ — the cleaned, queryable release of the AIJ UWE benchmark Cases A-E.

    python clean/build.py            # rebuild everything, run every check, exit 1 on any failure
    python clean/build.py --check    # re-run the checks against what is on disk, build nothing

Inputs (never modified):
    case-a/, case-b/, case-c/   the Zenodo files as cloned
    case-d/, case-e/                      the clone's workbooks / 3dm (cross-checks only)
    clean/sources/zenodo_caseD/, clean/sources/zenodo_caseE/
                                                        the official Zenodo files the clone lacks
                                                        (SHA256SUMS.txt beside them; see manifest provenance)

Outputs (all under clean/, all regenerated from scratch, byte-deterministic):
    cases/<id>/points.csv|parquet        the measurement table in the canonical schema (SCHEMA.md)
    cases/<id>/approach_flow.csv|parquet the approach-flow profile, same units
    cases/<id>/directions.csv            one row per (config, wind direction): the wind vector in the case frame
    cases/<id>/geometry*.stl|json        cleaned geometry, metres, same frame as the points
    points.parquet, approach_flow.parquet, directions.parquet   all cases stacked (case_id column)
    manifest.json                        what each file is, counts, frames, transforms, inflow fits, provenance
    units.json                           column -> unit/meaning (the sidecar; headers carry no units)
    checks.json                          every validity check with the numbers it measured
    build.log                            every transform applied, in order

Every number that leaves this script is either read from a source file or derived by a transform that
is logged. Nothing is typed in from memory; the stated geometry (box sizes, pitches) is read from the
readmes / data paper AND verified against the point grids and STLs in the checks.

Requirements: python >= 3.10, numpy, pandas, pyarrow, xlrd (BIFF8 .xls), rhino3dm (Case E 3dm).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))          # .../clean
REPO = os.path.abspath(os.path.join(HERE, os.pardir))        # the AIJ repository
SRC = os.path.join(HERE, "sources")

RELEASE_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
KAPPA = 0.41

POINT_COLUMNS = ["case_id", "config", "instrument", "point_id", "wind_direction_deg", "wind_direction",
                 "x", "y", "z", "U", "V", "W", "uu", "vv", "ww", "k", "Vs", "velocity_ratio"]
TEXT_COLUMNS = {"case_id", "config", "instrument", "wind_direction"}
INT_COLUMNS = {"point_id"}

UNITS = {
    "case_id": {"unit": "", "meaning": "AIJ UWE case letter: A, B, C, D or E"},
    "config": {"unit": "", "meaning": "configuration within the case: 'default' (A, B, D); Case C centre building '0D' | '1D' | '2D'; Case E 'bc' (before construction) | 'ac' (after construction)"},
    "instrument": {"unit": "", "meaning": "'split_fibre' = hot-wire split-fibre probe, vector components; 'thermistor' = omnidirectional scalar speed"},
    "point_id": {"unit": "", "meaning": "the tunnel's own measurement point number (No.); shared across configurations and directions of a case"},
    "wind_direction_deg": {"unit": "deg", "meaning": "the case's wind direction label. A-D: the AIJ turntable angle WD (0 = +x). E: meteorological FROM-direction, clockwise from north (N = 0, E = 90). The flow vector per direction is in directions.csv"},
    "wind_direction": {"unit": "", "meaning": "compass name of the FROM-direction (Case E only; '' elsewhere)"},
    "x": {"unit": "m", "meaning": "case frame (SCHEMA.md): +x = streamwise at WD = 0 for A-D, +x = east for E; model-scale metres for A-D, full-scale metres for E"},
    "y": {"unit": "m", "meaning": "case frame: +y lateral (A-D), +y = north (E)"},
    "z": {"unit": "m", "meaning": "height above the ground plane"},
    "U": {"unit": "m/s", "meaning": "mean velocity component along +x"},
    "V": {"unit": "m/s", "meaning": "mean velocity component along +y (positive toward +y in EVERY case; Case B's published sign is flipped, see manifest transform)"},
    "W": {"unit": "m/s", "meaning": "mean velocity component along +z"},
    "uu": {"unit": "m^2/s^2", "meaning": "variance of the x-component fluctuation <u'u'> (Case A publishes rms; squared here)"},
    "vv": {"unit": "m^2/s^2", "meaning": "variance <v'v'>"},
    "ww": {"unit": "m^2/s^2", "meaning": "variance <w'w'>"},
    "k": {"unit": "m^2/s^2", "meaning": "turbulent kinetic energy as published (= (uu+vv+ww)/2 wherever all three variances exist; checked)"},
    "Vs": {"unit": "m/s", "meaning": "mean omnidirectional SCALAR wind speed from a thermistor anemometer. NOT |mean velocity vector| (Case D's split-fibre |U| column is dropped, see log)"},
    "velocity_ratio": {"unit": "-", "meaning": "Case E: Vs / U_ref with U_ref = the approach-flow speed at z = 15.9 m (full scale); see manifest cases.E.normalisation"},
}
APPROACH_FLOW_UNITS = {
    "case_id": UNITS["case_id"], "z": {"unit": "m", "meaning": "height above ground (model-scale metres A-D, full-scale metres E)"},
    "U": {"unit": "m/s", "meaning": "mean streamwise velocity"},
    "uu": UNITS["uu"], "vv": UNITS["vv"], "ww": UNITS["ww"], "k": {"unit": "m^2/s^2", "meaning": "turbulent kinetic energy"},
}
DIRECTION_UNITS = {
    "case_id": UNITS["case_id"], "config": UNITS["config"], "instrument": UNITS["instrument"],
    "wind_direction_deg": UNITS["wind_direction_deg"], "wind_direction": UNITS["wind_direction"],
    "flow_dir_x": {"unit": "-", "meaning": "x-component of the unit vector the mean wind BLOWS TOWARD, in the case frame"},
    "flow_dir_y": {"unit": "-", "meaning": "y-component of the same unit vector"},
    "rows": {"unit": "", "meaning": "rows of points.csv in this (config, direction, instrument)"},
    "measured": {"unit": "", "meaning": "of those, rows whose measured quantity is not NaN"},
    "sense_basis": {"unit": "", "meaning": "what fixes the rotation sense of this direction (measured from the data / read from a figure / definition)"},
    "status": {"unit": "", "meaning": "'settled' | 'unverified' (see QUESTIONS.md)"},
}

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

# --------------------------------------------------------------------------------------------- logging

LOG: list[str] = []
CHECKS: list[dict] = []


def log(msg: str):
    LOG.append(msg)
    print(msg)


def check(case: str, name: str, ok: bool, warn: bool = False, **measured):
    """Record one validity check. `measured` holds the numbers the verdict rests on.

    warn=True marks a check whose failure is a KNOWN, documented discrepancy in the published
    sources (listed in README.md / QUESTIONS.md): it is recorded as a warning and does not fail
    the build, so the finding cannot be hidden by loosening a tolerance.
    """
    verdict = "PASS" if ok else ("WARN" if warn else "FAIL")
    clean = {k: _jsonable(v) for k, v in measured.items()}
    CHECKS.append({"case": case, "check": name, "pass": bool(ok), "severity": "warning" if (warn and not ok) else ("info" if ok else "error"), **clean})
    log(f"  [{verdict}] {case} {name}" + (f"  {json.dumps(clean, ensure_ascii=False)}" if clean else ""))
    return ok


def _jsonable(v):
    if isinstance(v, (np.floating, float)):
        x = float(v)
        if math.isnan(x):
            return None
        if math.isinf(x):
            return "inf" if x > 0 else "-inf"
        return x
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, np.ndarray):
        return [_jsonable(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    return v


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------- readers

def num(v):
    """float or NaN for the sentinels the sources use ('', '-', -999.9)."""
    if v is None:
        return math.nan
    if isinstance(v, (int, float, np.floating)):
        x = float(v)
    else:
        s = str(v).strip()
        if s in ("", "-", "nan", "NaN"):
            return math.nan
        try:
            x = float(s)
        except ValueError:
            return math.nan
    if abs(x + 999.9) < 1e-9:
        return math.nan
    return x


def bare(name: str) -> str:
    """'x[mm]' / 'x (m)' / 'U(m/s)' -> 'x' / 'x' / 'U'. Also folds the full-width 'ｚ' of RS-S_caseD.csv."""
    n = name.replace("﻿", "").replace("ｚ", "z").split("(")[0].split("[")[0].strip()
    return n


def read_csv_rows(path: str):
    """(bare header, rows as lists of str). Drops blank rows; keeps a trailing empty column out of the header."""
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    header = [bare(h) for h in rows[0]]
    while header and header[-1] == "":
        header.pop()
    return header, rows[1:]


def xls(path: str):
    import xlrd
    return xlrd.open_workbook(path)


# --------------------------------------------------------------------------------------------- geometry helpers

def box_tris(lo, hi):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    p = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]
    return [(p[a], p[b], p[c]) for a, b, c in faces]


def tris_of_boxes(boxes):
    out = []
    for b in boxes:
        out.extend(box_tris(b["min"], b["max"]))
    return out


def read_ascii_stl(path):
    tris, cur = [], []
    with io.open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            s = line.strip()
            if s.startswith("vertex"):
                cur.append(tuple(float(t) for t in s.split()[1:4]))
                if len(cur) == 3:
                    tris.append(tuple(cur))
                    cur = []
    return tris


def _normal(t):
    a, b, c = (np.array(v) for v in t)
    n = np.cross(b - a, c - a)
    l = np.linalg.norm(n)
    return (n / l) if l > 0 else np.zeros(3)


def write_ascii_stl(path, tris, name):
    """LF-only ASCII STL; CRLF makes OpenFOAM keep the \\r in the last token of a line."""
    with io.open(path, "w", encoding="ascii", newline="\n") as f:
        f.write(f"solid {name}\n")
        for t in tris:
            n = _normal(t)
            f.write(f"  facet normal {n[0]:.6g} {n[1]:.6g} {n[2]:.6g}\n    outer loop\n")
            for p in t:
                f.write(f"      vertex {p[0]:.7g} {p[1]:.7g} {p[2]:.7g}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {name}\n")


def shells_from_tris(tris, tol=1e-9):
    key = lambda p: tuple(round(c / tol) for c in p)
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for t in tris:
        k0, k1, k2 = (key(p) for p in t)
        r0, r1, r2 = find(k0), find(k1), find(k2)
        if r0 != r1:
            parent[r0] = r1
        if find(k1) != r2:
            parent[find(k1)] = r2
    groups = defaultdict(list)
    for t in tris:
        groups[find(key(t[0]))].append(t)
    return list(groups.values())


def stl_stats(tris, tol=1e-7):
    key = lambda p: tuple(round(c / tol) for c in p)
    edges = defaultdict(int)
    vol = 0.0
    lo = [math.inf] * 3
    hi = [-math.inf] * 3
    for a, b, c in tris:
        ka, kb, kc = key(a), key(b), key(c)
        for u, v in ((ka, kb), (kb, kc), (kc, ka)):
            edges[tuple(sorted((u, v)))] += 1
        vol += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        for p in (a, b, c):
            for i in range(3):
                lo[i] = min(lo[i], p[i])
                hi[i] = max(hi[i], p[i])
    counts = defaultdict(int)
    for n in edges.values():
        counts[n] += 1
    return {"triangles": len(tris), "bbox_min": [round(v, 6) for v in lo], "bbox_max": [round(v, 6) for v in hi],
            "signed_volume": round(vol, 9), "edges": len(edges), "edges_shared_by_two_faces": counts.get(2, 0),
            "edges_boundary": counts.get(1, 0), "edges_non_manifold": sum(v for k, v in counts.items() if k > 2),
            "watertight": counts.get(2, 0) == len(edges)}


def orient_outward(tris, tol=1e-4):
    out, flipped, shells = [], 0, 0
    for shell in shells_from_tris(tris, tol=tol):
        shells += 1
        if stl_stats(shell)["signed_volume"] < 0:
            flipped += 1
            out.extend((a, c, b) for a, b, c in shell)
        else:
            out.extend(shell)
    return out, shells, flipped


def points_under_roof(xy: np.ndarray, z: float, tris) -> np.ndarray:
    """For each (x, y): is there a triangle whose XY projection contains it and whose surface sits above z?

    A point inside a building sees that building's roof above it; a point in the street sees nothing
    (overhangs would be false positives — none of these geometries has any). Works for closed boxes
    and for the open-edged Case E STL alike.
    """
    T = np.asarray(tris, dtype=float)  # (n, 3, 3)
    a, b, c = T[:, 0, :2], T[:, 1, :2], T[:, 2, :2]
    za, zb, zc = T[:, 0, 2], T[:, 1, 2], T[:, 2, 2]
    hit = np.zeros(len(xy), dtype=bool)
    d = (b[:, 1] - c[:, 1]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 1] - c[:, 1])
    ok = np.abs(d) > 1e-12
    a, b, c, za, zb, zc, d = a[ok], b[ok], c[ok], za[ok], zb[ok], zc[ok], d[ok]
    for i, (px, py) in enumerate(xy):
        l1 = ((b[:, 1] - c[:, 1]) * (px - c[:, 0]) + (c[:, 0] - b[:, 0]) * (py - c[:, 1])) / d
        l2 = ((c[:, 1] - a[:, 1]) * (px - c[:, 0]) + (a[:, 0] - c[:, 0]) * (py - c[:, 1])) / d
        l3 = 1.0 - l1 - l2
        eps = -1e-9
        inside = (l1 > eps) & (l2 > eps) & (l3 > eps) & (l1 < 1 - eps) & (l2 < 1 - eps) & (l3 < 1 - eps)
        if not inside.any():
            continue
        zs = (l1 * za + l2 * zb + l3 * zc)[inside]
        hit[i] = bool((zs > z + 1e-9).any())
    return hit


def points_in_boxes(xyz: np.ndarray, boxes, inclusive: bool = False) -> np.ndarray:
    """Strictly inside by default (a point ON a face plane is a fluid point and counts as outside);
    inclusive=True counts face-plane points as inside (used to predict which lattice nodes a block covers)."""
    inside = np.zeros(len(xyz), dtype=bool)
    tol = -1e-9 if inclusive else 1e-9
    for b in boxes:
        lo, hi = np.array(b["min"]), np.array(b["max"])
        inside |= np.all((xyz > lo + tol) & (xyz < hi - tol), axis=1)
    return inside


def rot_xy(xy: np.ndarray, deg: float) -> np.ndarray:
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.column_stack([c * xy[:, 0] - s * xy[:, 1], s * xy[:, 0] + c * xy[:, 1]])


# --------------------------------------------------------------------------------------------- fits

def log_law_fit(z, U, zlo, zhi):
    """Least squares of U on ln z over zlo <= z <= zhi: U = (u*/kappa) ln(z/z0)."""
    z, U = np.asarray(z, float), np.asarray(U, float)
    m = (z >= zlo - 1e-12) & (z <= zhi + 1e-12) & np.isfinite(U)
    A = np.column_stack([np.log(z[m]), np.ones(m.sum())])
    (a, b), *_ = np.linalg.lstsq(A, U[m], rcond=None)
    ustar = KAPPA * a
    z0 = math.exp(-b / a)
    pred = a * np.log(z[m]) + b
    rms = float(np.sqrt(np.mean((pred - U[m]) ** 2)))
    return {"z_range_m": [float(zlo), float(zhi)], "points": int(m.sum()), "u_star_m_s": round(ustar, 5), "z0_m": z0,
            "z0_mm": round(z0 * 1000, 4), "rms_residual_m_s": round(rms, 4), "rms_residual_rel": round(rms / float(np.mean(U[m])), 4)}


def log_law_U(fit, z):
    return fit["u_star_m_s"] / KAPPA * math.log(z / fit["z0_m"])


def power_law_fit(z, U, zlo, zhi):
    z, U = np.asarray(z, float), np.asarray(U, float)
    m = (z >= zlo - 1e-12) & (z <= zhi + 1e-12) & np.isfinite(U) & (U > 0)
    A = np.column_stack([np.log(z[m]), np.ones(m.sum())])
    (alpha, c), *_ = np.linalg.lstsq(A, np.log(U[m]), rcond=None)
    pred = np.exp(alpha * np.log(z[m]) + c)
    return {"z_range_m": [float(zlo), float(zhi)], "points": int(m.sum()), "alpha": round(float(alpha), 4),
            "max_rel_error": round(float(np.max(np.abs(pred / U[m] - 1))), 4)}


def interp_log(z, U, zq):
    """U at zq by linear interpolation in ln z (the honest reading of a tabulated boundary-layer profile)."""
    z, U = np.asarray(z, float), np.asarray(U, float)
    return float(np.interp(math.log(zq), np.log(z), U))


# --------------------------------------------------------------------------------------------- case facts (from the readmes / data paper; verified in the checks)

CASES = {
    "A": {"title": "Case A — flow around a 1:1:2 building", "folder": "case-a", "zenodo_concept": "10.5281/zenodo.15050147", "zenodo_version": "10.5281/zenodo.15050148",
          "b": 0.08, "H": 0.16, "U_H_stated": 4.49, "Re_H": 24000, "scale": None,
          "contact": "Takeshi Ishihara <ishihara@bridge.t.u-tokyo.ac.jp>", "collectors": ["Takeshi Ishihara (The University of Tokyo)", "Kazuki Hibi (Numerical Flow Design)"],
          "citation": "Meng, Y., & Hibi, K. (1998). Turbulent measurements of the flow field around a high-rise building. J. Wind Eng. JAWE 76, 55-64. https://doi.org/10.5359/jawe.1998.76_55"},
    "B": {"title": "Case B — flow around a 1:4:4 slab", "folder": "case-b", "zenodo_concept": "10.5281/zenodo.15401455", "zenodo_version": "10.5281/zenodo.15401456",
          "depth": 0.05, "width": 0.20, "H": 0.20, "U_H_stated": 5.1, "Re_H": 72000, "scale": None,
          "contact": "Yoshihide Tominaga <tominaga@abe.niit.ac.jp>", "collectors": ["Yoshihide Tominaga (Niigata Institute of Technology)"],
          "citation": "Miyazaki, T., Tominaga, Y. (2003). Wind tunnel experiment on flow field around a building model with a scale ratio of 4:4:1 placed within the surface boundary layer. Proc. Annual Meeting of Hokuriku Chapter, AIJ, 201-204 (in Japanese). https://www.aij.or.jp/paper/detail.html?productId=313933"},
    "C": {"title": "Case C — flow within a 3 x 3 array of blocks", "folder": "case-c", "zenodo_concept": "10.5281/zenodo.15401791", "zenodo_version": "10.5281/zenodo.15401792",
          "D": 0.20, "pitch": 0.40, "U_H_stated": 3.65, "Re_H": 52000, "scale": None,
          "contact": "Yoshitami Nonomura <nonomura.yoshitami@yamato-u.ac.jp>", "collectors": ["Yoshitami Nonomura (Yamato University)"],
          "citation": "Nonomura, Y., Kobayashi, N., Tominaga, Y., Mochida, A. (2003). The cross comparison of CFD results for flow field around building models (part 3). Japan Association for Wind Engineering 95, 83-84 (in Japanese). https://doi.org/10.14887/jaweam.2003.0.41.0"},
    "D": {"title": "Case D — flow around a high-rise building in city blocks", "folder": "case-d", "zenodo_concept": "10.5281/zenodo.15402668", "zenodo_version": "10.5281/zenodo.15402669",
          "H": 0.25, "U_H_stated": 6.65, "Re_H": 110000, "scale": 400,
          "contact": "Yoshihide Tominaga <tominaga@abe.niit.ac.jp>", "collectors": ["Yoshihide Tominaga (Niigata Institute of Technology)"],
          "citation": "Kikumoto, H., Okaze, T., Yoshie, R. et al. (2026). Comprehensive Experimental Database for Validating CFD Simulations in Urban Wind Environment: Benchmark Cases Curated by the Architectural Institute of Japan. Japan Architectural Review 9(1), e70083, section 3.4. https://doi.org/10.1002/2475-8876.70083"},
    "E": {"title": "Case E — flow within an actual urban area in Niigata", "folder": "case-e", "zenodo_concept": "10.5281/zenodo.15429017", "zenodo_version": "10.5281/zenodo.15429018",
          "ZR": 250.0, "UR": 7.8, "z_ref": 15.9, "Re": 17000, "scale": 250,
          "contact": "Yoshihide Tominaga <tominaga@abe.niit.ac.jp>", "collectors": ["Yoshihide Tominaga (Niigata Institute of Technology)"],
          "citation": "Tominaga, Y., Mochida, A., Yoshie, R., Kataoka, H., Nozu, T., Yoshikawa, M., Shirasawa, T. (2008). AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings. JWEIA 96, 1749-1761. https://doi.org/10.1016/j.jweia.2008.02.058"},
}
EDITORS = ["Yoshihide Tominaga (Niigata Institute of Technology)", "Hideki Kikumoto (The University of Tokyo)", "Tsubasa Okaze (Institute of Science Tokyo)"]


def row(**kw):
    r = {c: (("" if c in TEXT_COLUMNS else math.nan)) for c in POINT_COLUMNS}
    r["config"] = "default"
    r["wind_direction_deg"] = 0.0
    r.update(kw)
    return r


# --------------------------------------------------------------------------------------------- Case A

def build_A(prov):
    c = "A"
    folder = os.path.join(REPO, CASES[c]["folder"])
    rs = os.path.join(folder, "RS-caseA.csv")
    af = os.path.join(folder, "AF_caseA.csv")
    prov[c] = [rs, af, os.path.join(folder, "LF-caseA.xls"), os.path.join(folder, "readme_caseA.md")]
    header, rows = read_csv_rows(rs)
    log(f"[A] RS-caseA.csv header (bare): {header}; units in the published header: metres, m/s, rms m/s, k m2/s2")
    idx = {h: i for i, h in enumerate(header)}
    out = []
    for r in rows:
        g = lambda n: num(r[idx[n]])
        out.append(row(case_id=c, instrument="split_fibre", point_id=int(g("No.")),
                       x=g("x"), y=g("y"), z=g("z"), U=g("U"), V=g("V"), W=g("W"),
                       uu=g("u_rms") ** 2, vv=g("v_rms") ** 2, ww=g("w_rms") ** 2, k=g("k")))
    log("[A] transform: u_rms, v_rms, w_rms (m/s) -> uu, vv, ww = rms^2 (m^2/s^2), so A and B carry the same turbulence quantity")
    log("[A] transform: coordinates kept (already metres); V kept (positive toward +y, see check A.lateral_sign); origin kept (building centre)")
    pts = pd.DataFrame(out, columns=POINT_COLUMNS)

    h, ar = read_csv_rows(af)
    ai = {n: i for i, n in enumerate(h)}
    afl = pd.DataFrame([{"case_id": c, "z": num(r[ai["z"]]), "U": num(r[ai["U"]]), "uu": num(r[ai["u_rms"]]) ** 2, "vv": num(r[ai["v_rms"]]) ** 2,
                         "ww": num(r[ai["w_rms"]]) ** 2, "k": num(r[ai["k"]])} for r in ar])
    log("[A] approach flow: AF_caseA.csv, 24 heights, rms squared to variances as above")

    boxes = [{"min": [-CASES[c]["b"] / 2, -CASES[c]["b"] / 2, 0.0], "max": [CASES[c]["b"] / 2, CASES[c]["b"] / 2, CASES[c]["H"]]}]
    geo = [("default", boxes, "generated from the readme's stated dimensions b = 0.08 m, H = 2b = 0.16 m, centred on the origin (MP-z_caseA.png)")]

    # ---- checks
    check(c, "row_count_matches_readme", len(pts) == 186, rows=len(pts), expected=186, source="MP drawings / data paper: 186 points")
    check(c, "point_ids_unique_and_contiguous", sorted(pts.point_id) == list(range(1, 187)))
    check(c, "no_sentinels_or_nan_in_measured_columns", not pts[["x", "y", "z", "U", "V", "W", "uu", "vv", "ww", "k"]].isna().any().any())
    kerr = float(np.max(np.abs(pts.k - 0.5 * (pts.uu + pts.vv + pts.ww))))
    check(c, "k_equals_half_sum_of_variances", kerr < 2e-3, max_abs_error=kerr, note="k published to 3 dp; rms to 3 dp")
    inside = points_in_boxes(pts[["x", "y", "z"]].to_numpy(), boxes)
    check(c, "no_sensor_inside_building", int(inside.sum()) == 0, inside=int(inside.sum()))
    ctrl = points_in_boxes(np.column_stack([pts.x + 0.03, pts.y + 0.04, pts.z]).to_numpy() if False else np.column_stack([pts.x.to_numpy() + 0.03, pts.y.to_numpy() + 0.04, pts.z.to_numpy()]), boxes)
    check(c, "control_shifted_points_are_detected_inside", int(ctrl.sum()) > 0, inside_after_shift=int(ctrl.sum()), shift_m=[0.03, 0.04, 0])
    bb = [pts.x.min(), pts.x.max(), pts.y.min(), pts.y.max(), pts.z.min(), pts.z.max()]
    check(c, "extents_sane", bb[0] >= -0.1 and bb[1] <= 0.3 and bb[2] >= -0.2 and bb[3] <= 1e-9 and bb[4] > 0 and bb[5] <= 0.4, bbox=bb,
          note="points on the y <= 0 half, z = 0.01 .. 0.32 (MP drawings)")
    # lateral sign: just outside the y<0 flank, upstream half of the side face, the flow deflects AWAY from the centreline => V < 0 when +y is positive
    flank = pts[(np.isclose(pts.x, -0.04)) & (np.isclose(pts.y, -0.05)) & (pts.z < 0.1)]
    check(c, "lateral_sign_V_negative_on_y_negative_flank", bool((flank.V < 0).all()), points=flank[["x", "y", "z", "V"]].to_dict("records"))
    # LF workbook cross-check (coordinates there are x/b, y/b, z/b)
    wb = xls(os.path.join(folder, "LF-caseA.xls"))
    sh = wb.sheet_by_name("Results (Ver. sec.)")
    mx = 0.0
    n = 0
    for r in range(2, sh.nrows):
        if sh.cell_value(r, 0) == "":
            continue
        no = int(sh.cell_value(r, 0))
        xb, yb, zb = (float(sh.cell_value(r, k)) for k in (1, 2, 3))
        p = pts[(pts.point_id == no)].iloc[0]
        mx = max(mx, abs(xb * 0.08 - p.x), abs(yb * 0.08 - p.y), abs(zb * 0.08 - p.z), abs(float(sh.cell_value(r, 4)) - p.U))
        n += 1
    check(c, "legacy_workbook_agrees_with_csv", mx < 1e-6, rows_compared=n, max_abs_diff=mx, note="LF-caseA.xls 'Results (Ver. sec.)' x/b*0.08 etc. vs RS-caseA.csv")
    # inflow
    fit = log_law_fit(afl.z, afl.U, 0.02, 2 * CASES[c]["H"])
    UH = interp_log(afl.z, afl.U, CASES[c]["H"])
    inflow = {"U_H_m_s": round(UH, 4), "U_H_stated_m_s": CASES[c]["U_H_stated"], "H_m": CASES[c]["H"],
              "log_law": {**fit, "error_at_H_rel": round(log_law_U(fit, CASES[c]["H"]) / UH - 1, 4)},
              "power_law": power_law_fit(afl.z, afl.U, 0.02, 2 * CASES[c]["H"]), "method": f"least squares, kappa = {KAPPA}, z = 0.02 .. 2H on AF_caseA.csv"}
    check(c, "U_H_from_profile_matches_stated", abs(UH - CASES[c]["U_H_stated"]) < 0.05, U_H_profile=UH, U_H_stated=CASES[c]["U_H_stated"])
    frame = {"origin": "building centre on the ground plane", "x": "+x streamwise (wind at WD = 0 blows toward +x); building x in [-0.04, 0.04]",
             "y": "+y lateral; building y in [-0.04, 0.04]; points published on the y <= 0 half", "z": "+z up; roof at 0.16", "length_scale": "model metres (the source states no model:full scale ratio)"}
    transform = {"coordinate_scale": 1.0, "lateral_sign": 1, "origin_shift_m": [0, 0, 0], "turbulence": "rms squared to variance",
                 "note": "none of x, y, z, U, V, W, k changed"}
    return pts, afl, geo, inflow, frame, transform


# --------------------------------------------------------------------------------------------- Case B

def build_B(prov):
    c = "B"
    folder = os.path.join(REPO, CASES[c]["folder"])
    rs = os.path.join(folder, "RS_caseB.csv")
    af = os.path.join(folder, "AF_caseB.csv")
    prov[c] = [rs, af, os.path.join(folder, "LF_caseB.xls"), os.path.join(folder, "readme_caseB.md")]
    header, rows = read_csv_rows(rs)
    log(f"[B] RS_caseB.csv header (bare): {header}; published units: x,y,z MILLIMETRES, velocities m/s, variances m2/s2")
    idx = {h: i for i, h in enumerate(header)}
    out = []
    for r in rows:
        g = lambda n: num(r[idx[n]])
        out.append(row(case_id=c, instrument="split_fibre", point_id=int(g("No.")),
                       x=g("x") / 1000.0, y=g("y") / 1000.0, z=g("z") / 1000.0, U=g("U"), V=-g("V"), W=g("W"),
                       uu=g("<u'2>"), vv=g("<v'2>"), ww=g("<w'2>"), k=g("k")))
    log("[B] transform: x, y, z millimetres -> metres (x 0.001)")
    log("[B] transform: V -> -V. The published V is positive toward -y: at (-25, -110, 12.5) mm, just outside the y = -100 mm flank where the flow must deflect away from the centreline (toward -y), the file has V = +3.630 m/s; Case A at the same place has V = -2.893 and Case D's split fibre V = +2.055 on its +y flank. Flipping V makes V positive toward +y in every case. (For a y-symmetric building 'flip V' and 'flip y' are the same transform; V is flipped so the coordinates stay the drawing's.)")
    pts = pd.DataFrame(out, columns=POINT_COLUMNS)

    h, ar = read_csv_rows(af)
    ai = {n: i for i, n in enumerate(h)}
    afl = pd.DataFrame([{"case_id": c, "z": num(r[ai["z"]]), "U": num(r[ai["U"]]), "uu": num(r[ai["<u'2>"]]), "vv": num(r[ai["<v'2>"]]), "ww": num(r[ai["<w'2>"]]), "k": num(r[ai["k"]])} for r in ar])
    log("[B] approach flow: AF_caseB.csv, 12 heights in metres; the '1/4 power' fit column is dropped (a fit, not a measurement)")

    boxes = [{"min": [-CASES[c]["depth"] / 2, -CASES[c]["width"] / 2, 0.0], "max": [CASES[c]["depth"] / 2, CASES[c]["width"] / 2, CASES[c]["H"]]}]
    geo = [("default", boxes, "generated from the readme's stated dimensions 0.05 x 0.20 x 0.20 m, centred on the origin (MP-z_caseB.png)")]

    check(c, "row_count_matches_readme", len(pts) == 224, rows=len(pts), expected=224)
    check(c, "point_ids_unique_and_contiguous", sorted(pts.point_id) == list(range(1, 225)))
    check(c, "no_sentinels_or_nan_in_measured_columns", not pts[["x", "y", "z", "U", "V", "W", "uu", "vv", "ww", "k"]].isna().any().any())
    kerr = float(np.max(np.abs(pts.k - 0.5 * (pts.uu + pts.vv + pts.ww))))
    check(c, "k_equals_half_sum_of_variances", kerr < 2e-3, max_abs_error=kerr)
    inside = points_in_boxes(pts[["x", "y", "z"]].to_numpy(), boxes)
    check(c, "no_sensor_inside_building", int(inside.sum()) == 0, inside=int(inside.sum()))
    ctrl = points_in_boxes(np.column_stack([pts.x.to_numpy() + 0.03, pts.y.to_numpy() + 0.05, pts.z.to_numpy()]), boxes)
    check(c, "control_shifted_points_are_detected_inside", int(ctrl.sum()) > 0, inside_after_shift=int(ctrl.sum()), shift_m=[0.03, 0.05, 0])
    bb = [pts.x.min(), pts.x.max(), pts.y.min(), pts.y.max(), pts.z.min(), pts.z.max()]
    check(c, "extents_sane_after_mm_to_m", bb[0] >= -0.1 and bb[1] <= 0.6 and bb[2] >= -0.4 and bb[3] <= 1e-9 and bb[4] > 0 and bb[5] <= 0.4, bbox=bb,
          note="MP drawings: x -0.075 .. 0.55 m, y -0.35 .. 0, z 0.0125 .. 0.35 m")
    flank = pts[(np.isclose(pts.x, -0.025)) & (np.isclose(pts.y, -0.110)) & (pts.z < 0.05)]
    check(c, "lateral_sign_V_negative_on_y_negative_flank_after_flip", bool((flank.V < 0).all()) and len(flank) > 0, points=flank[["x", "y", "z", "V"]].to_dict("records"))
    # seven locations were measured twice: the foot of each vertical-plane profile (z = 12.5 mm, y = 0) and the
    # horizontal plane's centreline row share coordinates but carry different values (two runs, two point numbers)
    dup = pts.groupby(["x", "y", "z"]).filter(lambda g: len(g) > 1).sort_values(["x", "point_id"])
    pairs = [{"x": float(g.x.iloc[0]), "ids": [int(i) for i in g.point_id], "U": [float(u) for u in g.U], "abs_dU": round(float(abs(g.U.iloc[0] - g.U.iloc[1])), 3)} for _, g in dup.groupby(["x", "y", "z"])]
    check(c, "seven_locations_measured_twice", len(pairs) == 7 and all(len(p["ids"]) == 2 for p in pairs), pairs=pairs,
          mean_abs_dU=round(float(np.mean([p["abs_dU"] for p in pairs])), 3), note="repeat measurements of the same location in two runs; both rows are kept (their point numbers differ). The spread is a free repeatability estimate.")
    wb = xls(os.path.join(folder, "LF_caseB.xls"))
    mx, n = 0.0, 0
    for sn, offset in (("Results (Ver. sec.)", 0), ("Results (Hol. sec.)", 109)):
        sh = wb.sheet_by_name(sn)
        for r in range(3, sh.nrows):
            if sh.cell_value(r, 0) == "":
                continue
            no = int(sh.cell_value(r, 0)) + offset
            xm, ym, zm, U, V = (float(sh.cell_value(r, k)) for k in (1, 2, 3, 4, 5))
            m = pts[pts.point_id == no].iloc[0]
            mx = max(mx, abs(m.x - xm / 1000), abs(m.y - ym / 1000), abs(m.z - zm / 1000), abs(m.U - U), abs(m.V + V))
            n += 1
    check(c, "legacy_workbook_agrees_with_csv", mx < 1e-6 and n == 224, rows_compared=n, max_abs_diff=mx,
          note="LF_caseB.xls (mm, published V sign) vs the cleaned table (m, V flipped); the CSV numbers the vertical-section sheet 1..109 and the horizontal-section sheet 110..224")
    fit = log_law_fit(afl.z, afl.U, 0.02, 2 * CASES[c]["H"])
    UH = interp_log(afl.z, afl.U, CASES[c]["H"])
    inflow = {"U_H_m_s": round(UH, 4), "U_H_stated_m_s": CASES[c]["U_H_stated"], "H_m": CASES[c]["H"],
              "log_law": {**fit, "error_at_H_rel": round(log_law_U(fit, CASES[c]["H"]) / UH - 1, 4)},
              "power_law": power_law_fit(afl.z, afl.U, 0.02, 2 * CASES[c]["H"]), "method": f"least squares, kappa = {KAPPA}, z = 0.02 .. 2H on AF_caseB.csv"}
    check(c, "U_H_from_profile_matches_stated", abs(UH - CASES[c]["U_H_stated"]) < 0.1, U_H_profile=UH, U_H_stated=CASES[c]["U_H_stated"], note="profile has a row at exactly z = 0.2 m: 5.133")
    frame = {"origin": "building centre on the ground plane", "x": "+x streamwise (wind at WD = 0 blows toward +x); slab x in [-0.025, 0.025]",
             "y": "+y lateral; slab y in [-0.10, 0.10]; points published on the y <= 0 half", "z": "+z up; roof at 0.20", "length_scale": "model metres (the source states no model:full scale ratio)"}
    transform = {"coordinate_scale": 0.001, "lateral_sign": -1, "origin_shift_m": [0, 0, 0], "turbulence": "variances as published",
                 "note": "x, y, z from mm to m; V sign flipped; nothing else changed"}
    return pts, afl, geo, inflow, frame, transform


# --------------------------------------------------------------------------------------------- Case C

def blocks_C(centre: str):
    D, P = CASES["C"]["D"], CASES["C"]["pitch"]
    boxes = []
    for cx in (-P, 0.0, P):
        for cy in (-P, 0.0, P):
            if cx == 0.0 and cy == 0.0:
                h = {"0D": 0.0, "1D": D, "2D": 2 * D}[centre]
                if h == 0.0:
                    continue
            else:
                h = D
            boxes.append({"min": [round(cx - D / 2, 9), round(cy - D / 2, 9), 0.0], "max": [round(cx + D / 2, 9), round(cy + D / 2, 9), round(h, 9)]})
    return boxes


def build_C(prov):
    c = "C"
    folder = os.path.join(REPO, CASES[c]["folder"])
    rs = os.path.join(folder, "RS_caseC.csv")
    af = os.path.join(folder, "AF_caseC.csv")
    prov[c] = [rs, af, os.path.join(folder, "LF-caseC.xls"), os.path.join(folder, "readme_caseC.md")]
    header, rows = read_csv_rows(rs)
    log(f"[C] RS_caseC.csv header (bare): {header}; the published header ends with a trailing comma (empty 8th column, dropped); CB is TEXT")
    idx = {h: i for i, h in enumerate(header)}
    out = []
    for r in rows:
        g = lambda n: num(r[idx[n]])
        out.append(row(case_id=c, instrument="thermistor", config=r[idx["CB"]].strip(), point_id=int(g("No.")),
                       wind_direction_deg=g("WD"), x=g("x"), y=g("y"), z=g("z"), Vs=g("Vs")))
    log("[C] transform: CB text ('0D','1D','2D') -> config; WD -> wind_direction_deg; coordinates kept (metres); Vs kept")
    pts = pd.DataFrame(out, columns=POINT_COLUMNS)

    h, ar = read_csv_rows(af)
    ai = {n: i for i, n in enumerate(h)}
    afl = pd.DataFrame([{"case_id": c, "z": num(r[ai["z"]]), "U": num(r[ai["U"]]), "uu": num(r[ai["u_rms"]]) ** 2, "vv": math.nan, "ww": math.nan, "k": math.nan} for r in ar])
    log("[C] approach flow: AF_caseC.csv, 16 heights, u_rms squared to uu; no v, w, k published")

    geo = [(cfg, blocks_C(cfg), f"generated: nine {CASES[c]['D']} m cubes on a {CASES[c]['pitch']} m pitch (street = D), centre block {cfg}; pitch verified against the point grid below")
           for cfg in ("0D", "1D", "2D")]

    # ---- checks
    check(c, "row_count_is_3WD_x_3CB_x_120", len(pts) == 1080, rows=len(pts))
    combos = pts.groupby(["config", "wind_direction_deg"]).size()
    check(c, "nine_configurations_of_120_points", len(combos) == 9 and bool((combos == 120).all()), combos={f"{k[0]}@{k[1]}": int(v) for k, v in combos.items()})
    ids = sorted(pts.point_id.unique())
    missing = sorted(set(range(1, 133)) - set(ids))
    check(c, "point_numbers_4_to_132_with_readme_gaps", ids[0] == 4 and ids[-1] == 132 and missing == [1, 2, 3, 34, 35, 36, 37, 46, 55, 100, 101, 102], missing=missing,
          note="readme: 'Missing point numbers: 1, 2, 3, 34, 35, 36, 37, 46, 55, 100, 101, 102'")
    same = pts.groupby("point_id")[["x", "y", "z"]].nunique().max().max()
    check(c, "all_nine_configurations_share_one_point_set", int(same) == 1)
    check(c, "all_points_at_z_0.02", bool(np.allclose(pts.z, 0.02)))
    check(c, "no_sentinels_or_nan", not pts[["x", "y", "z", "Vs"]].isna().any().any())
    # pitch from the grid: the 13x13 lattice x,y in -0.30..0.30 step 0.05 minus the 9 footprints = the 120 measured nodes
    lat = {(round(x, 3), round(y, 3)) for x in np.arange(-0.30, 0.301, 0.05) for y in np.arange(-0.30, 0.301, 0.05)}
    have = {(round(x, 3), round(y, 3)) for x, y in pts[["x", "y"]].drop_duplicates().to_numpy()}
    absent = lat - have
    inside_1D = points_in_boxes(np.array([[x, y, 0.02] for x, y in sorted(lat)]), blocks_C("1D"), inclusive=True)
    pred_absent = {p for p, i in zip(sorted(lat), inside_1D) if i}
    check(c, "absent_lattice_nodes_are_exactly_the_nine_footprints_at_pitch_0.40", absent == pred_absent and len(absent) == 49, absent=len(absent), lattice=len(lat), measured=len(have),
          note="also true for a 0.375 m pitch; the 0.40 m pitch (street = D) is read from MP-z-caseC.png and Figure 3 of the data paper")
    for cfg in ("0D", "1D", "2D"):
        bx = blocks_C(cfg)
        xyz = pts[pts.config == cfg][["x", "y", "z"]].drop_duplicates().to_numpy()
        inside = points_in_boxes(xyz, bx)
        check(c, f"no_sensor_inside_building_{cfg}", int(inside.sum()) == 0, inside=int(inside.sum()), points=len(xyz))
    on_face = int(((np.isclose(np.abs(pts.x), 0.30)) | (np.isclose(np.abs(pts.y), 0.30))).sum() / 9)
    check(c, "points_on_a_building_face_plane_counted", on_face == 24, points_on_face_plane=on_face, note="|x| = 0.30 or |y| = 0.30 in the gap between blocks: fluid points on a plane that is a wall elsewhere")
    ctrl = points_in_boxes(np.column_stack([pts.x.to_numpy() + 0.2, pts.y.to_numpy(), pts.z.to_numpy()]), blocks_C("1D"))
    check(c, "control_shifted_points_are_detected_inside", int(ctrl.sum()) > 0, inside_after_shift=int(ctrl.sum()), shift_m=[0.2, 0, 0])
    # frame: WD = 0 blows toward +x => the field is y-mirror symmetric and the windward band is faster than the leeward one
    def mirror_residual(cfg, wd, fn):
        s = pts[(pts.config == cfg) & (pts.wind_direction_deg == wd)]
        m = {(round(x, 3), round(y, 3)): v for x, y, v in s[["x", "y", "Vs"]].to_numpy()}
        d = [abs(v - m[fn(k)]) for k, v in m.items() if fn(k) in m]
        return float(np.mean(d)), len(d)
    sym = {}
    for cfg in ("0D", "1D", "2D"):
        ymir, n1 = mirror_residual(cfg, 0.0, lambda k: (k[0], round(-k[1], 3)))
        xmir, n2 = mirror_residual(cfg, 0.0, lambda k: (round(-k[0], 3), k[1]))
        s = pts[(pts.config == cfg) & (pts.wind_direction_deg == 0.0)]
        up, down = s[s.x <= -0.25].Vs.mean(), s[s.x >= 0.25].Vs.mean()
        sym[cfg] = {"WD0_y_mirror_mean_abs_dVs": round(ymir, 4), "WD0_x_mirror_mean_abs_dVs": round(xmir, 4), "pairs": n1, "mean_Vs_x<=-0.25": round(up, 4), "mean_Vs_x>=0.25": round(down, 4)}
        check(c, f"WD0_flow_is_along_x_{cfg}", ymir < 0.2 and xmir > 2 * ymir and up > down, **sym[cfg])
        anti, n3 = mirror_residual(cfg, 45.0, lambda k: (round(-k[1], 3), round(-k[0], 3)))
        main, n4 = mirror_residual(cfg, 45.0, lambda k: (k[1], k[0]))
        sym[cfg].update({"WD45_antidiagonal_mirror_mean_abs_dVs": round(anti, 4), "WD45_maindiagonal_mirror_mean_abs_dVs": round(main, 4)})
        check(c, f"WD45_symmetry_plane_is_y_eq_minus_x_{cfg}", anti < 0.2 and main > 2 * anti, antidiagonal=round(anti, 4), maindiagonal=round(main, 4),
              note="so in the CSV frame WD rotates the wind from +x TOWARD -y; Figure 3 of the data paper draws it toward +y (QUESTIONS.md)")
    # legacy workbook: velocity ratios normalised by U at the same height, U(0.02) = 2.434 from AF_caseC.csv
    wb = xls(os.path.join(folder, "LF-caseC.xls"))
    U002 = float(afl[np.isclose(afl.z, 0.02)].U.iloc[0])
    mx, n, implied = 0.0, 0, []
    for wd, sn in ((0.0, "Results(0_deg)"), (22.5, "Results(22.5_deg)"), (45.0, "Results(45_deg)")):
        sh = wb.sheet_by_name(sn)
        for r in range(2, sh.nrows):
            if sh.cell_value(r, 1) == "":
                continue
            no = int(sh.cell_value(r, 1))
            for col, cfg in ((5, "0D"), (6, "1D"), (7, "2D")):
                v = pts[(pts.point_id == no) & (pts.config == cfg) & (pts.wind_direction_deg == wd)].Vs.iloc[0]
                ratio = float(sh.cell_value(r, col))
                mx = max(mx, abs(ratio * U002 - v))
                implied.append(v / ratio)
                n += 1
    check(c, "legacy_workbook_ratio_x_U(0.02)_equals_csv_Vs_to_0.3pct", mx < 0.01 and n == 1080, rows_compared=n, max_abs_diff=mx, U_at_0_02=U002,
          implied_reference_speed_min=round(min(implied), 4), implied_reference_speed_max=round(max(implied), 4),
          note=f"the legacy ratios are NOT exactly Vs / {U002}: Vs / ratio spans {min(implied):.4f}-{max(implied):.4f} m/s, i.e. the workbook normalised each value by a slightly different reference (plausibly the reference speed measured during that run). Agreement is within 0.3 % of Vs; do not use the ratios to recover a third decimal of Vs. The CSV's 2-dp Vs is the released value.")
    UD = float(afl[np.isclose(afl.z, 0.20)].U.iloc[0])
    fit1 = log_law_fit(afl.z, afl.U, 0.02, 0.40)
    fit2 = log_law_fit(afl.z, afl.U, 0.01, 0.40)
    for f in (fit1, fit2):
        f["error_at_H_rel"] = round(log_law_U(f, 0.20) / UD - 1, 4)
        f["error_at_z_0.02_rel"] = round(log_law_U(f, 0.02) / U002 - 1, 4)
    inflow = {"U_H_m_s": UD, "U_H_stated_m_s": CASES[c]["U_H_stated"], "H_m": 0.20, "U_at_measurement_height_m_s": U002, "measurement_height_m": 0.02,
              "turbulence_intensity_at_H": round(float(np.sqrt(afl[np.isclose(afl.z, 0.20)].uu.iloc[0])) / UD, 4),
              "log_law": fit1, "log_law_alt_window": fit2, "power_law": power_law_fit(afl.z, afl.U, 0.02, 0.40),
              "method": f"least squares, kappa = {KAPPA}; two windows because every point is scored at z = 0.02 m, the lowest tabulated height but one"}
    check(c, "U_H_from_profile_matches_stated", abs(UD - CASES[c]["U_H_stated"]) < 0.02, U_H_profile=UD, U_H_stated=CASES[c]["U_H_stated"])
    frame = {"origin": "array centre on the ground plane (centre of the middle block)", "x": "+x streamwise at WD = 0 (measured: see checks WD0_flow_is_along_x)",
             "y": "+y lateral", "z": "+z up; every point at z = 0.02 = 0.1 D",
             "wind_direction_rotation": "In this frame WD rotates the wind from +x TOWARD -y (measured: the WD = 45 field is mirror-symmetric about y = -x at the experiment's repeatability and not about y = +x). flow_dir = (cos WD, -sin WD). Figure 3 of the data paper draws the opposite sense — QUESTIONS.md Q1.",
             "length_scale": "model metres (the source states no model:full scale ratio)"}
    transform = {"coordinate_scale": 1.0, "lateral_sign": 1, "origin_shift_m": [0, 0, 0], "note": "no numeric change; CB text to config, trailing empty column dropped"}
    return pts, afl, geo, inflow, frame, transform, sym


# --------------------------------------------------------------------------------------------- Case D

def boxes_D(stl_path):
    tris = read_ascii_stl(stl_path)
    boxes = []
    for shell in shells_from_tris(tris):
        p = np.array([v for t in shell for v in t])
        lo, hi = p.min(axis=0), p.max(axis=0)
        corners = {tuple(np.round([x, y, z], 6)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])}
        bad = [v for v in p if tuple(np.round(v, 6)) not in corners]
        if bad:
            raise SystemExit(f"Case D shell is not a box: {len(bad)} off-corner vertices near {bad[0]}")
        boxes.append({"min": [round(float(v), 6) for v in lo], "max": [round(float(v), 6) for v in hi]})
    boxes.sort(key=lambda b: (b["min"][0], b["min"][1]))
    return boxes, tris


def build_D(prov):
    c = "D"
    zd = os.path.join(SRC, "zenodo_caseD")
    rst, rss, af, stl, lf = (os.path.join(zd, n) for n in ("RS-T_caseD.csv", "RS-S_caseD.csv", "AF_caseD.csv", "BD_caseD.stl", "LF_caseD.xls"))
    prov[c] = [rst, rss, af, stl, lf, os.path.join(zd, "readme_caseD.md"), os.path.join(zd, "MP_caseD.png")]
    header_t, rows_t = read_csv_rows(rst)
    header_s, rows_s = read_csv_rows(rss)
    log(f"[D] RS-T_caseD.csv header (bare): {header_t}; RS-S_caseD.csv header (bare): {header_s} (the published z header is the FULL-WIDTH character U+FF5A 'ｚ[m]', folded to 'z'); unmeasured = -999.9")
    it = {h: i for i, h in enumerate(header_t)}
    out = []
    for r in rows_t:
        g = lambda n: num(r[it[n]])
        out.append(row(case_id=c, instrument="thermistor", point_id=int(g("No.")), wind_direction_deg=g("WD"), x=g("x"), y=g("y"), z=g("z"), Vs=g("Vs")))
    log("[D] transform (thermistor): -999.9 -> NaN; coordinates kept (the Zenodo CSV is already in metres; the LF workbook's are millimetres)")
    # split fibre: variances from the LF workbook (the original quantity, 3-4 significant digits); the CSV publishes rms rounded to 4 dp
    wb = xls(lf)
    s = wb.sheet_by_name("Results (Exp_S)")
    var = {}
    for r in range(3, s.nrows):
        if s.cell_value(r, 1) != "":
            var[int(s.cell_value(r, 0))] = (float(s.cell_value(r, 5)), float(s.cell_value(r, 7)), float(s.cell_value(r, 9)), float(s.cell_value(r, 10)), float(s.cell_value(r, 12)))
    is_ = {h: i for i, h in enumerate(header_s)}
    uvw = {}
    for r in range(3, s.nrows):
        if s.cell_value(r, 1) != "":
            uvw[int(s.cell_value(r, 0))] = (float(s.cell_value(r, 4)), float(s.cell_value(r, 6)), float(s.cell_value(r, 8)))
    mag_err, mx_rms, mx_uvw, mx_k, n_s = 0.0, 0.0, 0.0, 0.0, 0
    for r in rows_s:
        g = lambda n: num(r[is_[n]])
        if math.isnan(g("U")):
            continue  # -999.9 rows: this point was not measured with the split fibre (coordinates are in the thermistor table)
        no = int(g("No."))
        uu, vv, ww, mag_wb, k_wb = var[no]
        U, V, W = uvw[no]
        mx_uvw = max(mx_uvw, abs(g("U") - U), abs(g("V") - V), abs(g("W") - W))
        mx_rms = max(mx_rms, abs(g("u_rms") ** 2 - uu), abs(g("v_rms") ** 2 - vv), abs(g("w_rms") ** 2 - ww))
        mx_k = max(mx_k, abs(g("k") - k_wb))
        mag_err = max(mag_err, abs(mag_wb - math.sqrt(U * U + V * V + W * W)), abs(g("Vs") - math.sqrt(U * U + V * V + W * W)))
        n_s += 1
        out.append(row(case_id=c, instrument="split_fibre", point_id=no, wind_direction_deg=0.0, x=g("x"), y=g("y"), z=g("z"),
                       U=U, V=V, W=W, uu=uu, vv=vv, ww=ww, k=k_wb))
    log(f"[D] transform (split fibre): values taken from LF_caseD.xls 'Results (Exp_S)' (U, V, W, variances and k at full precision; k = (uu+vv+ww)/2 there exactly) and cross-checked against RS-S_caseD.csv: U/V/W max |diff| {mx_uvw:.1e}, rms^2 vs variance max |diff| {mx_rms:.1e} (the CSV rounds rms to 4 dp), k max |diff| {mx_k:.1e} (the CSV rounds k to 3 dp). The CSV's 'Vs' column and the workbook's 'Scalar Vel.' are |mean velocity vector| = sqrt(U^2+V^2+W^2) (max |diff| {mag_err:.1e}), NOT a thermistor reading: DROPPED rather than put under Vs. The 45 -999.9 rows (points not measured by the split fibre) are omitted")
    check(c, "split_fibre_csv_agrees_with_workbook", mx_uvw < 1e-9 and mx_rms < 6e-4 and mx_k < 6e-4 and n_s == 33, rows=n_s, max_abs_diff_UVW=mx_uvw, max_abs_diff_rms2_vs_variance=mx_rms, max_abs_diff_k=mx_k)
    check(c, "split_fibre_Vs_column_is_the_vector_magnitude", mag_err < 1e-3, max_abs_diff=mag_err, note="so it is not a thermistor reading and is dropped; thermistor Vs at the same 33 points is in the thermistor rows")
    pts = pd.DataFrame(out, columns=POINT_COLUMNS)

    h, ar = read_csv_rows(af)
    ai = {n: i for i, n in enumerate(h)}
    afl = pd.DataFrame([{"case_id": c, "z": num(r[ai["z"]]), "U": num(r[ai["U"]]), "uu": math.nan, "vv": math.nan, "ww": math.nan, "k": num(r[ai["k"]])} for r in ar])
    log("[D] approach flow: AF_caseD.csv (Zenodo), 13 heights in metres, U and k; the LF workbook holds the same profile unrounded (checked)")

    boxes, raw_tris = boxes_D(stl)
    raw = stl_stats(raw_tris)
    geo = [("default", boxes, f"rebuilt from the {len(boxes)} closed shells of BD_caseD.stl (Zenodo; {raw['triangles']} raw facets incl. duplicates, every roof wound inward, signed volume {raw['signed_volume']}), each reduced to its axis-aligned box")]
    log(f"[D] geometry: BD_caseD.stl -> {len(boxes)} boxes; raw STL stats {raw}")

    # ---- checks
    T = pts[pts.instrument == "thermistor"]
    S = pts[pts.instrument == "split_fibre"]
    check(c, "thermistor_rows_78_points_x_3_directions", len(T) == 234 and T.point_id.nunique() == 78, rows=len(T), points=int(T.point_id.nunique()))
    meas = T.groupby("wind_direction_deg").Vs.apply(lambda v: int(v.notna().sum())).to_dict()
    check(c, "thermistor_66_measured_per_direction", all(v == 66 for v in meas.values()), measured_per_direction=meas, note="MP_caseD.png: 12 points in the band around the tower are marked unmeasured")
    unm = sorted(T[(T.wind_direction_deg == 0.0) & T.Vs.isna()].point_id)
    check(c, "unmeasured_thermistor_points_are_the_tower_band", unm == [26, 27, 28, 29, 32, 33, 36, 37, 40, 41, 42, 43], unmeasured_ids=unm)
    check(c, "split_fibre_33_points_all_measured", len(S) == 33 and not S[["U", "V", "W", "uu", "vv", "ww", "k"]].isna().any().any(), rows=len(S))
    kerr = float(np.max(np.abs(S.k - 0.5 * (S.uu + S.vv + S.ww))))
    check(c, "k_equals_half_sum_of_variances", kerr < 1e-9, max_abs_error=kerr)
    check(c, "split_fibre_points_are_a_subset_of_the_thermistor_points", set(S.point_id) <= set(T.point_id))
    xyT = T.drop_duplicates("point_id").set_index("point_id")[["x", "y", "z"]]
    xyS = S.set_index("point_id")[["x", "y", "z"]]
    check(c, "shared_points_have_identical_coordinates", bool(np.allclose(xyT.loc[xyS.index].to_numpy(), xyS.to_numpy())))
    check(c, "all_points_at_z_0.005", bool(np.allclose(pts.z, 0.005)))
    xyz = T.drop_duplicates("point_id")[["x", "y", "z"]].to_numpy()
    inside = points_in_boxes(xyz, boxes)
    check(c, "no_sensor_inside_building", int(inside.sum()) == 0, inside=int(inside.sum()), points=len(xyz))
    for name, dx, dy in (("shift_x_0.05", 0.05, 0.0), ("swap_xy", None, None)):
        q = np.column_stack([xyz[:, 1], xyz[:, 0], xyz[:, 2]]) if dx is None else xyz + np.array([dx, dy, 0])
        ctrl = points_in_boxes(q, boxes)
        check(c, f"control_{name}_is_detected_inside", int(ctrl.sum()) > 0, inside_after_transform=int(ctrl.sum()))
    # geometry facts vs the readme / paper
    heights = sorted({round(b["max"][2] - b["min"][2], 6) for b in boxes})
    tower = [b for b in boxes if b["max"][2] > 0.1]
    lo = [min(b["min"][i] for b in boxes) for i in range(3)]
    hi = [max(b["max"][i] for b in boxes) for i in range(3)]
    check(c, "geometry_matches_readme", heights == [0.025, 0.25] and len(tower) == 1 and len(boxes) == 83
          and np.allclose(tower[0]["min"], [-0.03125, -0.03125, 0]) and np.allclose(tower[0]["max"], [0.03125, 0.03125, 0.25]),
          block_heights=heights, boxes=len(boxes), tower=tower, array_bbox=[lo, hi],
          note="readme: tower 0.0625 x 0.0625 x 0.25 m, blocks 0.1 x 0.1 x 0.025 m; STL and point table share one frame (origin = tower centre)")
    vol = sum((b["max"][0] - b["min"][0]) * (b["max"][1] - b["min"][1]) * (b["max"][2] - b["min"][2]) for b in boxes)
    check(c, "rebuilt_volume_equals_analytic", abs(vol - (0.0625 ** 2 * 0.25 + 82 * 0.1 * 0.1 * 0.025)) < 1e-9, volume_m3=vol)
    # frame: WD = 0 along +x. The 0 deg thermistor field is EXACTLY y-mirror symmetric (33 pairs), 22.5/45 are not
    m0 = T[T.wind_direction_deg == 0.0].dropna(subset=["Vs"]).set_index(["x", "y"]).Vs
    def mirror_stats(wd):
        s = T[T.wind_direction_deg == wd].dropna(subset=["Vs"])
        m = {(round(x, 5), round(y, 5)): v for x, y, v in s[["x", "y", "Vs"]].to_numpy()}
        d = [abs(v - m[(k[0], round(-k[1], 5))]) for k, v in m.items() if (k[0], round(-k[1], 5)) in m]
        return {"pairs": len(d), "max_abs_dVs": round(max(d), 4), "mean_abs_dVs": round(float(np.mean(d)), 4)}
    ms = {wd: mirror_stats(wd) for wd in (0.0, 22.5, 45.0)}
    check(c, "WD0_thermistor_field_exactly_y_mirror_symmetric", ms[0.0]["max_abs_dVs"] == 0.0 and ms[22.5]["max_abs_dVs"] > 0.5 and ms[45.0]["max_abs_dVs"] > 0.5, **{f"WD{k}": v for k, v in ms.items()},
          note="the 0 deg half was measured and mirrored: 33 independent values; 22.5 and 45 deg are not symmetric, and the y-symmetric array cannot fix their rotation sense (QUESTIONS.md Q2)")
    up = S[S.x < -0.03125]
    check(c, "WD0_blows_toward_plus_x", bool((S.U > 0).sum() > 15) and bool((up.U < 0).any()), U_positive=int((S.U > 0).sum()), U_negative_upwind_of_tower=int((up.U < 0).sum()),
          note="split-fibre U > 0 at the stream-like points, < 0 in the windward horseshoe in front of the tower face at x = -0.03125")
    flank = S[(np.isclose(S.y, 0.1125))]
    up_, dn_ = flank[flank.x < 0], flank[flank.x > 0]
    check(c, "lateral_sign_V_diverges_upstream_and_converges_downstream_on_the_plus_y_side", bool((up_.V > 0).all()) and bool((dn_.V < 0).all()) and len(up_) > 0 and len(dn_) > 0,
          points=flank[["x", "y", "V"]].to_dict("records"), note="on the +y side of the tower the flow is pushed toward +y ahead of it (V > 0 at x < 0) and returns toward the centreline behind it (V < 0 at x > 0): V positive toward +y, the same convention as Case A and as Case B after its flip")
    # workbook cross-checks
    t = wb.sheet_by_name("Results (Exp_T)")
    mx, n = 0.0, 0
    for r in range(5, t.nrows):
        no = int(t.cell_value(r, 0))
        for col, wd in ((4, 0.0), (5, 22.5), (6, 45.0)):
            v = T[(T.point_id == no) & (T.wind_direction_deg == wd)].Vs.iloc[0]
            w = t.cell_value(r, col)
            if w == "-":
                mx = max(mx, 0 if math.isnan(v) else math.inf)
            else:
                mx = max(mx, abs(float(w) - v))
            n += 1
        mx = max(mx, abs(float(t.cell_value(r, 1)) / 1000 - xyT.loc[no].x), abs(float(t.cell_value(r, 2)) / 1000 - xyT.loc[no].y))
    check(c, "legacy_workbook_agrees_with_zenodo_csv", mx < 1e-9, cells_compared=n, max_abs_diff=mx, note="LF_caseD.xls (mm, '-') vs RS-T_caseD.csv (m, -999.9)")
    inf = wb.sheet_by_name("Inflow")
    wz = [(float(inf.cell_value(r, 1)) / 1000, float(inf.cell_value(r, 3)), float(inf.cell_value(r, 5))) for r in range(3, inf.nrows) if isinstance(inf.cell_value(r, 1), float)]
    mxa = max(max(abs(z - afl.z.iloc[i]), abs(U - afl.U.iloc[i]), abs(k - afl.k.iloc[i])) for i, (z, U, k) in enumerate(wz))
    check(c, "approach_flow_csv_matches_workbook_to_3dp", mxa < 6e-4, rows=len(wz), max_abs_diff=mxa)
    UH = interp_log(afl.z, afl.U, 0.25)
    U005 = float(afl[np.isclose(afl.z, 0.005)].U.iloc[0])
    fit1 = log_law_fit(afl.z, afl.U, 0.005, 0.5)
    fit2 = log_law_fit(afl.z, afl.U, 0.02, 0.5)
    for f in (fit1, fit2):
        f["error_at_H_rel"] = round(log_law_U(f, 0.25) / UH - 1, 4)
        f["error_at_z_0.005_rel"] = round(log_law_U(f, 0.005) / U005 - 1, 4)
        f["inlet_k_m2_s2_atmBoundaryLayer"] = round(f["u_star_m_s"] ** 2 / math.sqrt(0.09), 4)
    inflow = {"U_H_m_s": round(UH, 4), "U_H_stated_m_s": CASES[c]["U_H_stated"], "H_m": 0.25, "U_at_measurement_height_m_s": U005, "measurement_height_m": 0.005,
              "k_at_measurement_height_m2_s2": float(afl[np.isclose(afl.z, 0.005)].k.iloc[0]), "k_at_H_m2_s2": round(interp_log(afl.z, afl.k, 0.25), 4),
              "log_law": fit1, "log_law_alt_window": fit2, "power_law": power_law_fit(afl.z, afl.U, 0.02, 0.5),
              "method": f"least squares, kappa = {KAPPA}; two windows because the measurement plane z/H = 0.02 lies below the 0.02..2H window used for A/B"}
    check(c, "U_H_from_profile_matches_stated", abs(UH - CASES[c]["U_H_stated"]) < 0.05, U_H_profile=UH, U_H_stated=CASES[c]["U_H_stated"])
    frame = {"origin": "tower centre on the ground plane (the array's bounding box is centred on it)", "x": "+x streamwise at WD = 0 (measured: split-fibre U, exact y-mirror symmetry of the 0 deg field)",
             "y": "+y lateral", "z": "+z up; every point at z = 0.005 = 0.02 H",
             "wind_direction_rotation": "UNVERIFIED for 22.5 and 45 deg: the array is exactly y-mirror symmetric so the data cannot fix the sense; the scoping read of Figure 4 of the data paper says +x toward +y, i.e. flow_dir = (cos WD, +sin WD) — the OPPOSITE of what Case C's data show for Case C. QUESTIONS.md Q2.",
             "length_scale": "model metres; scale 1:400 (readme), H = 0.25 m = 100 m full scale"}
    transform = {"coordinate_scale": 1.0, "lateral_sign": 1, "origin_shift_m": [0, 0, 0],
                 "note": "Zenodo CSVs are in metres already; -999.9 -> NaN; split-fibre |U| column dropped; variances from the workbook"}
    return pts, afl, geo, inflow, frame, transform, {"raw_stl_stats": raw, "thermistor_mirror_symmetry": ms}


# --------------------------------------------------------------------------------------------- Case E

def mesh_3dm(path, state):
    import rhino3dm
    f = rhino3dm.File3dm.Read(path)
    layers = {l.Index: l.Name for l in f.Layers}
    wanted = {"buildings"} if state == "bc" else {"buildings", "buildings_new_construction"}
    tris = []
    for o in f.Objects:
        if layers.get(o.Attributes.LayerIndex) not in wanted:
            continue
        m = o.Geometry
        if not isinstance(m, rhino3dm.Mesh):
            continue
        vs = [(m.Vertices[i].X, m.Vertices[i].Y, m.Vertices[i].Z) for i in range(len(m.Vertices))]
        for i in range(len(m.Faces)):
            face = m.Faces[i]
            a, b, cc, d = face[0], face[1], face[2], face[3]
            tris.append((vs[a], vs[b], vs[cc]))
            if d != cc:
                tris.append((vs[a], vs[cc], vs[d]))
    return tris


def build_E(prov):
    c = "E"
    ze = os.path.join(SRC, "zenodo_caseE")
    lf, rs, af, stl = (os.path.join(ze, n) for n in ("LF_caseE.xls", "RS_caseE.csv", "AF_caseE.csv", "BD_caseE.stl"))
    dm = os.path.join(REPO, CASES[c]["folder"], "case-e.3dm")
    prov[c] = [lf, rs, af, stl, os.path.join(ze, "readme_caseE.md"), os.path.join(ze, "MP_caseE.png"), dm]
    wb = xls(lf)
    g = wb.sheet_by_name("Geometry&Points")
    pts_xy = {}
    for r in range(g.nrows):
        no = num(g.cell_value(r, 1))
        if not math.isnan(no) and not math.isnan(num(g.cell_value(r, 2))):
            pts_xy[int(no)] = (num(g.cell_value(r, 2)), num(g.cell_value(r, 3)))
    out = []
    for state, sheet in (("bc", "Results (Before Construction)"), ("ac", "Results (After Construction)")):
        sh = wb.sheet_by_name(sheet)
        for r in range(sh.nrows):
            no = num(sh.cell_value(r, 1))
            if math.isnan(no) or int(no) not in pts_xy:
                continue
            x, y = pts_xy[int(no)]
            for i, name in enumerate(COMPASS):
                out.append(row(case_id=c, instrument="thermistor", config=state, point_id=int(no), wind_direction=name, wind_direction_deg=i * 22.5,
                               x=x, y=y, z=2.0, velocity_ratio=num(sh.cell_value(r, 2 + i))))
    log("[E] source: LF_caseE.xls (Zenodo; byte-identical cells to the clone's LF_caseE.xls) — it carries the velocity ratios at full precision, while RS_caseE.csv rounds them to 2 dp (checked below). Coordinates: 'Geometry&Points' sheet, 'm in actual scale, origin: centre of the reproducing area'; z = 2.0 m full scale (0.008 m model) from the readme")
    log("[E] transform: wide sheets (80 rows x 16 compass columns x 2 states) -> long rows; compass name -> wind_direction_deg = 22.5 * index (N = 0, clockwise); no numeric change")
    pts = pd.DataFrame(out, columns=POINT_COLUMNS)

    ZR, UR = CASES[c]["ZR"], CASES[c]["UR"]
    inf = wb.sheet_by_name("Inflow")
    afl = pd.DataFrame([{"case_id": c, "z": float(inf.cell_value(r, 1)) * ZR, "U": float(inf.cell_value(r, 2)) * UR, "uu": math.nan, "vv": math.nan, "ww": math.nan,
                         "k": float(inf.cell_value(r, 3)) * UR ** 2} for r in range(2, inf.nrows) if isinstance(inf.cell_value(r, 1), float)])
    log(f"[E] approach flow: 'Inflow' sheet z/ZR, U/UR, k/UR^2 de-normalised with ZR = {ZR} m (1 m model), UR = {UR} m/s (sheet notes); full-scale metres")

    # geometry: official STL is model scale (1:250) after construction; the clone's 3dm is full scale with bc/ac on layers
    off = read_ascii_stl(stl)
    off_full = [tuple(tuple(v * CASES[c]["scale"] for v in p) for p in t) for t in off]
    s_off = stl_stats(off_full)
    log(f"[E] geometry: BD_caseE.stl (Zenodo, after construction) is MODEL scale — bbox z max 0.24 m = 60 m / 250; scaled x {CASES[c]['scale']} to full-scale metres; stats {s_off}")
    ac3, sh_ac, fl_ac = orient_outward(mesh_3dm(dm, "ac"))
    bc3, sh_bc, fl_bc = orient_outward(mesh_3dm(dm, "bc"))
    s_ac, s_bc = stl_stats(ac3), stl_stats(bc3)
    log(f"[E] geometry (Eddy3D-derived): case-e.3dm layers 'buildings' (+ 'buildings_new_construction'): ac {s_ac}, {fl_ac}/{sh_ac} shells flipped outward; bc {s_bc}, {fl_bc}/{sh_bc} flipped")
    geo = [("ac", None, off_full, f"official BD_caseE.stl (Zenodo) scaled x{CASES[c]['scale']} from model to full-scale metres; {s_off['triangles']} triangles, {s_off['edges_boundary']} boundary edges (not watertight as published)"),
           ("ac_3dm", None, ac3, "Eddy3D-side reconstruction from case-e.3dm, layers 'buildings' + 'buildings_new_construction', shells oriented outward"),
           ("bc_3dm", None, bc3, "Eddy3D-side reconstruction of the BEFORE-construction state from case-e.3dm, layer 'buildings' only (the sites of A, B, C are empty on that layer); no published source exists for this state")]

    # ---- checks
    check(c, "row_count_80_x_16_x_2", len(pts) == 2560 and pts.point_id.nunique() == 80, rows=len(pts), points=int(pts.point_id.nunique()))
    check(c, "no_sentinels_or_nan", not pts[["x", "y", "z", "velocity_ratio"]].isna().any().any())
    h, rr = read_csv_rows(rs)
    ii = {n: i for i, n in enumerate(h)}
    key = {(int(r["point_id"]), r["config"], r["wind_direction"]): r["velocity_ratio"] for r in pts.to_dict("records")}
    mx = max(abs(float(r[ii["Velocity_Ratio"]]) - key[(int(float(r[ii["No."]])), r[ii["case"]], r[ii["Wind_direction"]])]) for r in rr)
    mxc = max(max(abs(float(r[ii["x"]]) - pts_xy[int(float(r[ii["No."]]))][0]), abs(float(r[ii["y"]]) - pts_xy[int(float(r[ii["No."]]))][1]), abs(float(r[ii["z"]]) - 2.0)) for r in rr)
    check(c, "zenodo_csv_is_the_workbook_rounded_to_2dp", mx <= 0.005 + 1e-9 and mxc == 0 and len(rr) == 2560, max_abs_diff_ratio=mx, max_abs_diff_xyz=mxc, csv_rows=len(rr))
    # quantisation: every ratio is an integer multiple of one quantum q
    v = pts.velocity_ratio.to_numpy()
    vmin = v[v > 0].min()
    q = None
    for kq in range(1, 40):
        cand = vmin / kq
        if np.max(np.abs(v / cand - np.round(v / cand))) < 1e-6:
            q = cand
            break
    levels = int(len(np.unique(np.round(v / q))))
    U_ref = 0.01 * UR / q
    check(c, "velocity_ratio_is_quantised", q is not None and levels < 80, quantum=q, distinct_levels=levels, smallest_value=float(vmin), smallest_in_quanta=int(round(vmin / q)),
          note="the published ratios are U/UR rounded to 0.01 then re-normalised by UR/U(15.9 m); the data's own resolution is +/- q/2")
    U_ref_interp = interp_log(afl.z, afl.U, CASES[c]["z_ref"])
    check(c, "U_ref_from_quantum_agrees_with_profile_at_15.9m", abs(U_ref / U_ref_interp - 1) < 0.02, U_ref_from_quantum=U_ref, U_ref_log_interp=U_ref_interp, U_ref_paper="4.0 (section 3.5: 'the inflow wind velocity at that height (4.0 m/s)')")
    h2, ar = read_csv_rows(af)
    a2 = {n: i for i, n in enumerate(h2)}
    mxa = max(max(abs(num(r[a2["z"]]) - afl.z.iloc[i]), abs(num(r[a2["U"]]) - afl.U.iloc[i]), abs(num(r[a2["k"]]) - afl.k.iloc[i])) for i, r in enumerate(ar))
    check(c, "zenodo_AF_csv_matches_denormalised_workbook_profile", mxa < 6e-4 and len(ar) == len(afl), rows=len(ar), max_abs_diff=mxa)
    # frame & geometry: every point in open space, against BOTH geometries; control rotation must put points inside
    ids = pts.drop_duplicates("point_id").point_id.to_numpy()
    xy = pts.drop_duplicates("point_id")[["x", "y"]].to_numpy()
    known = {}
    for name, tris in (("official_stl_x250", off_full), ("3dm_ac", ac3), ("3dm_bc", bc3)):
        hit = points_under_roof(xy, 2.0, tris)
        V = np.array([p for t in tris for p in t])
        dmin = [float(np.hypot(V[:, 0] - x, V[:, 1] - y).min()) for x, y in xy]
        inside_ids = [int(i) for i in ids[hit]]
        extra = {"inside": int(hit.sum()), "points": len(xy), "inside_point_ids": inside_ids, "nearest_vertex_min_m": round(min(dmin), 3), "nearest_vertex_median_m": round(float(np.median(dmin)), 3)}
        if name == "official_stl_x250":
            # KNOWN discrepancy: point 50 at (-45.5, -45.0) lies 0.17 m inside a wall of the official STL (roof 6.75 m) and 2.06 m clear in the 3dm
            check(c, f"no_sensor_inside_building_{name}", int(hit.sum()) == 0, warn=True, **extra,
                  note="the official STL and the 3dm are different triangulations of the same district; where they disagree by a metre a street-edge sensor can fall inside one of them. Listed in QUESTIONS.md Q3 and manifest known_issues")
            known["official_stl_points_inside"] = {"point_ids": inside_ids, "nearest_vertex_m": [round(dmin[list(ids).index(i)], 3) for i in inside_ids]}
        else:
            check(c, f"no_sensor_inside_building_{name}", int(hit.sum()) == 0, **extra)
    ctrl = points_under_roof(rot_xy(xy, 10.0), 2.0, off_full)
    check(c, "control_points_rotated_10deg_land_inside_buildings", int(ctrl.sum()) >= 5, inside_after_rotation=int(ctrl.sum()), note="proves the check can resolve a frame error")
    check(c, "official_stl_x250_matches_3dm_extent", all(abs(a - b) < 6.0 for a, b in zip(s_off["bbox_min"][:2] + s_off["bbox_max"][:2], s_ac["bbox_min"][:2] + s_ac["bbox_max"][:2])) and abs(s_off["bbox_max"][2] - 60.0) < 1e-6,
          official_bbox=[s_off["bbox_min"], s_off["bbox_max"]], threedm_bbox=[s_ac["bbox_min"], s_ac["bbox_max"]], note="same origin and axes to a few metres at the district edge; the two files are different triangulations of the same block")
    tall = sorted(stl_stats(sh)["bbox_max"][2] for sh in shells_from_tris(off_full, tol=1e-4))[-3:]
    check(c, "new_buildings_60_18_18_present_in_official_stl", abs(tall[-1] - 60.0) < 1e-6, tallest_three_m=tall, note="A = 60 m; B and C are 18 m among many 18-30 m roofs")
    bb = [pts.x.min(), pts.x.max(), pts.y.min(), pts.y.max()]
    check(c, "extents_sane", bb[0] > -200 and bb[1] < 200 and bb[2] > -200 and bb[3] < 200 and bool(np.allclose(pts.z, 2.0)), bbox=bb, note="points within the 400 m turntable, MP_caseE.png")
    delta = pts.pivot_table(index=["point_id", "wind_direction"], columns="config", values="velocity_ratio")
    d = (delta["ac"] - delta["bc"])
    bydir = d.groupby(level="wind_direction").apply(lambda s: float(np.mean(np.abs(s)))).sort_values(ascending=False)
    check(c, "construction_signal_present", abs(float(d.mean())) > 0.05, mean_ac_minus_bc=float(d.mean()), sd=float(d.std()), largest_mean_abs_delta_direction=bydir.index[0], largest=float(bydir.iloc[0]), smallest_direction=bydir.index[-1], smallest=float(bydir.iloc[-1]))
    inflow = {"U_ref_m_s": round(U_ref, 4), "z_ref_m": CASES[c]["z_ref"], "U_ref_basis": "all 2560 ratios are integer multiples of one quantum q; U_ref = 0.01 UR / q (the sheet re-normalised U/UR, itself quantised at 0.01, by UR/U_ref); log-interpolation of the profile gives the value beside it",
              "U_ref_log_interp_m_s": round(U_ref_interp, 4), "quantum": q, "ZR_m": ZR, "UR_m_s": UR,
              "log_law": {**log_law_fit(afl.z, afl.U, 1.25, 75.0), "note": "does not fit — see rms_residual_rel; a tabulated inlet is the honest choice"},
              "power_law": power_law_fit(afl.z, afl.U, 1.25, 60.0), "power_law_whole_profile": power_law_fit(afl.z, afl.U, 1.25, 250.0),
              "epsilon_note": "the sheet defines epsilon(z) = Pk(z) = Cmu^0.5 k(z) dU/dz with Cmu = 0.09"}
    frame = {"origin": "centre of the reproduced area, ground plane ('Geometry&Points' sheet)", "x": "+x EAST (compass rose in MP_caseE.png)", "y": "+y NORTH",
             "z": "+z up; every point at z = 2.0 m", "wind_direction_rotation": "meteorological FROM-direction: N = 0 blows toward -y, E = 90 toward -x; flow_dir = (-sin WD, -cos WD). The geographic frame is kept because the district is real and both the points and the STL are published in it; the 'x along the wind' convention of A-D does not apply.",
             "length_scale": "FULL-scale metres (model 1:250); the official STL is model scale and is scaled x250 here"}
    transform = {"coordinate_scale": 1.0, "lateral_sign": 1, "origin_shift_m": [0, 0, 0], "geometry_scale": CASES[c]["scale"],
                 "note": "points unchanged (workbook values at full precision); STL x250; the 3dm-derived STLs are reoriented outward"}
    return pts, afl, geo, inflow, frame, transform, {"delta_by_direction": {k: round(v, 4) for k, v in bydir.items()}, "known_issues": known}


# --------------------------------------------------------------------------------------------- directions

def directions_for(case, pts, frame_note):
    rows = []
    for (cfg, inst, wd, wname), g in pts.groupby(["config", "instrument", "wind_direction_deg", "wind_direction"], sort=True):
        q = {"A": "U", "B": "U", "C": "Vs", "D": ("Vs" if inst == "thermistor" else "U"), "E": "velocity_ratio"}[case]
        r = math.radians(wd)
        if case in ("A", "B"):
            fx, fy, basis, status = 1.0, 0.0, "definition: +x streamwise (MP drawings; checks lateral_sign_*)", "settled"
        elif case == "C":
            fx, fy = math.cos(r), -math.sin(r)
            basis = "measured: WD0 field y-mirror symmetric and faster upwind; WD45 field mirror-symmetric about y = -x, not y = +x (checks WD45_symmetry_plane_*)" if wd else "measured: y-mirror symmetry + windward band faster (checks WD0_flow_is_along_x_*)"
            status = "settled (from the data; disagrees with Figure 3 of the data paper — QUESTIONS.md Q1)" if wd else "settled"
        elif case == "D":
            fx, fy = math.cos(r), math.sin(r)
            if wd == 0:
                basis, status = "measured: split-fibre U > 0, exact y-mirror symmetry of the 0 deg field", "settled"
            elif wd == 22.5:
                # The solved Eddy3D field (2026-10-15) scores R 0.80 in this sense and 0.40 in its y mirror.
                basis = ("read from Figure 4 of the data paper; the y-symmetric array makes the sense undecidable from "
                         "the data alone, and the solved Eddy3D field corroborates it (R 0.80 in this sense, 0.40 mirrored)")
                status = "corroborated by a solved field — QUESTIONS.md Q2"
            else:
                basis = "read from Figure 4 of the data paper (scoping); the y-symmetric array makes the sense undecidable from the data"
                status = "unverified — QUESTIONS.md Q2"
        else:
            fx, fy, basis, status = -math.sin(r), -math.cos(r), "definition: compass FROM-direction, +y north (MP_caseE.png rose); checks no_sensor_inside_building_* + the rotation control", "settled"
        rows.append({"case_id": case, "config": cfg, "instrument": inst, "wind_direction_deg": wd, "wind_direction": wname,
                     "flow_dir_x": round(fx, 9) + 0.0, "flow_dir_y": round(fy, 9) + 0.0, "rows": int(len(g)), "measured": int(g[q].notna().sum()), "sense_basis": basis, "status": status})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------- writers

def fmt(v):
    if isinstance(v, str):
        return v
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    return format(float(v), ".10g")


def write_csv(path, df: pd.DataFrame):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(list(df.columns))
        for rec in df.itertuples(index=False):
            w.writerow([fmt(v) for v in rec])


def write_parquet(path, df: pd.DataFrame, units: dict, extra_meta: dict | None = None):
    import pyarrow as pa
    import pyarrow.parquet as pq
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df = df.copy()
    for col in df.columns:
        if col in TEXT_COLUMNS or col in ("sense_basis", "status"):
            df[col] = df[col].astype("string")
        elif col in INT_COLUMNS or col in ("rows", "measured"):
            df[col] = df[col].astype("int64")
        else:
            df[col] = df[col].astype("float64")
    table = pa.Table.from_pandas(df, preserve_index=False)
    meta = {b"units": json.dumps({k: units[k]["unit"] for k in df.columns if k in units}).encode(),
            b"column_meaning": json.dumps({k: units[k]["meaning"] for k in df.columns if k in units}).encode(),
            b"schema_version": SCHEMA_VERSION.encode(), b"release_version": RELEASE_VERSION.encode(),
            b"licence": b"CC BY 4.0", b"source": b"AIJ UWE benchmark (Kikumoto et al. 2026); clean/build.py"}
    if extra_meta:
        meta.update({k.encode(): json.dumps(v).encode() for k, v in extra_meta.items()})
    table = table.replace_schema_metadata(meta)
    pq.write_table(table, path, compression="zstd", write_statistics=True)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(_jsonable(obj), f, indent=1, ensure_ascii=False, allow_nan=False)
        f.write("\n")


def relp(p):
    return os.path.relpath(p, HERE).replace(os.sep, "/")


# --------------------------------------------------------------------------------------------- main

def build():
    prov: dict[str, list[str]] = {}
    results = {}
    A = build_A(prov); results["A"] = A
    B = build_B(prov); results["B"] = B
    C = build_C(prov); results["C"] = C
    Dd = build_D(prov); results["D"] = Dd
    E = build_E(prov); results["E"] = E

    all_pts, all_af, all_dir = [], [], []
    manifest_cases = {}
    for case in "ABCDE":
        pts, afl, geo, inflow, frame, transform = results[case][:6]
        extra = results[case][6] if len(results[case]) > 6 else None
        pts = pts.sort_values(["config", "instrument", "wind_direction_deg", "point_id"], kind="mergesort").reset_index(drop=True)
        for col in ("x", "y", "z"):
            pts[col] = pts[col].round(9)
        for col in ("uu", "vv", "ww"):
            pts[col] = pts[col].round(9)
        cdir = os.path.join(HERE, "cases", case)
        os.makedirs(cdir, exist_ok=True)
        write_csv(os.path.join(cdir, "points.csv"), pts)
        write_parquet(os.path.join(cdir, "points.parquet"), pts, UNITS, {"frame": frame, "transform": transform})
        write_csv(os.path.join(cdir, "approach_flow.csv"), afl)
        write_parquet(os.path.join(cdir, "approach_flow.parquet"), afl, APPROACH_FLOW_UNITS)
        dirs = directions_for(case, pts, frame)
        write_csv(os.path.join(cdir, "directions.csv"), dirs)
        all_pts.append(pts); all_af.append(afl); all_dir.append(dirs)
        gfiles = []
        for entry in geo:
            if case == "E":
                cfg, boxes, tris, note = entry
            else:
                cfg, boxes, note = entry
                tris = tris_of_boxes(boxes)
            name = "geometry.stl" if cfg in ("default",) else f"geometry_{cfg}.stl"
            write_ascii_stl(os.path.join(cdir, name), tris, f"AIJ_case{case}_{cfg}")
            st = stl_stats(tris)
            gf = {"configuration": cfg, "file": f"cases/{case}/{name}", "format": "ASCII STL, LF, metres, same frame as points.csv", "source": note, "stats": st}
            if boxes is not None:
                gf["boxes"] = boxes
                gf["box_count"] = len(boxes)
                if not st["watertight"]:
                    raise SystemExit(f"{case}/{cfg}: box geometry not watertight")
            gfiles.append(gf)
            log(f"[{case}] wrote {name}: {st['triangles']} triangles, watertight={st['watertight']}, bbox {st['bbox_min']}..{st['bbox_max']}")
        write_json(os.path.join(cdir, "geometry.json"), {"case_id": case, "units": "metres" + (" (full scale)" if case == "E" else " (model scale)"), "frame": frame, "files": gfiles})
        counts = {"rows": int(len(pts)), "distinct_points": int(pts.point_id.nunique()),
                  "by_config": {str(k): int(v) for k, v in pts.groupby("config").size().items()},
                  "by_instrument": {str(k): int(v) for k, v in pts.groupby("instrument").size().items()},
                  "by_direction": {str(k): int(v) for k, v in pts.groupby("wind_direction_deg").size().items()},
                  "nan_per_column": {k: int(v) for k, v in pts.isna().sum().items() if v}}
        cols_present = [cname for cname in POINT_COLUMNS if cname in TEXT_COLUMNS or cname in INT_COLUMNS or pts[cname].notna().any()]
        meta = CASES[case]
        manifest_cases[case] = {
            "id": case, "title": meta["title"], "status": "provisional" if case == "E" else "released",
            "status_note": ("Case E: points and inflow are released at full precision from the official workbook and pass every check; what stays provisional is the GEOMETRY of the before-construction state (an Eddy3D reconstruction with no published source) and the open questions in QUESTIONS.md (Q3)." if case == "E" else None),
            "doi": meta["zenodo_concept"], "doi_version": meta["zenodo_version"], "zenodo_record": f"https://zenodo.org/records/{meta['zenodo_concept'].split('.')[-1]}",
            "licence": "CC BY 4.0", "data_collectors": meta["collectors"], "editors_distributors": EDITORS, "contact": meta["contact"], "citation_requested": meta["citation"],
            "files": {"points_csv": f"cases/{case}/points.csv", "points_parquet": f"cases/{case}/points.parquet",
                      "approach_flow_csv": f"cases/{case}/approach_flow.csv", "approach_flow_parquet": f"cases/{case}/approach_flow.parquet",
                      "directions_csv": f"cases/{case}/directions.csv", "geometry_json": f"cases/{case}/geometry.json",
                      "geometry": [g["file"] for g in gfiles]},
            "columns_present": cols_present, "counts": counts,
            "configurations": dirs[["config", "instrument", "wind_direction_deg", "wind_direction", "rows", "measured", "status"]].to_dict("records"),
            "frame": frame, "transform_from_published": transform, "inflow": inflow,
            "geometry_summary": [{"configuration": g["configuration"], "file": g["file"], "triangles": g["stats"]["triangles"], "watertight": g["stats"]["watertight"], "bbox_min": g["stats"]["bbox_min"], "bbox_max": g["stats"]["bbox_max"], "boxes": g.get("box_count")} for g in gfiles],
            "provenance": [{"path": relp(p) if p.startswith(HERE) else os.path.relpath(p, REPO).replace(os.sep, "/"), "sha256": sha256(p), "bytes": os.path.getsize(p),
                            "origin": ("Zenodo " + meta["zenodo_version"] + " (downloaded; SHA256SUMS.txt beside it)") if p.startswith(SRC) else "repository clone of the Zenodo record"} for p in prov[case]],
            "known_issues": (extra or {}).get("known_issues", {}),
            "extra_measurements": {k: v for k, v in (extra or {}).items() if k != "known_issues"},
        }
    big = pd.concat(all_pts, ignore_index=True)
    write_csv(os.path.join(HERE, "points.csv"), big)
    write_parquet(os.path.join(HERE, "points.parquet"), big, UNITS)
    afl_all = pd.concat(all_af, ignore_index=True)
    write_csv(os.path.join(HERE, "approach_flow.csv"), afl_all)
    write_parquet(os.path.join(HERE, "approach_flow.parquet"), afl_all, APPROACH_FLOW_UNITS)
    dir_all = pd.concat(all_dir, ignore_index=True)
    write_csv(os.path.join(HERE, "directions.csv"), dir_all)
    write_parquet(os.path.join(HERE, "directions.parquet"), dir_all, DIRECTION_UNITS)
    write_json(os.path.join(HERE, "units.json"), {"points": UNITS, "approach_flow": APPROACH_FLOW_UNITS, "directions": DIRECTION_UNITS,
                                                   "note": "column headers in every CSV are bare names; this file is the units sidecar; the parquet files carry the same map in their schema metadata"})
    manifest = {
        "name": "AIJ UWE benchmark — cleaned release, Cases A-E", "version": RELEASE_VERSION, "schema_version": SCHEMA_VERSION,
        "licence": {"data": "CC BY 4.0", "url": "https://creativecommons.org/licenses/by/4.0/", "note": "The measurement data belongs to its collectors and distributors, named per case. Cite the benchmark paper and each case's requested citation."},
        "cite": {"benchmark": "Kikumoto, H., Okaze, T., Yoshie, R. et al. (2026). Comprehensive Experimental Database for Validating CFD Simulations in Urban Wind Environment: Benchmark Cases Curated by the Architectural Institute of Japan. Japan Architectural Review 9(1), e70083. https://doi.org/10.1002/2475-8876.70083",
                 "guidelines": "Tominaga, Y. et al. (2008). AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings. JWEIA 96, 1749-1761. https://doi.org/10.1016/j.jweia.2008.02.058"},
        "built_by": "clean/build.py (deterministic; re-run to regenerate; checks.json carries the validity checks, build.log every transform)",
        "schema": "SCHEMA.md", "readme": "README.md", "open_questions": "QUESTIONS.md",
        "files": {"points_csv": "points.csv", "points_parquet": "points.parquet", "approach_flow_csv": "approach_flow.csv", "approach_flow_parquet": "approach_flow.parquet",
                  "directions_csv": "directions.csv", "directions_parquet": "directions.parquet", "units": "units.json", "checks": "checks.json", "log": "build.log"},
        "columns": {k: v for k, v in UNITS.items()},
        "counts": {"rows": int(len(big)), "by_case": {k: int(v) for k, v in big.groupby("case_id").size().items()}},
        "cases": manifest_cases,
    }
    write_json(os.path.join(HERE, "manifest.json"), manifest)
    return manifest


def write_checks_and_log():
    failed = [c for c in CHECKS if c["severity"] == "error"]
    warned = [c for c in CHECKS if c["severity"] == "warning"]
    write_json(os.path.join(HERE, "checks.json"), {"total": len(CHECKS), "failed": len(failed), "warnings": len(warned),
                                                    "note": "severity 'warning' = a known, documented discrepancy in the published sources (README.md / QUESTIONS.md); it never fails the build", "checks": CHECKS})
    with io.open(os.path.join(HERE, "build.log"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(LOG) + "\n")
    return failed


def recheck():
    """--check: rebuild in memory (every source check runs again), then compare the on-disk tables
    against what the sources produce now, cell for cell, and the parquet files against the CSVs."""
    import pyarrow.parquet as pq
    prov = {}
    for case, fn in zip("ABCDE", (build_A, build_B, build_C, build_D, build_E)):
        pts = fn(prov)[0].sort_values(["config", "instrument", "wind_direction_deg", "point_id"], kind="mergesort").reset_index(drop=True)
        for col in ("x", "y", "z", "uu", "vv", "ww"):
            pts[col] = pts[col].round(9)
        disk_csv = pd.read_csv(os.path.join(HERE, "cases", case, "points.csv"), keep_default_na=True)
        disk_pq = pq.read_table(os.path.join(HERE, "cases", case, "points.parquet")).to_pandas()
        for name, disk in (("csv", disk_csv), ("parquet", disk_pq)):
            same_shape = list(disk.columns) == POINT_COLUMNS and len(disk) == len(pts)
            worst = 0.0
            if same_shape:
                for col in POINT_COLUMNS:
                    if col in TEXT_COLUMNS:
                        a = disk[col].fillna("").astype(str).to_numpy()
                        b = pts[col].fillna("").astype(str).to_numpy()
                        worst = max(worst, 0.0 if (a == b).all() else math.inf)
                    else:
                        a = disk[col].astype(float).to_numpy()
                        b = pts[col].astype(float).to_numpy()
                        both_nan = np.isnan(a) & np.isnan(b)
                        d = np.where(both_nan, 0.0, np.abs(a - b))
                        worst = max(worst, float(np.nanmax(np.where(np.isnan(d), math.inf, d))) if len(d) else 0.0)
            check(case, f"on_disk_{name}_matches_sources", same_shape and worst < 1e-9, rows=len(disk), max_abs_diff=worst)


def main():
    # The log quotes the published headers verbatim, including Case D's full-width 'ｚ' (U+FF5A);
    # a Windows console's default code page (cp1252) cannot encode it and the build dies mid-run.
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        recheck()
    else:
        build()
    failed = write_checks_and_log()
    print(f"\nchecks: {len(CHECKS) - len(failed)} passed, {len(failed)} failed ({sum(1 for c in CHECKS if c['severity'] == 'warning')} documented warnings)")
    for c in failed:
        print("FAILED:", c)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
