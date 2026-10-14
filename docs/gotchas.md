---
title: Data gotchas
nav_order: 4
---

# Things in the published files that silently corrupt a comparison

All of these were found by scoring or measuring the files rather than reading them. The cleaned tables served by
the API already apply the corrections (units, signs, frames); the raw files in the repository do not. Each case page
repeats its own list.

## Across cases

- **Scalar vs vector mean speed.** Cases C, D and E measure with thermistor anemometers: an *omnidirectional scalar*
  speed, not |mean velocity vector|. A RANS |U| is biased low against it, most where the flow is sheltered and
  turbulent. The data paper suggests comparing √(|U|² + 2k) as a conservative correction; Case D's split-fibre data
  measures the gap directly (thermistor / |U| = 1.34 as a ratio of means over the 33 shared points).
- **Each case has its own frame and unit.** A–D are model-scale metres with +x along the wind at WD = 0; E is
  full-scale metres with +x east and +y north and meteorological (from-) directions. Read `frame` in
  `/api/cases/{id}.json` before any number.

## Case A

- V is positive toward +y (checked: V = −2.893 m/s at (−0.040, −0.050, 0.010), just outside the y < 0 flank, where
  the flow must deflect away from the centreline).
- Coordinates are metres; turbulence columns are rms values. The API serves variances (uu = u_rms²) so A and B
  share one column meaning.

## Case B

1. **Cases A and B report the lateral velocity V with opposite sign conventions.** Just outside the windward side
   face the flow must deflect away from the centreline — toward −y on the y < 0 flank. Case A measures
   **V = −2.893 m/s** at (−0.040, −0.050, 0.010) with its edge at y = −0.04; Case B measures **V = +3.630 m/s** at
   (−0.025, −0.110, 0.013) with its edge at y = −0.100. Same flow feature, opposite sign, so **Case B's V is positive
   toward −y**. Scored without correcting for this, Case B's V comes out at R = −0.910 against an R = +0.959
   streamwise control on the same points — an anti-correlation no turbulence closure produces. The API flips Case B's
   V (`lateral_sign_applied: -1`).
2. **Case B's coordinates are millimetres** (`x[mm]`) while its velocities are m/s; Case A's are metres. Read as
   metres, every probe lands 1000× too far out. The API serves metres (`coordinate_scale_applied: 0.001`).

Case geometry was taken from each case's own measurement-point drawing (`MP-z_case*.png`), not inferred from the
CSV extents: both buildings are centred on the origin, with points published on the y ≤ 0 half by the tunnel's
symmetry convention.

## Case C

- The `CB` column is **text** (`0D`, `1D`, `2D`); a reader that parses every field as a number gets NaN for it. The
  header ends with a trailing comma (an empty 8th column).
- 1080 rows = 3 wind directions × 3 centre buildings × 120 points — nine configurations, not three. In the 0D
  configuration the 25 centre grid nodes are still absent although the ground there is free.
- **The wind-direction rotation sense is ambiguous between the CSV and the data paper's figure.** In the CSV's own
  frame the WD = 45° field is mirror-symmetric about y = −x to within the experiment's repeatability (0.10–0.13 m/s)
  and not about y = +x (0.5–0.8 m/s), so WD rotates the wind from +x toward −y. Figure 3 of the data paper draws the
  fan the other way. This release keeps the CSV frame; the question is invisible at WD = 0.
- 24 of the 120 points sit exactly on a building face plane (|x| = 0.30 or |y| = 0.30), in the gap between blocks.
- The 0.40 m pitch is read from the drawing and the paper (street = D); the point grid alone bounds it to (0.35, 0.40].
- Repeatability floor from the mirror-symmetric pairs: mean |ΔVs| 0.088–0.137 m/s (0.024–0.038 U_H).

## Case D

- All the data lives in `CaseD(Highrise+Blocks).xls`, a BIFF8 workbook (xlrd 2.x reads it; openpyxl cannot).
  Coordinates are millimetres.
- The shipped `BD_caseD.stl` is dirty: 1572 facets, 576 duplicates, all 83 roofs wound inward (signed volume
  0.011159 m³ against the true 0.021477 m³). The API's `geometry.stl` is rebuilt from the 83 shells' boxes: 996
  facets, watertight, volume 0.021477 m³.
- Unmeasured thermistor cells are `-` (null in the API). At WD = 0 the 66 measured values are 33 exact mirror pairs.
- **The rotation sense for 22.5° and 45° cannot be settled from the data** — the array is exactly y-mirror symmetric,
  so +θ and −θ give exact mirror fields. The choice (+x toward +y) rests on Figure 4 of the data paper.
- A prior Eddy3D comparison kept in the folder scores R = +0.096 against the thermistor: a frame or geometry error,
  not a validation.

## Case E

- **The velocity ratio is normalised by the inflow velocity at 15.9 m** (the Niigata meteorological station height;
  U(15.9 m) = 0.504531 × UR = 3.935 m/s with UR = 7.8 m/s at ZR = 250 m) — not by U_H, not by UR. A prior comparison
  in the folder divided by the wrong reference and came out low by a factor of 2.048.
- All 2560 published ratios are integer multiples of 0.0198204 (55 distinct levels): the data's own resolution is
  ±0.0099, 3.1 % of the median and about 10 % at the lowest points. No bar tighter than one quantum means anything.
- The readme describes `AF_caseE.csv`, `RS_caseE.csv` and `BD_caseE.stl`; the repository holds only the `.3dm`,
  `.ghx`, `.xls` and the MP drawing. Everything served here is extracted from the workbook and the 3dm.
- `CaseE(Niigata).3dm` is **full-scale metres**; `MP_caseE.png` is drawn at model scale (±0.8 m). Use layers
  `buildings` and `buildings_new_construction`; the map plate on the Japanese-named layer, the terrain plates and
  `probes` are not buildings. 475 of the 503 building shells are wound inward in the 3dm; the API's STLs are flipped
  outward.
- Do not take measurement coordinates from the `probes` layer: its spheres sit a median 2.31 m (max 21 m) from the
  workbook's points, which are authoritative.
