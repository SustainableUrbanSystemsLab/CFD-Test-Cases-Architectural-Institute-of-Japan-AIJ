---
title: "Case A — 1:1:2 building"
parent: Cases
nav_order: 1
---

# Case A — 1:1:2 building

Isolated 1:1:2 building, velocity field (split-fibre hot wire).

<figure class="figure">
<img src="{{ '/assets/geometry/case-a.png' | relative_url }}" alt="Case A — 1:1:2 building">
<figcaption><strong>Figure 1.</strong> Isolated 1:1:2 building, b = 0.08 m, H = 0.16 m (model scale); the wind blows along +x.</figcaption>
</figure>

## Configuration

| Parameter | Value |
|---|---|
| Building | 1:1:2 (width : depth : height) prism |
| Width b (m) | 0.08 |
| Height H (m) | 0.16 |
| Reynolds number Re_H | 24000 |
| U_H (m/s) | 4.491 |
| Wind directions (°) | 0 |
| Measurement planes | vertical centre plane y/b = 0, horizontal z/b = 0.125, horizontal z/b = 1.25 |
| Instrument | hot-wire anemometer, split-fibre probes (DANTEC 55R55 streamwise, 55R57 spanwise/vertical), 1000 Hz, 60 s per point, 500 Hz low-pass |
| Wind tunnel | Technical Research Institute, Shimizu Corporation, Tokyo |
| Scale, note | model scale; Eddy3D solves it at 1:100 (b = 8 m, H = 16 m) with the tunnel velocities |

## Frame and units

| Property | Definition |
|---|---|
| Origin | building centre on the ground plane |
| x | +x streamwise (the wind at WD = 0 blows toward +x); building spans x in [-0.04, 0.04] |
| y | +y lateral; building spans y in [-0.04, 0.04]; points published on the y <= 0 half by the tunnel's symmetry convention |
| z | +z up from the ground; roof at z = 0.16 |
| Lateral sign applied | 1 |
| Coordinate scale applied | 1.0 |
| Unit of length | m (model scale) |
| Unit of velocity | m/s |
| Unit of variance | m^2/s^2 |
| Unit of k | m^2/s^2 |

## Reference data

Source in this repository: `case-a/RS-caseA.csv` (approach flow: `case-a/AF_caseA.csv`).

