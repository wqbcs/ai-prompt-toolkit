"""A/B测试统计检验——t检验、Mann-Whitney U检验、Cohen's d、置信区间、自动选择检验。"""
from __future__ import annotations

import math
from typing import Any

_DEFAULT_ALPHA = 0.05


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _variance(values: list[float], ddof: int = 1) -> float:
    if len(values) <= ddof:
        return 0.0
    m = _mean(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - ddof)


def _std(values: list[float], ddof: int = 1) -> float:
    return math.sqrt(_variance(values, ddof))


def _t_distribution_cdf(t: float, df: int) -> float:
    x = df / (df + t * t)
    return 1.0 - 0.5 * _regularized_beta(x, df / 2.0, 0.5)


def _regularized_beta(x: float, a: float, b: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    lbeta = _log_beta(a, b)
    front = math.exp(a * math.log(x) + b * math.log(1.0 - x) - lbeta)

    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_cf(x, a, b) / a
    else:
        return 1.0 - front * _beta_cf(1.0 - x, b, a) / b


def _beta_cf(x: float, a: float, b: float, max_iter: int = 200, eps: float = 1e-10) -> float:
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta

        if abs(delta - 1.0) < eps:
            break

    return h


def _log_beta(a: float, b: float) -> float:
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _normal_ppf(p: float) -> float:
    if p <= 0.0:
        return -8.0
    if p >= 1.0:
        return 8.0

    rational_coeffs = [
        -3.969683028665376e+01, 2.209460984245205e+02,
        -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    ]
    rational_coeffs2 = [
        -5.447609879822406e+01, 1.615858368580409e+02,
        -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    rational_coeffs3 = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
        4.374664141464968e+00, 2.938163982698783e+00,
    ]
    rational_coeffs4 = [
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e+00, 3.754408661907416e+00,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((rational_coeffs3[0]*q + rational_coeffs3[1])*q + rational_coeffs3[2])*q +
                  rational_coeffs3[3])*q + rational_coeffs3[4])*q + rational_coeffs3[5]) / \
               ((((rational_coeffs4[0]*q + rational_coeffs4[1])*q + rational_coeffs4[2])*q +
                 rational_coeffs4[3])*q + 1.0)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((rational_coeffs[0]*r + rational_coeffs[1])*r + rational_coeffs[2])*r +
                  rational_coeffs[3])*r + rational_coeffs[4])*r + rational_coeffs[5]) * q / \
               (((((rational_coeffs2[0]*r + rational_coeffs2[1])*r + rational_coeffs2[2])*r +
                  rational_coeffs2[3])*r + rational_coeffs2[4])*r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((rational_coeffs3[0]*q + rational_coeffs3[1])*q + rational_coeffs3[2])*q +
                   rational_coeffs3[3])*q + rational_coeffs3[4])*q + rational_coeffs3[5]) / \
                ((((rational_coeffs4[0]*q + rational_coeffs4[1])*q + rational_coeffs4[2])*q +
                  rational_coeffs4[3])*q + 1.0)


def t_test(
    sample_a: list[float],
    sample_b: list[float],
    *,
    paired: bool = False,
    alternative: str = "two-sided",
) -> dict[str, Any]:
    n_a = len(sample_a)
    n_b = len(sample_b)

    if n_a < 2 or n_b < 2:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "degrees_of_freedom": 0,
            "significant": False,
            "test_type": "t_test",
            "error": "样本量不足(需>=2)",
        }

    mean_a = _mean(sample_a)
    mean_b = _mean(sample_b)
    var_a = _variance(sample_a)
    var_b = _variance(sample_b)

    if paired:
        if n_a != n_b:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "degrees_of_freedom": 0,
                "significant": False,
                "test_type": "paired_t_test",
                "error": "配对检验要求两组样本量相同",
            }
        diffs = [a - b for a, b in zip(sample_a, sample_b)]
        mean_d = _mean(diffs)
        std_d = _std(diffs)
        if std_d == 0:
            return {
                "statistic": 0.0,
                "p_value": 1.0 if mean_d == 0 else 0.0,
                "degrees_of_freedom": n_a - 1,
                "significant": mean_d != 0,
                "test_type": "paired_t_test",
            }
        t_stat = mean_d / (std_d / math.sqrt(n_a))
        df = n_a - 1
    else:
        pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)
        if pooled_var == 0:
            return {
                "statistic": 0.0,
                "p_value": 1.0 if mean_a == mean_b else 0.0,
                "degrees_of_freedom": n_a + n_b - 2,
                "significant": mean_a != mean_b,
                "test_type": "welch_t_test",
            }
        se = math.sqrt(pooled_var * (1.0 / n_a + 1.0 / n_b))
        t_stat = (mean_a - mean_b) / se
        df = n_a + n_b - 2

    if df <= 0:
        p_value = 1.0
    else:
        p_value = 2.0 * (1.0 - _t_distribution_cdf(abs(t_stat), df))
        if alternative == "less":
            p_value = 1.0 - _t_distribution_cdf(t_stat, df)
        elif alternative == "greater":
            p_value = _t_distribution_cdf(t_stat, df)

    return {
        "statistic": round(t_stat, 6),
        "p_value": round(max(0.0, min(1.0, p_value)), 6),
        "degrees_of_freedom": df,
        "significant": p_value < _DEFAULT_ALPHA,
        "test_type": "paired_t_test" if paired else "welch_t_test",
        "mean_a": round(mean_a, 6),
        "mean_b": round(mean_b, 6),
    }


