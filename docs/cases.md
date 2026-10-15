---
title: Cases
nav_order: 2
has_children: true
---

# The five cases

One page per case. Each opens with the geometry render, then the configuration facts, the frame and units the
cleaned data is served in, the reference data's layout, the inflow fit, the known data issues, and —
where a validation exists — the results. The same facts are served by the API as `/api/cases/{id}.json`.

{% include case-gallery.md %}

| Case | What it tests | Quantity | Frame served |
|---|---|---|---|
| [A — 1:1:2 building]({{ '/cases/case-a/' | relative_url }}) | an isolated tall prism | U, V, W, variances, k | model-scale metres, +x streamwise |
| [B — 1:4:4 slab]({{ '/cases/case-b/' | relative_url }}) | an isolated wide slab | U, V, W, variances, k | model-scale metres (converted from mm), +x streamwise, V sign unified |
| [C — 3 × 3 block array]({{ '/cases/case-c/' | relative_url }}) | streets between cubes, a taller centre block, 3 directions | scalar speed Vs at 0.1 D | model-scale metres, +x streamwise at WD = 0 |
| [D — high-rise among blocks]({{ '/cases/case-d/' | relative_url }}) | a tower in a regular low-rise array, 3 directions | scalar speed Vs at 5 mm; U, V, W, k at 33 points | model-scale metres (converted from mm), +x streamwise at WD = 0 |
| [E — Niigata district]({{ '/cases/case-e/' | relative_url }}) | a real district before and after a 60 m high-rise, 16 directions | velocity ratio at 2 m | full-scale metres, +x east, +y north |
