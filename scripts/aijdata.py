"""The AIJ UWE benchmark as data: case facts, the cleaned measurement tables and the geometry.

Everything `build_api.py` serves comes through this module, so the API and the site cannot
disagree about a number that lives here.

Sources, in order of preference:

1. `clean/` — the canonical cleaned release (Parquet + CSV + manifest.json, built by `clean/build.py`).
   When `clean/manifest.json` names a CSV for a case, the points table is read from it and the
   output records `points_source` as that path.
2. The raw per-case folders in this repository (`case-a/RS-caseA.csv`, …, the BIFF8
   workbooks for D and E). This is the fallback that makes the build work before `clean/` is
   complete, and it applies the same cleaning rules the README documents.

Canonical point columns (every case is a subset of these):

    point_id             int     the tunnel's own point number
    config               str     configuration key ("default", "0D"/"1D"/"2D", "bc"/"ac")
    instrument           str     "split_fibre" | "thermistor" (Case D carries both)
    wind_direction       str     compass name (Case E only; "" elsewhere)
    wind_direction_deg   float   AIJ wind direction, degrees (0 = the case's reference direction)
    x, y, z              float   metres, in the case frame (see CASES[...]['frame'])
    U, V, W              float   m/s, mean velocity components (+x, +y, +z of the case frame)
    uu, vv, ww           float   m^2/s^2, velocity VARIANCES (Case A's rms values are squared)
    k                    float   m^2/s^2, turbulent kinetic energy
    Vs                   float   m/s, mean scalar (omnidirectional, thermistor) wind speed
    velocity_ratio       float   dimensionless, Vs / U_ref (Case E; U_ref = U(15.9 m) = 3.935 m/s)

Missing / unmeasured values are None (null in JSON, empty in CSV).
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import struct
from collections import defaultdict
from typing import Iterable

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, os.pardir))

POINT_COLUMNS = ["point_id", "config", "instrument", "wind_direction", "wind_direction_deg",
                 "x", "y", "z", "U", "V", "W", "uu", "vv", "ww", "k", "Vs", "velocity_ratio"]

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
           "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

LICENCE = {
    "data": "CC BY 4.0",
    "data_url": "https://creativecommons.org/licenses/by/4.0/",
    "note": ("The measurement data belongs to its collectors and distributors, named per case. "
             "Cite the AIJ UWE benchmark and the accompanying papers when using it."),
}

CITATION = {
    "benchmark": ("Kikumoto, H., Okaze, T., Yoshie, R., Tachibana, T., Ishihara, T., Nonomura, Y., Kiyota, N., "
                  "Kondo, H., Mochida, A., Tominaga, Y. (2026). Comprehensive Experimental Database for "
                  "Validating CFD Simulations in Urban Wind Environment: Benchmark Cases Curated by the "
                  "Architectural Institute of Japan. Japan Architectural Review 9(1), e70083. "
                  "https://doi.org/10.1002/2475-8876.70083"),
    "guidelines": ("Tominaga, Y., Mochida, A., Yoshie, R., Kataoka, H., Nozu, T., Yoshikawa, M., "
                   "Shirasawa, T. (2008). AIJ guidelines for practical applications of CFD to pedestrian "
                   "wind environment around buildings. J. Wind Eng. Ind. Aerodyn. 96, 1749-1761. "
                   "https://doi.org/10.1016/j.jweia.2008.02.058"),
    "per_case": "Each case lists its own data collectors, Zenodo DOI and requested citation.",
}

# ----------------------------------------------------------------------------- case facts
# Numbers here are the ones the README states; where a value was measured during scoping rather
# than published by AIJ, the entry says so ("derived").

CASES = {
    "A": {
        "id": "A", "slug": "case-a", "title": "Case A — 1:1:2 building",
        "short": "Isolated 1:1:2 building, velocity field (split-fibre hot wire).",
        "folder": "case-a",
        "reference_file": "case-a/RS-caseA.csv",
        "approach_flow_file": "case-a/AF_caseA.csv",
        "readme": "case-a/readme_caseA.md",
        "render": "validation/geometry/geom_caseA.png",
        "configuration": {
            "building": "1:1:2 (width : depth : height) prism",
            "b_m": 0.08, "H_m": 0.16,
            "Re_H": 24000,
            "U_H_m_s": 4.491,
            "wind_directions_deg": [0],
            "measurement_planes": ["vertical centre plane y/b = 0", "horizontal z/b = 0.125", "horizontal z/b = 1.25"],
            "instrument": "hot-wire anemometer, split-fibre probes (DANTEC 55R55 streamwise, 55R57 spanwise/vertical), 1000 Hz, 60 s per point, 500 Hz low-pass",
            "tunnel": "Technical Research Institute, Shimizu Corporation, Tokyo",
            "scale_note": "model scale; Eddy3D solves it at 1:100 (b = 8 m, H = 16 m) with the tunnel velocities",
        },
        "quantities": ["U", "V", "W", "uu", "vv", "ww", "k"],
        "units": {"length": "m (model scale)", "velocity": "m/s", "variance": "m^2/s^2", "k": "m^2/s^2"},
        "frame": {
            "origin": "building centre on the ground plane",
            "x": "+x streamwise (the wind at WD = 0 blows toward +x); building spans x in [-0.04, 0.04]",
            "y": "+y lateral; building spans y in [-0.04, 0.04]; points published on the y <= 0 half by the tunnel's symmetry convention",
            "z": "+z up from the ground; roof at z = 0.16",
            "lateral_sign_applied": 1,
            "coordinate_scale_applied": 1.0,
        },
        "people": {
            "data_collectors": ["Takeshi Ishihara (The University of Tokyo)", "Kazuki Hibi (Numerical Flow Design)"],
            "editors_distributors": ["Yoshihide Tominaga (Niigata Institute of Technology)", "Hideki Kikumoto (The University of Tokyo)", "Tsubasa Okaze (Institute of Science Tokyo)"],
            "contact": "Takeshi Ishihara <ishihara@bridge.t.u-tokyo.ac.jp>",
        },
        "doi": "10.5281/zenodo.15050147",
        "citation_requested": "Meng, Y., & Hibi, K. (1998). Turbulent measurements of the flow field around a high-rise building. Journal of Wind Engineering, JAWE, 76, 55-64. https://doi.org/10.5359/jawe.1998.76_55",
        "inflow_fit": {
            "method": "log law, kappa = 0.41, least squares over z = 0.02 ... 2H on the case's own approach-flow file",
            "u_star_m_s": 0.343, "z0_mm": 0.668, "U_H_measured_m_s": 4.491, "log_law_error_at_H": "+2.0 %",
        },
        "gotchas": [
            "Lateral velocity V is positive toward +y (checked: V = -2.893 m/s at (-0.040, -0.050, 0.010), just outside the y < 0 flank, deflecting away from the centreline). Case B uses the OPPOSITE sign; the API flips Case B so both agree.",
            "Coordinates are metres (Case B's are millimetres in the published file).",
            "Case A's turbulence columns are rms values (u_rms, ...). The API serves VARIANCES (uu = u_rms^2) so A and B share one column meaning.",
        ],
    },
    "B": {
        "id": "B", "slug": "case-b", "title": "Case B — 1:4:4 slab",
        "short": "Isolated 1:4:4 slab, velocity field (split-fibre hot wire).",
        "folder": "case-b",
        "reference_file": "case-b/RS_caseB.csv",
        "approach_flow_file": "case-b/AF_caseB.csv",
        "readme": "case-b/readme_caseB.md",
        "render": "validation/geometry/geom_caseB.png",
        "configuration": {
            "building": "1:4:4 (depth : width : height) slab",
            "depth_m": 0.05, "width_m": 0.20, "H_m": 0.20,
            "Re_H": 72000,
            "U_H_m_s": 5.133,
            "wind_directions_deg": [0],
            "measurement_planes": ["vertical centre plane y/H = 0", "horizontal z/H = 1/16"],
            "instrument": "hot-wire anemometer, split-fibre probe, 100 Hz, 60 s per point",
            "tunnel": "Niigata Institute of Technology, Kashiwazaki",
            "scale_note": "model scale; Eddy3D solves it at 1:100 (H = 20 m) with the tunnel velocities",
        },
        "quantities": ["U", "V", "W", "uu", "vv", "ww", "k"],
        "units": {"length": "m (model scale; converted from the published millimetres)", "velocity": "m/s", "variance": "m^2/s^2", "k": "m^2/s^2"},
        "frame": {
            "origin": "building centre on the ground plane",
            "x": "+x streamwise (the wind at WD = 0 blows toward +x); slab spans x in [-0.025, 0.025]",
            "y": "+y lateral; slab spans y in [-0.10, 0.10]; points published on the y <= 0 half by the tunnel's symmetry convention",
            "z": "+z up from the ground; roof at z = 0.20",
            "lateral_sign_applied": -1,
            "coordinate_scale_applied": 0.001,
        },
        "people": {
            "data_collectors": ["Yoshihide Tominaga (Niigata Institute of Technology)"],
            "editors_distributors": ["Hideki Kikumoto (The University of Tokyo)", "Tsubasa Okaze (Institute of Science Tokyo)"],
            "contact": "Yoshihide Tominaga <tominaga@abe.niit.ac.jp>",
        },
        "doi": "10.5281/zenodo.15401455",
        "citation_requested": "Miyazaki, T., Tominaga, Y. (2003). Wind tunnel experiment on flow field around a building model with a scale ratio of 4:4:1 placed within the surface boundary layer. Proc. Annual Meeting of Hokuriku Chapter, AIJ, 201-204 (in Japanese). https://www.aij.or.jp/paper/detail.html?productId=313933",
        "inflow_fit": {
            "method": "log law, kappa = 0.41, least squares over z = 0.02 ... 2H on the case's own approach-flow file",
            "u_star_m_s": 0.399, "z0_mm": 0.882, "U_H_measured_m_s": 5.133, "log_law_error_at_H": "+2.9 %",
        },
        "gotchas": [
            "The published coordinates are MILLIMETRES (x[mm]) while velocities are m/s. The API serves metres (coordinate_scale_applied = 0.001). Read as metres, every probe lands 1000x too far out.",
            "The published lateral velocity V is positive toward -y (V = +3.630 m/s at (-0.025, -0.110, 0.013), just outside the y < 0 flank where the flow must deflect toward -y). The API multiplies V by -1 (lateral_sign_applied = -1) so that V is positive toward +y as in Case A. Scored without this, Case B's V comes out at R = -0.910 against R = +0.959 for U on the same points.",
            "The RANS solution is symmetric, so model V = 0 on the centre plane while the tunnel measures small non-zero values there.",
        ],
    },
    "C": {
        "id": "C", "slug": "case-c", "title": "Case C — 3 × 3 block array",
        "short": "3 x 3 array of 0.20 m cubes, centre block at 0D / 1D / 2D, pedestrian-height scalar speed (thermistor), 3 wind directions.",
        "folder": "case-c",
        "reference_file": "case-c/RS_caseC.csv",
        "approach_flow_file": "case-c/AF_caseC.csv",
        "readme": "case-c/readme_caseC.md",
        "render": "validation/geometry/geom_caseC.png",
        "configuration": {
            "array": "3 x 3 cubes, D = 0.20 m, block centres at x, y in {-0.4, 0, +0.4} m (pitch 0.40 m = 2D, street width D)",
            "D_m": 0.20,
            "centre_building": {"0D": "no centre building", "1D": "0.2 x 0.2 x 0.2 m (same as the surroundings)", "2D": "0.2 x 0.2 x 0.4 m"},
            "wind_directions_deg": [0, 22.5, 45],
            "configurations": 9,
            "configurations_note": "3 centre-building heights x 3 wind directions; all nine share the identical 120-point set",
            "measurement_height_m": 0.02,
            "measurement_height_note": "z = 0.1 D for every point (2.0 m at the 1:100 scale Eddy3D solves it at)",
            "Re_D": 52000,
            "U_H_m_s": 3.654,
            "U_H_note": "U at z = D = 0.20 m from AF_caseC.csv; the data paper states U_H = 3.65 m/s",
            "instrument": "thermistor anemometer (omnidirectional scalar speed), 1 Hz, 30 s per point; approach flow by I-type hot wire, 500 Hz, 30 s",
            "tunnel": "Technology Development Division, Fujita Corporation, Tokyo",
            "pitch_note": "The 0.40 m pitch is read from MP-z-caseC.png and Figure 3 of the data paper (street = D); the 120-point grid alone bounds the pitch to (0.35, 0.40] m (the 49 absent nodes of the 13 x 13 grid are exactly the nine footprints for 0.375 m as well as 0.40 m).",
        },
        "quantities": ["Vs"],
        "units": {"length": "m (model scale)", "velocity": "m/s"},
        "frame": {
            "origin": "array centre on the ground plane (centre of the middle block)",
            "x": "+x streamwise at WD = 0 (checked three ways on the data: y -> -y is a symmetry, the x <= -0.25 band is faster than x >= +0.25 in every configuration, and the regression slope of Vs is most negative within 0.8-4.3 deg of +x)",
            "y": "+y lateral",
            "z": "+z up; all points at z = 0.02",
            "wind_direction_rotation": "In the CSV's own frame WD rotates the wind from +x TOWARD -y (the WD = 45 field is mirror-symmetric about y = -x to within the experiment's repeatability, 0.10-0.13 m/s, and not about y = +x, 0.5-0.8 m/s). Figure 3 of the data paper draws the fan rotating toward +y. The two disagree by a y-sign flip; this release keeps the CSV frame, which is the frame the point coordinates live in. The disagreement is invisible at WD = 0.",
            "lateral_sign_applied": 1,
            "coordinate_scale_applied": 1.0,
        },
        "people": {
            "data_collectors": ["Yoshitami Nonomura (Yamato University)"],
            "editors_distributors": ["Yoshihide Tominaga (Niigata Institute of Technology)", "Hideki Kikumoto (The University of Tokyo)", "Tsubasa Okaze (Institute of Science Tokyo)"],
            "contact": "Yoshitami Nonomura <nonomura.yoshitami@yamato-u.ac.jp>",
        },
        "doi": "10.5281/zenodo.15401791",
        "citation_requested": "Nonomura, Y., Kobayashi, N., Tominaga, Y., Mochida, A. (2003). The cross comparison of CFD results for flow field around building models (part 3). Japan Association for Wind Engineering, 95, 83-84 (in Japanese). https://doi.org/10.14887/jaweam.2003.0.41.0",
        "inflow_fit": {
            "method": "log law, kappa = 0.41, least squares on AF_caseC.csv (16 points, z = 0.01 ... 1.2 m); two windows, because Case C scores at ONE height (z = 0.02 m) and the near-ground half of the fit matters",
            "windows": [
                {"z_range_m": [0.02, 0.40], "u_star_m_s": 0.25598, "z0_mm": 0.4797, "error_at_U_D": "+3.08 %", "error_at_z_0.02": "-4.31 %", "scored_ratio_bias": "-7.17 %"},
                {"z_range_m": [0.01, 0.40], "u_star_m_s": 0.22853, "z0_mm": 0.2362, "error_at_U_D": "+2.83 %", "error_at_z_0.02": "+1.65 %", "scored_ratio_bias": "-1.15 %"},
            ],
            "power_law_exponent_fitted": 0.190, "power_law_exponent_paper": 0.28,
            "turbulence_intensity_at_D": 0.219,
            "note": "derived during scoping, not published by AIJ; the tunnel profile is closer to a power law than a log law, so a log-law inlet carries a ~2.3 % rms residual over the fitted range",
        },
        "gotchas": [
            "The measured quantity Vs is the MEAN OMNIDIRECTIONAL SCALAR speed from a thermistor, not |mean velocity vector|. A RANS |U| is biased low against it; the data paper suggests comparing sqrt(|U|^2 + 2k) as a conservative correction (over all 1080 rows no Vs is below 0.13 U_H).",
            "The 'CB' column is TEXT ('0D', '1D', '2D'); a reader that parses every field as a number gets NaN for it. The header ends with a trailing comma (an empty 8th column).",
            "1080 rows = 3 wind directions x 3 centre buildings x 120 points, not 3 configurations. In the 0D configuration the 25 centre grid nodes are still absent although the ground there is free: the grid is held constant across configurations.",
            "24 of the 120 points sit exactly on a building face plane (|x| = 0.30 or |y| = 0.30) in the open gap between two blocks: legitimate fluid points, but a probe's cell lookup is delicate there.",
            "Point numbers 1, 2, 3, 34, 35, 36, 37, 46, 55, 100, 101, 102 do not occur (No. runs 4 ... 132 with nine interior gaps).",
            "Experimental repeatability, from the mirror-symmetric point pairs: mean |dVs| 0.088-0.137 m/s (0.024-0.038 U_H).",
        ],
    },
    "D": {
        "id": "D", "slug": "case-d", "title": "Case D — high-rise among city blocks",
        "short": "1:1:4 tower in a regular array of 82 low blocks, pedestrian-height scalar speed (thermistor, 3 wind directions) plus a 33-point split-fibre velocity field at WD = 0.",
        "folder": "case-d",
        "reference_file": "case-d/LF_caseD.xls",
        "approach_flow_file": "case-d/LF_caseD.xls [sheet Inflow]",
        "readme": None,
        "render": "validation/geometry/geom_caseD.png",
        "configuration": {
            "tower": "0.25H x 0.25H x H = 62.5 x 62.5 x 250 mm (1:1:4)",
            "H_m": 0.25,
            "blocks": "82 blocks of 0.4H x 0.4H x 0.1H = 100 x 100 x 25 mm",
            "roads": "0.1H / 0.2H / 0.3H = 25 / 50 / 75 mm; 9 columns in x (pitch alternating 175 / 150 mm), 11 rows in y (pitch 125 mm); corners cut by the turntable circle",
            "array_extent_m": {"x": [-0.700, 0.700], "y": [-0.675, 0.675], "z": [0, 0.25]},
            "scale": "1:400 (H = 100 m full scale; the 5 mm measurement plane = 2 m)",
            "Re_H": 110000,
            "U_H_m_s": 6.65,
            "wind_directions_deg": [0, 22.5, 45],
            "measurement_height_m": 0.005,
            "instrument": "thermistor anemometer (78 points x 3 directions; 66 measured per direction, 12 points in the band around the tower unmeasured) and split-fibre probe (33 points at WD = 0: U, V, W, variances, k)",
            "tunnel": "see the data paper (Kikumoto et al. 2026, section 3.4)",
        },
        "quantities": ["Vs", "U", "V", "W", "uu", "vv", "ww", "k"],
        "units": {"length": "m (model scale; converted from the workbook's millimetres)", "velocity": "m/s", "variance": "m^2/s^2", "k": "m^2/s^2"},
        "frame": {
            "origin": "tower centre on the ground plane (the array's bounding box is centred on it)",
            "x": "+x streamwise at WD = 0 (the 0 deg thermistor field is exactly y-mirror symmetric; the split-fibre U is positive at the stream-like points and negative in the tower's windward horseshoe)",
            "y": "+y lateral",
            "z": "+z up; all points at z = 0.005",
            "wind_direction_rotation": "+x toward +y, read from Figure 4 of the data paper. The array is exactly y-mirror symmetric, so the rotation sense CANNOT be settled from the measurements: headings +theta and -theta give exact mirror fields. Treat 22.5 and 45 deg with that caveat.",
            "lateral_sign_applied": 1,
            "coordinate_scale_applied": 0.001,
        },
        "people": {
            "data_collectors": ["Yoshihide Tominaga (Niigata Institute of Technology)"],
            "editors_distributors": ["Hideki Kikumoto (The University of Tokyo)", "Tsubasa Okaze (Institute of Science Tokyo)"],
            "contact": "Yoshihide Tominaga <tominaga@abe.niit.ac.jp>",
        },
        "doi": "10.5281/zenodo.15402668",
        "doi_note": "The case folder ships without the Zenodo record's readme and CSVs; they are mirrored byte for byte under clean/sources/zenodo_caseD/ (people and DOI from that readme and the data paper's reference 50).",
        "citation_requested": "Kikumoto, H. et al. (2026). Japan Architectural Review 9(1), e70083, section 3.4.",
        "inflow_fit": {
            "method": "log law, kappa = 0.41, least squares on the workbook's 13-point profile (z = 5 ... 1200 mm); two windows, because the measurement plane z/H = 0.02 sits below the 0.02 ... 2H window used for Cases A and B",
            "windows": [
                {"z_range": "0.005 ... 2H", "u_star_m_s": 0.3418, "z0_mm": 0.0859, "error_at_z_5mm": "-11.2 %", "profile_rms": "7.9 %", "inlet_k_m2_s2": 0.3895, "inlet_k_vs_tunnel": "-26 % to -48 %"},
                {"z_range": "0.02 ... 2H", "u_star_m_s": 0.4240, "z0_mm": 0.4033, "error_at_z_5mm": "-30.0 %", "profile_rms": "12.5 % / 4.7 %", "inlet_k_m2_s2": 0.5991, "inlet_k_vs_tunnel": "+13 % to -20 %"},
            ],
            "power_law_exponent_fitted": 0.189, "power_law_exponent_paper": 0.25,
            "note": "derived during scoping, not published by AIJ; a log-law inlet cannot be right at both the measurement plane and the upper profile",
        },
        "gotchas": [
            "All of Case D's data lives in LF_caseD.xls, a genuine OLE2/BIFF8 workbook (read it with xlrd 2.x; openpyxl cannot). Sheets: 'Geometry&Points', 'Inflow', 'Results (Exp_S)' (split fibre, WD = 0), 'Results (Exp_T)' (thermistor, 0 / 22.5 / 45 deg).",
            "Coordinates are millimetres in the workbook; the API serves metres.",
            "The shipped BD_caseD.stl is dirty: 1572 facets of which 576 are duplicates, and all 83 roofs are wound inward (signed volume 0.011159 m^3 against the true 0.021477 m^3). The API's geometry.stl is rebuilt from the 83 shells' bounding boxes: 996 facets, watertight, volume 0.021477 m^3.",
            "The thermistor reads a SCALAR speed. Over the 33 points where both instruments overlap at WD = 0, the ratio of mean thermistor speed to mean |U| is 1.342 (the mean of the per-point ratios is 1.50). sqrt(|U|^2 + 2k) from the split-fibre data matches the thermistor to FB +0.058, R 0.947; |U| alone to FB +0.292, R 0.872.",
            "Unmeasured thermistor cells are '-' in the workbook (null here). At WD = 0 the 66 measured values are 33 exact mirror pairs, so only 33 are independent; at 22.5 and 45 deg all 66 are independent.",
            "A prior Eddy3D comparison kept in the folder (case-d-eddy3d-prior-comparison.xlsx) scores R = +0.096 against the thermistor: a frame or geometry error, not a closure result. It is not a validation.",
        ],
    },
    "E": {
        "id": "E", "slug": "case-e", "title": "Case E — Niigata district",
        "short": "Real district in Niigata at 1:250, before and after a 60 m high-rise and two 18 m mid-rises; pedestrian-height velocity ratio (thermistor), 16 wind directions.",
        "folder": "case-e",
        "reference_file": "case-e/LF_caseE.xls",
        "approach_flow_file": "case-e/LF_caseE.xls [sheet Inflow]",
        "readme": "case-e/readme_caseE.md",
        "render": "validation/geometry/geom_caseE.png",
        "configuration": {
            "district": "Niigata City urban area near the Shinano River; dense low-rise stock (median top 6 m, max 30 m)",
            "scale": "1:250",
            "states": {"bc": "before construction (sites of A, B, C empty)", "ac": "after construction of A (60 m high-rise), B and C (18 m mid-rises)"},
            "new_buildings": {"A": "60 m high-rise, bbox x [-79.3, -49.1], y [-17.1, 18.3]", "B": "18 m, bbox x [41.5, 61.0], y [-18.5, 8.5]", "C": "18 m, bbox x [64.0, 83.5], y [-8.0, 19.0]"},
            "wind_directions": COMPASS,
            "wind_directions_deg": [i * 22.5 for i in range(16)],
            "measurement_height_m": 2.0,
            "measurement_height_note": "2 m full scale = 0.008 m model scale",
            "points": 80, "values": 2560,
            "Re": 17000,
            "normalisation": "velocity ratio = mean scalar speed at 2 m / inflow velocity at 15.9 m (the Niigata meteorological station height); U(15.9 m) = 0.504531 x UR = 3.935 m/s with UR = 7.8 m/s at ZR = 250 m",
            "instrument": "thermistor anemometer, 100 Hz, 60 s per point, mean scalar wind speed",
            "tunnel": "Niigata Institute of Technology, Kashiwazaki",
        },
        "quantities": ["velocity_ratio"],
        "units": {"length": "m (FULL scale)", "velocity_ratio": "dimensionless"},
        "frame": {
            "origin": "centre of the reproduced area, ground plane",
            "x": "+x EAST (full-scale metres)",
            "y": "+y NORTH (compass rose in MP_caseE.png)",
            "z": "+z up; all points at z = 2.0",
            "wind_direction_rotation": "Meteorological: the compass name is the direction the wind comes FROM (N = 0 deg blows toward -y, E = 90 deg toward -x), clockwise from north. This case keeps its geographic frame instead of '+x along the wind' because the district is real and its coordinates are the data's.",
            "lateral_sign_applied": 1,
            "coordinate_scale_applied": 1.0,
        },
        "people": {
            "data_collectors": ["Yoshihide Tominaga (Niigata Institute of Technology)"],
            "editors_distributors": ["Hideki Kikumoto (The University of Tokyo)", "Tsubasa Okaze (Institute of Science Tokyo)"],
            "contact": "Yoshihide Tominaga <tominaga@abe.niit.ac.jp>",
        },
        "doi": "10.5281/zenodo.15429017",
        "citation_requested": "Tominaga, Y. et al. (2008). AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings. JWEIA 96, 1749-1761. https://doi.org/10.1016/j.jweia.2008.02.058",
        "inflow_fit": {
            "method": "the workbook publishes z/ZR, U/UR, k/UR^2 with ZR = 250 m, UR = 7.8 m/s and epsilon = Cmu^0.5 k dU/dz (Cmu = 0.09); de-normalised to full-scale metres and m/s here",
            "U_ref_15_9m_m_s": 3.935,
            "log_law": "does not fit: kappa = 0.41 fits reach 5.3-9.4 % max error over the relevant height range and overshoot U(15.9 m) by 4-7 %",
            "power_law_exponent": {"ground_to_60m": 0.158, "whole_profile": 0.201},
            "note": "derived during scoping, not published by AIJ",
        },
        "gotchas": [
            "The velocity ratio is normalised by the inflow velocity at 15.9 m (= 3.935 m/s), NOT by U_H and NOT by UR = 7.8 m/s. A prior Eddy3D comparison in the folder divided by the wrong reference and came out low by a factor of 2.048 (FAC2 0.338 -> 0.863 once rescaled, R unchanged at 0.661).",
            "All 2560 published ratios are integer multiples of 0.0198204 (55 distinct levels): the data's own resolution is +/-0.0099, 3.1 % of the median value and about 10 % at the lowest points.",
            "The readme describes AF_caseE.csv, RS_caseE.csv and BD_caseE.stl, but this repository holds only the .3dm, .ghx, .xls and the MP drawing; everything here is extracted from the workbook and the 3dm.",
            "case-e.3dm is FULL-SCALE metres (MP_caseE.png is drawn at model scale, +/-0.8 m). Use layers 'buildings' (5,015 meshes, before construction) and 'buildings_new_construction' (3 prisms); exclude the map plate on the Japanese-named general layer, the terrain plates (the site is flat) and 'probes'.",
            "Do not take the measurement coordinates from the 3dm's 'probes' layer: its 80 spheres sit a median 2.31 m (max 21 m) from the workbook's points, which are authoritative (all 80 fall in open space, min 0.83 m from a building edge).",
            "The measured quantity is a scalar (thermistor) speed; a RANS |U| is biased low against it in a dense canopy. The construction signal (ac - bc) is largest for SW (mean |d| 0.2155) and smallest for SSE (0.093).",
        ],
    },
}

CASE_IDS = ["A", "B", "C", "D", "E"]


# ----------------------------------------------------------------------------- helpers

def _f(v):
    """A float, or None for the empty / '-' / -999.9 sentinels the files use."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        s = str(v).strip()
        if s in ("", "-", "nan", "NaN"):
            return None
        try:
            x = float(s)
        except ValueError:
            return None
    if math.isnan(x) or abs(x + 999.9) < 1e-6:
        return None
    return x


