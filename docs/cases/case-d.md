---
title: "Case D — high-rise among city blocks"
parent: Cases
nav_order: 4
---

# Case D — high-rise among city blocks

1:1:4 tower in a regular array of 82 low blocks, pedestrian-height scalar speed (thermistor, 3 wind directions) plus a 33-point split-fibre velocity field at WD = 0.

![Case D — high-rise among city blocks]({{ '/assets/geom_caseD.png' | relative_url }})

## Configuration

| | |
|---|---|
| tower | 0.25H x 0.25H x H = 62.5 x 62.5 x 250 mm (1:1:4) |
| H_m | 0.25 |
| blocks | 82 blocks of 0.4H x 0.4H x 0.1H = 100 x 100 x 25 mm |
| roads | 0.1H / 0.2H / 0.3H = 25 / 50 / 75 mm; 9 columns in x (pitch alternating 175 / 150 mm), 11 rows in y (pitch 125 mm); corners cut by the turntable circle |
| array_extent_m | **x**: -0.7, 0.7<br>**y**: -0.675, 0.675<br>**z**: 0, 0.25 |
| scale | 1:400 (H = 100 m full scale; the 5 mm measurement plane = 2 m) |
| Re_H | 110000 |
| U_H_m_s | 6.65 |
| wind_directions_deg | 0, 22.5, 45 |
| measurement_height_m | 0.005 |
| instrument | thermistor anemometer (78 points x 3 directions; 66 measured per direction, 12 points in the band around the tower unmeasured) and split-fibre probe (33 points at WD = 0: U, V, W, variances, k) |
| tunnel | see the data paper (Kikumoto et al. 2026, section 3.4) |

## Frame and units

