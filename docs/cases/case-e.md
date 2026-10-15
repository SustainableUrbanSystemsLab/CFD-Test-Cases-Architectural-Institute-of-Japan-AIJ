---
title: "Case E — Niigata district"
parent: Cases
nav_order: 5
---

# Case E — Niigata district

Real district in Niigata at 1:250, before and after a 60 m high-rise and two 18 m mid-rises; pedestrian-height velocity ratio (thermistor), 16 wind directions.

| |
|---|
| ![Case E — Niigata district, bc]({{ '/assets/geometry/case-e-before.png' | relative_url }})<br><span class="caption">Before construction: the existing district, about 400 m across (full scale).</span> |
| ![Case E — Niigata district, ac]({{ '/assets/geometry/case-e-after.png' | relative_url }})<br><span class="caption">After construction: the 60 m high-rise and the two 18 m mid-rises (blue) added.</span> |
{: .figures }

<p class="caption"><strong>Figure 1.</strong> The two states, on one scale (full-scale metres, +x east, +y north); the arrow marks SW, the direction Eddy3D is scored at.</p>

## Configuration

| Parameter | Value |
|---|---|
| District | Niigata City urban area near the Shinano River; dense low-rise stock (median top 6 m, max 30 m) |
| Scale | 1:250 |
| States | **bc**: before construction (sites of A, B, C empty)<br>**ac**: after construction of A (60 m high-rise), B and C (18 m mid-rises) |
| New buildings | **A**: 60 m high-rise, bbox x [-79.3, -49.1], y [-17.1, 18.3]<br>**B**: 18 m, bbox x [41.5, 61.0], y [-18.5, 8.5]<br>**C**: 18 m, bbox x [64.0, 83.5], y [-8.0, 19.0] |
| Wind directions | N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW, WSW, W, WNW, NW, NNW |
| Wind directions (°) | 0.0, 22.5, 45.0, 67.5, 90.0, 112.5, 135.0, 157.5, 180.0, 202.5, 225.0, 247.5, 270.0, 292.5, 315.0, 337.5 |
| Measurement height (m) | 2.0 |
| Measurement height, note | 2 m full scale = 0.008 m model scale |
| Points | 80 |
| Values | 2560 |
| Reynolds number | 17000 |
| Normalisation | velocity ratio = mean scalar speed at 2 m / inflow velocity at 15.9 m (the Niigata meteorological station height); U(15.9 m) = 0.504531 x UR = 3.935 m/s with UR = 7.8 m/s at ZR = 250 m |
| Instrument | thermistor anemometer, 100 Hz, 60 s per point, mean scalar wind speed |
| Wind tunnel | Niigata Institute of Technology, Kashiwazaki |

## Frame and units

| Property | Definition |
|---|---|
| Origin | centre of the reproduced area, ground plane |
| x | +x EAST (full-scale metres) |
| y | +y NORTH (compass rose in MP_caseE.png) |
| z | +z up; all points at z = 2.0 |
| Wind direction convention | Meteorological: the compass name is the direction the wind comes FROM (N = 0 deg blows toward -y, E = 90 deg toward -x), clockwise from north. This case keeps its geographic frame instead of '+x along the wind' because the district is real and its coordinates are the data's. |
| Lateral sign applied | 1 |
| Coordinate scale applied | 1.0 |
| Unit of length | m (FULL scale) |
| Unit of velocity ratio | dimensionless |

## Reference data

Source in this repository: `case-e/LF_caseE.xls` (approach flow: `case-e/LF_caseE.xls [sheet Inflow]`).

The cleaned table has **2560 rows** over **80 distinct points**; columns `point_id`, `config`, `instrument`, `wind_direction`, `wind_direction_deg`, `x`, `y`, `z`, `velocity_ratio`.

| Configuration | Points |
|---|---|
| before construction, 16 wind directions | 80 per direction |
| after construction, 16 wind directions | 80 per direction |

### Inflow

| Property | Value |
|---|---|
| Method | the workbook publishes z/ZR, U/UR, k/UR^2 with ZR = 250 m, UR = 7.8 m/s and epsilon = Cmu^0.5 k dU/dz (Cmu = 0.09); de-normalised to full-scale metres and m/s here |
| U_ref at 15.9 m (m/s) | 3.935 |
| Log law | does not fit: kappa = 0.41 fits reach 5.3-9.4 % max error over the relevant height range and overshoot U(15.9 m) by 4-7 % |
| Power-law exponent | **ground to 60m**: 0.158<br>**whole profile**: 0.201 |
| Note | derived during scoping, not published by AIJ |

## Known data issues

- The velocity ratio is normalised by the inflow velocity at 15.9 m (= 3.935 m/s), NOT by U_H and NOT by UR = 7.8 m/s. A prior Eddy3D comparison in the folder divided by the wrong reference and came out low by a factor of 2.048 (FAC2 0.338 -> 0.863 once rescaled, R unchanged at 0.661).
- All 2560 published ratios are integer multiples of 0.0198204 (55 distinct levels): the data's own resolution is +/-0.0099, 3.1 % of the median value and about 10 % at the lowest points.
- The readme describes AF_caseE.csv, RS_caseE.csv and BD_caseE.stl, but this repository holds only the .3dm, .ghx, .xls and the MP drawing; everything here is extracted from the workbook and the 3dm.
- case-e.3dm is FULL-SCALE metres (MP_caseE.png is drawn at model scale, +/-0.8 m). Use layers 'buildings' (5,015 meshes, before construction) and 'buildings_new_construction' (3 prisms); exclude the map plate on the Japanese-named general layer, the terrain plates (the site is flat) and 'probes'.
- Do not take the measurement coordinates from the 3dm's 'probes' layer: its 80 spheres sit a median 2.31 m (max 21 m) from the workbook's points, which are authoritative (all 80 fall in open space, min 0.83 m from a building edge).
- The measured quantity is a scalar (thermistor) speed; a RANS |U| is biased low against it in a dense canopy. The construction signal (ac - bc) is largest for SW (mean |d| 0.2155) and smallest for SSE (0.093).