def _read_csv(path):
    with io.open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.reader(f) if any(c.strip() for c in r)]
    header = [h.split("(")[0].split("[")[0].strip() for h in rows[0]]
    return header, rows[1:]


def _row(**kw):
    r = {c: None for c in POINT_COLUMNS}
    r["config"] = "default"
    r["instrument"] = ""
    r["wind_direction"] = ""
    r["wind_direction_deg"] = 0.0
    r.update(kw)
    return r


# ----------------------------------------------------------------------------- raw loaders

def _points_ab(case):
    meta = CASES[case]
    scale = meta["frame"]["coordinate_scale_applied"]
    lsign = meta["frame"]["lateral_sign_applied"]
    header, rows = _read_csv(os.path.join(REPO, meta["reference_file"]))
    idx = {n: i for i, n in enumerate(header)}
    out = []
    for r in rows:
        g = lambda n: _f(r[idx[n]]) if n in idx and idx[n] < len(r) else None
        if case == "A":
            uu, vv, ww = (None if g(n) is None else g(n) ** 2 for n in ("u_rms", "v_rms", "w_rms"))
        else:
            uu, vv, ww = g("<u'2>"), g("<v'2>"), g("<w'2>")
        v = g("V")
        out.append(_row(point_id=int(g("No.")), instrument="split_fibre",
                        x=g("x") * scale, y=g("y") * scale, z=g("z") * scale,
                        U=g("U"), V=None if v is None else lsign * v, W=g("W"),
                        uu=uu, vv=vv, ww=ww, k=g("k")))
    return out


