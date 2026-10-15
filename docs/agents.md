---
title: For agents
nav_order: 6
---

# Using this from an agent or a script

Start at [`/llms.txt`]({{ '/llms.txt' | relative_url }}). It has the walk below in plain text, every endpoint, and
every known data issue, and it is regenerated with the data. The formal contract is
[`/api/openapi.json`]({{ '/api/openapi.json' | relative_url }}), together with the JSON Schema that each document
names in `$schema`.

## The walk

1. **`GET /api/index.json`**: every endpoint and every file with its size and SHA-256, the API version, the
   `data_version`, the changelog, the licence and how to cite. If the Pages site is unreachable, `fallback_base_url`
   serves the identical files raw from the repository.
2. **`GET /api/cases.json`**: the five cases with their frame, units, counts, engine status and links. Pick an `id`.
3. **`GET /api/cases/{id}.json`**: read `frame`, `units` and `known_issues` **before** the numbers, because they
   differ per case. A–D are model-scale metres with +x along the wind. E is full-scale metres, +x east, +y north,
   with meteorological directions. `configurations` lists the values `config`, `wind_direction_deg` and `instrument`
   take in the point table.
4. **`GET /api/cases/{id}/points.json`** (or the `points.csv` download): every value is SI (m, m/s, m²/s²), in one
   frame per case. Unmeasured values are `null` (an empty cell in CSV). `columns` lists the fields present, and
   `column_meaning` defines each. Case E's quantity is a dimensionless `velocity_ratio` (Vs / U(15.9 m), with
   U(15.9 m) = 3.935 m/s).
5. **`GET /api/cases/{id}/geometry.json`**, then the STL it links: metres, outward normals, origin at the building or
   array centre. Where the geometry is boxes (A–D), the JSON carries the box list, so you need not parse STL.
6. **`GET /api/validation.json`**: every case and engine in one table. **An engine whose status is not `scored` has
   no result for that case; do not infer one.** `scored` means a run exists, not that it agrees. For one case in
   full, `GET /api/cases/{id}/validation.json`: every score, the `headline` scores to quote, the figures, and
   `pairs`, the per-point measured and modelled values behind the scores.

## Rules that keep a comparison honest

- Normalise by the case's own U_H (`configuration.U_H_m_s`), or for Case E by U(15.9 m); normalise k by U_H².
- Compare a thermistor quantity (C, D, E: `Vs`, `velocity_ratio`) against the bracket |U| ≤ Vs ≤ √(|U|² + 2k), not
  against |U| alone.
- Probe at the published coordinates; never interpolate the reference.
- The served tables already apply each case's corrections: Case B's V is sign-unified and its coordinates are in
  metres. Do not apply those corrections a second time when starting from the raw files.
- Use the download URLs the documents give rather than building them yourself, and check each file against its
  `sha256`.
- Quote `data_version` with any number you report: it identifies exactly the data the number came from.

## Cite

- Kikumoto, H., Okaze, T., Yoshie, R., Tachibana, T., Ishihara, T., Nonomura, Y., Kiyota, N., Kondo, H., Mochida, A., Tominaga, Y. (2026).
  *Comprehensive Experimental Database for Validating CFD Simulations in Urban Wind Environment: Benchmark Cases Curated by the Architectural Institute of Japan.* Japan Architectural Review 9(1), e70083.
  [doi:10.1002/2475-8876.70083](https://doi.org/10.1002/2475-8876.70083)
- Tominaga, Y. et al. (2008). *AIJ guidelines for practical applications of CFD to pedestrian wind environment around
  buildings.* JWEIA 96, 1749–1761. https://doi.org/10.1016/j.jweia.2008.02.058
- Each case's own requested citation and Zenodo DOI are in `/api/cases/{id}.json` (`citation_requested`, `doi`).
- Licence: CC BY 4.0 (SPDX `CC-BY-4.0`). The data belongs to its collectors and distributors.
