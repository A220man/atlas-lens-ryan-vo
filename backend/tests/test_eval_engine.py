"""Unit tests for the empirical evaluation engine.

Covers metric honesty: observations are derived from measured values and never
assert a benchmark number that was not actually observed for the run.
"""

from app.services.eval_engine import EvaluationEngine, _build_observations


def _dag_observation(observations):
    """Return the single DAG healing observation line, or fail loudly."""
    matches = [o for o in observations if "DAG structural healing" in o]
    assert len(matches) == 1
    return matches[0]


def test_build_observations_uses_measured_healing_pct():
    """The DAG healing observation must embed the measured rate, not a fixed 100%."""
    observations = _build_observations(
        sample_count=2,
        mean_token_savings=35.38,
        imitation_suppression_pct=100.0,
        healing_pct=50.0,
        mean_latency_ms=0.08,
    )
    dag_obs = _dag_observation(observations)
    assert "50.0%" in dag_obs
    assert "100%" not in dag_obs


def test_build_observations_data_driven_all_metrics():
    """Every metric in the observations reflects the value passed into the helper."""
    observations = _build_observations(
        sample_count=13,
        mean_token_savings=42.5,
        imitation_suppression_pct=95.0,
        healing_pct=90.0,
        mean_latency_ms=0.123,
    )
    joined = "||".join(f"{i}:{o}" for i, o in enumerate(observations))
    assert "13 conversation sequences" in joined
    assert "42.5%" in joined
    assert "95.0%" in joined
    assert "90.0%" in joined
    assert "0.123 ms" in joined


def test_build_observations_full_healing_reports_measured_100_percent():
    """When every corrupt DAG heals, the observation reports the measured 100.0%."""
    observations = _build_observations(
        sample_count=1,
        mean_token_savings=10.0,
        imitation_suppression_pct=100.0,
        healing_pct=100.0,
        mean_latency_ms=1.0,
    )
    dag_obs = _dag_observation(observations)
    assert "100.0%" in dag_obs


def test_build_observations_count_matches_metric_count():
    """Observations list size must match the number of measured metrics (no dead lines)."""
    observations = _build_observations(
        sample_count=1,
        mean_token_savings=1.0,
        imitation_suppression_pct=1.0,
        healing_pct=1.0,
        mean_latency_ms=1.0,
    )
    assert len(observations) == 5