| | |
|---|---|
| origin | tower centre on the ground plane (the array's bounding box is centred on it) |
| x | +x streamwise at WD = 0 (the 0 deg thermistor field is exactly y-mirror symmetric; the split-fibre U is positive at the stream-like points and negative in the tower's windward horseshoe) |
| y | +y lateral |
| z | +z up; all points at z = 0.005 |
| wind_direction_rotation | +x toward +y, read from Figure 4 of the data paper. The array is exactly y-mirror symmetric, so the rotation sense CANNOT be settled from the measurements: headings +theta and -theta give exact mirror fields. Treat 22.5 and 45 deg with that caveat. |
| lateral_sign_applied | 1 |
| coordinate_scale_applied | 0.001 |
| unit: length | m (model scale; converted from the workbook's millimetres) |
| unit: velocity | m/s |
| unit: variance | m^2/s^2 |
| unit: k | m^2/s^2 |

## Reference data

Source in this repository: `case-d/LF_caseD.xls` (approach flow: `case-d/LF_caseD.xls [sheet Inflow]`).

The cleaned table has **267 rows** over **78 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction_deg`, `x`, `y`, `z`, `U`, `V`, `W`, `uu`, `vv`, `ww`, `k`, `Vs`.

Unmeasured cells (null): U 234, V 234, W 234, uu 234, vv 234, ww 234, k 234, Vs 69.

| configuration | points |
|---|---|
| instrument thermistor, wind_direction_deg 0.0 | 78 (66 measured) |
| instrument thermistor, wind_direction_deg 22.5 | 78 (66 measured) |
| instrument thermistor, wind_direction_deg 45.0 | 78 (66 measured) |
| instrument split_fibre, wind_direction_deg 0.0 | 33 (33 measured) |

### Inflow

| | |
|---|---|
| method | log law, kappa = 0.41, least squares on the workbook's 13-point profile (z = 5 ... 1200 mm); two windows, because the measurement plane z/H = 0.02 sits below the 0.02 ... 2H window used for Cases A and B |
| window | z_range 0.005 ... 2H; u_star_m_s 0.3418; z0_mm 0.0859; error_at_z_5mm -11.2 %; profile_rms 7.9 %; inlet_k_m2_s2 0.3895; inlet_k_vs_tunnel -26 % to -48 % |
| window | z_range 0.02 ... 2H; u_star_m_s 0.424; z0_mm 0.4033; error_at_z_5mm -30.0 %; profile_rms 12.5 % / 4.7 %; inlet_k_m2_s2 0.5991; inlet_k_vs_tunnel +13 % to -20 % |
| power_law_exponent_fitted | 0.189 |
| power_law_exponent_paper | 0.25 |
| note | derived during scoping, not published by AIJ; a log-law inlet cannot be right at both the measurement plane and the upper profile |

## Things to know before comparing

- All of Case D's data lives in LF_caseD.xls, a genuine OLE2/BIFF8 workbook (read it with xlrd 2.x; openpyxl cannot). Sheets: 'Geometry&Points', 'Inflow', 'Results (Exp_S)' (split fibre, WD = 0), 'Results (Exp_T)' (thermistor, 0 / 22.5 / 45 deg).
- Coordinates are millimetres in the workbook; the API serves metres.
- The shipped BD_caseD.stl is dirty: 1572 facets of which 576 are duplicates, and all 83 roofs are wound inward (signed volume 0.011159 m^3 against the true 0.021477 m^3). The API's geometry.stl is rebuilt from the 83 shells' bounding boxes: 996 facets, watertight, volume 0.021477 m^3.
- The thermistor reads a SCALAR speed. Over the 33 points where both instruments overlap at WD = 0, the ratio of mean thermistor speed to mean |U| is 1.342 (the mean of the per-point ratios is 1.50). sqrt(|U|^2 + 2k) from the split-fibre data matches the thermistor to FB +0.058, R 0.947; |U| alone to FB +0.292, R 0.872.
- Unmeasured thermistor cells are '-' in the workbook (null here). At WD = 0 the 66 measured values are 33 exact mirror pairs, so only 33 are independent; at 22.5 and 45 deg all 66 are independent.
- A prior Eddy3D comparison kept in the folder (case-d-eddy3d-prior-comparison.xlsx) scores R = +0.096 against the thermistor: a frame or geometry error, not a closure result. It is not a validation.

## Validation

### Eddy3D ML wind surrogate (pedestrian height)

| | Vs, thermistor, 3 WD | \|U\|, split fibre, WD 0 | Vs, WD 0, lattice cut at ±250 m | wind reversed (control) |
|---|---|---|---|---|
| **R** | +0.325 | +0.587 | +0.220 | +0.492 |
| **FAC2** | 0.343 | 0.515 | 0.636 | 0.470 |
| **FB** | +0.673 | +0.231 | +0.489 | +0.555 |
| **hit rate** | 0.167 | 0.242 | 0.273 | 0.197 |
| **n** | 198 | 33 | 66 | 66 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Reproduce: Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_aij_ml.py.

![aij_ml_agreement.png]({{ '/assets/aij_ml_agreement.png' | relative_url }})

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| endpoint | |
|---|---|
| case | [`/api/cases/D.json`]({{ '/api/cases/D.json' | relative_url }}) |
| points (JSON) | [`/api/cases/D/points.json`]({{ '/api/cases/D/points.json' | relative_url }}) |
| points (CSV) | [`/api/cases/D/points.csv`]({{ '/api/cases/D/points.csv' | relative_url }}) |
| geometry | [`/api/cases/D/geometry.json`]({{ '/api/cases/D/geometry.json' | relative_url }}) |
| geometry STL | [`/api/cases/D/geometry.stl`]({{ '/api/cases/D/geometry.stl' | relative_url }}) |
| validation | [`/api/cases/D/validation.json`]({{ '/api/cases/D/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Yoshihide Tominaga (Niigata Institute of Technology)
- Editors and distributors: Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15402668](https://doi.org/10.5281/zenodo.15402668)
- Citation requested: Kikumoto, H. et al. (2026). Japan Architectural Review 9(1), e70083, section 3.4.
- Licence: CC BY 4.0
