"""安全扫描引擎。"""

from ai_prompt_toolkit.security.types import (
    Finding,
    InheritanceFinding,
    InjectionRule,
    RiskLevel,
    ScanResult,
)
from ai_prompt_toolkit.security.injection_detector import InjectionDetector
from ai_prompt_toolkit.security.inheritance_auditor import (
    DictTemplateProvider,
    InheritanceAuditor,
    TemplateProvider,
)
from ai_prompt_toolkit.security.scanner import Scanner
from ai_prompt_toolkit.security.engine import FusionEngine, EngineResult, LayerResult
from ai_prompt_toolkit.security.badge import generate_scorecard_badge, generate_score_svg, Theme


def scan_template(
    template_id: str,
    text: str,
    provider: TemplateProvider | None = None,
    *,
    incremental: bool = False,
) -> ScanResult:
    """SDK 便捷入口：扫描单个模板。"""
    if provider is None:
        provider = DictTemplateProvider({})
    scanner = Scanner(provider)
    return scanner.scan(template_id, text, incremental=incremental)