def mann_whitney_u_test(
    sample_a: list[float],
    sample_b: list[float],
    *,
    alternative: str = "two-sided",
) -> dict[str, Any]:
    n_a = len(sample_a)
    n_b = len(sample_b)

    if n_a == 0 or n_b == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "significant": False,
            "test_type": "mann_whitney_u",
            "error": "样本量不足",
        }

    combined = [(v, "a") for v in sample_a] + [(v, "b") for v in sample_b]
    combined.sort(key=lambda x: x[0])

    ranks: dict[str, float] = {}
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[combined[k][1]] = ranks.get(combined[k][1], 0.0) + avg_rank
        i = j

    u_a = ranks.get("a", 0.0) - n_a * (n_a + 1) / 2.0
    u_b = ranks.get("b", 0.0) - n_b * (n_b + 1) / 2.0
    u_stat = min(u_a, u_b)

    mean_u = n_a * n_b / 2.0
    var_u = n_a * n_b * (n_a + n_b + 1) / 12.0

    if var_u == 0:
        p_value = 1.0
    else:
        z = (u_stat - mean_u) / math.sqrt(var_u)
        p_value = 2.0 * (1.0 - _normal_cdf(abs(z)))
        if alternative == "less":
            p_value = _normal_cdf(z)
        elif alternative == "greater":
            p_value = 1.0 - _normal_cdf(z)

    return {
        "statistic": round(u_stat, 4),
        "p_value": round(max(0.0, min(1.0, p_value)), 6),
        "u_a": round(u_a, 4),
        "u_b": round(u_b, 4),
        "significant": p_value < _DEFAULT_ALPHA,
        "test_type": "mann_whitney_u",
        "z_value": round((u_stat - mean_u) / math.sqrt(var_u), 4) if var_u > 0 else 0.0,
    }


def cohens_d(sample_a: list[float], sample_b: list[float]) -> dict[str, Any]:
    n_a = len(sample_a)
    n_b = len(sample_b)

    if n_a < 2 or n_b < 2:
        return {"effect_size": 0.0, "magnitude": "undefined", "error": "样本量不足"}

    mean_a = _mean(sample_a)
    mean_b = _mean(sample_b)
    var_a = _variance(sample_a)
    var_b = _variance(sample_b)

    pooled_std = math.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))

    if pooled_std == 0:
        d = 0.0 if mean_a == mean_b else float("inf")
    else:
        d = (mean_a - mean_b) / pooled_std

    abs_d = abs(d)
    if abs_d < 0.2:
        magnitude = "negligible"
    elif abs_d < 0.5:
        magnitude = "small"
    elif abs_d < 0.8:
        magnitude = "medium"
    else:
        magnitude = "large"

    return {
        "effect_size": round(d, 6),
        "magnitude": magnitude,
        "mean_a": round(mean_a, 6),
        "mean_b": round(mean_b, 6),
        "pooled_std": round(pooled_std, 6),
    }