def _points_c():
    header, rows = _read_csv(os.path.join(REPO, CASES["C"]["reference_file"]))
    idx = {n: i for i, n in enumerate(header)}
    out = []
    for r in rows:
        out.append(_row(point_id=int(float(r[idx["No."]])), config=r[idx["CB"]].strip(), instrument="thermistor",
                        wind_direction_deg=float(r[idx["WD"]]),
                        x=_f(r[idx["x"]]), y=_f(r[idx["y"]]), z=_f(r[idx["z"]]), Vs=_f(r[idx["Vs"]])))
    return out


def _xls(path):
    import xlrd  # BIFF8 .xls; openpyxl cannot read these
    return xlrd.open_workbook(os.path.join(REPO, path))


def _points_d():
    wb = _xls(CASES["D"]["reference_file"])
    out = []
    t = wb.sheet_by_name("Results (Exp_T)")
    for r in range(5, t.nrows):
        no = _f(t.cell_value(r, 0))
        if no is None:
            continue
        x, y, z = (_f(t.cell_value(r, c)) for c in (1, 2, 3))
        for col, wd in ((4, 0.0), (5, 22.5), (6, 45.0)):
            out.append(_row(point_id=int(no), instrument="thermistor", wind_direction_deg=wd,
                            x=x / 1000, y=y / 1000, z=z / 1000, Vs=_f(t.cell_value(r, col))))
    s = wb.sheet_by_name("Results (Exp_S)")
    for r in range(3, s.nrows):
        no = _f(s.cell_value(r, 0))
        if no is None or _f(s.cell_value(r, 1)) is None:
            continue
        c = [_f(s.cell_value(r, i)) for i in range(13)]
        out.append(_row(point_id=int(no), instrument="split_fibre", wind_direction_deg=0.0,
                        x=c[1] / 1000, y=c[2] / 1000, z=c[3] / 1000,
                        U=c[4], uu=c[5], V=c[6], vv=c[7], W=c[8], ww=c[9], Vs=c[10], k=c[12]))
    return out


