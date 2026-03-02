import math

from experiments.equivalence_report import bootstrap_mean_ci


def test_bootstrap_mean_ci_deterministic():
    vals = [-1.0, 0.0, 1.0, 2.0, -2.0, 0.5, -0.5, 1.5, -1.5]
    lo1, hi1 = bootstrap_mean_ci(vals, ci_level=0.9, n_samples=5000, seed=123)
    lo2, hi2 = bootstrap_mean_ci(vals, ci_level=0.9, n_samples=5000, seed=123)
    assert lo1 == lo2
    assert hi1 == hi2


def test_bootstrap_mean_ci_monotonic_with_samples():
    vals = [0.0, 0.0, 0.0, 1.0, 1.0]
    lo_small, hi_small = bootstrap_mean_ci(vals, ci_level=0.9, n_samples=200, seed=7)
    lo_big, hi_big = bootstrap_mean_ci(vals, ci_level=0.9, n_samples=5000, seed=7)
    assert lo_small <= hi_small
    assert lo_big <= hi_big
    assert math.isfinite(lo_big)
    assert math.isfinite(hi_big)


def test_bootstrap_mean_ci_singleton_is_degenerate():
    lo, hi = bootstrap_mean_ci([0.25], ci_level=0.9, n_samples=1000, seed=0)
    assert lo == 0.25
    assert hi == 0.25

