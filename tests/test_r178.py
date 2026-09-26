"""R178测试: 内置模板自洽守护 — golden快照防新误报

机制: 对src/ai_prompt_toolkit/templates/下所有模板跑lint, HIGH/CRITICAL发现
必须与快照(tests/fixtures/template_high_baseline.json)完全一致:
- 快照外新增HIGH → FAIL(新规则误报必须先审查)
- 快照内消失(已修复) → FAIL并提示更新快照(庆祝收缩, 显式确认)
债务消化目标: 每轮修复后重新生成快照, 计数只减不增(R178起点: 237条)。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_prompt_toolkit.linter.linter import PromptLinter

TEMPLATES_DIR = Path("src/ai_prompt_toolkit/templates")
SNAPSHOT = Path("tests/fixtures/template_high_baseline.json")

# R179: 部署语境规则豁免 — 这些规则的适用对象是"生产部署配置"(运行时的模型调用/缓存/
# 数据治理/编排/合规), 而模板是资产源文件。同ESLint对config文件的overrides逻辑。
# 豁免是显式的、带理由的、可审查的; 新规则不得擅自加入。
TEMPLATE_EXEMPT_RULES: dict[str, str] = {
    # 模型选型/供应链 — 部署时决策, 模板只声明兼容性
    "P224": "模型版本锁定是部署时决策",
    "P100": "ModelArts护栏是部署配置",
    "P221": "模型来源验证是部署侧",
    "P196": "推理超时是运行时配置",
    "P197": "max_tokens是运行时配置",
    "P239": "速率限制是运行时配置",
    "P237": "侧信道防护是基础设施",
    "P231": "梯度保护属训练期",
    # 数据治理/合规 — 部署侧数据流
    "P114": "GDPR对齐属部署侧数据流",
    "P202": "用户同意机制属部署侧",
    "P205": "数据留存属部署侧数据治理",
    "P241": "数据最小化属部署侧合规",
    "P201": "合规声明属部署侧",
    "P255": "未成年人保护属部署侧",
    "P253": "金融保护属部署侧",
    "P079": "跨境合规属部署侧",
    # 运行时编排/缓存/检索 — 模板是单资产, 无编排面
    "P161": "模板注入转义属运行时渲染",
    "P162": "缓存投毒属运行时缓存",
    "P180": "链式编排属运行时",
    "P249": "级联防护属运行时",
    "P206": "检索净化属运行时RAG",
    "P209": "上下文窗口属运行时",
    "P207": "幻觉检测属运行时",
    "P248": "漂移检测属运营期",
    # 多模态运行时处理
    "P131": "输入模态声明是模板可选特性",
    "P138": "多模态链式攻击属运行时",
    "P139": "多模态数据隔离属运行时",
    "P216": "图像注入预处理属运行时",
    "P132": "图像安全校验属运行时",
    "P133": "音频过滤属运行时",
    "P218": "跨模态隔离属运行时",
    "P039": "多模态内容安全属运行时",
    # Agent/沙箱 — 运行时编排与执行环境
    "P194": "多Agent通信属运行时编排",
    "P065": "链式错误隔离属运行时编排",
    "P159": "沙箱隔离属部署执行环境",
    "P127": "安全沙箱属部署执行环境",
    # 鸿蒙ArkTS代码规范 — 针对.ets代码文件, 模板中的示例代码不适用
    "P186": "ArkTS范式迁移针对.ets代码",
    "P121": "ArkTS严格模式针对.ets代码",
    "P122": "Stage生命周期针对.ets代码",
    "P146": "UIAbility生命周期针对.ets代码",
    "P087": "Ability声明针对.ets代码",
    "P211": "ArkUI懒加载针对.ets代码",
    "P172": "LazyForEach针对.ets代码",
    "P124": "ohos权限声明属部署清单",
    "P089": "ohos权限声明属部署清单",
    "P094": "ohos网络安全属部署配置",
    "P130": "ohos网络安全属部署配置",
}


def _collect_highs() -> dict[str, list[str]]:
    linter = PromptLinter()
    result: dict[str, list[str]] = {}
    for p in sorted(TEMPLATES_DIR.rglob("*.md")):
        r = linter.lint(p.name, p.read_text(encoding="utf-8"))
        highs = sorted(
            f"{f.rule_id}:{getattr(f.severity, 'value', '')}"
            for f in r.findings
            if getattr(f.severity, "value", "") in ("high", "critical") and f.rule_id not in TEMPLATE_EXEMPT_RULES
        )
        result[str(p.relative_to(TEMPLATES_DIR))] = highs
    return result


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


class TestTemplateSelfConsistency:
    def test_snapshot_exists(self):
        assert SNAPSHOT.exists(), "快照缺失, 运行生成脚本"

    def test_no_new_high_findings(self, snapshot):
        """快照外新增HIGH → 阻塞(新规则误报必须先审查)"""
        current = _collect_highs()
        offenders = []
        for name, highs in current.items():
            known = set(snapshot.get(name, {}).get("high_findings", []))
            new = [h for h in highs if h not in known]
            if new:
                offenders.append(f"{name}: {new}")
        assert not offenders, (
            "模板出现快照外HIGH发现(疑似新规则误报):\n"
            + "\n".join(offenders)
            + "\n→ 修复规则误报(上下文门控/降级)或修正模板内容后重新生成快照"
        )

    def test_debt_only_shrinks(self, snapshot):
        """债务只允许收缩: 当前HIGH总数不得超过快照记账总数"""
        current = _collect_highs()
        total_now = sum(len(v) for v in current.values())
        total_known = sum(len(v.get("high_findings", [])) for v in snapshot.values())
        assert total_now <= total_known, f"HIGH总数增长: {total_known}→{total_now} — 禁止无意识膨胀"
        if total_now < total_known:
            print(f"\n[债务收缩] {total_known}→{total_now}, 请重新生成快照固化成果")