def _points_e():
    wb = _xls(CASES["E"]["reference_file"])
    g = wb.sheet_by_name("Geometry&Points")
    pts = {}
    for r in range(g.nrows):
        no = _f(g.cell_value(r, 1))
        if no is not None and _f(g.cell_value(r, 2)) is not None:
            pts[int(no)] = (_f(g.cell_value(r, 2)), _f(g.cell_value(r, 3)))
    out = []
    for state, sheet in (("bc", "Results (Before Construction)"), ("ac", "Results (After Construction)")):
        sh = wb.sheet_by_name(sheet)
        for r in range(sh.nrows):
            no = _f(sh.cell_value(r, 1))
            if no is None or int(no) not in pts:
                continue
            x, y = pts[int(no)]
            for i, name in enumerate(COMPASS):
                out.append(_row(point_id=int(no), config=state, instrument="thermistor",
                                wind_direction=name, wind_direction_deg=i * 22.5,
                                x=x, y=y, z=2.0, velocity_ratio=_f(sh.cell_value(r, 2 + i))))
    return out


RAW_LOADERS = {"A": lambda: _points_ab("A"), "B": lambda: _points_ab("B"),
               "C": _points_c, "D": _points_d, "E": _points_e}


# ----------------------------------------------------------------------------- clean/ adapter

