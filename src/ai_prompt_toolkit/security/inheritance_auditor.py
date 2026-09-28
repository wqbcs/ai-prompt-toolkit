"""继承链审计器——检测深度、循环、断裂和风险传播。"""

from __future__ import annotations

from typing import Any, Protocol

from ai_prompt_toolkit.security.types import InheritanceFinding, RiskLevel

MAX_INHERITANCE_DEPTH = 5


class TemplateProvider(Protocol):
    def get_parent_id(self, template_id: str) -> str | None: ...

    def template_exists(self, template_id: str) -> bool: ...

    def get_risk_tags(self, template_id: str) -> list[str]: ...


class DictTemplateProvider:
    def __init__(self, templates: dict[str, dict[str, Any]]) -> None:
        self._templates = templates

    def get_parent_id(self, template_id: str) -> str | None:
        tpl = self._templates.get(template_id)
        if tpl is None:
            return None
        return tpl.get("parent_id")

    def template_exists(self, template_id: str) -> bool:
        return template_id in self._templates

    def get_risk_tags(self, template_id: str) -> list[str]:
        tpl = self._templates.get(template_id)
        if tpl is None:
            return []
        tags: list[str] = tpl.get("risk_tags", [])
        return tags


class InheritanceAuditor:
    def __init__(self, provider: TemplateProvider, *, max_depth: int = MAX_INHERITANCE_DEPTH) -> None:
        self._provider = provider
        self._max_depth = max_depth

    def audit(self, template_id: str) -> list[InheritanceFinding]:
        findings: list[InheritanceFinding] = []
        path_visited: set[str] = set()
        fully_visited: set[str] = set()
        chain: list[str] = []

        self._dfs(template_id, chain, path_visited, fully_visited, findings)
        self._check_risk_propagation(template_id, findings)

        return findings

    def _dfs(
        self,
        current_id: str,
        chain: list[str],
        path_visited: set[str],
        fully_visited: set[str],
        findings: list[InheritanceFinding],
    ) -> None:
        if current_id in path_visited:
            cycle_chain = [*chain, current_id]
            findings.append(
                InheritanceFinding(
                    template_id=chain[0] if chain else current_id,
                    parent_id=current_id,
                    chain=cycle_chain,
                    depth=len(cycle_chain) - 1,
                    risk_level=RiskLevel.CRITICAL,
                    issue_type="circular",
                    description=f"检测到循环继承：{' -> '.join(cycle_chain)}",
                    remediation="打破循环依赖，重构模板继承关系",
                )
            )
            return

        if current_id in fully_visited:
            return

        if not self._provider.template_exists(current_id):
            if chain:
                findings.append(
                    InheritanceFinding(
                        template_id=chain[0],
                        parent_id=current_id,
                        chain=[*chain, current_id],
                        depth=len(chain),
                        risk_level=RiskLevel.HIGH,
                        issue_type="broken",
                        description=f"继承链断裂：父模板 '{current_id}' 不存在",
                        remediation=f"创建缺失的父模板 '{current_id}' 或修改继承指向",
                    )
                )
            return

        path_visited.add(current_id)
        chain.append(current_id)

        if len(chain) - 1 > self._max_depth:
            findings.append(
                InheritanceFinding(
                    template_id=chain[0],
                    parent_id=current_id,
                    chain=list(chain),
                    depth=len(chain) - 1,
                    risk_level=RiskLevel.HIGH,
                    issue_type="depth_exceeded",
                    description=f"继承深度 {len(chain) - 1} 超过最大阈值 {self._max_depth}",
                    remediation="减少继承层级，考虑扁平化模板结构",
                )
            )

        parent_id = self._provider.get_parent_id(current_id)
        if parent_id is not None:
            self._dfs(parent_id, chain, path_visited, fully_visited, findings)

        chain.pop()
        path_visited.discard(current_id)
        fully_visited.add(current_id)

    def _check_risk_propagation(self, template_id: str, findings: list[InheritanceFinding]) -> None:
        chain: list[str] = []
        # R197: get_parent_id返回str|None — 显式标注, while条件即判None
        current: str | None = template_id
        seen: set[str] = set()
        while current is not None:
            if current in seen:
                break
            if not self._provider.template_exists(current):
                break
            seen.add(current)
            chain.append(current)
            current = self._provider.get_parent_id(current)

        all_risks: dict[str, str] = {}
        for tid in chain:
            tags = self._provider.get_risk_tags(tid)
            for tag in tags:
                if tag not in all_risks:
                    all_risks[tag] = tid

        high_risk_tags = {"pii", "sensitive", "confidential", "secret", "credential"}
        propagated = {tag: src for tag, src in all_risks.items() if tag in high_risk_tags}

        if propagated and len(chain) > 1:
            risk_names = ", ".join(propagated.keys())
            findings.append(
                InheritanceFinding(
                    template_id=template_id,
                    parent_id=chain[-1] if len(chain) > 1 else "",
                    chain=list(chain),
                    depth=len(chain) - 1,
                    risk_level=RiskLevel.MEDIUM,
                    issue_type="risk_propagation",
                    description=f"高风险标签 [{risk_names}] 通过继承链传播到子模板",
                    remediation="在子模板中添加风险隔离约束或断开继承",
                )
            )
