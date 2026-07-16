"""程序化Prompt生成 — 参考guidance的gen/select/json约束

P3-02: 程序化构建Prompt，支持条件/循环/选择/约束
- PromptBuilder: 链式API构建复杂Prompt
- 约束生成: 长度/格式/语言约束
- 模板变量: {{variable}}占位符
- 条件分支: if/else逻辑
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PromptBlock:
    content: str
    block_type: str = "text"
    condition: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class PromptBuilder:
    def __init__(self, role: str = "", language: str = "zh-CN"):
        self._blocks: list[PromptBlock] = []
        self._variables: dict[str, str] = {}
        self._constraints: list[str] = []
        self._role = role
        self._language = language

    def set_role(self, role: str, skills: list[str] | None = None) -> PromptBuilder:
        content = f"你是一个专业的{role}。"
        if skills:
            content += f"你的核心能力包括：{'、'.join(skills)}。"
        self._blocks.append(PromptBlock(content=content, block_type="role"))
        self._role = role
        return self

    def add_instruction(self, instruction: str) -> PromptBuilder:
        self._blocks.append(PromptBlock(content=instruction, block_type="instruction"))
        return self

    def add_step(self, step: str, step_num: int | None = None) -> PromptBuilder:
        prefix = f"{step_num}. " if step_num else "- "
        self._blocks.append(PromptBlock(content=prefix + step, block_type="step"))
        return self

    def add_steps(self, steps: list[str]) -> PromptBuilder:
        for i, step in enumerate(steps, 1):
            self.add_step(step, i)
        return self

    def add_example(self, input_text: str, output_text: str) -> PromptBuilder:
        content = f"示例：\n输入：{input_text}\n输出：{output_text}"
        self._blocks.append(PromptBlock(content=content, block_type="example"))
        return self

    def add_constraint(self, constraint: str) -> PromptBuilder:
        self._constraints.append(constraint)
        return self

    def add_output_format(self, format_desc: str) -> PromptBuilder:
        content = f"输出格式：\n{format_desc}"
        self._blocks.append(PromptBlock(content=content, block_type="format"))
        return self

    def add_variable(self, name: str, default: str = "") -> PromptBuilder:
        self._variables[name] = default
        self._blocks.append(PromptBlock(content=f"{{{{{name}}}}}", block_type="variable"))
        return self

    def add_error_handling(self, fallback: str = "请说明原因") -> PromptBuilder:
        content = f'如果无法完成，请回复"无法完成，{fallback}"。'
        self._blocks.append(PromptBlock(content=content, block_type="error_handling"))
        return self

    def add_condition(self, condition: str, if_content: str, else_content: str = "") -> PromptBuilder:
        self._blocks.append(PromptBlock(
            content=if_content, block_type="condition",
            condition=condition, metadata={"else_content": else_content},
        ))
        return self

    def add_few_shot(self, examples: list[dict[str, str]]) -> PromptBuilder:
        for ex in examples:
            self.add_example(ex.get("input", ""), ex.get("output", ""))
        return self

    def build(self, context: dict[str, str] | None = None) -> str:
        parts: list[str] = []
        for block in self._blocks:
            content = block.content
            if block.block_type == "condition" and context:
                cond_key = block.condition or ""
                if context.get(cond_key):
                    parts.append(content)
                elif block.metadata.get("else_content"):
                    parts.append(block.metadata["else_content"])
            else:
                parts.append(content)

        if self._constraints:
            constraint_text = "约束条件：\n" + "\n".join(f"- {c}" for c in self._constraints)
            parts.append(constraint_text)

        result = "\n\n".join(parts)

        if context:
            for key, value in context.items():
                result = result.replace(f"{{{{{key}}}}}", value)

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self._role,
            "language": self._language,
            "blocks": len(self._blocks),
            "variables": list(self._variables.keys()),
            "constraints": self._constraints,
        }


def build_from_template(template: str, **kwargs: Any) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))

    pattern = re.compile(r"\{\{(\w+)\}\}")
    remaining = pattern.findall(result)
    if remaining:
        for var in remaining:
            result = result.replace(f"{{{{{var}}}}}", f"[{var}]")

    return result