_SYNONYMS = {
    "point_id": ["point_id", "point", "no", "no.", "id", "point_no"],
    "config": ["config", "configuration", "cb", "centre_building", "center_building", "state", "case"],
    "instrument": ["instrument", "probe"],
    "wind_direction": ["wind_direction", "direction", "compass"],
    "wind_direction_deg": ["wind_direction_deg", "wd", "wd_deg", "wind_deg", "theta_deg"],
    "x": ["x", "x_m"], "y": ["y", "y_m"], "z": ["z", "z_m"],
    "U": ["u", "u_m_s"], "V": ["v", "v_m_s"], "W": ["w", "w_m_s"],
    "uu": ["uu", "u2", "u_var", "<u'2>"], "vv": ["vv", "v2", "v_var", "<v'2>"], "ww": ["ww", "w2", "w_var", "<w'2>"],
    "k": ["k", "tke"], "Vs": ["vs", "scalar_speed", "vs_m_s"],
    "velocity_ratio": ["velocity_ratio", "vr", "ratio"],
}


def _find_csvs(obj, acc):
    if isinstance(obj, str):
        if obj.lower().endswith(".csv"):
            acc.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _find_csvs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _find_csvs(v, acc)


def clean_manifest():
    p = os.path.join(REPO, "clean", "manifest.json")
    if not os.path.isfile(p):
        return None
    with io.open(p, encoding="utf-8") as f:
        return json.load(f)


