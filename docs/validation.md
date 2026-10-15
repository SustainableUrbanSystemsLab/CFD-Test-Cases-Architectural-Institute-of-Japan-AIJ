---
title: Validation
nav_order: 3
---

# Validation: Eddy3D vs the tunnel

**Status.** *Scored* means a run exists and its scores are on this page — not that it agrees; how well it agrees is
in the numbers and their reading. Anything not marked scored is not a claim; see "What is still running" below.

## Method

Each case is solved through Eddy3D's production case writer (`build-case → run → probe`), not a hand-built
OpenFOAM case, so what is validated is what a user gets. The probe sits at **exactly the tunnel's own measurement
coordinates**, so no interpolation enters the comparison.

- Cases C–E measure an omnidirectional *scalar* speed with thermistors, so the model is scored as √(\|U\|² + 2k) and
  as \|U\| — the two ends of the bracket the measurement has to fall in.
- The tunnel's model-scale geometry is solved at 1:100 (Cases A, B) with the tunnel's own velocities; the log-law
  inlet is fitted to each case's own approach-flow file over z = 0.02 … 2H (`u*`, `z₀` below), and the profile
  shape is scale-invariant for a log law, so U/U_H values carry over unchanged.
- Everything is normalised by U_H (k by U_H²), the benchmark's own convention.
- Metrics per quantity: Pearson **R**; **FAC2**, the fraction of points within a factor of two; **FB**, the fractional
  bias 2(ō − p̄)/(ō + p̄), positive when the model is low; and the **hit rate**, the fraction within D = 0.25 relative
  or W = 0.05 U_H absolute. NMSE, NAD, MG, VG are in the API's `validation.json`.
- Case B's lateral velocity is sign-corrected before scoring (see [Known data issues]({{ '/known-data-issues/' | relative_url }})).
- The reattachment length L_r behind the building is read from a wake line at ground level.

## Cases A and B — does the model agree?

<figure class="figure">
<img src="{{ '/assets/figures/cases-ab-openfoam-agreement.png' | relative_url }}" alt="Measured vs modelled, Cases A and B">
<figcaption><strong>Figure 1.</strong> Measured vs modelled, Cases A and B.</figcaption>
</figure>

Measured against modelled for each quantity, with the 1:1 line and, where the quantity does not change sign, the
factor-of-two band.

| | A — U | A — V | A — W | A — k | B — U | B — V | B — W | B — k |
|---|---|---|---|---|---|---|---|---|
| **R** | +0.955 | +0.961 | +0.708 | +0.480 | +0.959 | +0.910 | +0.929 | +0.399 |
| **FAC2** | 0.817 | 0.349 | 0.398 | 0.667 | 0.701 | 0.281 | 0.536 | 0.562 |
| **FB** | +0.185 | −0.207 | −1.501 | +0.478 | +0.240 | +0.370 | +0.263 | +0.463 |
| **hit rate** | 0.586 | 0.892 | 0.801 | 0.177 | 0.562 | 0.612 | 0.808 | 0.223 |

Normalised by U_H throughout. Hit rate uses D = 0.25, W = 0.05 U_H.
Reattachment length behind the building: **L_r/H = 1.49** (Case A), **3.27** (Case B).

Reading these honestly:

- **The streamwise field is right** — R ≈ 0.96 in both cases, FAC2 0.82 / 0.70.
- **k is under-predicted in both** (FB ≈ +0.47, R ≈ 0.4), the familiar realizable k-ε behaviour and consistent with
  what Eddy3D already records for AIJ Case H.
- **FAC2 on V and W is low by construction, not by failure.** Those components change sign, so factor-of-two
  agreement is a harsh measure near zero; R and hit rate are the meaningful columns there. The flat row of model
  V ≈ 0 in Case B's panel is the symmetry plane: a RANS solution is symmetric, so V ≡ 0 at y = 0, while the tunnel
  measures small non-zero values.
