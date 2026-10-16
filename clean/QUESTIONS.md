# Open questions for the data collectors (Ilker / Patrick to forward)

Things the published files, readmes and the data paper (Kikumoto et al. 2026, JAR 9(1) e70083)
cannot settle, each with what was measured and what one line from the collector would close.
Contacts are in `manifest.json → cases.<id>.contact`. Numbers below are in `checks.json`.

## Q1 — Case C: which way does the turntable turn? (Nonomura)

In `RS_caseC.csv`'s own frame (+x = the WD = 0 flow, confirmed three ways on the data) the WD = 45°
field is mirror-symmetric about the line **y = −x**: mean |ΔVs| over the 57 mirror pairs is
0.108 / 0.103 / 0.130 m/s for 0D / 1D / 2D — the experiment's own repeatability floor — while the
mirror about y = +x gives 0.52 / 0.77 / 0.80 m/s. So in the CSV the wind rotates from +x **toward
−y** as WD grows. Figure 3 of the data paper draws the 0 / 22.5 / 45° arrows fanning toward **+y**.
The two differ by a sign of y, which is invisible at WD = 0.

This release keeps the CSV frame (`directions.csv`: flow_dir = (cos WD, −sin WD)) because the point
coordinates live in it. **Question:** is the y axis of `RS_caseC.csv` the one in Figure 3, or its
mirror? Equivalently: for WD = 45°, does the wind come from the (−x, +y) quadrant or the (−x, −y)
quadrant of the CSV coordinates?

*Update 2026-10-14 — a second, independent line of evidence.* Eddy3D solved all nine configurations
(OpenFOAM 12, realizable k-ε) and scored the 120 points both ways on the same solutions: in the CSV's
sense R = 0.83–0.91 at 22.5° and 45°; in Figure 3's sense (the y mirror) R = −0.33 … +0.03. A RANS
solution knows nothing about the CSV's convention, so the data's own symmetry and the physics now agree;
the question stays open only for the collector's word on Figure 3.

## Q2 — Case D: rotation sense for 22.5° and 45° (Tominaga)

The 83-block array is exactly symmetric under y → −y, so a wind at +θ and one at −θ give exact mirror
fields and **no measurement can distinguish them**; the 0° thermistor column is itself an exact
y-mirror (33 pairs with ΔVs = 0, i.e. half of it was measured and mirrored). The sense used here
(flow_dir = (cos WD, +sin WD), status `unverified`) is a reading of Figure 4 of the data paper, and
it is the OPPOSITE of what Case C's data show for Case C. The Zenodo readme (now in
`clean/sources/zenodo_caseD/`) does not state it either.

**Question:** at WD = 22.5° and 45°, is the wind turned from +x toward +y or toward −y, in the
coordinates of `RS-T_caseD.csv` / `MP_caseD.png`? (Also: which half of the 0° plane was actually
measured, +y or −y?)

*Update 2026-10-15 — the solved field decides 22.5°.* No measurement alone can, but a solution can: Eddy3D
solved the array at 22.5° (OpenFOAM 12, realizable k-ε, 3.6 million cells) and scored the 66 measured
points in this release's sense and in its y mirror on the same solution. In Figure 4's sense (+x toward
+y) R = 0.80, FAC2 0.92; mirrored R = 0.40, FAC2 0.74. A RANS solution knows nothing about the figure, so
22.5° is corroborated in Figure 4's sense (`directions.csv` says so); 45° stays unverified until it is
solved. The question stays open for the collector's word, and for 45°.

*Update 2026-10-16 — and 45°.* Solved the same way (3000 iterations, the same residual plateau as 0° and
22.5°): in Figure 4's sense R = 0.85, FAC2 0.89; mirrored R = 0.17, FAC2 0.70 — a wider margin than at 22.5°.
Both rotated headings are now corroborated in Figure 4's sense. The question stays open only for the
collector's own word, and for which half of the 0° plane was measured.

## Q3 — Case E: the sensor frame against the two geometries (Tominaga)

