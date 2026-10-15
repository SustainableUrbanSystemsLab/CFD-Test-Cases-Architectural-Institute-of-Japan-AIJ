---
title: "Case C — 3 × 3 block array"
parent: Cases
nav_order: 3
---

# Case C — 3 × 3 block array

3 x 3 array of 0.20 m cubes, centre block at 0D / 1D / 2D, pedestrian-height scalar speed (thermistor), 3 wind directions.

| | | |
|---|---|---|
| ![Case C — 3 × 3 block array, 0D]({{ '/assets/geometry/case-c-0d.png' | relative_url }})<br><span class="caption">0D: the centre block removed.</span> | ![Case C — 3 × 3 block array, 1D]({{ '/assets/geometry/case-c-1d.png' | relative_url }})<br><span class="caption">1D: the centre block as tall as its neighbours, D = 0.20 m.</span> | ![Case C — 3 × 3 block array, 2D]({{ '/assets/geometry/case-c-2d.png' | relative_url }})<br><span class="caption">2D: the centre block twice as tall, 2D = 0.40 m.</span> |
{: .figures }

<p class="caption"><strong>Figure 1.</strong> The three configurations of the centre block, on one scale; 120 measurement points each, at three wind directions.</p>

## Configuration

| Parameter | Value |
|---|---|
| Array | 3 x 3 cubes, D = 0.20 m, block centres at x, y in {-0.4, 0, +0.4} m (pitch 0.40 m = 2D, street width D) |
| Block size D (m) | 0.2 |
| Centre building | **0D**: no centre building<br>**1D**: 0.2 x 0.2 x 0.2 m (same as the surroundings)<br>**2D**: 0.2 x 0.2 x 0.4 m |
| Wind directions (°) | 0, 22.5, 45 |
| Configurations | 9 |
| Configurations, note | 3 centre-building heights x 3 wind directions; all nine share the identical 120-point set |
| Measurement height (m) | 0.02 |
| Measurement height, note | z = 0.1 D for every point (2.0 m at the 1:100 scale Eddy3D solves it at) |
| Reynolds number Re_D | 52000 |
| U_H (m/s) | 3.654 |
| U_H, note | U at z = D = 0.20 m from AF_caseC.csv; the data paper states U_H = 3.65 m/s |
| Instrument | thermistor anemometer (omnidirectional scalar speed), 1 Hz, 30 s per point; approach flow by I-type hot wire, 500 Hz, 30 s |
| Wind tunnel | Technology Development Division, Fujita Corporation, Tokyo |
| Pitch, note | The 0.40 m pitch is read from MP-z-caseC.png and Figure 3 of the data paper (street = D); the 120-point grid alone bounds the pitch to (0.35, 0.40] m (the 49 absent nodes of the 13 x 13 grid are exactly the nine footprints for 0.375 m as well as 0.40 m). |

## Frame and units

| Property | Definition |
|---|---|
| Origin | array centre on the ground plane (centre of the middle block) |
| x | +x streamwise at WD = 0 (checked three ways on the data: y -> -y is a symmetry, the x <= -0.25 band is faster than x >= +0.25 in every configuration, and the regression slope of Vs is most negative within 0.8-4.3 deg of +x) |
| y | +y lateral |
| z | +z up; all points at z = 0.02 |
| Wind direction convention | In the CSV's own frame WD rotates the wind from +x TOWARD -y (the WD = 45 field is mirror-symmetric about y = -x to within the experiment's repeatability, 0.10-0.13 m/s, and not about y = +x, 0.5-0.8 m/s). Figure 3 of the data paper draws the fan rotating toward +y. The two disagree by a y-sign flip; this release keeps the CSV frame, which is the frame the point coordinates live in. The disagreement is invisible at WD = 0. |
| Lateral sign applied | 1 |
| Coordinate scale applied | 1.0 |
| Unit of length | m (model scale) |
| Unit of velocity | m/s |

## Reference data

Source in this repository: `case-c/RS_caseC.csv` (approach flow: `case-c/AF_caseC.csv`).

