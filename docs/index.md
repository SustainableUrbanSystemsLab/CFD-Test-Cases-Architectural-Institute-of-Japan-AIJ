---
title: Home
nav_order: 1
---

# AIJ UWE benchmark — cleaned data, validation, API

Wind-tunnel reference data from the **AIJ UWE** (Architectural Institute of Japan, Urban Wind Environment)
benchmark, cleaned and packaged case by case, together with Eddy3D's validation against it. Everything here
is also served as a [static API]({{ '/api-reference/' | relative_url }}) for scripts and agents.

<div style="display:flex;gap:6px;flex-wrap:wrap;margin:1em 0">
<a href="{{ '/cases/case-a/' | relative_url }}"><img src="{{ '/assets/geom_caseA.png' | relative_url }}" alt="Case A" style="width:19%;min-width:140px"></a>
<a href="{{ '/cases/case-b/' | relative_url }}"><img src="{{ '/assets/geom_caseB.png' | relative_url }}" alt="Case B" style="width:19%;min-width:140px"></a>
<a href="{{ '/cases/case-c/' | relative_url }}"><img src="{{ '/assets/geom_caseC.png' | relative_url }}" alt="Case C" style="width:19%;min-width:140px"></a>
<a href="{{ '/cases/case-d/' | relative_url }}"><img src="{{ '/assets/geom_caseD.png' | relative_url }}" alt="Case D" style="width:19%;min-width:140px"></a>
<a href="{{ '/cases/case-e/' | relative_url }}"><img src="{{ '/assets/geom_caseE.png' | relative_url }}" alt="Case E" style="width:19%;min-width:140px"></a>
</div>

| Case | Configuration | Measurements | Scored |
|---|---|---|---|
| [A]({{ '/cases/case-a/' | relative_url }}) | 1:1:2 building, b = 0.08 m, H = 0.16 m, Re_H ≈ 24,000 | 186 points, U/V/W/k | OpenFOAM 12, OpenLB, ML |
| [B]({{ '/cases/case-b/' | relative_url }}) | 1:4:4 slab, 0.05 × 0.20 × 0.20 m, Re_H ≈ 72,000 | 224 points, U/V/W/k | OpenFOAM 12, OpenLB, ML |
| [C]({{ '/cases/case-c/' | relative_url }}) | 3 × 3 block array, centre building at 0D / 1D / 2D, 3 wind directions | 1080 points, pedestrian height, scalar speed | OpenFOAM 12, ML |
| [D]({{ '/cases/case-d/' | relative_url }}) | High-rise among 82 blocks, 1:400, 3 wind directions | 78 points × 3 (thermistor) + 33 (split fibre) | ML; OpenFOAM solving |
| [E]({{ '/cases/case-e/' | relative_url }}) | Niigata district, 1:250, pre/post high-rise, 16 wind directions | 80 points × 16 × 2, velocity ratio | OpenFOAM 12 (SW), ML |

*Scored* means a run exists and its scores are published here — not that it agrees; how well it agrees is in the
numbers and their reading on the [Validation]({{ '/validation/' | relative_url }}) page. FluidX3D is running on A
and B; OpenLB is scored on A and B and, at the resolution this machine runs, cannot reach the C–E pedestrian
planes (measured, on the Validation page). Anything not marked scored is not a claim.

## Where to go

- **[Cases]({{ '/cases/' | relative_url }})** — one page per case: geometry render, configuration facts, the reference data's
  layout and frame, the inflow fit, what to know before comparing, and the validation results where they exist.
- **[Validation]({{ '/validation/' | relative_url }})** — how Eddy3D is scored against the tunnel, the scores for A, B and C, the ML surrogate, and what is still running.
- **[Data gotchas]({{ '/gotchas/' | relative_url }})** — the things in the published files that silently corrupt a comparison (units, signs, frames, scalar vs vector speed).
- **[API]({{ '/api-reference/' | relative_url }})** — every endpoint with `curl` and Python examples: cleaned points (SI, one frame), cleaned STL geometry in metres (per case, or all of it in one archive), validation scores.
- **[For agents]({{ '/agents/' | relative_url }})** — the walk through the API, and [`/api/llms.txt`]({{ '/api/llms.txt' | relative_url }}).

## Licence and attribution

The measurement data belongs to its collectors and distributors, named per case (CC BY 4.0). Cite the AIJ UWE
benchmark — Kikumoto et al. (2026), *Comprehensive Experimental Database for Validating CFD Simulations in Urban Wind Environment: Benchmark Cases Curated by the Architectural Institute of Japan*,
Japan Architectural Review 9(1) e70083, [doi:10.1002/2475-8876.70083](https://doi.org/10.1002/2475-8876.70083)
— and each case's dataset and requested citation, linked on its case page.