def _clean_entry(manifest, case):
    """The manifest entry for one case, whatever shape the manifest takes."""
    cases = manifest.get("cases", manifest)
    if isinstance(cases, dict):
        for key in (case, case.lower(), f"case{case}", f"case_{case}", f"case-{case.lower()}", f"Case{case}"):
            if key in cases:
                return cases[key]
    if isinstance(cases, list):
        for e in cases:
            if isinstance(e, dict) and str(e.get("id", e.get("case", ""))).upper().endswith(case):
                return e
    return None


def _points_clean(case):
    m = clean_manifest()
    if m is None:
        return None, None
    entry = _clean_entry(m, case)
    if entry is None:
        return None, None
    csvs = []
    _find_csvs(entry, csvs)
    # prefer a file that looks like the point table
    csvs.sort(key=lambda s: (0 if any(t in s.lower() for t in ("point", "rs_", "rs-", "measure")) else 1, len(s)))
    for rel in csvs:
        path = rel if os.path.isabs(rel) else os.path.join(REPO, "clean", rel)
        if not os.path.isfile(path):
            path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            continue
        with io.open(path, encoding="utf-8-sig", newline="") as f:
            rd = csv.DictReader(f)
            names = {n: n.split("(")[0].split("[")[0].strip().lower() for n in rd.fieldnames or []}
            mapping = {}
            for canon, syns in _SYNONYMS.items():
                for raw, low in names.items():
                    if low in syns and canon not in mapping:
                        mapping[canon] = raw
            if not ({"x", "y", "z"} <= set(mapping)):
                continue
            rows = []
            for r in rd:
                row = _row()
                for canon, raw in mapping.items():
                    v = r.get(raw)
                    if canon in ("config", "instrument", "wind_direction"):
                        row[canon] = (v or "").strip() or row[canon]
                    elif canon == "point_id":
                        fv = _f(v)
                        row[canon] = None if fv is None else int(fv)
                    else:
                        row[canon] = _f(v)
                if row["wind_direction_deg"] is None:
                    row["wind_direction_deg"] = 0.0
                rows.append(row)
            if rows:
                return rows, os.path.relpath(path, REPO).replace(os.sep, "/")
    return None, None


