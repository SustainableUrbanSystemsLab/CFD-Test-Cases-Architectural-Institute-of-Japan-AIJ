---
title: "Case D — high-rise among city blocks"
parent: Cases
nav_order: 4
---

# Case D — high-rise among city blocks

1:1:4 tower in a regular array of 82 low blocks, pedestrian-height scalar speed (thermistor, 3 wind directions) plus a 33-point split-fibre velocity field at WD = 0.

<figure class="figure">
<img src="{{ '/assets/geometry/case-d.png' | relative_url }}" alt="Case D — high-rise among city blocks">
<figcaption><strong>Figure 1.</strong> A 0.25 m tower (blue) among 82 low blocks over 1.40 m × 1.35 m (1:400 model scale); the arrow is WD = 0°.</figcaption>
</figure>

## Configuration

| Parameter | Value |
|---|---|
| Tower | 0.25H x 0.25H x H = 62.5 x 62.5 x 250 mm (1:1:4) |
| Height H (m) | 0.25 |
| Blocks | 82 blocks of 0.4H x 0.4H x 0.1H = 100 x 100 x 25 mm |
| Roads | 0.1H / 0.2H / 0.3H = 25 / 50 / 75 mm; 9 columns in x (pitch alternating 175 / 150 mm), 11 rows in y (pitch 125 mm); corners cut by the turntable circle |
| Array extent (m) | **x**: -0.7, 0.7<br>**y**: -0.675, 0.675<br>**z**: 0, 0.25 |
| Scale | 1:400 (H = 100 m full scale; the 5 mm measurement plane = 2 m) |
| Reynolds number Re_H | 110000 |
| U_H (m/s) | 6.65 |
| Wind directions (°) | 0, 22.5, 45 |
| Measurement height (m) | 0.005 |
| Instrument | thermistor anemometer (78 points x 3 directions; 66 measured per direction, 12 points in the band around the tower unmeasured) and split-fibre probe (33 points at WD = 0: U, V, W, variances, k) |
| Wind tunnel | see the data paper (Kikumoto et al. 2026, section 3.4) |

## Frame and units

