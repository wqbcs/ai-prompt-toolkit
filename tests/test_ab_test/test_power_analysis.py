"""统计功效分析测试 — power_analysis/power_curve/min_detectable_effect"""

from __future__ import annotations

from ai_prompt_toolkit.ab_test.statistics import (
    min_detectable_effect,
    power_analysis,
    power_curve,
)


class TestPowerAnalysis:
    def test_compute_sample_size_medium_effect(self):
        result = power_analysis(effect_size=0.5, alpha=0.05, power=0.8)
        assert result["required_n_per_group"] is not None
        assert result["required_n_per_group"] > 0
        assert result["effect_magnitude"] == "medium"
        assert result["achieved_power"] >= 0.8

    def test_compute_sample_size_small_effect(self):
        result = power_analysis(effect_size=0.2, alpha=0.05, power=0.8)
        assert result["required_n_per_group"] > 50
        assert result["effect_magnitude"] == "small"

    def test_compute_sample_size_large_effect(self):
        result = power_analysis(effect_size=0.8, alpha=0.05, power=0.8)
        assert result["required_n_per_group"] < 30
        assert result["effect_magnitude"] == "large"

    def test_paired_test_smaller_sample(self):
        result_two = power_analysis(effect_size=0.5, test_type="two_sample")
        result_paired = power_analysis(effect_size=0.5, test_type="paired")
        assert result_paired["required_n_per_group"] <= result_two["required_n_per_group"]

    def test_achieved_power_with_given_n(self):
        result = power_analysis(effect_size=0.5, n_per_group=64)
        assert "achieved_power" in result
        assert "current_n_per_group" in result
        assert result["current_n_per_group"] == 64
        assert "power_sufficient" in result

    def test_insufficient_n_shows_deficit(self):
        result = power_analysis(effect_size=0.5, n_per_group=10)
        assert result["n_deficit"] > 0
        assert result["power_sufficient"] is False

    def test_sufficient_n_shows_no_deficit(self):
        result = power_analysis(effect_size=0.5, n_per_group=200)
        assert result["n_deficit"] == 0
        assert result["power_sufficient"] is True

    def test_zero_effect_size_error(self):
        result = power_analysis(effect_size=0.0)
        assert "error" in result
        assert result["required_n_per_group"] is None

    def test_negative_effect_size_error(self):
        result = power_analysis(effect_size=-0.5)
        assert "error" in result

    def test_higher_power_more_samples(self):
        r80 = power_analysis(effect_size=0.5, power=0.8)
        r90 = power_analysis(effect_size=0.5, power=0.9)
        assert r90["required_n_per_group"] > r80["required_n_per_group"]

    def test_stricter_alpha_more_samples(self):
        r05 = power_analysis(effect_size=0.5, alpha=0.05)
        r01 = power_analysis(effect_size=0.5, alpha=0.01)
        assert r01["required_n_per_group"] > r05["required_n_per_group"]

    def test_required_total_two_sample(self):
        result = power_analysis(effect_size=0.5, test_type="two_sample")
        assert result["required_total"] == result["required_n_per_group"] * 2

    def test_required_total_paired(self):
        result = power_analysis(effect_size=0.5, test_type="paired")
        assert result["required_total"] == result["required_n_per_group"]


class TestPowerCurve:
    def test_power_curve_basic(self):
        result = power_curve(effect_size=0.5, max_n=100)
        assert len(result["sample_sizes"]) > 0
        assert len(result["powers"]) == len(result["sample_sizes"])
        assert result["powers"][-1] > result["powers"][0]

    def test_power_curve_finds_80_percent(self):
        result = power_curve(effect_size=0.5, max_n=200)
        assert result["n_for_80_power"] is not None
        assert result["n_for_80_power"] > 0

    def test_power_curve_data_points(self):
        result = power_curve(effect_size=0.5, max_n=50)
        assert len(result["data_points"]) > 0
        for dp in result["data_points"]:
            assert "n_per_group" in dp
            assert "power" in dp

    def test_power_monotonically_increases(self):
        result = power_curve(effect_size=0.5, max_n=200)
        powers = result["powers"]
        for i in range(1, len(powers)):
            assert powers[i] >= powers[i - 1] - 0.01


class TestMinDetectableEffect:
    def test_mde_basic(self):
        result = min_detectable_effect(n_per_group=50)
        assert result["mde"] > 0
        assert result["mde_magnitude"] in ("small", "medium", "large", "negligible")
        assert "interpretation" in result

    def test_mde_decreases_with_larger_n(self):
        mde_50 = min_detectable_effect(n_per_group=50)
        mde_200 = min_detectable_effect(n_per_group=200)
        assert mde_200["mde"] < mde_50["mde"]

    def test_mde_too_small_n(self):
        result = min_detectable_effect(n_per_group=1)
        assert "error" in result
        assert result["mde"] is None

    def test_mde_paired_vs_two_sample(self):
        mde_paired = min_detectable_effect(n_per_group=50, test_type="paired")
        mde_two = min_detectable_effect(n_per_group=50, test_type="two_sample")
        assert mde_paired["mde"] < mde_two["mde"]