The cleaned table has **1080 rows** over **120 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction_deg`, `x`, `y`, `z`, `Vs`.

| Configuration | Points |
|---|---|
| 0D, WD 0° | 120 |
| 0D, WD 22.5° | 120 |
| 0D, WD 45° | 120 |
| 1D, WD 0° | 120 |
| 1D, WD 22.5° | 120 |
| 1D, WD 45° | 120 |
| 2D, WD 0° | 120 |
| 2D, WD 22.5° | 120 |
| 2D, WD 45° | 120 |

### Inflow

| Property | Value |
|---|---|
| Method | log law, kappa = 0.41, least squares on AF_caseC.csv (16 points, z = 0.01 ... 1.2 m); two windows, because Case C scores at ONE height (z = 0.02 m) and the near-ground half of the fit matters |
| Fit window | z range m [0.02, 0.4]; Friction velocity u* (m/s) 0.25598; Roughness length z₀ (mm) 0.4797; error at U D +3.08 %; error at z 0.02 -4.31 %; scored ratio bias -7.17 % |
| Fit window | z range m [0.01, 0.4]; Friction velocity u* (m/s) 0.22853; Roughness length z₀ (mm) 0.2362; error at U D +2.83 %; error at z 0.02 +1.65 %; scored ratio bias -1.15 % |
| Power-law exponent, fitted | 0.19 |
| Power-law exponent, data paper | 0.28 |
| Turbulence intensity at D | 0.219 |
| Note | derived during scoping, not published by AIJ; the tunnel profile is closer to a power law than a log law, so a log-law inlet carries a ~2.3 % rms residual over the fitted range |

## Known data issues

- The measured quantity Vs is the MEAN OMNIDIRECTIONAL SCALAR speed from a thermistor, not |mean velocity vector|. A RANS |U| is biased low against it; the data paper suggests comparing sqrt(|U|^2 + 2k) as a conservative correction (over all 1080 rows no Vs is below 0.13 U_H).
- The 'CB' column is TEXT ('0D', '1D', '2D'); a reader that parses every field as a number gets NaN for it. The header ends with a trailing comma (an empty 8th column).
- 1080 rows = 3 wind directions x 3 centre buildings x 120 points, not 3 configurations. In the 0D configuration the 25 centre grid nodes are still absent although the ground there is free: the grid is held constant across configurations.
- 24 of the 120 points sit exactly on a building face plane (|x| = 0.30 or |y| = 0.30) in the open gap between two blocks: legitimate fluid points, but a probe's cell lookup is delicate there.
- Point numbers 1, 2, 3, 34, 35, 36, 37, 46, 55, 100, 101, 102 do not occur (No. runs 4 ... 132 with nine interior gaps).
- Experimental repeatability, from the mirror-symmetric point pairs: mean |dVs| 0.088-0.137 m/s (0.024-0.038 U_H).

## Validation

### OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor) — configuration 0D

Quantity: Vs (thermistor) scored against sqrt(|U|^2 + 2k) [scalar] and |U| [vector]; both normalised by U_H = U(z = D) = 3.654 m/s.

| Metric | WD 0° √(\|U\|²+2k) | WD 0° \|U\| | WD 22.5° √(\|U\|²+2k) | WD 22.5° \|U\| | WD 45° √(\|U\|²+2k) | WD 45° \|U\| |
|---|---|---|---|---|---|---|
| **R** | +0.824 | +0.804 | +0.857 | +0.846 | +0.831 | +0.801 |
| **FAC2** | 0.908 | 0.658 | 0.983 | 0.833 | 0.942 | 0.800 |
| **FB** | +0.266 | +0.466 | +0.106 | +0.295 | +0.121 | +0.307 |
| **hit rate** | 0.567 | 0.308 | 0.750 | 0.433 | 0.783 | 0.533 |
| **n** | 120 | 120 | 120 | 120 | 120 | 120 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/C/pairs/openfoam12-realizableKE.csv`]({{ '/api/cases/C/pairs/openfoam12-realizableKE.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseC0DContainerE2E; figures validation/plot_case_c_openfoam.py.

### OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor) — configuration 1D

Quantity: Vs (thermistor) scored against sqrt(|U|^2 + 2k) [scalar] and |U| [vector]; both normalised by U_H = U(z = D) = 3.654 m/s.

| Metric | WD 0° √(\|U\|²+2k) | WD 0° \|U\| | WD 22.5° √(\|U\|²+2k) | WD 22.5° \|U\| | WD 45° √(\|U\|²+2k) | WD 45° \|U\| |
|---|---|---|---|---|---|---|
| **R** | +0.801 | +0.741 | +0.896 | +0.882 | +0.872 | +0.873 |
| **FAC2** | 0.858 | 0.550 | 0.975 | 0.725 | 0.942 | 0.850 |
| **FB** | +0.341 | +0.551 | +0.192 | +0.394 | +0.198 | +0.353 |
| **hit rate** | 0.433 | 0.292 | 0.675 | 0.367 | 0.733 | 0.433 |
| **n** | 120 | 120 | 120 | 120 | 120 | 120 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/C/pairs/openfoam12-realizableKE.csv`]({{ '/api/cases/C/pairs/openfoam12-realizableKE.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseC1DContainerE2E; figures validation/plot_case_c_openfoam.py.

### OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor) — configuration 2D

Quantity: Vs (thermistor) scored against sqrt(|U|^2 + 2k) [scalar] and |U| [vector]; both normalised by U_H = U(z = D) = 3.654 m/s.

| Metric | WD 0° √(\|U\|²+2k) | WD 0° \|U\| | WD 22.5° √(\|U\|²+2k) | WD 22.5° \|U\| | WD 45° √(\|U\|²+2k) | WD 45° \|U\| |
|---|---|---|---|---|---|---|
| **R** | +0.857 | +0.848 | +0.906 | +0.894 | +0.909 | +0.912 |
| **FAC2** | 0.850 | 0.692 | 0.983 | 0.900 | 0.958 | 0.900 |
| **FB** | +0.251 | +0.443 | +0.091 | +0.240 | +0.103 | +0.243 |
| **hit rate** | 0.492 | 0.317 | 0.875 | 0.633 | 0.883 | 0.608 |
| **n** | 120 | 120 | 120 | 120 | 120 | 120 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/C/pairs/openfoam12-realizableKE.csv`]({{ '/api/cases/C/pairs/openfoam12-realizableKE.csv' | relative_url }}). Reproduce: Eddy3D fixture TestAijCaseC2DContainerE2E; figures validation/plot_case_c_openfoam.py.

### Eddy3D ML wind surrogate (pedestrian height)

| Metric | Vs, 9 configurations | Vs, 2D WD 0, lattice cut at ±250 m | wind reversed (control) |
|---|---|---|---|
| **R** | +0.212 | +0.075 | -0.441 |
| **FAC2** | 0.444 | 0.875 | 0.725 |
| **FB** | +0.666 | +0.192 | +0.367 |
| **hit rate** | 0.181 | 0.400 | 0.392 |
| **n** | 1080 | 120 | 120 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Per-point values: [`/api/cases/C/pairs/ml-surrogate.csv`]({{ '/api/cases/C/pairs/ml-surrogate.csv' | relative_url }}). Reproduce: Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py.

<figure class="figure">
<img src="{{ '/assets/figures/case-c-openfoam-agreement.png' | relative_url }}" alt="case-c-openfoam-agreement.png">
<figcaption><strong>Figure 2.</strong> Case C, OpenFOAM 12: measured Vs/U_H against the modelled √(|U|²+2k)/U_H (filled) and |U|/U_H (hollow), one panel per configuration (centre block × wind direction).</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/case-c-openfoam-bias-map.png' | relative_url }}" alt="case-c-openfoam-bias-map.png">
<figcaption><strong>Figure 3.</strong> Case C, OpenFOAM 12: log₂(model / tunnel) of the scalar speed at each of the 120 points on the plan of the array, per configuration — where the model is slow and where it is fast.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/ml-surrogate-agreement.png' | relative_url }}" alt="ml-surrogate-agreement.png">
<figcaption><strong>Figure 4.</strong> Eddy3D ML surrogate (Yel-2.0): measured against predicted pedestrian-height speed, one panel per case, with the 1:1 line and the factor-of-two band.</figcaption>
</figure>

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| Resource | Endpoint |
|---|---|
| Case | [`/api/cases/C.json`]({{ '/api/cases/C.json' | relative_url }}) |
| Points (JSON) | [`/api/cases/C/points.json`]({{ '/api/cases/C/points.json' | relative_url }}) |
| Points (CSV) | [`/api/cases/C/points.csv`]({{ '/api/cases/C/points.csv' | relative_url }}) |
| Approach flow (CSV) | [`/api/cases/C/approach_flow.csv`]({{ '/api/cases/C/approach_flow.csv' | relative_url }}) |
| Geometry | [`/api/cases/C/geometry.json`]({{ '/api/cases/C/geometry.json' | relative_url }}) |
| Geometry (STL) | [`/api/cases/C/geometry.stl`]({{ '/api/cases/C/geometry.stl' | relative_url }}) |
| Validation | [`/api/cases/C/validation.json`]({{ '/api/cases/C/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Yoshitami Nonomura (Yamato University)
- Editors and distributors: Yoshihide Tominaga (Niigata Institute of Technology), Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15401791](https://doi.org/10.5281/zenodo.15401791)
- Citation requested: Nonomura, Y., Kobayashi, N., Tominaga, Y., Mochida, A. (2003). The cross comparison of CFD results for flow field around building models (part 3). Japan Association for Wind Engineering, 95, 83-84 (in Japanese). https://doi.org/10.14887/jaweam.2003.0.41.0
- Licence: CC BY 4.0