- **Case A's W FB of −1.50 and its NMSE are artefacts of a near-zero mean** (mean measured W is ~0.01 m/s), not a
  blow-up. Read R = +0.71 instead.

## Cases A and B — where does it agree?

<figure class="figure">
<img src="{{ '/assets/figures/cases-ab-openfoam-profiles.png' | relative_url }}" alt="Centre-plane profiles, Cases A and B">
<figcaption><strong>Figure 2.</strong> Centre-plane profiles, Cases A and B.</figcaption>
</figure>

Vertical profiles of U/U_H on the centre plane at the first three measured stations behind the building, offset
per station. The model follows the measured profile closely above roof height and in the recovering wake; the
near-ground deficit immediately behind the building is where the closure does least well.

## Case C — the 3 × 3 block array

All nine configurations (centre block 0D / 1D / 2D × WD 0°, 22.5°, 45°), solved at 1:100 on a cylindrical domain —
the tunnel's turntable: the array turns with WD, the domain does not — ~310,000 cells per centre-block height,
3000 iterations per direction, the 120 probes at exactly the tunnel's coordinates.

<figure class="figure">
<img src="{{ '/assets/figures/case-c-openfoam-agreement.png' | relative_url }}" alt="Case C, measured vs modelled">
<figcaption><strong>Figure 3.</strong> Case C, measured vs modelled.</figcaption>
</figure>

| centre block | WD | R | FAC2 | FB | hit rate | \|U\| alone: FB / R |
|---|---|---|---|---|---|---|
| 0D | 0° | +0.824 | 0.908 | +0.266 | 0.567 | +0.466 / +0.804 |
| 0D | 22.5° | +0.857 | 0.983 | +0.106 | 0.750 | +0.295 / +0.846 |
| 0D | 45° | +0.831 | 0.942 | +0.121 | 0.783 | +0.307 / +0.801 |
| 1D | 0° | +0.801 | 0.858 | +0.341 | 0.433 | +0.551 / +0.741 |
| 1D | 22.5° | +0.896 | 0.975 | +0.192 | 0.675 | +0.394 / +0.882 |
| 1D | 45° | +0.872 | 0.942 | +0.198 | 0.733 | +0.353 / +0.873 |
| 2D | 0° | +0.857 | 0.850 | +0.251 | 0.492 | +0.443 / +0.848 |
| 2D | 22.5° | +0.906 | 0.983 | +0.091 | 0.875 | +0.240 / +0.894 |
| 2D | 45° | +0.909 | 0.958 | +0.103 | 0.883 | +0.243 / +0.912 |

<figure class="figure">
<img src="{{ '/assets/figures/case-c-openfoam-bias-map.png' | relative_url }}" alt="Case C, where the model is slow or fast">
<figcaption><strong>Figure 4.</strong> Case C, where the model is slow or fast.</figcaption>
</figure>

- **The pattern is right in every configuration** — R 0.80–0.91, FAC2 0.85–0.98.
- **The model is slow, worst at WD = 0** (FB +0.25 … +0.34, hit rate 0.43–0.57; at 22.5° and 45° FB +0.09 … +0.20,
  hit rate 0.68–0.88). The map puts the deficit in the streets running along the wind.
- **It is not the scalar-vs-vector question.** The tunnel reads above even √(\|U\|² + 2k) at 902 of the 1080 points
  (84 %); \|U\| alone is lower still.
- **Where the deficit comes from is not settled.** An earlier version of this page put it on the inflow, reading the
  approach flow at the probe height as 0.83 of the tunnel's. That reading was a sampling artefact: upstream of the
  array the probe height lies below the centre of the first cell of the coarse background mesh, where the probes'
  cell-to-point interpolation runs linearly to zero at the wall (the sampled |U| is exactly proportional to z there:
  1.00 m/s at 1 m, 2.01 m/s at 2 m). At z = D the approach matches the tunnel (0.99). At the measurement points the
  sampling is sound: none of the 240 checked (2D at 0°, 0D at 45°) has its 2 m sample inside the first cell.