def confidence_interval(
    sample: list[float],
    confidence: float = 0.95,
) -> dict[str, Any]:
    n = len(sample)
    if n < 2:
        return {
            "lower": 0.0,
            "upper": 0.0,
            "mean": 0.0,
            "std_error": 0.0,
            "confidence": confidence,
            "error": "样本量不足(需>=2)",
        }

    m = _mean(sample)
    se = _std(sample) / math.sqrt(n)
    alpha = 1.0 - confidence

    z = _normal_ppf(1.0 - alpha / 2.0)

    margin = z * se
    lower = m - margin
    upper = m + margin

    return {
        "lower": round(lower, 6),
        "upper": round(upper, 6),
        "mean": round(m, 6),
        "std_error": round(se, 6),
        "margin": round(margin, 6),
        "confidence": confidence,
    }


def auto_select_test(
    sample_a: list[float],
    sample_b: list[float],
    *,
    alpha: float = 0.05,
    normality_threshold: int = 30,
) -> dict[str, Any]:
    n_a = len(sample_a)
    n_b = len(sample_b)

    if n_a < 2 or n_b < 2:
        return {
            "selected_test": "none",
            "reason": "样本量不足",
            "result": {},
            "effect_size": {},
            "confidence_interval_a": {},
            "confidence_interval_b": {},
        }

    use_parametric = n_a >= normality_threshold and n_b >= normality_threshold

    if use_parametric:
        result = t_test(sample_a, sample_b)
        ci_a = confidence_interval(sample_a)
        ci_b = confidence_interval(sample_b)
    else:
        result = mann_whitney_u_test(sample_a, sample_b)
        ci_a = confidence_interval(sample_a)
        ci_b = confidence_interval(sample_b)

    effect = cohens_d(sample_a, sample_b)

    return {
        "selected_test": result.get("test_type", "unknown"),
        "reason": (
            f"样本量(n_a={n_a}, n_b={n_b})>={normality_threshold}，选择参数检验"
            if use_parametric
            else f"样本量(n_a={n_a}, n_b={n_b})<{normality_threshold}，选择非参数检验"
        ),
        "parametric": use_parametric,
        "result": result,
        "effect_size": effect,
        "confidence_interval_a": ci_a,
        "confidence_interval_b": ci_b,
        "significant": result.get("significant", False),
        "p_value": result.get("p_value", 1.0),
    }


def bayesian_ab_test(
    successes_a: int,
    trials_a: int,
    successes_b: int,
    trials_b: int,
    *,
    prior_alpha: float = 1.0,
    prior_beta: float = 1.0,
    n_samples: int = 50000,
) -> dict[str, Any]:
    """贝叶斯A/B测试 — Beta后验+蒙特卡洛采样

    适用于转化率/成功率等二项分布场景。
    小样本(<30)时比频率学派更稳定。

    Args:
        successes_a: A组成功次数
        trials_a: A组总试验次数
        successes_b: B组成功次数
        trials_b: B组总试验次数
        prior_alpha: Beta先验alpha(默认1.0=均匀先验)
        prior_beta: Beta先验beta(默认1.0=均匀先验)
        n_samples: 蒙特卡洛采样次数
    """
    import random

    if trials_a <= 0 or trials_b <= 0:
        return {
            "test_type": "bayesian_ab",
            "error": "试验次数必须>0",
            "prob_b_better": 0.0,
            "expected_loss_a": 0.0,
            "expected_loss_b": 0.0,
        }

    alpha_a = prior_alpha + successes_a
    beta_a = prior_beta + trials_a - successes_a
    alpha_b = prior_alpha + successes_b
    beta_b = prior_beta + trials_b - successes_b

    b_better = 0
    total_diff = 0.0
    loss_a = 0.0
    loss_b = 0.0

    random.seed(42)

    for _ in range(n_samples):
        p_a = _beta_sample(alpha_a, beta_a)
        p_b = _beta_sample(alpha_b, beta_b)

        if p_b > p_a:
            b_better += 1
            loss_a += p_b - p_a
        else:
            loss_b += p_a - p_b

        total_diff += p_b - p_a

    prob_b_better = b_better / n_samples
    mean_diff = total_diff / n_samples

    rate_a = successes_a / trials_a
    rate_b = successes_b / trials_b

    return {
        "test_type": "bayesian_ab",
        "prob_b_better": round(prob_b_better, 6),
        "prob_a_better": round(1.0 - prob_b_better, 6),
        "expected_loss_a": round(loss_a / n_samples, 6),
        "expected_loss_b": round(loss_b / n_samples, 6),
        "mean_diff": round(mean_diff, 6),
        "rate_a": round(rate_a, 6),
        "rate_b": round(rate_b, 6),
        "credible_interval_diff": _compute_credible_interval(
            alpha_a, beta_a, alpha_b, beta_b, n_samples,
        ),
        "significant": prob_b_better > 0.95 or prob_b_better < 0.05,
        "recommendation": "B" if prob_b_better > 0.95 else "A" if prob_b_better < 0.05 else "insufficient_evidence",
    }