The cleaned table has **186 rows** over **186 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction_deg`, `x`, `y`, `z`, `U`, `V`, `W`, `uu`, `vv`, `ww`, `k`.

| Configuration | Points |
|---|---|
| default, WD 0° | 186 |

### Inflow

| Property | Value |
|---|---|
| Method | log law, kappa = 0.41, least squares over z = 0.02 ... 2H on the case's own approach-flow file |
| Friction velocity u* (m/s) | 0.343 |
| Roughness length z₀ (mm) | 0.668 |
| U_H, measured (m/s) | 4.491 |
| Log-law error at H | +2.0 % |

## Known data issues

- Lateral velocity V is positive toward +y (checked: V = -2.893 m/s at (-0.040, -0.050, 0.010), just outside the y < 0 flank, deflecting away from the centreline). Case B uses the OPPOSITE sign; the API flips Case B so both agree.
- Coordinates are metres (Case B's are millimetres in the published file).
- Case A's turbulence columns are rms values (u_rms, ...). The API serves VARIANCES (uu = u_rms^2) so A and B share one column meaning.

## Validation

### OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor)

Reattachment length L_r/H = 1.49.

| Metric | U | V | W | k |
|---|---|---|---|---|
| **R** | +0.955 | +0.961 | +0.708 | +0.480 |
| **FAC2** | 0.817 | 0.349 | 0.398 | 0.667 |
| **FB** | +0.185 | -0.207 | -1.501 | +0.478 |
| **hit rate** | 0.586 | 0.892 | 0.801 | 0.177 |
| **n** | 186 | 186 | 186 | 186 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/A/pairs/openfoam12-realizableKE.csv`]({{ '/api/cases/A/pairs/openfoam12-realizableKE.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseAContainerE2E; figures validation/plot_cases_ab_openfoam.py.

### OpenLB (Eddy3D LBM)

Reattachment length L_r/H = 3.39.

| Metric | U | U, points ≥ 2 dx | V | W | k (resolved) | V, lateral sign flipped (control) |
|---|---|---|---|---|---|---|
| **R** | +0.758 | +0.812 | +0.646 | +0.540 | +0.200 | -0.646 |
| **FAC2** | 0.425 | 0.645 | 0.172 | 0.124 | 0.000 | 0.118 |
| **FB** | +0.395 | +0.169 | +0.041 | -1.759 | +1.971 | +98.234 |
| **hit rate** | 0.371 | 0.562 | 0.624 | 0.586 | 0.000 | 0.570 |
| **n** | 186 | 121 | 186 | 186 | 186 | 186 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/A/pairs/openlb.csv`]({{ '/api/cases/A/pairs/openlb.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseAOpenLbContainerE2E (OpenLB eddy3dWind, CPU image, dx = 1.6 m); figure validation/plot_cases_ab_engines.py.

### FluidX3D (Eddy3D GPU LBM)

Reattachment length L_r/H = 0.05.

| Metric | U, comparable heights | V, comparable heights | W, comparable heights | U, all points | U, approach flow alone (control) |
|---|---|---|---|---|---|
| **R** | +0.840 | +0.845 | +0.591 | +0.806 | +0.510 |
| **FAC2** | 0.603 | 0.259 | 0.224 | 0.597 | 0.767 |
| **FB** | +0.405 | -0.692 | -1.678 | +0.372 | -0.256 |
| **hit rate** | 0.569 | 0.750 | 0.414 | 0.452 | 0.586 |
| **n** | 116 | 116 | 116 | 186 | 116 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/A/pairs/fluidx3d.csv`]({{ '/api/cases/A/pairs/fluidx3d.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseAFluidX3DE2E (Eddy3DCli.Tests/Validation/TestAijVelocityFluidX3DE2E; FluidX3D GPU lattice Boltzmann, D3Q19 Smagorinsky LES, dx = H/64, 40 + 200 H/U_H spin-up + averaging, with an empty-domain control on the same lattice); figure validation/plot_cases_ab_engines.py.

### Eddy3D ML wind surrogate (pedestrian height)

| Metric | \|U\| (z = 0.01 m plane) | \|U\|, lattice cut at ±250 m | wind reversed (control) |
|---|---|---|---|
| **R** | -0.125 | +0.434 | -0.125 |
| **FAC2** | 0.262 | 0.615 | 0.262 |
| **FB** | +0.772 | +0.401 | +0.772 |
| **hit rate** | 0.092 | 0.338 | 0.092 |
| **n** | 65 | 65 | 65 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/A/pairs/ml-surrogate.csv`]({{ '/api/cases/A/pairs/ml-surrogate.csv' | relative_url }}). Reproduce: Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py.

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
<figcaption><strong>Figure 4.</strong> Cases A and B, every engine on the same points: measured against modelled U/U_H and V/U_H, one row per engine (OpenFOAM 12; OpenLB at dx = 1.6 m; FluidX3D at H/64). FluidX3D is scored on the filled points, the heights where its empty-domain control holds the imposed log law; the hollow points near the ground are excluded.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/ml-surrogate-agreement.png' | relative_url }}" alt="ml-surrogate-agreement.png">
<figcaption><strong>Figure 5.</strong> Eddy3D ML surrogate (Yel-2.0): measured against predicted pedestrian-height speed, one panel per case, with the 1:1 line and the factor-of-two band.</figcaption>
</figure>

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| Resource | Endpoint |
|---|---|
| Case | [`/api/cases/A.json`]({{ '/api/cases/A.json' | relative_url }}) |
| Points (JSON) | [`/api/cases/A/points.json`]({{ '/api/cases/A/points.json' | relative_url }}) |
| Points (CSV) | [`/api/cases/A/points.csv`]({{ '/api/cases/A/points.csv' | relative_url }}) |
| Approach flow (CSV) | [`/api/cases/A/approach_flow.csv`]({{ '/api/cases/A/approach_flow.csv' | relative_url }}) |
| Geometry | [`/api/cases/A/geometry.json`]({{ '/api/cases/A/geometry.json' | relative_url }}) |
| Geometry (STL) | [`/api/cases/A/geometry.stl`]({{ '/api/cases/A/geometry.stl' | relative_url }}) |
| Validation | [`/api/cases/A/validation.json`]({{ '/api/cases/A/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Takeshi Ishihara (The University of Tokyo), Kazuki Hibi (Numerical Flow Design)
- Editors and distributors: Yoshihide Tominaga (Niigata Institute of Technology), Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15050147](https://doi.org/10.5281/zenodo.15050147)
- Citation requested: Meng, Y., & Hibi, K. (1998). Turbulent measurements of the flow field around a high-rise building. Journal of Wind Engineering, JAWE, 76, 55-64. https://doi.org/10.5359/jawe.1998.76_55
- Licence: CC BY 4.0