- **The frame is checked by the scores.** Scored with the paper figure's rotation sense (the y mirror) R falls to
  −0.33 … +0.03 at 22.5° and 45°; with upwind and downwind swapped to −0.41 … +0.14 in eight of nine configurations.
- An independent re-scoring from the probe files and the original `RS_caseC.csv` reproduces every number (largest
  difference 9 × 10⁻¹⁶).

## Case E — the Niigata district, wind from SW

Before and after the construction of a 60 m tower and two 18 m blocks, each state on a 504 m-radius cylinder
(about one million cells, 2 m at the buildings), the tunnel's own profile imposed as a table
(`wind.inlet: "manual"`), the model's speed over its own solved U(15.9 m).

<figure class="figure">
<img src="{{ '/assets/figures/case-e-openfoam-agreement.png' | relative_url }}" alt="Case E, measured vs modelled, before, after and the change">
<figcaption><strong>Figure 5.</strong> Case E, measured vs modelled, before, after and the change.</figcaption>
</figure>

| | FAC2 | FB | q | R |
|---|---|---|---|---|
| before · √(\|U\|²+2k) | 0.95 | +0.12 | 0.61 | 0.69 |
| before · \|U\| | 0.79 | +0.27 | 0.41 | 0.69 |
| after · √(\|U\|²+2k) | 0.89 | +0.23 | 0.47 | 0.85 |
| after · \|U\| | 0.74 | +0.34 | 0.30 | 0.84 |
| ceiling control: the tunnel's *before*, scored as a model of its *after* | 0.79 | +0.37 | 0.35 | 0.10 |

<figure class="figure">
<img src="{{ '/assets/figures/case-e-openfoam-bias-map.png' | relative_url }}" alt="Case E, where the model is slow or fast">
<figcaption><strong>Figure 6.</strong> Case E, where the model is slow or fast.</figcaption>
</figure>

The construction change (after − before), in which inflow, closure and instrument biases largely cancel, has
R = 0.84, the sign right at 75 % of the points where the tunnel resolved a change, and about 60 % of the measured
size — far above the control that ignores the construction. The absolute ratios are low, and the cause is not
established: an earlier version of this page blamed an approach flow decaying near the ground, but those readings
(0.41 and 0.79 of the imposed table at 1.25 m and 2.5 m) were taken inside the first cell of the coarse upstream
mesh, where the sampling interpolates to zero at the wall (see *Inflow*).

## Case D — the high-rise among city blocks, wind directions 0° and 22.5°

Two of the three headings (45° is solving): 3.6 million cells at 1:400 on a cylinder domain, 3000
iterations, the 66 measured thermistor points and the 33 split-fibre points at z/H = 0.02.

<figure class="figure">
<img src="{{ '/assets/figures/case-d-openfoam-agreement.png' | relative_url }}" alt="Case D, measured vs modelled">
<figcaption><strong>Figure 7.</strong> Case D, wind directions 0° and 22.5°: measured against modelled speed on the thermistor plane, and at the split-fibre points (0° only).</figcaption>
</figure>

| | n | FAC2 | FB | q | R |
|---|---|---|---|---|---|
| WD 0° · thermistor Vs · √(\|U\|²+2k) | 66 | 0.73 | +0.21 | 0.48 | 0.80 |
| WD 0° · thermistor Vs · \|U\| | 66 | 0.67 | +0.36 | 0.39 | 0.81 |
| WD 22.5° · thermistor Vs · √(\|U\|²+2k) | 66 | 0.92 | +0.05 | 0.67 | 0.80 |
| WD 22.5° · thermistor Vs · \|U\| | 66 | 0.82 | +0.15 | 0.64 | 0.78 |
| WD 22.5° · the same, rotation sense mirrored (control) | 66 | 0.74 | +0.05 | 0.36 | 0.40 |
| WD 0° · split fibre \|U\| · \|U\| | 33 | 0.76 | +0.07 | 0.52 | 0.85 |
| WD 0° · split fibre U · U | 33 | 0.48 | +0.67 | 0.52 | 0.95 |

