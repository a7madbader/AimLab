"""Synthetic mouse data with known properties, used to test the analysis code."""
import math
import random

from aimlab.mouse.analysis import Sample


def steady_stream(hz, seconds, dx_per_report=3, dy_per_report=0, jitter_ms=0.0, seed=1):
    rnd = random.Random(seed)
    period = 1e9 / hz
    n = int(seconds * hz)
    out, t = [], 0.0
    for _ in range(n):
        t += period + rnd.uniform(-jitter_ms, jitter_ms) * 1e6
        out.append(Sample(int(t), dx_per_report, dy_per_report))
    return out


def swipe(total_counts, duration_s, hz=1000, wobble_counts=0.0, speed_profile=None):
    """A straight swipe along +x with an optional sideways sine wobble.
    speed_profile: function(progress 0..1) -> relative speed (default constant)."""
    n = max(2, int(duration_s * hz))
    prof = speed_profile or (lambda p: 1.0)
    weights = [prof(i / (n - 1)) for i in range(n)]
    wsum = sum(weights)
    out, carry_x, carry_y, prev_wy = [], 0.0, 0.0, 0.0
    for i in range(n):
        carry_x += total_counts * weights[i] / wsum
        dx = int(round(carry_x)); carry_x -= dx
        wy = wobble_counts * math.sin(2 * math.pi * 3 * i / n)
        dy = int(round(wy - prev_wy + carry_y)); carry_y = (wy - prev_wy + carry_y) - dy
        prev_wy = wy
        out.append(Sample(int(i * 1e9 / hz), dx, dy))
    return out
