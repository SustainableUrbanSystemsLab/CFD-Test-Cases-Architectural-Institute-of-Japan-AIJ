---
title: Validation
nav_order: 3
---

# Validation: Eddy3D vs the tunnel

**Status: Cases A and B, OpenFOAM 12 (realizable k-ε).** Cases C–E and the other solvers are not done yet — see
"What is not validated yet" below. Nothing on this page is a claim about them.

## Method

Each case is solved through Eddy3D's production case writer (`build-case → run → probe`), not a hand-built
OpenFOAM case, so what is validated is what a user gets. The probe sits at **exactly the tunnel's own measurement
coordinates**, so no interpolation enters the comparison.

- The tunnel's model-scale geometry is solved at 1:100 (Cases A, B) with the tunnel's own velocities; the log-law
  inlet is fitted to each case's own approach-flow file over z = 0.02 … 2H (`u*`, `z₀` below), and the profile
  shape is scale-invariant for a log law, so U/U_H values carry over unchanged.
- Everything is normalised by U_H (k by U_H²), the benchmark's own convention.
- Metrics per quantity: Pearson **R**; **FAC2**, the fraction of points within a factor of two; **FB**, the fractional
  bias 2(ō − p̄)/(ō + p̄), positive when the model is low; and the **hit rate**, the fraction within D = 0.25 relative
  or W = 0.05 U_H absolute. NMSE, NAD, MG, VG are in the API's `validation.json`.
- Case B's lateral velocity is sign-corrected before scoring (see [Data gotchas]({{ '/gotchas/' | relative_url }})).
- The reattachment length L_r behind the building is read from a wake line at ground level.

## Does the model agree?

![Measured vs modelled, Cases A and B]({{ '/assets/aij_agreement.png' | relative_url }})

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

## Where does it agree?

![Centre-plane profiles, Cases A and B]({{ '/assets/aij_profiles.png' | relative_url }})

Vertical profiles of U/U_H on the centre plane at the first three measured stations behind the building, offset
per station. The model follows the measured profile closely above roof height and in the recovering wake; the
near-ground deficit immediately behind the building is where the closure does least well.

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

`validation/plot_aij.py` (UltraPlot) builds both figures from the solved studies and the reference CSVs. The Eddy3D
fixtures are `TestAijCaseAContainerE2E` and `TestAijCaseBContainerE2E`. The scores they wrote are snapshotted in
`validation/results/` and served unchanged by `/api/cases/{id}/validation.json`.

## What is not validated yet

| | A | B | C | D | E |
|---|---|---|---|---|---|
| OpenFOAM | ✅ | ✅ | — | — | — |
| OpenLB | — | — | — | — | — |
| FluidX3D | — | — | — | — | — |
| ML surrogate | n/a | n/a | — | — | — |

Cases C–E need their geometry built (C is parametric, D ships an STL, E is a Rhino model of a real district) — the
API now serves cleaned STLs for all three, which is the first step, not the validation. The ML surrogate predicts
**pedestrian-height** wind, which Cases A and B do not measure, so there is nothing to compare for those two —
marked n/a rather than pending.

Two things that will shape the C/D/E validations when they come, both measured on the data rather than assumed:

- **Scalar vs vector speed.** C, D and E measure with thermistor anemometers, which report a mean *omnidirectional
  scalar* speed; steady RANS gives the magnitude of the mean velocity, which is lower by construction. Case D is the
  only case where both instruments overlap: over its 33 shared points the thermistor reads 1.34× |U| (ratio of means),
  and √(|U|² + 2k) from the split-fibre data matches the thermistor to FB +0.058 where |U| alone gives +0.292. A
  Case C/D/E score will therefore be reported as the bracket |U| ≤ Vs ≤ √(|U|² + 2k), not as one number.
- **The inlet is a log law, the tunnels' profiles are not.** Fitted power-law exponents are 0.19 (C, D) and 0.16–0.20
  (E) against the papers' 0.28 / 0.25; a log-law fit misses the single measurement height by −4 … −11 % depending on
  the fitting window, and sets the inlet k 26–48 % below the tunnel's (Case D). These are declared systematics, and
  the first thing to quote if the scores come back worse than A and B.