- **The pattern is right**: R 0.80 on the thermistor plane and 0.85 on the split-fibre |U|. The frame check the
  fixture asserts (R > 0.5 at 0°; a prior Eddy3D attempt at this case scored R 0.10) passes with room to spare.
- **Against the instrument that measures what RANS computes, the model is nearly unbiased.** On the 33 split-fibre
  points its |U| has FB +0.07; against the thermistor it is +0.21 with √(|U|²+2k) and +0.36 with |U|. In the
  tunnel itself the thermistor reads 1.34 times the split-fibre |U| over the same 33 points, so most of the
  thermistor gap is the instrument, not the flow.
- **Its streamwise component is low** (U FB +0.67, R 0.95) while its |U| is not: more of the model's
  near-ground speed is in the lateral and vertical components than the tunnel's.
- **At 22.5° the solved field corroborates the rotation sense the data cannot decide.** The array is symmetric about y = 0, so a
  wind turned toward +y and one turned toward −y give mirror-image fields, and the measurements alone cannot say
  which was used; the data paper's Figure 4 draws +y. Scored on the same solution, Figure 4's sense gives R
  0.80 and FAC2 0.92, its mirror R 0.40 and FAC2 0.74. At 22.5° the model is also nearly unbiased against
  the thermistor (FB +0.05 with √(|U|²+2k)).
- **At 0° the 66 thermistor values are 33 mirror pairs**, so only 33 are independent and the mirror control is
  trivially equal there.
- The numbers were reproduced from the solver's probe output against the cleaned table, with the frame mapped
  independently and separate metric code.

## Cases A and B — every engine on the same points

<figure class="figure">
<img src="{{ '/assets/figures/cases-ab-engine-comparison.png' | relative_url }}" alt="Measured vs modelled U and V, Cases A and B, one row per engine">
<figcaption><strong>Figure 8.</strong> Measured vs modelled U and V, Cases A and B, one row per engine.</figcaption>
</figure>

OpenLB (Eddy3D's `eddy3dWind`: Smagorinsky, third-order regularised D3Q19, CPU image) solved the same two
experiments with the same fitted inflow and probed the same measured points, at dx = 1.6 m — H/10 for A, H/12.5
for B, 1.3 and 2.6 million cells, 1.8 h and 4.1 h on four threads. That is a screening resolution: H/20 costs about
16 times the cell-steps on this image.

| case · quantity | n | FAC2 | FB | q | R | OpenFOAM FAC2 / q / R |
|---|---|---|---|---|---|---|
| A · U/U_H, all points | 186 | 0.43 | +0.40 | 0.37 | 0.76 | 0.82 / 0.59 / 0.96 |
| A · U/U_H, points ≥ 2 cells above the floor | 121 | 0.65 | +0.17 | 0.56 | 0.81 | — |
| A · V/U_H | 186 | 0.17 | — | 0.62 | 0.65 | 0.35 / 0.89 / 0.96 |
| A · W/U_H | 186 | 0.12 | — | 0.59 | 0.54 | 0.40 / 0.80 / 0.71 |
| B · U/U_H, all points | 224 | 0.38 | +0.28 | 0.29 | 0.79 | 0.70 / 0.56 / 0.96 |
| B · U/U_H, points ≥ 2 cells above the floor | 95 | 0.64 | −0.07 | 0.52 | 0.90 | — |
| B · V/U_H | 224 | 0.13 | — | 0.55 | 0.83 | 0.28 / 0.61 / 0.91 |
| B · W/U_H | 224 | 0.24 | — | 0.65 | 0.77 | 0.54 / 0.81 / 0.93 |

Reading these:

- **The flat band of near-zero model U in the OpenLB row is the floor.** OpenLB meets the ground with a plain
  no-slip (bounce-back) wall and carries the roughness only in the inlet profile; in the undisturbed column at
  the windward face its U is 0.29 of the inlet log law one cell up, 0.69 at two, 0.95 at three and 1.02–1.07
  from four. Case A's lowest plane sits 0.6 cells up, so above two cells FAC2 rises to 0.65 and FB falls to +0.17.
- **The solve is nearly steady.** The resolved k is 0.7 % (A) and 10 % (B) of the measured one: a steady
  log-law inflow at H/10 resolves almost no turbulence, so k is not compared, and with nothing to entrain the
  wakes run long (A: L_r = 3.39 H against OpenFOAM's 1.49) or displaced (B: its field fits best sampled H/2
  downstream).
- **Its frame is right:** with the lateral sign flipped V's R becomes −0.65 (A) and −0.83 (B), and U scrambled
  across the points drops R to 0.10.
- Each number above was reproduced from the solver's own probe output against the original Zenodo CSVs (largest
  difference 1 × 10⁻¹⁵).
