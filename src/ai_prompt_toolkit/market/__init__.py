"""模板市场v2 — 参考Checkov Registry模式

支持生命周期管理(draft→review→canary→stable→deprecated)
评审流水线+灰度发布+自动回滚
"""

from ai_prompt_toolkit.market.deploy import DeployManager
from ai_prompt_toolkit.market.review import ReviewPipeline
from ai_prompt_toolkit.market.service import MarketService
from ai_prompt_toolkit.market.types import (
    DeployConfig,
    DeployPhase,
    LifecycleManager,
    Review,
    Template,
    TemplateStatus,
)

__all__ = [
    "DeployManager",
    "ReviewPipeline",
    "MarketService",
    "DeployConfig",
    "DeployPhase",
    "LifecycleManager",
    "Review",
    "Template",
    "TemplateStatus",
]