| Property | Definition |
|---|---|
| Origin | tower centre on the ground plane (the array's bounding box is centred on it) |
| x | +x streamwise at WD = 0 (the 0 deg thermistor field is exactly y-mirror symmetric; the split-fibre U is positive at the stream-like points and negative in the tower's windward horseshoe) |
| y | +y lateral |
| z | +z up; all points at z = 0.005 |
| Wind direction convention | +x toward +y, read from Figure 4 of the data paper. The array is exactly y-mirror symmetric, so the measurements alone cannot settle the rotation sense (headings +theta and -theta give exact mirror fields); solved Eddy3D fields corroborate Figure 4's sense: R 0.80 (22.5 deg) and 0.85 (45 deg) in it, 0.40 and 0.17 mirrored. |
| Lateral sign applied | 1 |
| Coordinate scale applied | 0.001 |
| Unit of length | m (model scale; converted from the workbook's millimetres) |
| Unit of velocity | m/s |
| Unit of variance | m^2/s^2 |
| Unit of k | m^2/s^2 |

## Reference data

Source in this repository: `case-d/LF_caseD.xls` (approach flow: `case-d/LF_caseD.xls [sheet Inflow]`).

The cleaned table has **267 rows** over **78 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction_deg`, `x`, `y`, `z`, `U`, `V`, `W`, `uu`, `vv`, `ww`, `k`, `Vs`.

Unmeasured cells (null): U 234, V 234, W 234, uu 234, vv 234, ww 234, k 234, Vs 69.

| Configuration | Points |
|---|---|
| thermistor, WD 0° | 78 (66 measured) |
| thermistor, WD 22.5° | 78 (66 measured) |
| thermistor, WD 45° | 78 (66 measured) |
| split fibre, WD 0° | 33 (33 measured) |

### Inflow

| Property | Value |
|---|---|
| Method | log law, kappa = 0.41, least squares on the workbook's 13-point profile (z = 5 ... 1200 mm); two windows, because the measurement plane z/H = 0.02 sits below the 0.02 ... 2H window used for Cases A and B |
| Fit window | z range 0.005 ... 2H; Friction velocity u* (m/s) 0.3418; Roughness length z₀ (mm) 0.0859; error at z 5mm -11.2 %; profile rms 7.9 %; inlet k m2 s2 0.3895; inlet k vs tunnel -26 % to -48 % |
| Fit window | z range 0.02 ... 2H; Friction velocity u* (m/s) 0.424; Roughness length z₀ (mm) 0.4033; error at z 5mm -30.0 %; profile rms 12.5 % / 4.7 %; inlet k m2 s2 0.5991; inlet k vs tunnel +13 % to -20 % |
| Power-law exponent, fitted | 0.189 |
| Power-law exponent, data paper | 0.25 |
| Note | derived during scoping, not published by AIJ; a log-law inlet cannot be right at both the measurement plane and the upper profile |

## Known data issues

- All of Case D's data lives in LF_caseD.xls, a genuine OLE2/BIFF8 workbook (read it with xlrd 2.x; openpyxl cannot). Sheets: 'Geometry&Points', 'Inflow', 'Results (Exp_S)' (split fibre, WD = 0), 'Results (Exp_T)' (thermistor, 0 / 22.5 / 45 deg).
- Coordinates are millimetres in the workbook; the API serves metres.
- The shipped BD_caseD.stl is dirty: 1572 facets of which 576 are duplicates, and all 83 roofs are wound inward (signed volume 0.011159 m^3 against the true 0.021477 m^3). The API's geometry.stl is rebuilt from the 83 shells' bounding boxes: 996 facets, watertight, volume 0.021477 m^3.
- The thermistor reads a SCALAR speed. Over the 33 points where both instruments overlap at WD = 0, the ratio of mean thermistor speed to mean |U| is 1.342 (the mean of the per-point ratios is 1.50). sqrt(|U|^2 + 2k) from the split-fibre data matches the thermistor to FB +0.058, R 0.947; |U| alone to FB +0.292, R 0.872.
- Unmeasured thermistor cells are '-' in the workbook (null here). At WD = 0 the 66 measured values are 33 exact mirror pairs, so only 33 are independent; at 22.5 and 45 deg all 66 are independent.
- A prior Eddy3D comparison kept in the folder (case-d-eddy3d-prior-comparison.xlsx) scores R = +0.096 against the thermistor: a frame or geometry error, not a closure result. It is not a validation.

## Validation

### OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor)

| Metric | WD 0°, thermistor Vs · √(\|U\|²+2k) | WD 0°, thermistor Vs · \|U\| | WD 0°, split fibre \|U\| | WD 0°, split fibre U | WD 22.5°, thermistor Vs · √(\|U\|²+2k) | WD 22.5°, thermistor Vs · \|U\| | WD 22.5°, rotation sense mirrored (control) | WD 45°, thermistor Vs · √(\|U\|²+2k) | WD 45°, thermistor Vs · \|U\| | WD 45°, rotation sense mirrored (control) |
|---|---|---|---|---|---|---|---|---|---|---|
| **R** | +0.803 | +0.811 | +0.853 | +0.945 | +0.803 | +0.783 | +0.400 | +0.854 | +0.844 | +0.170 |
| **FAC2** | 0.727 | 0.667 | 0.758 | 0.485 | 0.924 | 0.818 | 0.742 | 0.894 | 0.818 | 0.697 |
| **FB** | +0.214 | +0.362 | +0.071 | +0.668 | +0.050 | +0.154 | +0.050 | +0.090 | +0.170 | +0.090 |
| **hit rate** | 0.485 | 0.394 | 0.515 | 0.515 | 0.667 | 0.636 | 0.364 | 0.712 | 0.697 | 0.242 |
| **n** | 66 | 66 | 33 | 33 | 66 | 66 | 66 | 66 | 66 | 66 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/D/pairs/openfoam12-realizableKE.csv`]({{ '/api/cases/D/pairs/openfoam12-realizableKE.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseDContainerE2E (EDDY3D_AIJD_HEADINGS=0,22.5,45); figure validation/plot_case_d_openfoam.py.

### Eddy3D ML wind surrogate (pedestrian height)

| Metric | Vs, thermistor, 3 WD | \|U\|, split fibre, WD 0 | Vs, WD 0, lattice cut at ±250 m | wind reversed (control) |
|---|---|---|---|---|
| **R** | +0.325 | +0.587 | +0.220 | +0.492 |
| **FAC2** | 0.343 | 0.515 | 0.636 | 0.470 |
| **FB** | +0.673 | +0.231 | +0.489 | +0.555 |
| **hit rate** | 0.167 | 0.242 | 0.273 | 0.197 |
| **n** | 198 | 33 | 66 | 66 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/D/pairs/ml-surrogate.csv`]({{ '/api/cases/D/pairs/ml-surrogate.csv' | relative_url }}). Reproduce: Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py.

<figure class="figure">
<img src="{{ '/assets/figures/case-d-openfoam-agreement.png' | relative_url }}" alt="case-d-openfoam-agreement.png">
<figcaption><strong>Figure 2.</strong> Case D, OpenFOAM 12, wind directions 0°, 22.5° and 45°: measured thermistor Vs/U_H against the modelled √(|U|²+2k)/U_H (filled) and |U|/U_H (hollow), and the split-fibre |U| against the modelled |U| at 0°. At 0° the 66 thermistor points are 33 mirror pairs.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/ml-surrogate-agreement.png' | relative_url }}" alt="ml-surrogate-agreement.png">
<figcaption><strong>Figure 3.</strong> Eddy3D ML surrogate (Yel-2.0): measured against predicted pedestrian-height speed, one panel per case, with the 1:1 line and the factor-of-two band.</figcaption>
</figure>

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| Resource | Endpoint |
|---|---|
| Case | [`/api/cases/D.json`]({{ '/api/cases/D.json' | relative_url }}) |
| Points (JSON) | [`/api/cases/D/points.json`]({{ '/api/cases/D/points.json' | relative_url }}) |
| Points (CSV) | [`/api/cases/D/points.csv`]({{ '/api/cases/D/points.csv' | relative_url }}) |
| Approach flow (CSV) | [`/api/cases/D/approach_flow.csv`]({{ '/api/cases/D/approach_flow.csv' | relative_url }}) |
| Geometry | [`/api/cases/D/geometry.json`]({{ '/api/cases/D/geometry.json' | relative_url }}) |
| Geometry (STL) | [`/api/cases/D/geometry.stl`]({{ '/api/cases/D/geometry.stl' | relative_url }}) |
| Validation | [`/api/cases/D/validation.json`]({{ '/api/cases/D/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Yoshihide Tominaga (Niigata Institute of Technology)
- Editors and distributors: Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15402668](https://doi.org/10.5281/zenodo.15402668)
- Citation requested: Kikumoto, H. et al. (2026). Japan Architectural Review 9(1), e70083, section 3.4.
- Licence: CC BY 4.0