1. Point 50 at (−45.5, −45.0) m lies **0.17 m inside a building wall of the official `BD_caseE.stl`**
   (roof at 6.75 m) and 2.06 m clear of the nearest wall in `case-e.3dm`. The other 79 points
   are in open space in both files (median 4.9 m from the nearest vertex). The two files are
   different triangulations of the district (official: 227 shells, 60,101 triangles, 5,253 open
   edges, bbox ±198 m after ×250; the 3dm: 5,015 meshes, bbox −201.5…203 m). Which is the
   measured model, and is point 50 really in the street?
2. The official STL is **model scale** (z max 0.24 m = 60 m / 250) while the readme calls the
   coordinates "actual scale"; the ×250 is this release's inference from the 60 m high-rise. Please
   confirm, and whether a watertight STL exists.
3. The dataset publishes **only the after-construction geometry**. The before-construction state
   used here (`geometry_bc_3dm.stl`) is the 3dm's `buildings` layer with the three sites empty. Is
   that what stood in the tunnel for the "bc" runs, or were there earlier buildings on the sites?
4. `RS_caseE.csv` on Zenodo is the workbook rounded to 2 dp (max |Δ| 0.00497); the workbook's values
   are exact multiples of 0.0198204 (= U/UR at 0.01 resolution re-normalised by UR / U(15.9 m), which
   gives U(15.9 m) = 3.935 m/s; the paper says 4.0). Which U_ref was used, and is the workbook the
   authoritative precision?

## Q4 — Case B: lateral sign and the seven repeated points (Tominaga)

1. The published V appears positive toward −y: V = +3.630 m/s at (−25, −110, 12.5) mm, just outside
   the y = −100 mm flank where the flow must deflect away from the centreline. Case A (V = −2.893 at
   the equivalent point) and Case D (V = +2.055 on the +y flank) both read positive toward +y. This
   release flips B's V. Please confirm the sign convention of V in `RS_caseB.csv` (or whether the
   published points are on the +y half rather than the −y half of the drawing).
2. Seven locations appear twice with different values: the foot of each vertical-section profile
   (z = 12.5 mm, y = 0; points 12, 43, 56, 69, 82, 95, 108) and the horizontal-plane centreline
   (points 110, 147, 160, 173, 186, 199, 212). |ΔU| = 0.05–0.14 m/s (mean 0.105). Two runs? Which
   is canonical, or should both be kept (as here) as a repeatability estimate?

## Q5 — Case C: what reference speed did the legacy workbook use? (Nonomura)

`LF-caseC.xls` publishes velocity ratios "normalized by the inflow velocity at the same height".
Multiplying by U(0.02 m) = 2.434 m/s from `AF_caseC.csv` reproduces the CSV's Vs only to 0.3 %:
Vs / ratio spans 2.4145–2.4525 m/s across the 1,080 values, so the ratios seem to use a per-run
reference. Is that so, and are the CSV's 2-dp Vs values the raw measurements?

## Q6 — Case D: the split-fibre "Scalar Vel." column (Tominaga)

`RS-S_caseD.csv`'s `Vs` and the workbook's `Scalar Vel.` equal √(U²+V²+W²) to 1e-15 at all 33
points, so they are the vector magnitude, not a thermistor reading, and are dropped here. Is that
right? (The thermistor readings at the same 33 points are in `RS-T_caseD.csv`; their ratio to the
magnitude averages 1.34.)

## Q7 — Cases A, B, C: model scale (Ishihara / Tominaga / Nonomura)

No model:full-scale ratio is stated for A, B or C (D says 1:400, E 1:250). Eddy3D solves them at
1:100 with the tunnel velocities, which only matters for how results are labelled. Is a nominal
scale on record?

## Q8 — Case C: data paper Table 2 vs the CSV point numbering (Nonomura)

The readme lists 1, 2, 3, 34, 35, 36, 37, 46, 55, 100, 101, 102 as missing point numbers and the CSV
agrees (4…132 with those gaps). Were points 1–3 and the nine interior gaps never measured, or
measured and withheld (e.g. inside buildings for one configuration)?
