"""
The payoff diagram: hand-built inline SVG, not matplotlib, so it renders
pixel-identical in the browser and in the Playwright-rendered PDF. This is the
signature visual of the report — the lognormal price distribution at
expiration is drawn as a translucent ribbon behind the payoff line, so the
probability of profit stops being an abstract percentage and becomes visible:
you can see how much of the price-space mass sits over the green region.
"""
from __future__ import annotations

import math

import numpy as np

# Palette — must match static/css/report.css exactly (the ribbon is decorative
# but the P/L colors are semantic and used nowhere else, per the design brief).
INK = "#000000"
INDIGO = "#4338CA"
MINT = "#0E9F6E"
CORAL = "#E5484D"
HAIRLINE = "#E4D6B8"
MUTED = "#64748B"

_WIDTH = 760
_HEIGHT = 360
_PAD_LEFT = 64
_PAD_RIGHT = 24
_PAD_TOP = 24
_PAD_BOTTOM = 48
_PLOT_W = _WIDTH - _PAD_LEFT - _PAD_RIGHT
_PLOT_H = _HEIGHT - _PAD_TOP - _PAD_BOTTOM
_RIBBON_FRACTION = 0.40  # of plot height, reserved for the density hill


def _lognormal_density(x: np.ndarray, S: float, T: float, r: float, sigma: float) -> np.ndarray:
    T = max(T, 1e-6)
    sigma = max(sigma, 1e-6)
    mu = math.log(S) + (r - 0.5 * sigma**2) * T
    denom = x * sigma * math.sqrt(2 * math.pi * T)
    return np.exp(-((np.log(x) - mu) ** 2) / (2 * sigma**2 * T)) / denom


def render_payoff_svg(strategy, spot_price: float, T: float, r: float, sigma: float) -> str:
    """`strategy` is a strategies.StrategyResult. Returns a standalone <svg>."""
    breakeven = strategy.breakeven[0]
    anchors = sorted({spot_price, breakeven, strategy.strike})

    x_lo = max(0.01, anchors[0] * 0.55)
    x_hi = anchors[-1] * 1.55
    xs = np.unique(np.concatenate([np.linspace(x_lo, x_hi, 220), np.array(anchors)]))
    xs.sort()

    payoff = strategy.payoff_fn(xs)
    y_min = min(float(payoff.min()), 0.0) * 1.1
    y_max = max(float(payoff.max()), 0.0) * 1.1 if payoff.max() > 0 else abs(y_min) * 0.3
    if y_max == y_min:
        y_max = y_min + 1.0

    density = _lognormal_density(xs, spot_price, T, r, sigma)
    density_max = float(density.max()) or 1.0

    def x_px(x: float) -> float:
        return _PAD_LEFT + (x - x_lo) / (x_hi - x_lo) * _PLOT_W

    def y_px(y: float) -> float:
        return _PAD_TOP + (y_max - y) / (y_max - y_min) * _PLOT_H

    def density_px(d: float) -> float:
        baseline = _PAD_TOP + _PLOT_H
        return baseline - (d / density_max) * (_PLOT_H * _RIBBON_FRACTION)

    zero_px = y_px(0.0)
    baseline_px = _PAD_TOP + _PLOT_H

    # Ribbon: filled area under the density curve.
    ribbon_pts = " ".join(f"{x_px(x):.1f},{density_px(d):.1f}" for x, d in zip(xs, density))
    ribbon_path = f"M {x_px(xs[0]):.1f},{baseline_px:.1f} L {ribbon_pts} L {x_px(xs[-1]):.1f},{baseline_px:.1f} Z"

    # Payoff line.
    line_pts = " ".join(f"{x_px(x):.1f},{y_px(y):.1f}" for x, y in zip(xs, payoff))
    payoff_line = f"M {line_pts}"

    # Profit/loss fills relative to the zero line, split cleanly at breakeven
    # (already an exact sample point, so no jagged edge).
    below_be = xs <= breakeven
    above_be = xs >= breakeven

    def area_path(mask: np.ndarray) -> str:
        xs_m, payoff_m = xs[mask], payoff[mask]
        if len(xs_m) < 2:
            return ""
        pts = " ".join(f"{x_px(x):.1f},{y_px(y):.1f}" for x, y in zip(xs_m, payoff_m))
        return f"M {x_px(xs_m[0]):.1f},{zero_px:.1f} L {pts} L {x_px(xs_m[-1]):.1f},{zero_px:.1f} Z"

    loss_region_path = area_path(below_be) if strategy.pop_direction == "above" else area_path(above_be)
    profit_region_path = area_path(above_be) if strategy.pop_direction == "above" else area_path(below_be)

    def price_label(x: float) -> str:
        return f"${x:,.2f}"

    spot_x, be_x = x_px(spot_price), x_px(breakeven)

    gridlines = []
    n_gridlines = 4
    for i in range(n_gridlines + 1):
        gy = y_min + (y_max - y_min) * i / n_gridlines
        gpx = y_px(gy)
        gridlines.append(
            f'<line x1="{_PAD_LEFT}" y1="{gpx:.1f}" x2="{_WIDTH - _PAD_RIGHT}" y2="{gpx:.1f}" '
            f'stroke="{HAIRLINE}" stroke-width="1" />'
            f'<text x="{_PAD_LEFT - 10}" y="{gpx + 4:.1f}" text-anchor="end" '
            f'font-family="JetBrains Mono, monospace" font-size="11" fill="{MUTED}">'
            f'{"+" if gy > 0 else ""}{gy:,.0f}</text>'
        )

    return f"""
<svg viewBox="0 0 {_WIDTH} {_HEIGHT}" xmlns="http://www.w3.org/2000/svg" class="payoff-svg" role="img"
     aria-label="Payoff diagram with probability ribbon">
  <rect x="0" y="0" width="{_WIDTH}" height="{_HEIGHT}" fill="white" />
  {''.join(gridlines)}

  <path d="{ribbon_path}" fill="{INDIGO}" fill-opacity="0.12" stroke="none" />

  <path d="{loss_region_path}" fill="{CORAL}" fill-opacity="0.10" stroke="none" />
  <path d="{profit_region_path}" fill="{MINT}" fill-opacity="0.10" stroke="none" />

  <line x1="{_PAD_LEFT}" y1="{zero_px:.1f}" x2="{_WIDTH - _PAD_RIGHT}" y2="{zero_px:.1f}"
        stroke="{INK}" stroke-width="1" stroke-opacity="0.35" />

  <line x1="{be_x:.1f}" y1="{_PAD_TOP}" x2="{be_x:.1f}" y2="{baseline_px:.1f}"
        stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="4 4" />
  <text x="{be_x:.1f}" y="{_PAD_TOP - 8}" text-anchor="middle"
        font-family="Inter Tight, sans-serif" font-size="11" fill="{MUTED}">
    breakeven {price_label(breakeven)}</text>

  <line x1="{spot_x:.1f}" y1="{_PAD_TOP}" x2="{spot_x:.1f}" y2="{baseline_px:.1f}"
        stroke="{INDIGO}" stroke-width="1.5" stroke-dasharray="2 3" />
  <text x="{spot_x:.1f}" y="{baseline_px + 20}" text-anchor="middle"
        font-family="Inter Tight, sans-serif" font-size="11" font-weight="600" fill="{INDIGO}">
    spot {price_label(spot_price)}</text>

  <path d="{payoff_line}" fill="none" stroke="{INK}" stroke-width="2.5" stroke-linejoin="round" />
</svg>
""".strip()
