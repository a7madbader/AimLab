"""Sensitivity maths. Pure functions, no Qt, no Windows APIs."""

CM_PER_INCH = 2.54
COMMON_DPI = (400, 500, 800, 1000, 1200, 1600, 2400, 3200, 4000, 6400)

# Degrees of rotation per mouse count at in-game sensitivity 1.0 ("yaw").
# Only values that are well established are listed; other games (and FOV-aware
# conversion) are added in the Game Profiles phase. Users can always enter a custom yaw.
GAME_YAW = {
    "cs2": 0.022,
    "valorant": 0.07,
    "apex": 0.022,
    "overwatch2": 0.0066,
    "cod": 0.0066,
}


def nearest(value, options):
    return min(options, key=lambda o: abs(o - value))


def edpi(dpi, sensitivity):
    return dpi * sensitivity


def cm_per_360(dpi, sensitivity, yaw):
    """Physical distance (cm) the mouse travels for a full 360 degree turn."""
    _positive(dpi=dpi, sensitivity=sensitivity, yaw=yaw)
    counts_per_360 = 360.0 / (sensitivity * yaw)
    return counts_per_360 / dpi * CM_PER_INCH


def sensitivity_for_cm360(dpi, target_cm360, yaw):
    _positive(dpi=dpi, target_cm360=target_cm360, yaw=yaw)
    return 360.0 * CM_PER_INCH / (dpi * target_cm360 * yaw)


def degrees_on_pad(pad_width_cm, cm360, usable_fraction=0.8):
    """How many degrees of turning fit in one swipe across the mousepad."""
    _positive(pad_width_cm=pad_width_cm, cm360=cm360)
    return 360.0 * pad_width_cm * usable_fraction / cm360


def pad_needed_cm(cm360, degrees):
    _positive(cm360=cm360)
    return cm360 * degrees / 360.0


def dpi_from_counts(counts, distance_cm):
    _positive(distance_cm=distance_cm)
    return counts / (distance_cm / CM_PER_INCH)


def _positive(**values):
    for k, v in values.items():
        if not v > 0:
            raise ValueError(f"{k} must be greater than zero")
