"""Axonometric renders of every geometry configuration the API serves.

    python validation/render_geometry.py

Writes validation/figures/geometry/case-<id>[-<configuration>].png. The geometry comes from
scripts/aijdata.py's `case_geometry`, the same function that writes the API's STL files, so a render
always shows exactly what /api/cases/{id}/geometry*.stl contains. The images carry no title or caption;
the site and the README set the caption next to each one.

Every case is drawn the same way so they compare at a glance: one camera standing on the upwind (-x) side,
flat shading from one fixed light, a recessive ground grid and the wind direction, on a 2:1 canvas. The
configurations of a case (C: 0D/1D/2D, E: before/after) share one window, so they line up side by side.

Why a hand-rolled projection rather than mplot3d: depth ordering. mplot3d sorts whole collections, not
faces, so buildings interpenetrate at these viewing angles. Here every polygon is projected to 2-D and
painted back to front (painter's algorithm), which is correct for convex, non-intersecting massing.

Why coplanar triangles are merged into quads first: stroking a triangle's edges draws the diagonal across
every face, which reads as a crease that is not there. Coplanar pairs sharing an edge become one quad, so an
outline is a building edge and nothing else.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir, "scripts"))
import aijdata as D  # noqa: E402

OUT = os.path.join(HERE, "figures", "geometry")

WIND = "#eb6834"
GRID = "#dcdcd9"
BODY = np.array([0.66, 0.68, 0.72])         # neutral massing, shaded per face
ACCENT = np.array([0.165, 0.471, 0.839])    # the subject of the case (#2a78d6)
EDGE = "#ffffff"

# One camera for every case. The azimuth is negative so that +x (the wind at WD = 0) runs left to right on
# screen while the camera stands on the -x side: the windward face is the one you see.
AZ, EL = math.radians(-34.0), math.radians(27.0)
_d = np.array([math.cos(AZ) * math.cos(EL), math.sin(AZ) * math.cos(EL), -math.sin(EL)])   # into the screen
_r = np.array([-math.sin(AZ), math.cos(AZ), 0.0])                                           # screen right
_u = np.cross(_d, _r)                                                                       # screen up
assert _u[2] > 0 and _r[0] > 0
# Light from above and behind the camera's left shoulder: roof brightest, windward face mid, side darkest.
LIGHT = np.array([-0.45, 0.28, 0.85])
LIGHT /= np.linalg.norm(LIGHT)


def project(p):
    """World (x, y, z) -> screen (right, up), plus depth into the screen."""
    p = np.asarray(p, float)
    return np.stack([p @ _r, p @ _u], -1), p @ _d


def _normal(p):
    n = np.cross(p[1] - p[0], p[2] - p[0])
    ln = np.linalg.norm(n)
    return n / ln if ln > 0 else n


def _convex_planar(q, tol=1e-6):
    n = _normal(q)
    if np.linalg.norm(n) == 0 or abs((q[3] - q[0]) @ n) > tol * (1 + np.abs(q).max()):
        return False
    signs = [np.sign(np.cross(q[(i + 1) % 4] - q[i], q[(i + 2) % 4] - q[(i + 1) % 4]) @ n) for i in range(4)]
    return all(s == signs[0] and s != 0 for s in signs)


def merge_coplanar(tris, tol=1e-6):
    """Pair triangles that share an edge and lie in one plane into convex quads; keep the rest as they are."""
    tris = np.asarray(tris, float)
    if len(tris) == 0:
        return []
    scale = 1.0 + np.abs(tris).max()
    key = lambda v: tuple(np.round(v / (tol * scale)).astype(np.int64))  # noqa: E731
    normals = np.array([_normal(t) for t in tris])
    edges = {}
    for t in range(len(tris)):
        k = [key(tris[t, i]) for i in range(3)]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges.setdefault(tuple(sorted((k[a], k[b]))), []).append((t, a, b))
    used = np.zeros(len(tris), bool)
    polys = []
    for owners in edges.values():
        if len(owners) != 2:
            continue
        (t1, a1, b1), (t2, a2, b2) = owners
        if used[t1] or used[t2] or abs(float(normals[t1] @ normals[t2])) < 0.9999:
            continue
        quad = np.array([tris[t1, 3 - a1 - b1], tris[t1, a1], tris[t2, 3 - a2 - b2], tris[t1, b1]])
        if _convex_planar(quad):
            polys.append(quad)
            used[t1] = used[t2] = True
    polys.extend(list(tris[~used]))
    return polys


def draw(ax, groups, edges):
    """groups: [(triangles, base colour)], painted back to front across all groups together."""
    polys, cols = [], []
    for tris, base in groups:
        for p in merge_coplanar(tris):
            polys.append(p)
            cols.append(np.clip(base * (0.50 + 0.50 * abs(float(_normal(p) @ LIGHT))), 0, 1))
    order = np.argsort([-project(p)[1].mean() for p in polys])
    ax.add_collection(PolyCollection([project(polys[i])[0] for i in order], facecolors=[cols[i] for i in order],
                                     edgecolors=EDGE if edges else "none", linewidths=0.5 if edges else 0.0,
                                     antialiased=True, joinstyle="round"))


def ground_grid(ax, x0, x1, y0, y1, step):
    for xv in np.arange(x0, x1 + 1e-9, step):
        p, _ = project([[xv, y0, 0], [xv, y1, 0]])
        ax.plot(p[:, 0], p[:, 1], color=GRID, lw=0.5, zorder=0)
    for yv in np.arange(y0, y1 + 1e-9, step):
        p, _ = project([[x0, yv, 0], [x1, yv, 0]])
        ax.plot(p[:, 0], p[:, 1], color=GRID, lw=0.5, zorder=0)


def arrow(ax, start, end, label, colour=WIND):
    p, _ = project([start, end])
    ax.annotate("", xy=p[1], xytext=p[0], arrowprops=dict(arrowstyle="-|>", color=colour, lw=2.2, mutation_scale=16))
    ax.text(p[0][0], p[0][1], label + "  ", color=colour, fontsize=11, ha="right", va="center")


def boxes_tris(boxes):
    return np.array([t for b in boxes for t in D.box_tris(b["min"], b["max"])], float)


def scene(case):
    """[(configuration, groups, edges)] and the decorations shared by every configuration of the case."""
    out = []
    for cfg, tris, boxes, _ in D.case_geometry(case):
        tris = np.asarray(tris, float)
        if case in ("A", "B"):
            groups = [(tris, ACCENT)]
        elif case == "C":
            centre = [b for b in boxes if abs(b["min"][0] + b["max"][0]) < 1e-9 and abs(b["min"][1] + b["max"][1]) < 1e-9]
            rest = [b for b in boxes if b not in centre]
            groups = [(boxes_tris(rest), BODY)] + ([(boxes_tris(centre), ACCENT)] if centre else [])
        elif case == "D":
            ztop = max(b["max"][2] for b in boxes)
            tall = [b for b in boxes if b["max"][2] > 0.6 * ztop]
            groups = [(boxes_tris([b for b in boxes if b not in tall]), BODY), (boxes_tris(tall), ACCENT)]
        else:
            groups = [(tris, BODY)]
        out.append((cfg, groups, case != "E"))
    if case == "E":
        # The new construction is what the after state adds to the before state.
        tris_of = {cfg: groups[0][0] for cfg, groups, _ in out}
        before, after = tris_of["bc"], tris_of["ac"]
        key = lambda t: frozenset(tuple(np.round(v, 3)) for v in t)  # noqa: E731
        old = {key(t) for t in before}
        new = np.array([key(t) not in old for t in after])
        out = [("bc", [(before, BODY)], False), ("ac", [(after[~new], BODY), (after[new], ACCENT)], False)]
    return out


def decorate(ax, case, lo, hi):
    if case == "A":
        ground_grid(ax, -0.16, 0.20, -0.12, 0.12, 0.04)
        arrow(ax, (-0.17, 0, 0.02), (-0.07, 0, 0.02), "wind")
    elif case == "B":
        ground_grid(ax, -0.15, 0.25, -0.2, 0.2, 0.05)
        arrow(ax, (-0.18, 0, 0.03), (-0.05, 0, 0.03), "wind")
    elif case == "C":
        ground_grid(ax, -0.6, 0.6, -0.6, 0.6, 0.2)
        arrow(ax, (-0.85, 0, 0.03), (-0.62, 0, 0.03), "wind, WD = 0°")
    elif case == "D":
        ground_grid(ax, lo[0] - 0.1, hi[0] + 0.1, lo[1] - 0.1, hi[1] + 0.1, 0.2)
        arrow(ax, (lo[0] - 0.32, 0, 0.03), (lo[0] - 0.08, 0, 0.03), "wind, WD = 0°")
    else:
        ground_grid(ax, lo[0], hi[0], lo[1], hi[1], 50)
        # Geographic frame: +x east, +y north. The scored direction is SW, so the arrow comes from the SW.
        s = 1 / math.sqrt(2)
        cx, cy = lo[0] + 10, lo[1] + 10
        arrow(ax, (cx - 60 * s, cy - 60 * s, 6), (cx, cy, 6), "wind from SW")
        arrow(ax, (hi[0] + 15, hi[1] - 70, 0), (hi[0] + 15, hi[1] - 10, 0), "N", colour="#5c5c5a")


ASPECT = 2.0   # every render is 2:1, so a row of them lines up and so do their captions
SIZE_IN = (8.0, 4.0)
DPI = 160      # 1280 x 640 px


def _limits(figs):
    """One window for every configuration of a case: the drawing, the arrows and their labels, padded to 2:1."""
    xl = [min(a.get_xlim()[0] for _, _, a in figs), max(a.get_xlim()[1] for _, _, a in figs)]
    yl = [min(a.get_ylim()[0] for _, _, a in figs), max(a.get_ylim()[1] for _, _, a in figs)]
    for _ in range(2):  # labels are sized in points: measure them at the current scale, widen, measure again
        for _, fig, ax in figs:
            ax.set_xlim(*xl)
            ax.set_ylim(*yl)
            fig.canvas.draw()
            for t in ax.texts:
                bb = t.get_window_extent().transformed(ax.transData.inverted())
                xl = [min(xl[0], bb.x0), max(xl[1], bb.x1)]
                yl = [min(yl[0], bb.y0), max(yl[1], bb.y1)]
    w, h = xl[1] - xl[0], yl[1] - yl[0]
    w, h = max(w, h * ASPECT) * 1.04, max(h, w / ASPECT) * 1.04
    cx, cy = (xl[0] + xl[1]) / 2, (yl[0] + yl[1]) / 2
    return (cx - w / 2, cx + w / 2), (cy - h / 2, cy + h / 2)


def render_case(case):
    configs = scene(case)
    allv = np.concatenate([np.concatenate([g for g, _ in groups]).reshape(-1, 3) for _, groups, _ in configs])
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    figs = []
    for cfg, groups, edges in configs:
        fig = plt.figure(figsize=SIZE_IN)
        ax = fig.add_axes((0, 0, 1, 1))
        decorate(ax, case, lo, hi)
        draw(ax, groups, edges)
        ax.set_aspect("equal", adjustable="datalim")
        ax.axis("off")
        ax.autoscale_view()
        figs.append((cfg, fig, ax))
    xl, yl = _limits(figs)
    written = []
    for cfg, fig, ax in figs:
        ax.set_xlim(*xl)
        ax.set_ylim(*yl)
        name = D.render_file(case, cfg)
        fig.savefig(os.path.join(OUT, name), dpi=DPI, facecolor="#ffffff")
        plt.close(fig)
        written.append(name)
    return written


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    cube = merge_coplanar(boxes_tris([{"min": [0, 0, 0], "max": [1, 1, 1]}]))
    assert len(cube) == 6 and all(len(q) == 4 for q in cube), "a unit cube must merge to six quads"
    for c in D.CASE_IDS:
        print(c, render_case(c))
