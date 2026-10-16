# clean/ — schema of the cleaned AIJ UWE release (Cases A–E)

Version `1.0.0` (schema `1.0.0`). Built by `clean/build.py` from the published Zenodo files; every
transform is listed in `build.log`, every validity check in `checks.json`, every source file with its
SHA-256 in `manifest.json`. **The headers carry no units.** Units live in `units.json` (and in each
Parquet file's schema metadata under the keys `units` and `column_meaning`).

## 1. One table, long format

`points.csv` / `points.parquet` hold every measured value of every case as one row per
*(case, configuration, instrument, point, wind direction)*. Per-case copies are `cases/<id>/points.*`
(identical rows, identical column order). The per-case CSV is what `scripts/aijdata.py` reads for the
site API (`clean/manifest.json` → `cases.<id>.files.points_csv`).

| column | type | unit | meaning |
|---|---|---|---|
| `case_id` | text | — | `A` `B` `C` `D` `E` |
| `config` | text | — | `default` (A, B, D) · C: centre building `0D` / `1D` / `2D` · E: `bc` before / `ac` after construction |
| `instrument` | text | — | `split_fibre` (hot-wire split-fibre probe: vector components) · `thermistor` (omnidirectional scalar speed) |
| `point_id` | int | — | the tunnel's own point number (`No.`); shared by every configuration and direction of a case |
| `wind_direction_deg` | float | deg | A–D: the AIJ turntable angle WD (0 = flow along +x). E: meteorological FROM-direction, clockwise from north (N = 0, E = 90). **Do not turn this into a vector yourself — read `flow_dir_x/y` from `directions.csv`.** |
| `wind_direction` | text | — | compass name (E only; empty elsewhere) |
| `x` `y` `z` | float | m | case frame, section 2. Model-scale metres for A–D, FULL-scale metres for E |
| `U` `V` `W` | float | m/s | mean velocity along +x, +y, +z. **V is positive toward +y in every case** (B's published sign is flipped) |
| `uu` `vv` `ww` | float | m²/s² | velocity variances ⟨u′u′⟩ … (A publishes rms; squared here) |
| `k` | float | m²/s² | turbulent kinetic energy as published (= ½(uu+vv+ww) wherever all three exist — checked) |
| `Vs` | float | m/s | mean omnidirectional scalar speed from a thermistor. Never a vector magnitude |
| `velocity_ratio` | float | — | E only: Vs / U_ref, U_ref = approach-flow speed at z = 15.9 m full scale (3.935 m/s, section 5) |

Rules:

- **Not measured = NaN** (empty cell in CSV, null in Parquet). The sources' `-999.9`, `-` and blank
  cells all become NaN. A column a case never measures is NaN for that whole case.
- The key `(case_id, config, instrument, point_id, wind_direction_deg)` is unique. Case B's seven
  repeat measurements keep their own point numbers (README, B).
- Rows are sorted by `(config, instrument, wind_direction_deg, point_id)` within a case; cases in
  order A–E. Floats are written with `%.10g`; coordinates and variances are rounded to 1e-9.
- A *derived* quantity the source publishes beside measured ones is dropped, not carried: Case D's
  split-fibre "Vs" / "Scalar Vel." (= √(U²+V²+W²), checked to 1e-15) and "Vs/UH"; Case B's
  "1/4 power" fit column. Everything else published is here.

## 2. Frames — one per case

All five: right-handed, +z up from the ground plane, origin on the ground. Lengths in metres.

| case | origin | +x | +y | scale of the coordinates | transform from the published files |
|---|---|---|---|---|---|
| A | building centre | streamwise at WD = 0 | lateral; points on the y ≤ 0 half | model (b = 0.08 m; no model:full ratio is stated) | none (metres as published); rms → variance |
| B | slab centre | streamwise | lateral; points on y ≤ 0 | model (H = 0.20 m; ratio not stated) | x, y, z **mm → m** (×0.001); **V → −V** |
| C | array centre (= centre block centre) | streamwise at WD = 0 | lateral | model (D = 0.20 m; ratio not stated) | none; `CB` text → `config` |
| D | tower centre | streamwise at WD = 0 | lateral | model, **1:400** (H = 0.25 m = 100 m) | none (Zenodo CSVs are in metres; the workbook's mm are cross-checked) |
| E | centre of the reproduced area | **east** | **north** | **full scale**, model 1:250 | none for points; official STL ×250 (it is model scale) |

Why the sign flip on B: just outside the y < 0 flank the flow must deflect away from the centreline,
i.e. toward −y. Case A reads V = −2.893 m/s there ((−0.040, −0.050, 0.010)); Case B reads
**+3.630** at the same place ((−0.025, −0.110, 0.0125)); Case D's split fibre reads +2.055 on its +y
flank. So B's published V is positive toward −y and is flipped so that V is positive toward +y
everywhere (`checks.json`: `lateral_sign_*`). For a y-symmetric building "flip V" and "flip y" are
the same transform; V is flipped so the coordinates stay the drawing's.

Why E keeps a geographic frame: the district is real, its points and its STL are published in
east/north coordinates, and its 16 directions are compass names. "+x along the wind" is a property
of A–D only.

### Wind direction → flow vector (`directions.csv`)

`directions.csv` has one row per `(case_id, config, instrument, wind_direction_deg)` with
`flow_dir_x`, `flow_dir_y` = the unit vector the mean wind **blows toward** in the case frame, the
row and measured counts, and `sense_basis` / `status` saying what fixes the rotation sense:

| case | flow_dir(WD) | how the sense is known |
|---|---|---|
| A, B | (1, 0) | definition |
| C | (cos WD, **−sin WD**) | measured from the data: the WD = 45° field is mirror-symmetric about y = −x (mean |ΔVs| 0.10–0.13 m/s, the experiment's repeatability) and not about y = +x (0.52–0.80). Figure 3 of the data paper draws the opposite sense — QUESTIONS Q1 |
| D | (cos WD, **+sin WD**) for 22.5°, 45° | **corroborated by solved fields**: the array is exactly y-mirror symmetric, so the sense cannot be settled from the data; it is taken from Figure 4 of the data paper, and Eddy3D's solved fields score R 0.80 / 0.85 in this sense against 0.40 / 0.17 mirrored (22.5° / 45°) — QUESTIONS Q2 |
| E | (−sin WD, −cos WD) | definition: FROM-direction, +y north (compass rose in `MP_caseE.png`); frame verified by all 80 points lying in open space and a 10° rotation control putting 26 inside buildings |

Note C and D disagree in sense. That is what the sources say today; it is the first question to
put to the data collectors.

## 3. Approach flow (`approach_flow.csv` / `.parquet`)

One row per published height: `case_id, z, U, uu, vv, ww, k` in the same units as section 1.
A: 24 heights (rms squared); B: 12; C: 16 (U and uu only); D: 13 (U and k); E: 12 heights
de-normalised from `z/ZR, U/UR, k/UR²` with ZR = 250 m (1 m model), UR = 7.8 m/s, in full-scale
metres. `manifest.json → cases.<id>.inflow` carries the measured U_H, the log-law fit(s)
(κ = 0.41, least squares on the published points, window stated, residual and errors at the heights
that matter) and a power-law fit — reproduced in `build.py`, never typed in.

## 4. Geometry (`cases/<id>/geometry*.stl`, `geometry.json`)

ASCII STL, LF line endings, outward normals, **metres in the same frame as the points** (so the E
files are full-scale and ~400 m across). `geometry.json` lists each file, its provenance, triangle
count, bounding box, watertightness, and — for A–D — the axis-aligned boxes it is made of, so a
consumer need not parse an STL at all.

| case | files | made from |
|---|---|---|
| A, B | `geometry.stl` | the readme's stated dimensions, centred (the MP drawings) |
| C | `geometry_0D/1D/2D.stl` | nine 0.20 m cubes on a 0.40 m pitch; the pitch is verified against the 120-point grid (the 49 absent nodes of the 13 × 13 lattice are exactly the nine footprints) and read from `MP-z-caseC.png` |
| D | `geometry.stl` | the 83 closed shells of the published `BD_caseD.stl`, each reduced to its box (the published file has 576 duplicate facets and every roof wound inward; the rebuild is watertight with the analytic volume 0.0214766 m³) |
| E | `geometry_ac.stl` | the official `BD_caseE.stl` scaled ×250 (after construction; 60,101 triangles; NOT watertight as published, 5,253 open edges) |
| E | `geometry_ac_3dm.stl`, `geometry_bc_3dm.stl` | Eddy3D-side reconstructions from `case-e.3dm` (layers `buildings` + `buildings_new_construction`); **the before-construction state has no published source** — provisional |

## 5. Case E normalisation

All 2,560 published ratios are integer multiples of one quantum q = 0.0198204 (55 distinct levels):
the sheet holds U/UR quantised at 0.01 and re-normalised by UR / U_ref, so
U_ref = 0.01 · UR / q = **3.935 m/s** at z = 15.9 m. Log-interpolating the published profile at
15.9 m gives 3.973 m/s (+1 %); the data paper says "4.0 m/s". The data's own resolution is ±q/2 =
±0.0099 — 3 % of the median ratio and 10 % of the smallest (5 quanta). Zenodo's `RS_caseE.csv` is
the workbook rounded to 2 dp; this release carries the workbook's full values.

## 6. Provenance and determinism

`manifest.json → cases.<id>.provenance` lists every source file read, with SHA-256 and byte size.
For D and E the official Zenodo files the repository clone lacks were downloaded into
`clean/sources/zenodo_case{D,E}/` (checksums in `SHA256SUMS.txt` beside them); the clone's
workbooks are byte-identical in content to Zenodo's `LF_*.xls` and are used as cross-checks. Two
consecutive builds produce byte-identical files (49 outputs hashed), so a changed hash means a
changed input or a changed `build.py`.

## 7. Site API

`scripts/aijdata.py` reads `clean/manifest.json`, finds each case's `points_csv`, maps the columns
by name and serves them unchanged through `docs/api/cases/<id>/points.{json,csv}`
(`points_source` in each file says so). Column `case_id` is deliberately not named `case`, which
that adapter would read as the configuration.
