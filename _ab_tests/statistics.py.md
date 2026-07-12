# A/B测试统计分析引擎 (Statistics)

> 完整的Python统计分析引擎实现，可直接运行

```python
"""
A/B 测试统计分析引擎

支持:
    - 独立样本 t 检验
    - Mann-Whitney U 检验
    - Cohen's d 效应量
    - 置信区间估计

用法:
    from statistics import ABStatistics
    stats = ABStatistics(group_a=[1.2, 1.5, 1.3], group_b=[2.1, 2.4, 2.0])
    result = stats.analyze()
"""

from __future__ import annotations

import math
import dataclasses
from typing import List, Dict, Any, Optional, Tuple


# ──────────────────────────────────────────
#  结果类型
# ──────────────────────────────────────────

@dataclasses.dataclass(frozen=True, slots=True)
class TestResult:
    """统计检验结果

    Attributes:
        test_name:    检验名称
        statistic:    检验统计量
        p_value:      p 值
        significant:  是否显著（α=0.05）
        effect_size:  效应量
        confidence_interval: 置信区间 (lower, upper)
        notes:        备注
    """
    test_name: str
    statistic: float
    p_value: float
    significant: bool
    effect_size: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    notes: str = ""

    def __repr__(self) -> str:
        sig = "显著" if self.significant else "不显著"
        return (
            f"{self.test_name}: statistic={self.statistic:.4f}, "
            f"p={self.p_value:.4f} ({sig}), d={self.effect_size:.4f}"
        )


@dataclasses.dataclass
class ABAnalysisReport:
    """A/B 分析报告

    Attributes:
        group_a_name: A 组名称
        group_b_name: B 组名称
        group_a_stats: A 组描述统计
        group_b_stats: B 组描述统计
        t_test:       t 检验结果
        mann_whitney:  Mann-Whitney U 检验结果
        cohens_d:     Cohen's d 效应量
        confidence_interval: 均值差的置信区间
        recommendation: 建议
    """
    group_a_name: str = "A"
    group_b_name: str = "B"
    group_a_stats: Dict[str, float] = dataclasses.field(default_factory=dict)
    group_b_stats: Dict[str, float] = dataclasses.field(default_factory=dict)
    t_test: Optional[TestResult] = None
    mann_whitney: Optional[TestResult] = None
    cohens_d: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    recommendation: str = ""

    def summary(self) -> str:
        """生成分析摘要"""
        lines = [
            f"A/B 分析报告",
            f"  {self.group_a_name}: n={self.group_a_stats.get('n',0)}, "
            f"mean={self.group_a_stats.get('mean',0):.4f}, "
            f"std={self.group_a_stats.get('std',0):.4f}",
            f"  {self.group_b_name}: n={self.group_b_stats.get('n',0)}, "
            f"mean={self.group_b_stats.get('mean',0):.4f}, "
            f"std={self.group_b_stats.get('std',0):.4f}",
        ]
        if self.t_test:
            lines.append(f"  t 检验: {self.t_test}")
        if self.mann_whitney:
            lines.append(f"  Mann-Whitney U: {self.mann_whitney}")
        lines.append(f"  Cohen's d: {self.cohens_d:.4f}")
        lines.append(f"  置信区间: [{self.confidence_interval[0]:.4f}, {self.confidence_interval[1]:.4f}]")
        if self.recommendation:
            lines.append(f"  建议: {self.recommendation}")
        return "\n".join(lines)


# ──────────────────────────────────────────
#  基础统计函数
# ──────────────────────────────────────────

def _mean(data: List[float]) -> float:
    """计算均值"""
    if not data:
        return 0.0
    return sum(data) / len(data)


def _variance(data: List[float], ddof: int = 1) -> float:
    """计算方差（默认无偏估计 ddof=1）"""
    if len(data) <= ddof:
        return 0.0
    m = _mean(data)
    return sum((x - m) ** 2 for x in data) / (len(data) - ddof)


def _std(data: List[float], ddof: int = 1) -> float:
    """计算标准差"""
    return math.sqrt(_variance(data, ddof))


def _median(data: List[float]) -> float:
    """计算中位数"""
    if not data:
        return 0.0
    s = sorted(data)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2


def _rank(data: List[float]) -> List[float]:
    """计算秩（用于 Mann-Whitney U）"""
    indexed = sorted(enumerate(data), key=lambda x: x[1])
    ranks = [0.0] * len(data)
    i = 0
    while i < len(indexed):
        j = i
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        avg_rank = (i + j + 1) / 2
        for k in range(i, j):
            ranks[indexed[k][0]] = avg_rank
        i = j
    return ranks


def descriptive_stats(data: List[float]) -> Dict[str, float]:
    """描述性统计"""
    if not data:
        return {"n": 0, "mean": 0, "std": 0, "min": 0, "max": 0, "median": 0}
    return {
        "n": len(data),
        "mean": round(_mean(data), 6),
        "std": round(_std(data), 6),
        "min": min(data),
        "max": max(data),
        "median": _median(data),
    }


# ──────────────────────────────────────────
#  t 检验（Welch's t-test）
# ──────────────────────────────────────────

def t_test(group_a: List[float], group_b: List[float]) -> TestResult:
    """Welch's t 检验（不假设等方差）

    H0: 两组均值相等
    HA: 两组均值不等

    Args:
        group_a: A 组数据
        group_b: B 组数据

    Returns:
        TestResult
    """
    n1, n2 = len(group_a), len(group_b)
    if n1 < 2 or n2 < 2:
        return TestResult(
            test_name="Welch's t-test",
            statistic=0.0,
            p_value=1.0,
            significant=False,
            notes="样本量不足（需 ≥2）",
        )

    mean1, mean2 = _mean(group_a), _mean(group_b)
    var1, var2 = _variance(group_a), _variance(group_b)

    se = math.sqrt(var1 / n1 + var2 / n2)
    if se == 0:
        return TestResult(
            test_name="Welch's t-test",
            statistic=0.0,
            p_value=1.0,
            significant=False,
            notes="标准误为 0（方差为 0）",
        )

    t_stat = (mean1 - mean2) / se

    # Welch-Satterthwaite 自由度
    df_num = (var1 / n1 + var2 / n2) ** 2
    df_den = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
    df = df_num / df_den if df_den > 0 else 1

    p_value = _two_tailed_t_p(t_stat, df)
    significant = p_value < 0.05

    return TestResult(
        test_name="Welch's t-test",
        statistic=round(t_stat, 6),
        p_value=round(p_value, 6),
        significant=significant,
        notes=f"df={df:.2f}",
    )


def _two_tailed_t_p(t_stat: float, df: float) -> float:
    """双侧 t 检验 p 值（使用近似公式）

    对于大 df 使用正态近似，小 df 使用近似修正
    """
    x = df / (df + t_stat ** 2)
    p = _incomplete_beta(df / 2, 0.5, x)
    return min(1.0, p)


def _incomplete_beta(a: float, b: float, x: float) -> float:
    """不完全 Beta 函数近似（用于 p 值计算）

    使用连分数展开近似
    """
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    # 使用简单的数值积分近似
    n_steps = 1000
    h = x / n_steps
    total = 0.0
    for i in range(n_steps):
        t_val = (i + 0.5) * h
        integrand = t_val ** (a - 1) * (1 - t_val) ** (b - 1)
        total += integrand * h

    # Beta(a,b)
    log_beta = _log_gamma(a) + _log_gamma(b) - _log_gamma(a + b)
    beta_val = math.exp(log_beta)

    return total / beta_val if beta_val > 0 else 0.5


def _log_gamma(x: float) -> float:
    """Log-Gamma 函数（Stirling 近似 + Lanczos 修正）"""
    if x <= 0:
        return 0.0

    # Lanczos 系数
    g = 7
    coef = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7,
    ]

    if x < 0.5:
        return math.log(math.pi / math.sin(math.pi * x)) - _log_gamma(1 - x)

    x -= 1
    a = coef[0]
    t = x + g + 0.5
    for i in range(1, len(coef)):
        a += coef[i] / (x + i)

    return 0.5 * math.log(2 * math.pi) + (x + 0.5) * math.log(t) - t + math.log(a)


# ──────────────────────────────────────────
#  Mann-Whitney U 检验
# ──────────────────────────────────────────

def mann_whitney_u(group_a: List[float], group_b: List[float]) -> TestResult:
    """Mann-Whitney U 检验（非参数检验）

    H0: 两组分布相同
    HA: 两组分布不同

    Args:
        group_a: A 组数据
        group_b: B 组数据

    Returns:
        TestResult
    """
    n1, n2 = len(group_a), len(group_b)
    if n1 == 0 or n2 == 0:
        return TestResult(
            test_name="Mann-Whitney U",
            statistic=0.0,
            p_value=1.0,
            significant=False,
            notes="样本量为 0",
        )

    combined = group_a + group_b
    ranks = _rank(combined)

    r1 = sum(ranks[:n1])
    u1 = n1 * n2 + n1 * (n1 + 1) / 2 - r1
    u2 = n1 * n2 - u1
    u_stat = min(u1, u2)

    # 正态近似 p 值
    mean_u = n1 * n2 / 2
    std_u = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)

    if std_u == 0:
        p_value = 1.0
    else:
        z = (u_stat - mean_u) / std_u
        p_value = 2 * (1 - _normal_cdf(abs(z)))
        p_value = min(1.0, p_value)

    significant = p_value < 0.05

    return TestResult(
        test_name="Mann-Whitney U",
        statistic=round(u_stat, 4),
        p_value=round(p_value, 6),
        significant=significant,
        notes=f"U1={u1:.1f}, U2={u2:.1f}",
    )


def _normal_cdf(x: float) -> float:
    """标准正态分布 CDF（近似）"""
    return 0.5 * (1 + _erf(x / math.sqrt(2)))


def _erf(x: float) -> float:
    """误差函数近似（Abramowitz & Stegun）"""
    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1 if x >= 0 else -1
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    return sign * y


# ──────────────────────────────────────────
#  Cohen's d 效应量
# ──────────────────────────────────────────

def cohens_d(group_a: List[float], group_b: List[float]) -> float:
    """Cohen's d 效应量

    解释:
        |d| < 0.2  — 微小
        |d| < 0.5  — 小
        |d| < 0.8  — 中等
        |d| ≥ 0.8  — 大

    Args:
        group_a: A 组数据
        group_b: B 组数据

    Returns:
        Cohen's d 值
    """
    n1, n2 = len(group_a), len(group_b)
    if n1 == 0 or n2 == 0:
        return 0.0

    mean1, mean2 = _mean(group_a), _mean(group_b)
    var1, var2 = _variance(group_a), _variance(group_b)

    # 合并标准差
    pooled_std = math.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if pooled_std == 0:
        return 0.0

    return (mean1 - mean2) / pooled_std


def interpret_cohens_d(d: float) -> str:
    """解释 Cohen's d"""
    d = abs(d)
    if d < 0.2:
        return "微小效应"
    if d < 0.5:
        return "小效应"
    if d < 0.8:
        return "中等效应"
    return "大效应"


# ──────────────────────────────────────────
#  置信区间
# ──────────────────────────────────────────

def mean_difference_ci(
    group_a: List[float],
    group_b: List[float],
    confidence: float = 0.95,
) -> Tuple[float, float]:
    """均值差的置信区间

    Args:
        group_a:    A 组数据
        group_b:    B 组数据
        confidence: 置信水平

    Returns:
        (下限, 上限)
    """
    n1, n2 = len(group_a), len(group_b)
    if n1 < 2 or n2 < 2:
        return (0.0, 0.0)

    mean1, mean2 = _mean(group_a), _mean(group_b)
    var1, var2 = _variance(group_a), _variance(group_b)

    diff = mean1 - mean2
    se = math.sqrt(var1 / n1 + var2 / n2)

    if se == 0:
        return (diff, diff)

    # Welch-Satterthwaite 自由度
    df_num = (var1 / n1 + var2 / n2) ** 2
    df_den = (var1 / n1) ** 2 / (n1 - 1) + (var2 / n2) ** 2 / (n2 - 1)
    df = df_num / df_den if df_den > 0 else 1

    # t 临界值近似
    alpha = 1 - confidence
    t_crit = _t_critical(df, alpha / 2)

    margin = t_crit * se
    return (diff - margin, diff + margin)


def _t_critical(df: float, alpha: float) -> float:
    """t 分布临界值近似

    使用正态近似 + 修正
    """
    z = _normal_ppf(1 - alpha)

    # Cornish-Fisher 展开
    g1 = (z ** 3 + z) / 4
    g2 = (5 * z ** 5 + 16 * z ** 3 + 3 * z) / 96
    g3 = (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / 384

    t = z + g1 / df + g2 / (df ** 2) + g3 / (df ** 3)
    return t


def _normal_ppf(p: float) -> float:
    """标准正态分布分位数（近似）"""
    if p <= 0:
        return -8.0
    if p >= 1:
        return 8.0
    if p == 0.5:
        return 0.0

    # Rational approximation (Abramowitz & Stegun)
    if p < 0.5:
        t = math.sqrt(-2 * math.log(p))
    else:
        t = math.sqrt(-2 * math.log(1 - p))

    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308

    result = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)

    if p < 0.5:
        return -result
    return result


# ──────────────────────────────────────────
#  综合分析
# ──────────────────────────────────────────

class ABStatistics:
    """A/B 测试统计分析引擎

    整合 t 检验、Mann-Whitney U、Cohen's d、置信区间
    """

    def __init__(
        self,
        group_a: List[float],
        group_b: List[float],
        group_a_name: str = "A",
        group_b_name: str = "B",
    ):
        if not group_a or not group_b:
            raise ValueError("两组数据均不能为空")
        self._a = group_a
        self._b = group_b
        self._a_name = group_a_name
        self._b_name = group_b_name

    def analyze(self) -> ABAnalysisReport:
        """执行综合分析"""
        d = cohens_d(self._a, self._b)
        ci = mean_difference_ci(self._a, self._b)

        t_result = t_test(self._a, self._b)
        mw_result = mann_whitney_u(self._a, self._b)

        # 生成建议
        if t_result.significant and mw_result.significant:
            if abs(d) >= 0.8:
                rec = f"强烈建议采用 {self._b_name if _mean(self._b) > _mean(self._a) else self._a_name}，效应量显著且大"
            elif abs(d) >= 0.5:
                rec = f"建议采用 {self._b_name if _mean(self._b) > _mean(self._a) else self._a_name}，效应量中等"
            else:
                rec = "统计显著但效应量小，需权衡成本决定"
        else:
            rec = "无统计显著差异，建议继续观察或增加样本量"

        return ABAnalysisReport(
            group_a_name=self._a_name,
            group_b_name=self._b_name,
            group_a_stats=descriptive_stats(self._a),
            group_b_stats=descriptive_stats(self._b),
            t_test=t_result,
            mann_whitney=mw_result,
            cohens_d=round(d, 6),
            confidence_interval=(round(ci[0], 6), round(ci[1], 6)),
            recommendation=rec,
        )


# ──────────────────────────────────────────
#  单元测试
# ──────────────────────────────────────────

def _run_tests() -> None:
    """内置单元测试"""
    passed = 0
    failed = 0

    def assert_eq(name: str, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")
            print(f"    expected: {expected}")
            print(f"    actual:   {actual}")

    def assert_lt(name: str, actual, upper):
        nonlocal passed, failed
        if actual < upper:
            passed += 1
        else:
            failed += 1
            print(f"  FAIL: {name}")
            print(f"    expected < {upper}")
            print(f"    actual: {actual}")

    # ── 测试 1: 描述统计 ──
    stats = descriptive_stats([1.0, 2.0, 3.0, 4.0, 5.0])
    assert_eq("均值", stats["mean"], 3.0)
    assert_eq("n", stats["n"], 5)
    assert_eq("中位数", stats["median"], 3.0)

    # ── 测试 2: t 检验 — 显著差异 ──
    group_a = [1.0, 1.2, 1.1, 0.9, 1.3, 1.0, 1.2, 1.1]
    group_b = [3.0, 3.2, 2.9, 3.1, 3.3, 3.0, 2.8, 3.1]
    result = t_test(group_a, group_b)
    assert_eq("t检验-显著", result.significant, True)
    assert_lt("t检验-p值", result.p_value, 0.01)

    # ── 测试 3: t 检验 — 无显著差异 ──
    group_a = [1.0, 1.1, 0.9, 1.2, 1.0]
    group_b = [1.1, 1.0, 1.2, 0.9, 1.1]
    result = t_test(group_a, group_b)
    assert_eq("t检验-不显著", result.significant, False)

    # ── 测试 4: Mann-Whitney U — 显著 ──
    group_a = [1.0, 1.2, 1.1, 0.9, 1.3]
    group_b = [5.0, 5.2, 4.9, 5.1, 5.3]
    result = mann_whitney_u(group_a, group_b)
    assert_eq("MW-U-显著", result.significant, True)

    # ── 测试 5: Cohen's d ──
    d = cohens_d([1.0, 1.1, 1.2], [3.0, 3.1, 3.2])
    assert_eq("Cohen-d-大", abs(d) > 2.0, True)

    d_small = cohens_d([1.0, 1.01, 0.99], [1.02, 1.01, 1.03])
    assert_eq("Cohen-d-小", abs(d_small) < 1.0, True)

    # ── 测试 6: 效应量解释 ──
    assert_eq("解释-大", "大效应" in interpret_cohens_d(1.0), True)
    assert_eq("解释-微小", "微小效应" in interpret_cohens_d(0.1), True)

    # ── 测试 7: 置信区间 ──
    ci = mean_difference_ci(group_a, group_b)
    assert_eq("CI-下限<上限", ci[0] < ci[1], True)

    # ── 测试 8: 综合分析 ──
    stats_engine = ABStatistics(
        group_a=[1.0, 1.2, 1.1, 0.9, 1.3, 1.0, 1.2, 1.1],
        group_b=[3.0, 3.2, 2.9, 3.1, 3.3, 3.0, 2.8, 3.1],
        group_a_name="OpenAI",
        group_b_name="Anthropic",
    )
    report = stats_engine.analyze()
    assert_eq("报告-A统计", "mean" in report.group_a_stats, True)
    assert_eq("报告-t检验", report.t_test is not None, True)
    assert_eq("报告-MW", report.mann_whitney is not None, True)
    assert_eq("报告-建议", len(report.recommendation) > 0, True)

    # ── 测试 9: 摘要 ──
    summary = report.summary()
    assert_eq("摘要-非空", len(summary) > 0, True)

    # ── 测试 10: 小样本 ──
    result = t_test([1.0], [2.0])
    assert_eq("小样本-不显著", result.significant, False)

    # ── 测试 11: 零方差 ──
    result = t_test([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
    assert_eq("零方差-不显著", result.significant, False)

    print(f"\nStatistics 测试: {passed} passed, {failed} failed")


if __name__ == "__main__":
    _run_tests()
```
