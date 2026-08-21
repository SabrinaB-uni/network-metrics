"""
Tiny inline-SVG chart helpers — no JavaScript, no external libraries.

Colours come from CSS classes (styled in style.css) so the charts adapt to the
light/dark theme automatically. Each function returns an SVG string that the
templates drop in with `{{ chart|safe }}`.
"""
from __future__ import annotations

import html


def _nice_max(v: float) -> int:
    if v <= 0:
        return 10
    for step in (10, 20, 25, 50, 100, 150, 200, 300, 500, 1000, 2000):
        if v <= step:
            return step
    return int((v // 1000 + 1) * 1000)


def line_chart(values, labels=None, width=940, height=260) -> str:
    """A filled line chart of `values` with optional x-axis `labels`."""
    if not values:
        return '<div class="chart-empty">No data yet</div>'

    pad_l, pad_r, pad_t, pad_b = 44, 16, 14, 28
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    ymax = _nice_max(max(values))
    n = len(values)

    def x(i):
        return pad_l + (plot_w * i / (n - 1) if n > 1 else 0)

    def y(val):
        return pad_t + plot_h * (1 - val / ymax)

    pts = [(x(i), y(v)) for i, v in enumerate(values)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = (f"M{pts[0][0]:.1f},{pad_t + plot_h:.1f} "
            + " ".join(f"L{px:.1f},{py:.1f}" for px, py in pts)
            + f" L{pts[-1][0]:.1f},{pad_t + plot_h:.1f} Z")

    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart" '
             f'preserveAspectRatio="none" role="img">']

    # horizontal gridlines + y labels
    for frac in (0, 0.5, 1):
        gy = pad_t + plot_h * frac
        val = int(ymax * (1 - frac))
        parts.append(f'<line class="chart-grid" x1="{pad_l}" y1="{gy:.1f}" '
                     f'x2="{width - pad_r}" y2="{gy:.1f}"/>')
        parts.append(f'<text class="chart-axis" x="{pad_l - 8}" y="{gy + 4:.1f}" '
                     f'text-anchor="end">{val}</text>')

    parts.append(f'<path class="chart-area" d="{area}"/>')
    parts.append(f'<polyline class="chart-line" points="{line}"/>')

    # x labels — show about six, evenly spaced
    if labels:
        step = max(1, n // 6)
        for i in range(0, n, step):
            parts.append(
                f'<text class="chart-axis" x="{x(i):.1f}" y="{height - 8}" '
                f'text-anchor="middle">{html.escape(str(labels[i]))}</text>')

    parts.append("</svg>")
    return "".join(parts)


def bar_chart(items, width=940, bar_h=24, gap=12, label_w=160) -> str:
    """Horizontal bars. `items` = list of {label, value, sub}."""
    if not items:
        return '<div class="chart-empty">No data yet</div>'

    vmax = max(i["value"] for i in items) or 1
    plot_w = width - label_w - 60
    height = len(items) * (bar_h + gap) + gap
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart-bars" role="img">']

    for idx, it in enumerate(items):
        top = gap + idx * (bar_h + gap)
        bw = plot_w * it["value"] / vmax
        label = html.escape(str(it["label"]))
        sub = html.escape(str(it.get("sub", "")))
        parts.append(f'<text class="chart-axis strong" x="0" y="{top + bar_h * 0.55:.0f}">'
                     f'{label}</text>')
        if sub:
            parts.append(f'<text class="chart-axis dim" x="0" y="{top + bar_h * 0.55 + 13:.0f}">'
                         f'{sub}</text>')
        parts.append(f'<rect class="chart-bar-bg" x="{label_w}" y="{top}" '
                     f'width="{plot_w}" height="{bar_h}" rx="4"/>')
        parts.append(f'<rect class="chart-bar" x="{label_w}" y="{top}" '
                     f'width="{bw:.1f}" height="{bar_h}" rx="4"/>')
        parts.append(f'<text class="chart-axis strong" x="{label_w + bw + 8:.1f}" '
                     f'y="{top + bar_h * 0.68:.0f}">{it["value"]}</text>')

    parts.append("</svg>")
    return "".join(parts)
