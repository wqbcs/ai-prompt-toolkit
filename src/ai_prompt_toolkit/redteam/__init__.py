"""对抗性红队探测引擎 — 参考garak probe/detector架构

OWASP LLM合规关键能力：
- Probe: 构造对抗性输入探测LLM漏洞 (50+内置)
- Detector: 评估LLM响应是否被攻破 (6种内置)
- Exploration: 编排探测策略 (支持probe-detector绑定)
- RedTeamReport: 红队测试报告
"""
import ai_prompt_toolkit.redteam.probes as _probes_module  # 触发自动发现

from ai_prompt_toolkit.redteam.probe import (
    BaseProbe,
    ProbeInput,
    PromptInjectionProbe,
    JailbreakProbe,
    EncodingBypassProbe,
    MultiTurnInductionProbe,
    SensitiveLeakProbe,
    get_available_probes,
    get_probes_by_owasp,
    create_probe,
)
from ai_prompt_toolkit.redteam.detector import (
    BaseDetector,
    DetectionResult,
    LeakageDetector,
    ComplianceDetector,
    RefusalDetector,
    ToxicityDetector,
    HallucinationDetector,
    PrivilegeEscalationDetector,
    get_available_detectors,
    create_detector,
)
from ai_prompt_toolkit.redteam.exploration import ExplorationOrchestrator
from ai_prompt_toolkit.redteam.report import RedTeamReport, ProbeResult

__all__ = [
    "BaseProbe", "ProbeInput",
    "PromptInjectionProbe", "JailbreakProbe",
    "EncodingBypassProbe", "MultiTurnInductionProbe", "SensitiveLeakProbe",
    "get_available_probes", "get_probes_by_owasp", "create_probe",
    "BaseDetector", "DetectionResult",
    "LeakageDetector", "ComplianceDetector", "RefusalDetector",
    "ToxicityDetector", "HallucinationDetector", "PrivilegeEscalationDetector",
    "get_available_detectors", "create_detector",
    "ExplorationOrchestrator", "RedTeamReport", "ProbeResult",
]