def _beta_sample(alpha: float, beta: float) -> float:
    import random
    if alpha <= 0 or beta <= 0:
        return 0.5
    x = random.gammavariate(alpha, 1.0)
    y = random.gammavariate(beta, 1.0)
    return x / (x + y) if (x + y) > 0 else 0.5


def _compute_credible_interval(
    alpha_a: float, beta_a: float,
    alpha_b: float, beta_b: float,
    n_samples: int,
) -> dict[str, float]:
    import random
    random.seed(42)
    diffs = []
    for _ in range(n_samples):
        p_a = _beta_sample(alpha_a, beta_a)
        p_b = _beta_sample(alpha_b, beta_b)
        diffs.append(p_b - p_a)
    diffs.sort()
    lower_idx = int(0.025 * n_samples)
    upper_idx = int(0.975 * n_samples)
    return {
        "lower_95": round(diffs[lower_idx], 6) if diffs else 0.0,
        "upper_95": round(diffs[min(upper_idx, n_samples - 1)], 6) if diffs else 0.0,
    }


def thompson_sampling(
    arms: list[dict[str, int]],
    *,
    n_rounds: int = 1000,
) -> dict[str, Any]:
    """Thompson Sampling多臂老虎机 — 自适应A/B测试

    每轮根据后验分布采样选择臂，自动平衡探索与利用。
    适用于持续运行的在线A/B测试。

    Args:
        arms: 每个臂的统计 [{"successes": int, "trials": int}, ...]
        n_rounds: 模拟轮次
    """
    import random

    if not arms:
        return {"test_type": "thompson_sampling", "error": "无臂数据", "recommendation": None}

    random.seed(42)
    n_arms = len(arms)
    alphas = [1.0 + a.get("successes", 0) for a in arms]
    betas = [1.0 + a.get("trials", 0) - a.get("successes", 0) for a in arms]

    arm_pulls = [0] * n_arms
    arm_successes = [0] * n_arms

    for _ in range(n_rounds):
        samples = [_beta_sample(alphas[i], betas[i]) for i in range(n_arms)]
        best_arm = samples.index(max(samples))
        arm_pulls[best_arm] += 1

        true_rate = arms[best_arm].get("successes", 0) / max(arms[best_arm].get("trials", 1), 1)
        if random.random() < true_rate:
            arm_successes[best_arm] += 1
            alphas[best_arm] += 1
        else:
            betas[best_arm] += 1

    rates = [s / max(p, 1) for s, p in zip(arm_successes, arm_pulls)]
    best_idx = rates.index(max(rates))

    return {
        "test_type": "thompson_sampling",
        "n_rounds": n_rounds,
        "n_arms": n_arms,
        "arm_pulls": arm_pulls,
        "arm_successes": arm_successes,
        "arm_rates": [round(r, 6) for r in rates],
        "recommendation": f"arm_{best_idx}",
        "allocation_pct": [round(p / n_rounds * 100, 1) for p in arm_pulls],
    }


