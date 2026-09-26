"""R12改进: 为场景模板自动添加角色定义(P001修复)"""

from __future__ import annotations

import re
from pathlib import Path

_ROLE_MAP = {
    "chaos": "你是一位混沌工程专家，精通故障注入、爆炸半径控制、稳态假设验证",
    "gitops": "你是一位GitOps实践专家，精通ArgoCD/Flux持续交付和基础设施即代码",
    "observability": "你是一位可观测性架构专家，精通分布式追踪、指标监控、日志聚合",
    "platform": "你是一位平台工程专家，精通内部开发者平台(IDP)和自服务基础设施",
    "deh": "你是一位华为云专属云(DeH)运维专家",
    "bms": "你是一位华为云裸金属服务器(BMS)运维专家",
    "as": "你是一位华为云弹性伸缩(AS)运维专家",
    "elb": "你是一位华为云弹性负载均衡(ELB)运维专家",
    "cce": "你是一位华为云CCE(云容器引擎)运维专家",
    "modelarts": "你是一位华为云ModelArts(AI开发平台)专家",
    "functiongraph": "你是一位华为云FunctionGraph(函数计算)专家",
    "gaussdb": "你是一位华为云GaussDB(分布式数据库)专家",
    "cse": "你是一位华为云CSE(微服务引擎)专家",
    "ief": "你是一位华为云IEF(智能边缘平台)专家",
    "vpc": "你是一位华为云VPC(虚拟私有云)网络专家",
    "dcs": "你是一位华为云DCS(分布式缓存)专家",
    "dws": "你是一位华为云DWS(数据仓库)专家",
    "rds": "你是一位华为云RDS(关系型数据库)专家",
}


def _infer_role(filepath: Path) -> str:
    name = filepath.stem.lower()
    for key, role in _ROLE_MAP.items():
        if key in name or key in str(filepath.parent):
            return role
    parent = filepath.parent.name.lower()
    if "huawei" in parent:
        return "你是一位华为云服务运维专家"
    return "你是一位云原生架构专家"


def fix_p001(target_dir: str = "_scenarios") -> int:
    base = Path(target_dir)
    fixed = 0
    for p in sorted(base.rglob("*.md")):
        text = p.read_text(encoding="utf-8")
        if "你是" in text:
            continue

        role = _infer_role(p)

        pattern = r"(#{2,3}\s*提示词模板\s*\n+(?:.*?\n)*?)((?:{{#if|###|你是一位|You are))"
        m = re.search(pattern, text)
        if not m:
            pattern2 = r"(#{2,3}\s*提示词模板\s*\n+)"
            m2 = re.search(pattern2, text)
            if m2:
                insert_pos = m2.end()
                text = text[:insert_pos] + f"{role}\n\n" + text[insert_pos:]
                p.write_text(text, encoding="utf-8")
                fixed += 1
                continue

        if m:
            insert_pos = m.start(2)
            text = text[:insert_pos] + f"{role}\n\n" + text[insert_pos:]
            p.write_text(text, encoding="utf-8")
            fixed += 1

    return fixed


if __name__ == "__main__":
    count = fix_p001()
    print(f"已为 {count} 个模板添加角色定义")
