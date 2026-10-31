"""Analysis of recorded raw mouse samples. Pure Python, fully unit-testable.

Every function reports what was measured and refuses (ok=False) rather than guessing
when there is not enough data.
"""
import math
from dataclasses import dataclass, field
from statistics import mean, median, pstdev

from .calculations import COMMON_DPI, dpi_from_counts, nearest

COMMON_POLLING_HZ = (125, 250, 500, 1000, 2000, 4000, 8000)


@dataclass(frozen=True)
class Sample:
    t_ns: int   # time this program received the report (perf_counter_ns)
    dx: int     # raw counts since previous report
    dy: int


def _moving(samples):
    return [s for s in samples if s.dx or s.dy]


# ------------------------------------------------------------------ polling rate
@dataclass
class PollingResult:
    ok: bool
    reason: str = ""
    hz: float = 0.0
    nearest_common_hz: int = 0
    median_ms: float = 0.0
    jitter_ms: float = 0.0
    p95_ms: float = 0.0
    n_intervals: int = 0


def analyze_polling(samples, max_gap_ms=20.0, min_intervals=100) -> PollingResult:
    """Estimate polling rate from the spacing of movement reports.

    Gaps longer than max_gap_ms (pauses in movement) are ignored. The rate is
    events / time (1 / mean interval), which stays correct even if Windows delivers
    some reports in bursts.
    """
    ts = [s.t_ns for s in _moving(samples)]
    intervals = []
    for a, b in zip(ts, ts[1:]):
        ms = (b - a) / 1e6
        if 0 < ms <= max_gap_ms:
            intervals.append(ms)
    if len(intervals) < min_intervals:
        return PollingResult(False, "insufficient", n_intervals=len(intervals))
    m = mean(intervals)
    hz = 1000.0 / m
    srt = sorted(intervals)
    return PollingResult(True, "", hz=hz, nearest_common_hz=nearest(hz, COMMON_POLLING_HZ),
                         median_ms=median(intervals), jitter_ms=pstdev(intervals),
                         p95_ms=srt[int(0.95 * (len(srt) - 1))], n_intervals=len(intervals))


# ------------------------------------------------------------------ DPI
@dataclass
class DpiResult:
    ok: bool
    reason: str = ""
    dpi: float = 0.0
    nearest_common: int = 0
    counts: float = 0.0
    distance_cm: float = 0.0


def analyze_dpi(samples, distance_cm, min_counts=50) -> DpiResult:
    if distance_cm <= 0:
        raise ValueError("distance must be positive")
    sx = sum(s.dx for s in samples)
    sy = sum(s.dy for s in samples)
    counts = math.hypot(sx, sy)   # net straight-line displacement
    if counts < min_counts:
        return DpiResult(False, "too_few", counts=counts, distance_cm=distance_cm)
    dpi = dpi_from_counts(counts, distance_cm)
    return DpiResult(True, "", dpi=dpi, nearest_common=nearest(dpi, COMMON_DPI),
                     counts=counts, distance_cm=distance_cm)


# ------------------------------------------------------------------ acceleration
@dataclass
class Swipe:
    label: str
    counts: float
    duration_s: float
    speed: float          # counts per second


def swipe_from_samples(label, samples) -> Swipe:
    mv = _moving(samples)
    counts = math.hypot(sum(s.dx for s in mv), sum(s.dy for s in mv))
    dur = (mv[-1].t_ns - mv[0].t_ns) / 1e9 if len(mv) >= 2 else 0.0
    return Swipe(label, counts, dur, counts / dur if dur > 0 else 0.0)


@dataclass
class AccelResult:
    status: str                 # none | possible | likely | inconclusive
    deviation_pct: float = 0.0  # (fast - slow) / slow * 100
    speed_ratio: float = 0.0
    swipes: list = field(default_factory=list)


def analyze_acceleration(swipes, min_speed_ratio=3.0, possible_pct=8.0, likely_pct=15.0) -> AccelResult:
    """Compare counts for equal-distance swipes at different speeds.

    Thresholds are deliberately wide: a person cannot repeat a physical distance
    more precisely than a few percent, so smaller differences are not reported.
    """
    valid = [s for s in swipes if s.counts > 0 and s.speed > 0]
    if len(valid) < 2:
        return AccelResult("inconclusive", swipes=list(swipes))
    valid.sort(key=lambda s: s.speed)
    slow, fast = valid[0], valid[-1]
    ratio = fast.speed / slow.speed
    dev = (fast.counts - slow.counts) / slow.counts * 100.0
    if ratio < min_speed_ratio:
        return AccelResult("inconclusive", dev, ratio, valid)
    a = abs(dev)
    status = "likely" if a >= likely_pct else "possible" if a >= possible_pct else "none"
    return AccelResult(status, dev, ratio, valid)


# ------------------------------------------------------------------ movement smoothness
@dataclass
class MovementMetrics:
    ok: bool
    reason: str = ""
    path_length: float = 0.0
    net_distance: float = 0.0
    straightness_pct: float = 0.0
    wobble_pct: float = 0.0       # rms sideways deviation as % of net distance
    speed_cv_pct: float = 0.0     # speed variation across the central 80% of the swipe
    duration_s: float = 0.0


def analyze_movement(samples, bin_ms=10.0, min_samples=20, min_path=100) -> MovementMetrics:
    mv = _moving(samples)
    if len(mv) < min_samples:
        return MovementMetrics(False, "insufficient")
    path = sum(math.hypot(s.dx, s.dy) for s in mv)
    sx, sy = sum(s.dx for s in mv), sum(s.dy for s in mv)
    net = math.hypot(sx, sy)
    if path < min_path or net <= 0:
        return MovementMetrics(False, "insufficient")
    ux, uy = sx / net, sy / net
    nx, ny = -uy, ux
    x = y = 0.0
    sq = 0.0
    for s in mv:
        x += s.dx
        y += s.dy
        sq += (x * nx + y * ny) ** 2
    wobble = math.sqrt(sq / len(mv)) / net * 100.0

    t0, t1 = mv[0].t_ns, mv[-1].t_ns
    dur = (t1 - t0) / 1e9
    if dur <= 0:
        return MovementMetrics(False, "insufficient")
    nbins = max(1, int((t1 - t0) / (bin_ms * 1e6)) + 1)
    bins = [0.0] * nbins
    for s in mv:
        bins[min(nbins - 1, int((s.t_ns - t0) / (bin_ms * 1e6)))] += math.hypot(s.dx, s.dy)
    lo, hi = int(nbins * 0.1), int(nbins * 0.9)
    central = bins[lo:hi]
    if len(central) < 5 or mean(central) == 0:
        return MovementMetrics(False, "insufficient")
    cv = pstdev(central) / mean(central) * 100.0
    return MovementMetrics(True, "", path, net, net / path * 100.0, wobble, cv, dur)
