---
title: "Case A — 1:1:2 building"
parent: Cases
nav_order: 1
---

# Case A — 1:1:2 building

Isolated 1:1:2 building, velocity field (split-fibre hot wire).

![Case A — 1:1:2 building]({{ '/assets/geom_caseA.png' | relative_url }})

## Configuration

| | |
|---|---|
| building | 1:1:2 (width : depth : height) prism |
| b_m | 0.08 |
| H_m | 0.16 |
| Re_H | 24000 |
| U_H_m_s | 4.491 |
| wind_directions_deg | 0 |
| measurement_planes | vertical centre plane y/b = 0, horizontal z/b = 0.125, horizontal z/b = 1.25 |
| instrument | hot-wire anemometer, split-fibre probes (DANTEC 55R55 streamwise, 55R57 spanwise/vertical), 1000 Hz, 60 s per point, 500 Hz low-pass |
| tunnel | Technical Research Institute, Shimizu Corporation, Tokyo |
| scale_note | model scale; Eddy3D solves it at 1:100 (b = 8 m, H = 16 m) with the tunnel velocities |

## Frame and units

| | |
|---|---|
| origin | building centre on the ground plane |
| x | +x streamwise (the wind at WD = 0 blows toward +x); building spans x in [-0.04, 0.04] |
| y | +y lateral; building spans y in [-0.04, 0.04]; points published on the y <= 0 half by the tunnel's symmetry convention |
| z | +z up from the ground; roof at z = 0.16 |
| lateral_sign_applied | 1 |
| coordinate_scale_applied | 1.0 |
| unit: length | m (model scale) |
| unit: velocity | m/s |
| unit: variance | m^2/s^2 |
| unit: k | m^2/s^2 |

## Reference data

Source in this repository: `Case_A_cleaned/RS-caseA.csv` (approach flow: `Case_A_cleaned/AF_caseA.csv`).

The cleaned table has **186 rows** over **186 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction_deg`, `x`, `y`, `z`, `U`, `V`, `W`, `uu`, `vv`, `ww`, `k`.

| configuration | points |
|---|---|
| config default, wind_direction_deg 0.0 | 186 |

### Inflow

| | |
|---|---|
| method | log law, kappa = 0.41, least squares over z = 0.02 ... 2H on the case's own approach-flow file |
| u_star_m_s | 0.343 |
| z0_mm | 0.668 |
| U_H_measured_m_s | 4.491 |
| log_law_error_at_H | +2.0 % |

## Things to know before comparing

- Lateral velocity V is positive toward +y (checked: V = -2.893 m/s at (-0.040, -0.050, 0.010), just outside the y < 0 flank, deflecting away from the centreline). Case B uses the OPPOSITE sign; the API flips Case B so both agree.
- Coordinates are metres (Case B's are millimetres in the published file).
- Case A's turbulence columns are rms values (u_rms, ...). The API serves VARIANCES (uu = u_rms^2) so A and B share one column meaning.

## Validation

**openfoam12-realizableKE** — solved time 3000, scale 1:100, 186 points; reattachment length L_r/H = 1.49. U by U_H, k by U_H^2 (the benchmark's own convention); hit rate D = 0.25, W = 0.05 U_H.

| | velocity.U | velocity.V | velocity.W | k |
|---|---|---|---|---|
| **R** | +0.955 | +0.961 | +0.708 | +0.480 |
| **FAC2** | 0.817 | 0.349 | 0.398 | 0.667 |
| **FB** | +0.185 | -0.207 | -1.501 | +0.478 |
| **hit rate** | 0.586 | 0.892 | 0.801 | 0.177 |

![agreement]({{ '/assets/aij_agreement.png' | relative_url }})

![profiles]({{ '/assets/aij_profiles.png' | relative_url }})

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| endpoint | |
|---|---|
| case | [`/api/cases/A.json`]({{ '/api/cases/A.json' | relative_url }}) |
| points (JSON) | [`/api/cases/A/points.json`]({{ '/api/cases/A/points.json' | relative_url }}) |
| points (CSV) | [`/api/cases/A/points.csv`]({{ '/api/cases/A/points.csv' | relative_url }}) |
| geometry | [`/api/cases/A/geometry.json`]({{ '/api/cases/A/geometry.json' | relative_url }}) |
| geometry STL | [`/api/cases/A/geometry.stl`]({{ '/api/cases/A/geometry.stl' | relative_url }}) |
| validation | [`/api/cases/A/validation.json`]({{ '/api/cases/A/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Takeshi Ishihara (The University of Tokyo), Kazuki Hibi (Numerical Flow Design)
- Editors and distributors: Yoshihide Tominaga (Niigata Institute of Technology), Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15050147](https://doi.org/10.5281/zenodo.15050147)
- Citation requested: Meng, Y., & Hibi, K. (1998). Turbulent measurements of the flow field around a high-rise building. Journal of Wind Engineering, JAWE, 76, 55-64. https://doi.org/10.5359/jawe.1998.76_55
- Licence: CC BY 4.0
