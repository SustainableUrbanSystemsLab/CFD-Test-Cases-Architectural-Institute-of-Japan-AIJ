---
title: For agents
nav_order: 6
---

# Using this from an agent or a script

Start at [`/api/llms.txt`]({{ '/api/llms.txt' | relative_url }}) — it is the same walk as below in plain text, with
every endpoint and every gotcha, and it is regenerated with the data.

## The walk

1. **`GET /api/index.json`** — the endpoint list, the schema version, the git commit the data was generated from, the
   licence and how to cite. If the Pages site is unreachable, `fallback_base_url` serves the identical files raw from
   the repository.
2. **`GET /api/cases.json`** — the five cases with their frame, units, counts, engine status and links. Pick an `id`.
3. **`GET /api/cases/{id}.json`** — read `frame`, `units` and `gotchas` **before** the numbers. They differ per case:
   A–D are model-scale metres with +x along the wind; E is full-scale metres, +x east, +y north, meteorological
   directions. `configurations` lists what `config` / `wind_direction_deg` / `instrument` take in the point table.
4. **`GET /api/cases/{id}/points.json`** (or `.csv`) — every value is SI: m, m/s, m²/s². One frame per case.
   Unmeasured values are `null` (empty in CSV). `columns` lists the fields present; `column_meaning` says what each is.
   Case E's quantity is a dimensionless `velocity_ratio` (Vs / U(15.9 m), U(15.9 m) = 3.935 m/s).
5. **`GET /api/cases/{id}/geometry.json`** then **`geometry.stl`** — metres, outward normals, origin at the building /
   array centre. Where the geometry is boxes (A, B, C, D) the JSON carries the box list, so you need not parse STL.
   Other configurations are `geometry_{configuration}.stl` (C: 0D, 1D; E: bc).
6. **`GET /api/cases/{id}/validation.json`** — Eddy3D scores per engine. **An empty `results` list means no validation
   exists for that case; do not infer one.** Today only A and B carry results (OpenFOAM 12, realizable k-ε).

## Rules that keep a comparison honest

- Normalise by the case's own U_H (`configuration.U_H_m_s`), or for E by U(15.9 m); k by U_H².
- Compare a thermistor quantity (C, D, E: `Vs`, `velocity_ratio`) against the bracket |U| ≤ Vs ≤ √(|U|² + 2k), not
  against |U| alone.
- Probe at the published coordinates; never interpolate the reference.
- Case B's V has already been sign-unified and converted to metres here — do not apply the corrections twice when
  starting from the raw files.
- Quote `generated_from` (the data commit) with any number you report.

## Cite

- Kikumoto, H., Tominaga, Y., Okaze, T. et al. (2026). *Comprehensive Experimental Database for Validating CFD
  Simulations in Urban Environments.* Japan Architectural Review 9(1), e70083.
- Tominaga, Y. et al. (2008). *AIJ guidelines for practical applications of CFD to pedestrian wind environment around
  buildings.* JWEIA 96, 1749–1761. https://doi.org/10.1016/j.jweia.2008.02.058
- Each case's own requested citation and Zenodo DOI are in `/api/cases/{id}.json` (`citation_requested`, `doi`).
- Licence: CC BY 4.0; the data belongs to its collectors and distributors.