def load_points(case):
    """(rows, source): the cleaned point table for a case, from clean/ when it has one."""
    rows, src = _points_clean(case)
    if rows:
        return rows, src
    return RAW_LOADERS[case](), CASES[case]["reference_file"]


# ----------------------------------------------------------------------------- approach flow

def load_approach_flow(case):
    """Rows of {z, U, k, ...} in metres and m/s, straight from each case's own profile."""
    meta = CASES[case]
    if case in ("A", "B", "C"):
        header, rows = _read_csv(os.path.join(REPO, meta["approach_flow_file"]))
        idx = {n: i for i, n in enumerate(header)}
        out = []
        for r in rows:
            d = {"z": _f(r[idx["z"]]), "U": _f(r[idx["U"]])}
            if "k" in idx:
                d["k"] = _f(r[idx["k"]])
            if "u_rms" in idx:
                d["u_rms"] = _f(r[idx["u_rms"]])
            out.append(d)
        return out, meta["approach_flow_file"]
    if case == "D":
        sh = _xls(meta["reference_file"]).sheet_by_name("Inflow")
        out = []
        for r in range(sh.nrows):
            z = _f(sh.cell_value(r, 1))
            if z is None:
                continue
            out.append({"z": z / 1000, "U": _f(sh.cell_value(r, 3)), "k": _f(sh.cell_value(r, 5))})
        return out, meta["approach_flow_file"]
    sh = _xls(meta["reference_file"]).sheet_by_name("Inflow")
    ZR, UR = 250.0, 7.8
    out = []
    for r in range(sh.nrows):
        zn = _f(sh.cell_value(r, 1))
        if zn is None:
            continue
        out.append({"z": zn * ZR, "U": _f(sh.cell_value(r, 2)) * UR, "k": _f(sh.cell_value(r, 3)) * UR * UR})
    return out, meta["approach_flow_file"]


# ----------------------------------------------------------------------------- geometry

