---
title: "Case B — 1:4:4 slab"
parent: Cases
nav_order: 2
---

# Case B — 1:4:4 slab

Isolated 1:4:4 slab, velocity field (split-fibre hot wire).

<figure class="figure">
<img src="{{ '/assets/geometry/case-b.png' | relative_url }}" alt="Case B — 1:4:4 slab">
<figcaption><strong>Figure 1.</strong> Isolated 1:4:4 slab, 0.05 m along the wind, 0.20 m across, 0.20 m tall (model scale); the wind blows along +x.</figcaption>
</figure>

## Configuration

| Parameter | Value |
|---|---|
| Building | 1:4:4 (depth : width : height) slab |
| Depth (m) | 0.05 |
| Width (m) | 0.2 |
| Height H (m) | 0.2 |
| Reynolds number Re_H | 72000 |
| U_H (m/s) | 5.133 |
| Wind directions (°) | 0 |
| Measurement planes | vertical centre plane y/H = 0, horizontal z/H = 1/16 |
| Instrument | hot-wire anemometer, split-fibre probe, 100 Hz, 60 s per point |
| Wind tunnel | Niigata Institute of Technology, Kashiwazaki |
| Scale, note | model scale; Eddy3D solves it at 1:100 (H = 20 m) with the tunnel velocities |

## Frame and units

| Property | Definition |
|---|---|
| Origin | building centre on the ground plane |
| x | +x streamwise (the wind at WD = 0 blows toward +x); slab spans x in [-0.025, 0.025] |
| y | +y lateral; slab spans y in [-0.10, 0.10]; points published on the y <= 0 half by the tunnel's symmetry convention |
| z | +z up from the ground; roof at z = 0.20 |
| Lateral sign applied | -1 |
| Coordinate scale applied | 0.001 |
| Unit of length | m (model scale; converted from the published millimetres) |
| Unit of velocity | m/s |
| Unit of variance | m^2/s^2 |
| Unit of k | m^2/s^2 |

## Reference data

Source in this repository: `case-b/RS_caseB.csv` (approach flow: `case-b/AF_caseB.csv`).