## Validation

### OpenFOAM 12, realizable k-epsilon (Eddy3D Outdoor) — configuration SW

| Metric | before, √(\|U\|²+2k) | before, \|U\| | after, √(\|U\|²+2k) | after, \|U\| | no-construction ceiling control |
|---|---|---|---|---|---|
| **R** | +0.688 | +0.692 | +0.845 | +0.835 | +0.099 |
| **FAC2** | 0.950 | 0.787 | 0.887 | 0.738 | 0.787 |
| **FB** | +0.124 | +0.266 | +0.226 | +0.341 | +0.368 |
| **hit rate** | 0.613 | 0.412 | 0.475 | 0.300 | 0.350 |
| **n** | 80 | 80 | 80 | 80 | 80 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Reproduce: Eddy3D fixture TestAijCaseEContainerE2E (EDDY3D_AIJ_E_DIRECTIONS=SW, tabulated inlet); figures validation/plot_case_e_openfoam.py (per-point pairs in validation/results/caseE_openfoam12_realizableKE_pairs.csv).

### Eddy3D ML wind surrogate (pedestrian height)

| Metric | Vs/U(15.9 m), 16 WD, bc + ac | after construction | after − before | after, lattice cut at ±250 m | wind reversed (control) |
|---|---|---|---|---|---|
| **R** | +0.433 | +0.425 | +0.399 | +0.230 | +0.425 |
| **FAC2** | 0.225 | 0.284 | 0.234 | 0.836 | 0.284 |
| **FB** | +0.996 | +0.853 | +0.077 | +0.053 | +0.853 |
| **hit rate** | 0.082 | 0.105 | 0.312 | 0.388 | 0.105 |
| **n** | 2560 | 1280 | 1280 | 1280 | 1280 |

velocities by U_H, k by U_H^2 (the benchmark's own convention; Case E by U at 15.9 m, as it is published); hit rate D = 0.25, W = 0.05 in those units. Reproduce: Eddy3D fixture Outdoor.ML.Tests/TestAijSurrogateE2E; figure validation/plot_ml_surrogate.py.

<figure class="figure">
<img src="{{ '/assets/figures/case-e-openfoam-agreement.png' | relative_url }}" alt="case-e-openfoam-agreement.png">
<figcaption><strong>Figure 2.</strong> Case E, OpenFOAM 12, wind from SW: measured velocity ratio against the modelled √(|U|²+2k)/U_ref (filled) and |U|/U_ref (hollow), before and after construction, and the change the construction makes.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/case-e-openfoam-bias-map.png' | relative_url }}" alt="case-e-openfoam-bias-map.png">
<figcaption><strong>Figure 3.</strong> Case E, OpenFOAM 12, wind from SW: log₂(model / tunnel) of the scalar speed at the 80 points on the plan of the district, before and after construction.</figcaption>
</figure>

<figure class="figure">
<img src="{{ '/assets/figures/ml-surrogate-agreement.png' | relative_url }}" alt="ml-surrogate-agreement.png">
<figcaption><strong>Figure 4.</strong> Eddy3D ML surrogate (Yel-2.0): measured against predicted pedestrian-height speed, one panel per case, with the 1:1 line and the factor-of-two band.</figcaption>
</figure>

How to read these is on the [Validation]({{ '/validation/' | relative_url }}) page.

## API

| Resource | Endpoint |
|---|---|
| case | [`/api/cases/E.json`]({{ '/api/cases/E.json' | relative_url }}) |
| points (JSON) | [`/api/cases/E/points.json`]({{ '/api/cases/E/points.json' | relative_url }}) |
| points (CSV) | [`/api/cases/E/points.csv`]({{ '/api/cases/E/points.csv' | relative_url }}) |
| geometry | [`/api/cases/E/geometry.json`]({{ '/api/cases/E/geometry.json' | relative_url }}) |
| geometry STL | [`/api/cases/E/geometry.stl`]({{ '/api/cases/E/geometry.stl' | relative_url }}) |
| validation | [`/api/cases/E/validation.json`]({{ '/api/cases/E/validation.json' | relative_url }}) |

## Attribution

- Data collectors: Yoshihide Tominaga (Niigata Institute of Technology)
- Editors and distributors: Hideki Kikumoto (The University of Tokyo), Tsubasa Okaze (Institute of Science Tokyo)
- DOI: [10.5281/zenodo.15429017](https://doi.org/10.5281/zenodo.15429017)
- Citation requested: Tominaga, Y. et al. (2008). AIJ guidelines for practical applications of CFD to pedestrian wind environment around buildings. JWEIA 96, 1749-1761. https://doi.org/10.1016/j.jweia.2008.02.058
- Licence: CC BY 4.0
