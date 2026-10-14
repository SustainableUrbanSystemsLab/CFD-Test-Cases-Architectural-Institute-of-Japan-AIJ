---
title: "Case B — 1:4:4 slab"
parent: Cases
nav_order: 2
---

# Case B — 1:4:4 slab

Isolated 1:4:4 slab, velocity field (split-fibre hot wire).

![Case B — 1:4:4 slab]({{ '/assets/geom_caseB.png' | relative_url }})

## Configuration

| | |
|---|---|
| building | 1:4:4 (depth : width : height) slab |
| depth_m | 0.05 |
| width_m | 0.2 |
| H_m | 0.2 |
| Re_H | 72000 |
| U_H_m_s | 5.133 |
| wind_directions_deg | 0 |
| measurement_planes | vertical centre plane y/H = 0, horizontal z/H = 1/16 |
| instrument | hot-wire anemometer, split-fibre probe, 100 Hz, 60 s per point |
| tunnel | Niigata Institute of Technology, Kashiwazaki |
| scale_note | model scale; Eddy3D solves it at 1:100 (H = 20 m) with the tunnel velocities |

## Frame and units

| | |
|---|---|
| origin | building centre on the ground plane |
| x | +x streamwise (the wind at WD = 0 blows toward +x); slab spans x in [-0.025, 0.025] |
| y | +y lateral; slab spans y in [-0.10, 0.10]; points published on the y <= 0 half by the tunnel's symmetry convention |
| z | +z up from the ground; roof at z = 0.20 |
| lateral_sign_applied | -1 |
| coordinate_scale_applied | 0.001 |
| unit: length | m (model scale; converted from the published millimetres) |
| unit: velocity | m/s |
| unit: variance | m^2/s^2 |
| unit: k | m^2/s^2 |

## Reference data

Source in this repository: `Case_B_cleaned/RS_caseB.csv` (approach flow: `Case_B_cleaned/AF_caseB.csv`).

The cleaned table has **224 rows** over **224 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction_deg`, `x`, `y`, `z`, `U`, `V`, `W`, `uu`, `vv`, `ww`, `k`.

| configuration | points |
|---|---|
| config default, wind_direction_deg 0.0 | 224 |

### Inflow

| | |
|---|---|
| method | log law, kappa = 0.41, least squares over z = 0.02 ... 2H on the case's own approach-flow file |
| u_star_m_s | 0.399 |
| z0_mm | 0.882 |
| U_H_measured_m_s | 5.133 |
| log_law_error_at_H | +2.9 % |

## Things to know before comparing

- The published coordinates are MILLIMETRES (x[mm]) while velocities are m/s. The API serves metres (coordinate_scale_applied = 0.001). Read as metres, every probe lands 1000x too far out.
- The published lateral velocity V is positive toward -y (V = +3.630 m/s at (-0.025, -0.110, 0.013), just outside the y < 0 flank where the flow must deflect toward -y). The API multiplies V by -1 (lateral_sign_applied = -1) so that V is positive toward +y as in Case A. Scored without this, Case B's V comes out at R = -0.910 against R = +0.959 for U on the same points.
- The RANS solution is symmetric, so model V = 0 on the centre plane while the tunnel measures small non-zero values there.

## Validation

**openfoam12-realizableKE** — solved time 3000, scale 1:100, 224 points; reattachment length L_r/H = 3.27. U by U_H, k by U_H^2 (the benchmark's own convention); hit rate D = 0.25, W = 0.05 U_H.

| | velocity.U | velocity.V | velocity.W | k |
|---|---|---|---|---|
| **R** | +0.959 | +0.910 | +0.929 | +0.399 |
| **FAC2** | 0.701 | 0.281 | 0.536 | 0.562 |
| **FB** | +0.240 | +0.370 | +0.263 | +0.463 |
| **hit rate** | 0.562 | 0.612 | 0.808 | 0.223 |

![agreement]({{ '/assets/aij_agreement.png' | relative_url }})

![profiles]({{ '/assets/aij_profiles.png' | relative_url }})

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| endpoint | |
|---|---|
| case | [`/api/cases/B.json`]({{ '/api/cases/B.json' | relative_url }}) |
| points (JSON) | [`/api/cases/B/points.json`]({{ '/api/cases/B/points.json' | relative_url }}) |
| points (CSV) | [`/api/cases/B/points.csv`]({{ '/api/cases/B/points.csv' | relative_url }}) |
| geometry | [`/api/cases/B/geometry.json`]({{ '/api/cases/B/geometry.json' | relative_url }}) |
| geometry STL | [`/api/cases/B/geometry.stl`]({{ '/api/cases/B/geometry.stl' | relative_url }}) |
| validation | [`/api/cases/B/validation.json`]({{ '/api/cases/B/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Yoshihide Tominaga (Niigata Institute of Technology)
- Editors and distributors: Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15401455](https://doi.org/10.5281/zenodo.15401455)
- Citation requested: Miyazaki, T., Tominaga, Y. (2003). Wind tunnel experiment on flow field around a building model with a scale ratio of 4:4:1 placed within the surface boundary layer. Proc. Annual Meeting of Hokuriku Chapter, AIJ, 201-204 (in Japanese). https://www.aij.or.jp/paper/detail.html?productId=313933
- Licence: CC BY 4.0