The cleaned table has **224 rows** over **224 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction_deg`, `x`, `y`, `z`, `U`, `V`, `W`, `uu`, `vv`, `ww`, `k`.

| Configuration | Points |
|---|---|
| default, WD 0° | 224 |

### Inflow

| Property | Value |
|---|---|
| Method | log law, kappa = 0.41, least squares over z = 0.02 ... 2H on the case's own approach-flow file |
| Friction velocity u* (m/s) | 0.399 |
| Roughness length z₀ (mm) | 0.882 |
| U_H, measured (m/s) | 5.133 |
| Log-law error at H | +2.9 % |

## Known data issues

- The published coordinates are MILLIMETRES (x[mm]) while velocities are m/s. The API serves metres (coordinate_scale_applied = 0.001). Read as metres, every probe lands 1000x too far out.
- The published lateral velocity V is positive toward -y (V = +3.630 m/s at (-0.025, -0.110, 0.013), just outside the y < 0 flank where the flow must deflect toward -y). The API multiplies V by -1 (lateral_sign_applied = -1) so that V is positive toward +y as in Case A. Scored without this, Case B's V comes out at R = -0.910 against R = +0.959 for U on the same points.
- The RANS solution is symmetric, so model V = 0 on the centre plane while the tunnel measures small non-zero values there.

## Validation

### OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor)

Reattachment length L_r/H = 3.27.

| Metric | U | V | W | k |
|---|---|---|---|---|
| **R** | +0.959 | +0.910 | +0.929 | +0.399 |
| **FAC2** | 0.701 | 0.281 | 0.536 | 0.562 |
| **FB** | +0.240 | +0.370 | +0.263 | +0.463 |
| **hit rate** | 0.562 | 0.612 | 0.808 | 0.223 |
| **n** | 224 | 224 | 224 | 224 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/B/pairs/openfoam12-realizableKE.csv`]({{ '/api/cases/B/pairs/openfoam12-realizableKE.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseBContainerE2E; figures validation/plot_cases_ab_openfoam.py.

### OpenLB (Eddy3D LBM)

Reattachment length L_r/H = 2.71.

| Metric | U | U, points ≥ 2 dx | V | W | k (resolved) | V, lateral sign flipped (control) |
|---|---|---|---|---|---|---|
| **R** | +0.790 | +0.900 | +0.831 | +0.774 | +0.486 | -0.831 |
| **FAC2** | 0.375 | 0.642 | 0.129 | 0.237 | 0.045 | 0.138 |
| **FB** | +0.280 | -0.072 | +1.392 | +0.376 | +1.641 | +2.873 |
| **hit rate** | 0.290 | 0.516 | 0.549 | 0.652 | 0.004 | 0.491 |
| **n** | 224 | 95 | 224 | 224 | 224 | 224 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/B/pairs/openlb.csv`]({{ '/api/cases/B/pairs/openlb.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseBOpenLbContainerE2E (OpenLB eddy3dWind, CPU image, dx = 1.6 m); figure validation/plot_cases_ab_engines.py.

### Eddy3D ML wind surrogate (pedestrian height)

| Metric | \|U\| (z = H/16 plane) | \|U\|, lattice cut at ±250 m | wind reversed (control) |
|---|---|---|---|
| **R** | -0.236 | +0.010 | -0.236 |
| **FAC2** | 0.361 | 0.459 | 0.361 |
| **FB** | +0.821 | +0.463 | +0.821 |
| **hit rate** | 0.172 | 0.189 | 0.172 |
| **n** | 122 | 122 | 122 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/B/pairs/ml-surrogate.csv`]({{ '/api/cases/B/pairs/ml-surrogate.csv' | relative_url }}). Reproduce: Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py.

<figure class="figure">
<img src="{{ '/assets/figures/cases-ab-openfoam-agreement.png' | relative_url }}" alt="cases-ab-openfoam-agreement.png">
<figcaption><strong>Figure 2.</strong> Cases A and B, OpenFOAM 12 (realizable k-ε): measured against modelled U, V, W and k at every measured point, normalised by U_H, with the 1:1 line and the factor-of-two band.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/cases-ab-openfoam-profiles.png' | relative_url }}" alt="cases-ab-openfoam-profiles.png">
<figcaption><strong>Figure 3.</strong> Cases A and B, OpenFOAM 12: centre-plane vertical profiles of U/U_H at the measurement stations, measured points against the modelled line.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/cases-ab-engine-comparison.png' | relative_url }}" alt="cases-ab-engine-comparison.png">
<figcaption><strong>Figure 4.</strong> Cases A and B, every engine on the same points: measured against modelled U/U_H and V/U_H, one row per engine.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/ml-surrogate-agreement.png' | relative_url }}" alt="ml-surrogate-agreement.png">
<figcaption><strong>Figure 5.</strong> Eddy3D ML surrogate (Yel-2.0): measured against predicted pedestrian-height speed, one panel per case, with the 1:1 line and the factor-of-two band.</figcaption>
</figure>

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| Resource | Endpoint |
|---|---|
| Case | [`/api/cases/B.json`]({{ '/api/cases/B.json' | relative_url }}) |
| Points (JSON) | [`/api/cases/B/points.json`]({{ '/api/cases/B/points.json' | relative_url }}) |
| Points (CSV) | [`/api/cases/B/points.csv`]({{ '/api/cases/B/points.csv' | relative_url }}) |
| Approach flow (CSV) | [`/api/cases/B/approach_flow.csv`]({{ '/api/cases/B/approach_flow.csv' | relative_url }}) |
| Geometry | [`/api/cases/B/geometry.json`]({{ '/api/cases/B/geometry.json' | relative_url }}) |
| Geometry (STL) | [`/api/cases/B/geometry.stl`]({{ '/api/cases/B/geometry.stl' | relative_url }}) |
| Validation | [`/api/cases/B/validation.json`]({{ '/api/cases/B/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Yoshihide Tominaga (Niigata Institute of Technology)
- Editors and distributors: Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15401455](https://doi.org/10.5281/zenodo.15401455)
- Citation requested: Miyazaki, T., Tominaga, Y. (2003). Wind tunnel experiment on flow field around a building model with a scale ratio of 4:4:1 placed within the surface boundary layer. Proc. Annual Meeting of Hokuriku Chapter, AIJ, 201-204 (in Japanese). https://www.aij.or.jp/paper/detail.html?productId=313933
- Licence: CC BY 4.0
