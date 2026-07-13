"""R12改进: 运行Lint并将评分回写到Front Matter lint_score字段"""
from __future__ import annotations

from pathlib import Path

import yaml

from ai_prompt_toolkit.frontmatter import parse_front_matter, serialize_front_matter
from ai_prompt_toolkit.linter.linter import PromptLinter


def update_lint_scores(target_dir: str = "_scenarios") -> dict[str, float]:
    base = Path(target_dir)
    scores: dict[str, float] = {}
    linter = PromptLinter()

    for p in sorted(base.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        parsed, body = parse_front_matter(text)
        if parsed is None:
            continue

        template_type = parsed.get("template_type", "prompt")
        result = linter.lint(p.name, body if body else text, template_type=template_type)
        score = result.score

        parsed["lint_score"] = round(score, 1)
        parsed["lint_last_checked"] = _now_iso()

        fm_yaml = yaml.dump(parsed, allow_unicode=True, default_flow_style=False, sort_keys=False)
        new_text = f"---\n{fm_yaml}---\n{body}"

        p.write_text(new_text, encoding="utf-8")
        scores[p.name] = score

    return scores


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


if __name__ == "__main__":
    scores = update_lint_scores()
    for name, score in sorted(scores.items(), key=lambda x: x[1]):
        print(f"  {score:5.1f} | {name}")
    avg = sum(scores.values()) / max(len(scores), 1)
    print(f"\n平均: {avg:.1f} | 文件: {len(scores)}")