- At this spacing Case B first crashed: OpenLB's STL reader segfaults when lattice nodes sit exactly on its
  octree planes. Eddy3D now moves such a lattice by 10⁻⁴ dx (`LBMCaseXml`), with a regression test that fails
  without the move.

**FluidX3D** (Eddy3D's GPU lattice-Boltzmann engine: D3Q19 with Smagorinsky LES) solved both experiments at dx =
H/64 (2.5 mm and 3.125 mm; 117 and 121 million cells) with the same fitted log-law inflow, averaging over 200 H/U_H
after 40 of spin-up (A) and over 500 after 100 (B). Each run has an empty-domain control on the same lattice, and a
point is scored only at a height where that control holds the imposed log law within 5 %: 116 of Case A's 186 points
and 88 of Case B's 224.

| case · quantity, comparable heights | n | FAC2 | FB | q | R | OpenFOAM on the same points: FAC2 / q / R |
|---|---|---|---|---|---|---|
| A · U/U_H | 116 | 0.60 | +0.41 | 0.57 | 0.84 | 0.85 / 0.73 / 0.95 |
| A · V/U_H | 116 | 0.26 | — | 0.75 | 0.85 | 0.27 / 0.90 / 0.95 |
| A · W/U_H | 116 | 0.22 | — | 0.41 | 0.59 | 0.49 / 0.79 / 0.93 |
| B · U/U_H | 88 | 0.64 | +0.26 | 0.57 | 0.95 | 0.78 / 0.68 / 0.97 |
| B · W/U_H | 88 | 0.48 | — | 0.32 | 0.85 | 0.78 / 0.69 / 0.95 |

Reading these:

- **The excluded points are the floor again.** FluidX3D meets the ground with a bounce-back wall and no roughness
  wall function. In the empty domain the flow at Case A's lowest plane (z = 0.01 m, 4 cells up) reads 0.52 of the
  imposed log law on average, and 0.86 at z = 0.04 m; Case B's three lowest heights read 0.77, 0.58 and 0.93. Those
  points are scored separately (`velocity.*.excluded`) and drawn hollow in the figure.
- **On Case A, the approach flow alone scores better on U.** On the comparable points, the empty-domain flow, with
  no building at all, scores U FAC2 0.77, FB −0.26 and hit rate 0.59, against the solved field's 0.60, +0.41 and
  0.57. Only the correlation shows the building's effect (0.84 against 0.51). On Case B the solved field beats its
  approach flow on every U statistic (FAC2 0.64 against 0.56, R 0.95 against 0.81).
- **Case B's V is not a headline score.** All 88 comparable points lie on the centre plane, where the mean V is zero
  by symmetry.
- **Its frame is right:** with the lateral sign flipped, Case A's V correlation becomes −0.85.
- Every number above was reproduced from the solver's own probe output against the cleaned tables, with the
  comparable set derived independently (largest difference 3 × 10⁻¹²).

## ML surrogate

<figure class="figure">
<img src="{{ '/assets/figures/ml-surrogate-agreement.png' | relative_url }}" alt="Measured vs predicted, ML surrogate, Cases A–E">
<figcaption><strong>Figure 9.</strong> Measured vs predicted, ML surrogate, Cases A–E.</figcaption>
</figure>

Eddy3D's Wind Predictor (the public `Yel-2.0` network) predicts \|U_mean\|/U_ref at one height, 1.8 m. Each case is
scaled so its measurement plane lands there — A ×180, B ×144, C ×90, D ×360, E ×0.9 — its buildings are rasterised
onto the model's 504 × 504 lattice of 2 m cells with the shipped grid code, the prediction is read at the tunnel's
own sensor coordinates, and U_ref is converted to U_H with each case's approach-flow file. Same metric code and
settings as the OpenFOAM rows.

| case · quantity | n | FB | FAC2 | R | hit rate | OpenFOAM, same points and quantity |
|---|---|---|---|---|---|---|
| A · \|U\|/U_H, z = 0.01 m plane | 65 | +0.77 | 0.26 | −0.13 | 0.09 | FB +0.27, FAC2 0.85, R +0.90, hit rate 0.45 |
| B · \|U\|/U_H, z = H/16 plane | 122 | +0.82 | 0.36 | −0.24 | 0.17 | FB +0.12, FAC2 0.84, R +0.87, hit rate 0.57 |
| C · Vs/U_H, 9 configurations | 1080 | +0.67 | 0.44 | +0.21 | 0.18 | √(\|U\|²+2k): FB +0.18, FAC2 0.93, R +0.87, hit rate 0.69 |
| D · Vs/U_H, thermistor, 3 WD | 198 | +0.67 | 0.34 | +0.33 | 0.17 | WD 0° and 22.5° (66 points each): √(\|U\|²+2k) FB +0.21 / +0.05, FAC2 0.73 / 0.92, R +0.80 / +0.80 |
| D · \|U\|/U_H, split fibre, WD 0 | 33 | +0.23 | 0.52 | +0.59 | 0.24 | FB +0.07, FAC2 0.76, R +0.85, hit rate 0.52 |
| E · Vs/U(15.9 m), 16 WD, before + after | 2560 | +1.00 | 0.22 | +0.43 | 0.08 | — |
| E · the same, SW only (both states) | 160 | +1.07 | 0.20 | +0.53 | 0.04 | \|U\|: FB +0.31, FAC2 0.76, R +0.81, hit rate 0.36 |

**It predicts roughly half the tunnel's speed everywhere, and it does not respond to the wind direction.** Reversing
the wind changes the predicted field by at most 1 × 10⁻⁴ U_ref over all 254,016 cells, in every case: the network
responds to spatial contrast in a channel, never to its level, and on a lattice that fills the window the direction
channels are constant planes. Cut the lattice at ±250 m and the direction enters through the step at its edge — but
on A, B and D the reversed wind then scores as well as the right one or better. These numbers grade the geometry
the model was given, not a wind it was told.

## Inflow

Fitted to each case's own approach-flow file over z = 0.02 … 2H, rather than assumed:

| Case | u\* (m/s) | z₀ (mm) | U_H measured (m/s) | log-law error |
|---|---|---|---|---|
| A | 0.343 | 0.668 | 4.491 | +2.0 % |
| B | 0.399 | 0.882 | 5.133 | +2.9 % |

Cases C, D and E carry their own fitted profiles on their pages — and a caveat each: their tunnels' profiles are
closer to a power law than a log law, and C, D and E all score at a single near-ground height, which is where a
log-law inlet is least right. The fits are in `/api/cases/{id}.json` under `inflow_fit`.

## Reproducing the figures

`validation/plot_cases_ab_openfoam.py` (Cases A and B), `validation/plot_case_c_openfoam.py` and `validation/plot_ml_surrogate.py` (UltraPlot)
build the figures. The Eddy3D fixtures are `TestAijCaseAContainerE2E`, `TestAijCaseBContainerE2E`,
`TestAijCaseC{0D,1D,2D}ContainerE2E` and `Outdoor.ML.Tests/TestAijSurrogateE2E`. The scores they wrote are
snapshotted in `validation/results/` with the per-point pairs beside them, and served unchanged by
`/api/cases/{id}/validation.json`.

## What is still running

| | A | B | C | D | E |
|---|---|---|---|---|---|
| OpenFOAM 12, realizable k-ε | scored | scored | scored | scored, WD 0° and 22.5° (45° solving) | scored, SW |
| OpenLB | scored | scored | not comparable at dx = 1.6 m | not comparable at dx = 1.6 m | not comparable at dx = 1.6 m |
| FluidX3D | scored | scored | not comparable (no ground wall function) | not comparable (no ground wall function) | not comparable (no ground wall function) |
| ML surrogate | scored | scored | scored | scored | scored |

**Why OpenLB is not scored on C–E — measured, not assumed.** Cases C, D and E measure only at pedestrian height,
and a point is scoreable on OpenLB only once it sits three to four cells above its no-slip floor. On the A and B
runs at dx = 1.6 m, read in the undisturbed column at the heights the other cases measure at:

| the other case's height | cells above the floor | U / inlet log law (A run, B run) |
|---|---|---|
| Case D, z/H = 0.02 | below the first fluid node | 0.11, 0.13 — no prediction |
| Case C, z = 0.1 D | 1–1.25 | 0.29, 0.40 |
| Case E, 2 m among ~6 m buildings (z/H ≈ 0.33) | 3.3–4.1 | 1.00, 1.06 |

A 2 m pedestrian plane therefore needs dx ≤ 0.5 m: 3.2 times finer in every direction, about 33 times the cells
and 105 times the cell-steps over the same domain — and the Case C array and the Niigata district are larger
domains than Case A's. This CPU image does not run that in useful time.
That is a statement about this resolution and this machine; a GPU run at dx ≤ 0.5 m would decide it.

**Why FluidX3D is not scored on C–E — measured on its own lattice.** The cause is the ground, not the resolution. In
the empty-domain run at H/64, 4–6 H downstream of the inlet (where the buildings stand), the flow at the heights the
other cases measure at reads, as a fraction of the imposed log law (mean across a span of ±H):

| the other case's height | cells above the floor at H/64 | U / log law |
|---|---|---|
| Case D, z/H = 0.02 | 1.3 | 0.37–0.53 |
| Case C, z/H = 0.10 | 6.4 | 0.58–0.68 |
| Case E, 2 m among ~6 m buildings (z/H ≈ 0.33) | 21 | 0.91–0.99 |

Refining makes it worse, not better. At H/32 the same height reads 0.74–0.80 (3.2 cells up); at H/64 the near-wall
flow forms stationary streaks, and across the span the ratio at z/H = 0.10 runs from 0.24 to 0.88 (4 H downstream).
Case E's height comes closest (0.91–0.99 at Case A's lattice), but the Niigata district fits on this GPU only at
about 1.6 cells per 2 m (an estimate from the lattice sizes, not a run). Scoring C–E on FluidX3D needs a ground wall function in the engine.

Two things that shape the C/D/E validations, both measured on the data rather than assumed:

- **Scalar vs vector speed.** C, D and E measure with thermistor anemometers, which report a mean *omnidirectional
  scalar* speed; steady RANS gives the magnitude of the mean velocity, which is lower by construction. Case D is the
  only case where both instruments overlap: over its 33 shared points the thermistor reads 1.34× |U| (ratio of means),
  and √(|U|² + 2k) from the split-fibre data matches the thermistor to FB +0.058 where |U| alone gives +0.292. A
  Case C/D/E score is therefore reported at both ends of the bracket \|U\| ≤ Vs ≤ √(\|U\|² + 2k).
- **The inlet is a log law, the tunnels' profiles are not.** Fitted power-law exponents are 0.19 (C, D) and 0.16–0.20
  (E) against the papers' 0.28 / 0.25; a log-law fit misses the single measurement height by −4 … −11 % depending on
  the fitting window, and sets the inlet k 26–48 % below the tunnel's (Case D). These are declared systematics, and
  the first thing to quote if the scores come back worse than A and B.
