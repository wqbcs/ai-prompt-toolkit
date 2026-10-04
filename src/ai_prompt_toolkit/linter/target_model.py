"""P1-16: --target-model 目标模型声明 × P262 品牌绑定交叉判定（R229）。

语义：prompt 声明了目标模型（`--target-model claude`）却把身份绑定到另一家
模型品牌（"你是ChatGPT"）= 明确的跨模型移植矛盾，比"未声明目标的绑定"更严重
→ P262 由 MEDIUM 升级为 HIGH，并在描述中注明矛盾双方。

设计约束：
- **数据驱动**：模型名 → 族 的映射是族表（MODEL_FAMILIES），不是 if/else 链
  （用户硬要求"避免硬编码"；新增模型族=加一行数据）。
- **保守升级**：品牌或目标模型任一侧解析不到族 → 不升级（确定性 + 低误报，
  01 §2 楔子）。未知模型名不会造成误升级。
- **纯函数**：`escalate_mismatched_brand(findings, target_model)` 不改输入列表，
  返回新列表——调用方（linter.lint）无副作用耦合，可独立测试。
"""

from __future__ import annotations

from ai_prompt_toolkit.types import Finding, Severity

__all__ = ["MODEL_FAMILIES", "P262_RULE_ID", "escalate_mismatched_brand", "resolve_family"]

P262_RULE_ID = "P262"

# 模型名（小写子串）→ 族。顺序=匹配优先级（先列的先命中）。
# 判定"跨模型矛盾"只需族级粒度，不需精确型号。
MODEL_FAMILIES: dict[str, tuple[str, ...]] = {
    "openai": ("gpt", "chatgpt", "dall-e", "o1", "o3"),
    "anthropic": ("claude",),
    "google": ("gemini", "palm"),
    "meta": ("llama",),
    "mistral": ("mistral", "mixtral"),
    "deepseek": ("deepseek",),
    "aliyun": ("qwen", "通义"),
    "baidu": ("ernie", "文心"),
    "bytedance": ("豆包",),
    "moonshot": ("kimi", "moonshot"),
    "xai": ("grok",),
}


def resolve_family(model_name: str) -> str | None:
    """模型名 → 族（子串匹配，大小写不敏感）。解析不到返回 None（保守）。"""
    n = model_name.strip().lower()
    if not n:
        return None
    for family, tokens in MODEL_FAMILIES.items():
        for tok in tokens:
            if tok.lower() in n:
                return family
    return None


def escalate_mismatched_brand(findings: list[Finding], target_model: str | None) -> list[Finding]:
    """P262 品牌与声明目标模型跨族 → 升级 HIGH + 描述注明矛盾双方。

    其余 finding 原样保留（同一对象引用，不复制）；输入列表不被修改。
    """
    if not target_model:
        return findings
    target_family = resolve_family(target_model)
    if target_family is None:
        return findings  # 目标模型未知 → 保守不升级

    out: list[Finding] = []
    for f in findings:
        if f.rule_id != P262_RULE_ID:
            out.append(f)
            continue
        brand = str(f.details.get("brand", "")) if isinstance(f.details, dict) else ""
        brand_family = resolve_family(brand)
        if brand_family is None or brand_family == target_family:
            out.append(f)  # 同族或品牌未知 → 不升级
            continue
        out.append(
            Finding(
                rule_id=f.rule_id,
                severity=Severity.HIGH,
                description=(
                    f"{f.description}（声明目标模型为 {target_model} [{target_family}]，"
                    f"却绑定 {brand} [{brand_family}] — 跨模型移植矛盾，部署到目标模型时身份失真）"
                ),
                location=f.location,
                remediation=f.remediation,
                details={**f.details, "target_model": target_model, "target_family": target_family, "escalated": True},
            )
        )
    return out