def sequential_analysis(
    successes_a: int,
    trials_a: int,
    successes_b: int,
    trials_b: int,
    *,
    alpha: float = 0.05,
    beta: float = 0.2,
) -> dict[str, Any]:
    """序贯概率比检验(SPRT) — 边收集数据边检验

    可在数据收集过程中随时停止检验，减少不必要的样本量。
    适用于持续监控的在线A/B测试。

    Args:
        successes_a/trials_a: A组数据
        successes_b/trials_b: B组数据
        alpha: 第一类错误率
        beta: 第二类错误率
    """
    if trials_a <= 0 or trials_b <= 0:
        return {"test_type": "sprt", "error": "试验次数必须>0", "decision": "continue"}

    rate_a = successes_a / trials_a
    rate_b = successes_b / trials_b

    p0 = rate_a
    p1 = rate_b if rate_b > rate_a else rate_a + 0.01

    if p0 <= 0 or p0 >= 1 or p1 <= 0 or p1 >= 1:
        return {
            "test_type": "sprt",
            "decision": "continue",
            "reason": "转化率在边界值，无法计算SPRT",
            "rate_a": round(rate_a, 6),
            "rate_b": round(rate_b, 6),
        }

    upper_bound = (1 - beta) / alpha
    lower_bound = beta / (1 - alpha)

    n = min(trials_a, trials_b)
    log_likelihood_ratio = 0.0

    for k in range(n):
        s_a = min(successes_a, k + 1)
        s_b = min(successes_b, k + 1)
        obs_rate = (s_a + s_b) / (2 * (k + 1))

        if obs_rate > 0 and obs_rate < 1:
            ll_p1 = obs_rate * math.log(p1 / p0) if p0 > 0 and p1 > 0 else 0
            ll_p0 = (1 - obs_rate) * math.log((1 - p1) / (1 - p0)) if (1 - p0) > 0 and (1 - p1) > 0 else 0
            log_likelihood_ratio += ll_p1 + ll_p0

    likelihood_ratio = math.exp(min(log_likelihood_ratio, 500))

    if likelihood_ratio >= upper_bound:
        decision = "reject_h0"
        reason = f"B显著优于A (LR={likelihood_ratio:.2f}>={upper_bound:.2f})"
    elif likelihood_ratio <= lower_bound:
        decision = "accept_h0"
        reason = f"A与B无显著差异 (LR={likelihood_ratio:.2f}<={lower_bound:.2f})"
    else:
        decision = "continue"
        reason = f"证据不足，继续收集数据 (LR={likelihood_ratio:.2f})"

    return {
        "test_type": "sprt",
        "decision": decision,
        "reason": reason,
        "likelihood_ratio": round(likelihood_ratio, 6),
        "upper_bound": round(upper_bound, 6),
        "lower_bound": round(lower_bound, 6),
        "rate_a": round(rate_a, 6),
        "rate_b": round(rate_b, 6),
        "n_observed": n,
    }


def recommend_statistical_method(
    sample_size: int,
    data_type: str = "binary",
) -> dict[str, Any]:
    """根据样本量和数据类型推荐统计方法

    Args:
        sample_size: 当前/预期样本量
        data_type: 数据类型("binary"=转化率, "continuous"=连续值)
    """
    if data_type == "binary":
        if sample_size < 30:
            return {
                "recommended": "bayesian_ab",
                "reason": f"样本量{n=}<30，贝叶斯方法更稳定",
                "alternatives": ["thompson_sampling", "sprt"],
            }
        elif sample_size < 100:
            return {
                "recommended": "bayesian_ab",
                "reason": f"样本量{n=}中等，贝叶斯方法可提供后验概率",
                "alternatives": ["t_test", "sprt"],
            }
        else:
            return {
                "recommended": "t_test",
                "reason": f"样本量{n=}>=100，频率学派方法稳健",
                "alternatives": ["bayesian_ab", "mann_whitney_u"],
            }
    else:
        if sample_size < 30:
            return {
                "recommended": "mann_whitney_u",
                "reason": f"样本量{n=}<30，非参数检验更安全",
                "alternatives": ["bayesian_ab"],
            }
        else:
            return {
                "recommended": "t_test",
                "reason": f"样本量{n=}>=30，参数检验适用",
                "alternatives": ["mann_whitney_u", "bayesian_ab"],
            }


def power_analysis(
    *,
    effect_size: float = 0.5,
    alpha: float = 0.05,
    power: float = 0.8,
    n_per_group: int | None = None,
    test_type: str = "two_sample",
) -> dict[str, Any]:
    """统计功效分析 — 计算所需样本量或检验功效

    F17: 支持A/B测试前的样本量规划和事后功效评估

    Args:
        effect_size: 期望效应量(Cohen's d, 小=0.2/中=0.5/大=0.8)
        alpha: 显著性水平(第一类错误率)
        power: 统计功效(1-β, 通常0.8)
        n_per_group: 每组样本量(None=计算所需样本量)
        test_type: 检验类型("two_sample"/"paired")

    Returns:
        包含样本量、功效、效应量等信息的字典
    """
    if effect_size <= 0:
        return {
            "error": "效应量必须>0",
            "effect_size": effect_size,
            "required_n_per_group": None,
            "achieved_power": None,
        }

    z_alpha = _normal_ppf(1.0 - alpha / 2.0)
    z_beta = _normal_ppf(power)

    if test_type == "paired":
        adjustment = 1.0
    else:
        adjustment = 2.0

    if n_per_group is None:
        n_required = math.ceil(
            adjustment * ((z_alpha + z_beta) / effect_size) ** 2
        )
        achieved_power = _compute_power(n_required, effect_size, alpha, test_type)
        return {
            "effect_size": effect_size,
            "effect_magnitude": _classify_effect_size(effect_size),
            "alpha": alpha,
            "target_power": power,
            "required_n_per_group": n_required,
            "required_total": n_required * 2 if test_type == "two_sample" else n_required,
            "achieved_power": round(achieved_power, 6),
            "test_type": test_type,
            "z_alpha": round(z_alpha, 4),
            "z_beta": round(z_beta, 4),
        }

    achieved_power = _compute_power(n_per_group, effect_size, alpha, test_type)

    n_required = math.ceil(
        adjustment * ((z_alpha + z_beta) / effect_size) ** 2
    )
    n_deficit = max(0, n_required - n_per_group)

    return {
        "effect_size": effect_size,
        "effect_magnitude": _classify_effect_size(effect_size),
        "alpha": alpha,
        "current_n_per_group": n_per_group,
        "achieved_power": round(achieved_power, 6),
        "target_power": power,
        "power_sufficient": achieved_power >= power,
        "required_n_per_group": n_required,
        "n_deficit": n_deficit,
        "required_total": n_required * 2 if test_type == "two_sample" else n_required,
        "test_type": test_type,
    }


