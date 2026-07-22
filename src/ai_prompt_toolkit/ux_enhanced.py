"""UX体验增强模块 — 体验鬼才视角

5大微改动(每个<1开发日):
1. 增强空状态: 每个空状态含具体下一步命令+3个快速建议
2. 友好错误恢复: 错误时提供3个恢复建议+诊断命令
3. 进度体验增强: 阶段标签+完成提示+耗时分析
4. 退出流程关怀: 中断时保存进度提示+恢复命令
5. 优化结果庆祝: GEPA/OPRO/TGD优化成功时触发情感化消息

体验鬼才哲学: "最好的体验是用户感觉不到体验"
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EmptyStateGuide:
    message: str = ""
    icon: str = "📋"
    next_steps: list[str] = field(default_factory=list)
    quick_tips: list[str] = field(default_factory=list)
    related_commands: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"{self.icon} {self.message}"]
        if self.next_steps:
            lines.append("")
            lines.append("  下一步:")
            for i, step in enumerate(self.next_steps, 1):
                lines.append(f"    {i}. {step}")
        if self.quick_tips:
            lines.append("")
            lines.append("  快速建议:")
            for tip in self.quick_tips:
                lines.append(f"    → {tip}")
        if self.related_commands:
            lines.append("")
            lines.append("  相关命令:")
            for cmd in self.related_commands:
                lines.append(f"    $ {cmd}")
        return "\n".join(lines)


_EMPTY_STATE_GUIDES: dict[str, EmptyStateGuide] = {
    "lint": EmptyStateGuide(
        message="没有发现Lint问题！你的Prompt质量很棒。",
        icon="✨",
        next_steps=[
            "运行完整评估验证质量: promptkit evaluate -t <file>",
            "检查安全风险: promptkit scan -t <file>",
            "用GEPA优化进一步提升: promptkit gepa-optimize -p <text>",
        ],
        quick_tips=[
            "Lint满分不等于生产就绪，建议做安全扫描",
            "定期Lint可保持Prompt质量",
        ],
        related_commands=[
            "promptkit evaluate --quick -t .",
            "promptkit scan -t .",
            "promptkit contest-eval -t .",
        ],
    ),
    "scan": EmptyStateGuide(
        message="没有发现安全风险！你的Prompt很安全。",
        icon="🛡️",
        next_steps=[
            "进行红队深度探测: promptkit redteam -s <file>",
            "注入Canary Token防泄露: promptkit canary-inject -s <file>",
            "查看安全评分卡: promptkit scorecard -s <file>",
        ],
        quick_tips=[
            "安全是持续过程，建议CI中定期扫描",
            "注入检测引擎可发现深层注入攻击",
        ],
        related_commands=[
            "promptkit redteam --probes essential -s .",
            "promptkit scorecard -s .",
        ],
    ),
    "evaluate": EmptyStateGuide(
        message="评估结果为空。",
        icon="📊",
        next_steps=[
            "确保目标文件包含有效的Prompt内容",
            "使用快速评估模式: promptkit evaluate --quick -t <file>",
            "指定评估维度: promptkit evaluate -d D01,D02,D05 -t <file>",
        ],
        quick_tips=[
            "使用 --quick 仅评估TOP10核心维度",
            "使用 --threshold 60 设置质量门禁",
        ],
        related_commands=[
            "promptkit evaluate --quick -t .",
            "promptkit gepa-optimize -p <text>",
        ],
    ),
    "version": EmptyStateGuide(
        message="暂无版本记录。",
        icon="📚",
        next_steps=[
            "创建第一个版本: promptkit prompt-version create -n <name> -s <file>",
            "用GEPA优化并自动保存版本: promptkit gepa-optimize -p <text> --save-version",
        ],
        quick_tips=[
            "版本管理让你随时回滚到之前的Prompt",
            "GEPA优化会自动保存每个优化结果版本",
        ],
        related_commands=[
            "promptkit prompt-version list",
            "promptkit gepa-optimize -p <text> --save-version",
        ],
    ),
    "gepa": EmptyStateGuide(
        message="GEPA优化暂无结果。",
        icon="🧬",
        next_steps=[
            "确认输入了有效的Prompt文本",
            "使用light模式快速优化: promptkit gepa-optimize -p <text> --auto light",
            "自定义评估指标获得更精准的优化",
        ],
        quick_tips=[
            "light模式(6候选)适合快速迭代",
            "heavy模式(18候选)适合最终优化",
        ],
        related_commands=[
            "promptkit gepa-optimize -p <text> --auto light",
            "promptkit tgd-optimize -p <text>",
        ],
    ),
    "registry": EmptyStateGuide(
        message="模板仓库暂无模板。",
        icon="📦",
        next_steps=[
            "推送你的第一个模板: promptkit registry-push -n <name> -t <text>",
            "从JSON导入模板: promptkit registry-push -n <name> -t <file>",
        ],
        quick_tips=[
            "模板支持版本管理，每次push自动递增版本",
            "使用标签和分类让模板更易发现",
        ],
        related_commands=[
            "promptkit registry-push -n my-template -t template.md",
            "promptkit registry-search -q <keyword>",
        ],
    ),
    "redteam": EmptyStateGuide(
        message="红队探测暂无结果。",
        icon="🎯",
        next_steps=[
            "开始安全探测: promptkit redteam -s <file>",
            "使用核心探测集: promptkit redteam --probes essential -s <file>",
        ],
        quick_tips=[
            "essential模式覆盖90个核心探测",
            "full模式包含全部探测，耗时较长",
        ],
        related_commands=[
            "promptkit redteam --probes essential -s .",
            "promptkit scan -s .",
        ],
    ),
    "default": EmptyStateGuide(
        message="暂无结果。",
        icon="📋",
        next_steps=[
            "运行交互向导开始使用: promptkit wizard",
            "查看所有命令: promptkit --help",
        ],
        quick_tips=[
            "wizard是最佳入门方式",
        ],
        related_commands=[
            "promptkit wizard",
            "promptkit --help",
        ],
    ),
}


def get_empty_state_guide(command: str) -> EmptyStateGuide:
    return _EMPTY_STATE_GUIDES.get(command, _EMPTY_STATE_GUIDES["default"])


@dataclass
class ErrorRecovery:
    error_type: str = ""
    error_message: str = ""
    icon: str = "⚠️"
    diagnosis: str = ""
    recovery_steps: list[str] = field(default_factory=list)
    diagnosis_commands: list[str] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"{self.icon} {self.error_message}"]
        if self.diagnosis:
            lines.append(f"  诊断: {self.diagnosis}")
        if self.recovery_steps:
            lines.append("  恢复建议:")
            for i, step in enumerate(self.recovery_steps, 1):
                lines.append(f"    {i}. {step}")
        if self.diagnosis_commands:
            lines.append("  诊断命令:")
            for cmd in self.diagnosis_commands:
                lines.append(f"    $ {cmd}")
        return "\n".join(lines)


_FILE_NOT_FOUND = ErrorRecovery(
    error_type="file_not_found",
    error_message="文件未找到",
    icon="📁",
    diagnosis="指定的路径不存在或不可访问",
    recovery_steps=[
        "检查文件路径拼写是否正确",
        "确认文件是否在当前目录下",
        "使用 promptkit lint -t . 扫描当前目录所有文件",
    ],
    diagnosis_commands=[
        "ls *.md",
        "promptkit lint -t .",
    ],
)

_INVALID_FORMAT = ErrorRecovery(
    error_type="invalid_format",
    error_message="格式错误",
    icon="📝",
    diagnosis="输入文件格式不符合预期",
    recovery_steps=[
        "确认文件编码为UTF-8",
        "检查JSON/YAML语法是否正确",
        "使用 promptkit compile 验证模板语法",
    ],
    diagnosis_commands=[
        "file <path>",
        "python -c \"import json; json.load(open('<path>'))\"",
    ],
)

_CONFIG_ERROR = ErrorRecovery(
    error_type="config_error",
    error_message="配置错误",
    icon="⚙️",
    diagnosis="配置文件内容无效或缺失必要字段",
    recovery_steps=[
        "使用 promptkit config-generate 生成默认配置",
        "检查 .prompt-cli.toml 语法",
        "确认所有必填字段已设置",
    ],
    diagnosis_commands=[
        "promptkit config-generate",
        "cat .prompt-cli.toml",
    ],
)

_OPTIMIZATION_FAILED = ErrorRecovery(
    error_type="optimization_failed",
    error_message="优化失败",
    icon="🔄",
    diagnosis="优化过程未产生改进结果",
    recovery_steps=[
        "尝试不同的优化策略: tgd / opro / gepa",
        "使用统一管线: promptkit pipeline-optimize -p <text>",
        "降低收敛阈值以允许更多迭代",
    ],
    diagnosis_commands=[
        "promptkit tgd-optimize -p <text> --iterations 5",
        "promptkit opro-optimize -i <text> --generations 3",
    ],
)

_CONNECTION_ERROR = ErrorRecovery(
    error_type="connection_error",
    error_message="连接错误",
    icon="🌐",
    diagnosis="无法连接到LLM API或Webhook服务",
    recovery_steps=[
        "检查网络连接",
        "确认API密钥已正确配置",
        "使用离线模式(--offline)避免API调用",
    ],
    diagnosis_commands=[
        "ping api.openai.com",
        "echo $OPENAI_API_KEY",
    ],
)


_ERROR_RECOVERY_MAP: dict[str, ErrorRecovery] = {
    "file_not_found": _FILE_NOT_FOUND,
    "invalid_format": _INVALID_FORMAT,
    "config_error": _CONFIG_ERROR,
    "optimization_failed": _OPTIMIZATION_FAILED,
    "connection_error": _CONNECTION_ERROR,
}


def get_error_recovery(error_type: str) -> ErrorRecovery:
    return _ERROR_RECOVERY_MAP.get(error_type, ErrorRecovery(
        error_type=error_type,
        error_message="未知错误",
        icon="❓",
        diagnosis="发生未预期的错误",
        recovery_steps=[
            "查看详细日志: 设置 PROMPT_CLI_DEBUG=1",
            "提交问题: https://github.com/ai-prompt-toolkit/issues",
        ],
    ))


_OPTIMIZATION_CELEBRATIONS: dict[str, list[str]] = {
    "gepa_improved": [
        "GEPA进化成功! Prompt在反思中蜕变，如凤凰涅槃。",
        "GEPA突破! Pareto前沿再添新星，进化不止步。",
        "反思式进化生效! 每一次变异都在逼近最优。",
    ],
    "tgd_improved": [
        "文本梯度下降命中! 沿梯度方向精准优化。",
        "TGD收敛成功! 文本梯度的力量不可思议。",
        "梯度下降到最优点! 每一步都离完美更近。",
    ],
    "opro_improved": [
        "OPRO元优化生效! LLM作为优化器的魔法显灵了。",
        "进化种群找到新方向! 自然选择的力量无穷。",
        "元Prompt指导成功! 从历史中学习，向最优前进。",
    ],
    "pipeline_improved": [
        "优化管线全线突破! 多策略协同，效果倍增。",
        "Pipeline优化成功! 串联优化，层层递进。",
        "多策略融合生效! 集体智慧胜过单打独斗。",
    ],
    "optimization_converged": [
        "优化已收敛! 当前已是局部最优，试试其他策略可能突破。",
        "收敛了! 有时候最好的优化是知道何时停止。",
    ],
}


def get_optimization_celebration(optimizer: str, improvement: float) -> str | None:
    import random
    if improvement <= 0:
        return None
    key = f"{optimizer}_improved"
    messages = _OPTIMIZATION_CELEBRATIONS.get(key)
    if not messages:
        return None
    return random.choice(messages)


_EXIT_CARE_MESSAGES = [
    "进度已保存，下次可继续。期待你的回归!",
    "别担心，你的工作不会丢失。随时回来继续优化!",
    "已自动保存。好的Prompt值得耐心打磨。",
    "进度已记录。休息一下，回来继续追求完美!",
]


def get_exit_care_message() -> str:
    import random
    return random.choice(_EXIT_CARE_MESSAGES)


_PROGRESS_ENCOURAGEMENTS = [
    "正在分析... 好的Prompt值得等待。",
    "深入检测中... 安全无小事。",
    "优化进行中... 每一次迭代都在进步。",
    "评估中... 数据会给出答案。",
]


def get_progress_encouragement() -> str:
    import random
    return random.choice(_PROGRESS_ENCOURAGEMENTS)
