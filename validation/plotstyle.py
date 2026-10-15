"""One look for every figure in validation/: what the plot scripts import instead of styling themselves.

The reference is the house style for publication figures: a bold title, panels lettered a, b, c in bold at
the upper left, a full black frame with minor ticks, major grid lines strong enough to read values off,
units in square brackets, the MEASUREMENT drawn in black and each model in its own fixed colour, and one
frameless legend centred under the panels.

    import plotstyle as ps
    ps.apply()
    fig, axs = uplt.subplots(...)
    ...
    ps.finish(fig, "Title", handles=[ps.line(ps.MEASURED, "Wind tunnel"), ...])
    ps.save(fig, "figure-name.png")
"""
from __future__ import annotations

import os

import ultraplot as uplt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
FIGURES = os.path.join(HERE, "figures")

# The measurement is black, as in every comparison figure of the house style; each engine keeps one
# colour across every figure (the repository's validated categorical palette).
MEASURED = "#1a1a1a"
OPENFOAM = "#2a78d6"
OPENLB = "#eda100"
FLUIDX3D = "#e87ba4"
ML = "#1baf7a"
REFERENCE = "#7a7a78"   # 1:1 and factor-of-two lines: recessive, never data
SURFACE = "#ffffff"
INK = "#1a1a1a"

# Diverging pair for model/measurement ratios: red where the model is slow, blue where it is fast.
SLOW = "#e34948"
FAST = "#2a78d6"
NEUTRAL = "#f0efec"


def apply():
    """Set the house style. Call once, before any subplots."""
    uplt.rc.update({
        "font.size": 10.0,
        "label.size": 11.0,
        "tick.labelsize": 10.0,
        "title.size": 11.5,
        "suptitle.size": 13.0,
        "suptitle.weight": "bold",
        "abc": "a",
        "abc.loc": "ul",
        "abc.size": 12.0,
        "abc.weight": "bold",
        "abc.border": True,
        "abc.borderwidth": 2.5,
        "grid": True,
        "grid.color": "black",
        "grid.alpha": 0.28,
        "grid.linewidth": 0.6,
        "gridminor": False,
        "axes.linewidth": 0.8,
        "tick.width": 0.8,
        "tick.len": 4.5,
        "tick.minor": True,
        "legend.frameon": False,
        "legend.fontsize": 10.5,
        "lines.linewidth": 1.6,
        "figure.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
    })


def line(color, label, lw=1.8, ls="-"):
    return Line2D([], [], color=color, lw=lw, ls=ls, label=label)


def marker(color, label, filled=True, size=6.5):
    return Line2D([], [], ls="none", marker="o", markersize=size, label=label,
                  markerfacecolor=color if filled else "none", markeredgecolor=color if not filled else SURFACE,
                  markeredgewidth=1.0 if not filled else 0.4)


def stats(ax, text, loc=(0.05, 0.80)):
    """Scores printed in the panel, under its letter, on a white halo so grid lines never cut them."""
    ax.text(*loc, text, transform=ax.transAxes, va="top", ha="left", fontsize=8.5, color=INK, zorder=10,
            bbox=dict(boxstyle="round,pad=0.25", facecolor=SURFACE, edgecolor="none", alpha=0.85))


def one_to_one(ax, lo, hi, factor_two=True):
    import numpy as np
    xs = np.array([lo, hi])
    ax.plot(xs, xs, color=REFERENCE, lw=1.0, zorder=1)
    if factor_two:
        pos = np.array([max(lo, 1e-6), hi])
        ax.plot(pos, 2 * pos, color=REFERENCE, lw=0.8, ls=":", zorder=1)
        ax.plot(pos, 0.5 * pos, color=REFERENCE, lw=0.8, ls=":", zorder=1)


def outer_ticks(axs, nrows, ncols):
    """Tick labels on the outer edge of a grid only; the panels share their limits, so inner labels repeat."""
    import numpy as np
    grid = np.asarray(axs).reshape(nrows, ncols)
    for r in range(nrows):
        for c in range(ncols):
            grid[r, c].tick_params(labelleft=(c == 0), labelbottom=(r == nrows - 1))


def finish(fig, title, handles=None, ncols=None, **fmt):
    """Bold title, panel letters, and one frameless legend centred under the panels."""
    fig.format(suptitle=title, **fmt)
    if handles:
        fig.legend(handles, loc="b", ncols=ncols or len(handles), frame=False)


def save(fig, name, dpi=200):
    os.makedirs(FIGURES, exist_ok=True)
    fig.save(os.path.join(FIGURES, name), dpi=dpi)
    print("wrote", name)