def _compute_power(
    n: int,
    effect_size: float,
    alpha: float,
    test_type: str,
) -> float:
    if n < 2 or effect_size <= 0:
        return 0.0

    z_alpha = _normal_ppf(1.0 - alpha / 2.0)
    adjustment = 1.0 if test_type == "paired" else 2.0
    ncp = effect_size / math.sqrt(adjustment / n)

    z_power = ncp - z_alpha
    power = _normal_cdf(z_power)

    return max(0.0, min(1.0, power))


def _classify_effect_size(d: float) -> str:
    abs_d = abs(d)
    if abs_d < 0.2:
        return "negligible"
    elif abs_d < 0.5:
        return "small"
    elif abs_d < 0.8:
        return "medium"
    else:
        return "large"


def power_curve(
    *,
    effect_size: float = 0.5,
    alpha: float = 0.05,
    max_n: int = 200,
    test_type: str = "two_sample",
) -> dict[str, Any]:
    """功效曲线 — 不同样本量下的检验功效变化

    Args:
        effect_size: 效应量
        alpha: 显著性水平
        max_n: 最大样本量(每组)
        test_type: 检验类型

    Returns:
        包含功效曲线数据的字典
    """
    sample_sizes = list(range(5, max_n + 1, 5))
    powers = []
    for n in sample_sizes:
        p = _compute_power(n, effect_size, alpha, test_type)
        powers.append(round(p, 6))

    min_80_n = None
    for n, p in zip(sample_sizes, powers):
        if p >= 0.8:
            min_80_n = n
            break

    return {
        "effect_size": effect_size,
        "effect_magnitude": _classify_effect_size(effect_size),
        "alpha": alpha,
        "test_type": test_type,
        "sample_sizes": sample_sizes,
        "powers": powers,
        "n_for_80_power": min_80_n,
        "data_points": [
            {"n_per_group": n, "power": p}
            for n, p in zip(sample_sizes, powers)
        ],
    }


def min_detectable_effect(
    *,
    n_per_group: int,
    alpha: float = 0.05,
    power: float = 0.8,
    test_type: str = "two_sample",
) -> dict[str, Any]:
    """最小可检测效应量(MDE) — 给定样本量能检测的最小效应

    Args:
        n_per_group: 每组样本量
        alpha: 显著性水平
        power: 统计功效
        test_type: 检验类型

    Returns:
        包含MDE信息的字典
    """
    if n_per_group < 2:
        return {
            "error": "样本量需>=2",
            "n_per_group": n_per_group,
            "mde": None,
        }

    z_alpha = _normal_ppf(1.0 - alpha / 2.0)
    z_beta = _normal_ppf(power)

    adjustment = 1.0 if test_type == "paired" else 2.0
    mde = (z_alpha + z_beta) * math.sqrt(adjustment / n_per_group)

    return {
        "n_per_group": n_per_group,
        "alpha": alpha,
        "power": power,
        "test_type": test_type,
        "mde": round(mde, 6),
        "mde_magnitude": _classify_effect_size(mde),
        "interpretation": f"在{n_per_group}人/组、α={alpha}、power={power}条件下，可检测≥{mde:.3f}的效应量(Cohen's d)",
    }