def box_tris(lo, hi):
    """12 outward-wound triangles of the axis-aligned box [lo, hi]."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    p = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 2, 1), (0, 3, 2),      # bottom (-z)
             (4, 5, 6), (4, 6, 7),      # top (+z)
             (0, 1, 5), (0, 5, 4),      # -y
             (1, 2, 6), (1, 6, 5),      # +x
             (2, 3, 7), (2, 7, 6),      # +y
             (3, 0, 4), (3, 4, 7)]      # -x
    return [(p[a], p[b], p[c]) for a, b, c in faces]


def boxes_c(centre):
    D = 0.20
    boxes = []
    for cx in (-0.4, 0.0, 0.4):
        for cy in (-0.4, 0.0, 0.4):
            if cx == 0.0 and cy == 0.0:
                h = {"0D": 0.0, "1D": D, "2D": 2 * D}[centre]
                if h == 0.0:
                    continue
            else:
                h = D
            boxes.append({"min": [round(cx - D / 2, 6), round(cy - D / 2, 6), 0.0],
                          "max": [round(cx + D / 2, 6), round(cy + D / 2, 6), round(h, 6)]})
    return boxes


BOX_GEOMETRY = {
    "A": {"default": [{"min": [-0.04, -0.04, 0.0], "max": [0.04, 0.04, 0.16]}]},
    "B": {"default": [{"min": [-0.025, -0.10, 0.0], "max": [0.025, 0.10, 0.20]}]},
    "C": {"0D": boxes_c("0D"), "1D": boxes_c("1D"), "2D": boxes_c("2D")},
}


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


def shells_from_tris(tris, tol=1e-9):
    """Connected components of a triangle soup by shared (welded) vertices."""
    key = lambda p: tuple(round(c / tol) for c in p)
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for t in tris:
        k0, k1, k2 = (key(p) for p in t)
        union(k0, k1)
        union(k1, k2)
    groups = defaultdict(list)
    for t in tris:
        groups[find(key(t[0]))].append(t)
    return list(groups.values())


def boxes_d():
    """The 83 shells of BD_caseD.stl, each reduced to its bounding box (they are all boxes)."""
    tris = read_ascii_stl(os.path.join(REPO, "case-d", "BD_caseD.stl"))
    boxes = []
    for shell in shells_from_tris(tris):
        pts = [p for t in shell for p in t]
        lo = [min(p[i] for p in pts) for i in range(3)]
        hi = [max(p[i] for p in pts) for i in range(3)]
        # every vertex must be a corner of the box, or this shell is not a box
        corners = {tuple(round(c, 6) for c in (x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])}
        bad = [p for p in pts if tuple(round(c, 6) for c in p) not in corners]
        if bad:
            raise ValueError(f"Case D shell is not a box: {len(bad)} off-corner vertices near {bad[0]}")
        boxes.append({"min": [round(c, 6) for c in lo], "max": [round(c, 6) for c in hi]})
    boxes.sort(key=lambda b: (b["min"][0], b["min"][1]))
    return boxes, len(tris)


def mesh_e(state):
    """Triangles of the Niigata district from the 3dm: 'bc' = buildings, 'ac' = + new construction."""
    import rhino3dm
    f = rhino3dm.File3dm.Read(os.path.join(REPO, "case-e", "case-e.3dm"))
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
            a, b, c, d = face[0], face[1], face[2], face[3]
            tris.append((vs[a], vs[b], vs[c]))
            if d != c:
                tris.append((vs[a], vs[c], vs[d]))
    return tris


def tris_of_boxes(boxes):
    out = []
    for b in boxes:
        out.extend(box_tris(b["min"], b["max"]))
    return out


def _normal(t):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    n = math.sqrt(nx * nx + ny * ny + nz * nz)
    return (nx / n, ny / n, nz / n) if n > 0 else (0.0, 0.0, 0.0)


def write_ascii_stl(path, tris, name):
    """LF-only ASCII STL (CRLF makes OpenFOAM's reader keep the \\r in the last token)."""
    with io.open(path, "w", encoding="ascii", newline="\n") as f:
        f.write(f"solid {name}\n")
        for t in tris:
            n = _normal(t)
            f.write(f"  facet normal {n[0]:.6g} {n[1]:.6g} {n[2]:.6g}\n    outer loop\n")
            for p in t:
                f.write(f"      vertex {p[0]:.6g} {p[1]:.6g} {p[2]:.6g}\n")
            f.write("    endloop\n  endfacet\n")
        f.write(f"endsolid {name}\n")


def stl_stats(tris, tol=1e-7):
    """Triangle count, bounding box, signed volume and the edge-manifold census of a soup."""
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
    return {
        "triangles": len(tris),
        "bbox_min": [round(v, 6) for v in lo], "bbox_max": [round(v, 6) for v in hi],
        "signed_volume": round(vol, 9),
        "edges": len(edges),
        "edges_shared_by_two_faces": counts.get(2, 0),
        "edges_boundary": counts.get(1, 0),
        "edges_non_manifold": sum(v for k, v in counts.items() if k > 2),
        "watertight": counts.get(2, 0) == len(edges),
    }


def orient_outward(tris, tol=1e-4):
    """Flip every closed shell whose signed volume is negative. Returns (tris, shells, flipped).

    The Niigata 3dm meshes are wound inconsistently (475 of 503 shells inward); OpenFOAM's
    snappyHexMesh and most STL consumers want outward normals.
    """
    out, flipped, shells = [], 0, 0
    for shell in shells_from_tris(tris, tol=tol):
        shells += 1
        if stl_stats(shell)["signed_volume"] < 0:
            flipped += 1
            out.extend((a, c, b) for a, b, c in shell)
        else:
            out.extend(shell)
    return out, shells, flipped


def case_geometry(case):
    """[(name, tris, boxes_or_None, note)] for a case — one entry per configuration."""
    if case in BOX_GEOMETRY:
        out = []
        for cfg, boxes in BOX_GEOMETRY[case].items():
            out.append((cfg, tris_of_boxes(boxes), boxes, "generated from the stated dimensions"))
        return out
    if case == "D":
        boxes, raw_facets = boxes_d()
        return [("default", tris_of_boxes(boxes), boxes,
                 f"rebuilt from the {len(boxes)} shells of BD_caseD.stl ({raw_facets} raw facets with duplicates and inward roofs), each reduced to its box")]
    if case == "E":
        out = []
        for state in ("bc", "ac"):
            tris, shells, flipped = orient_outward(mesh_e(state))
            out.append((state, tris, None,
                        "triangulated from case-e.3dm via rhino3dm, layers "
                        + ("'buildings'" if state == "bc" else "'buildings' + 'buildings_new_construction'")
                        + f"; {flipped} of {shells} shells were wound inward in the 3dm and are flipped outward here"))
        return out
    raise KeyError(case)


def git_head():
    try:
        with io.open(os.path.join(REPO, ".git", "HEAD"), encoding="utf-8") as f:
            ref = f.read().strip()
        if ref.startswith("ref:"):
            with io.open(os.path.join(REPO, ".git", ref[4:].strip()), encoding="utf-8") as f:
                return f.read().strip()
        return ref
    except OSError:
        return None
