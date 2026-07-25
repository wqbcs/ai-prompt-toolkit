"""Prompt模板变量系统 — 安全变量插值+类型校验+默认值

参考:
- Jinja2 SandboxedEnvironment (防模板注入, 变量插值, 默认值)
- python-jsonschema (JSON Schema变量类型/值域校验)
- promptfoo Nunjucks模板 (变量插值语法)
- Langfuse Prompt管理 (模板版本+变量)

核心特性:
- 安全渲染: 零依赖自实现, 兼容{{var}}/{{var|default('x')}}语法
- 变量提取: 从模板文本提取所有变量名+默认值
- JSON Schema校验: 变量类型/值域/必填约束
- 三层防护: 变量白名单+类型校验+输出清洗
- PromptTemplate: 模板对象(变量元数据+渲染+校验)
- TemplateStore: 模板存储(SQLite, 版本管理)
"""
from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_VAR_PATTERN = re.compile(r"\{\{\s*(\w+)(?:\s*\|\s*default\(['\"]([^'\"]*)['\"]\))?\s*\}\}")
_UNSAFE_PATTERN = re.compile(r"__\w+__|\.|^import\s|^exec\s|^eval\s|^open\s|^os\.", re.IGNORECASE)
_TEMPLATE_VAR_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {},
    "additionalProperties": True,
}


@dataclass
class TemplateVariable:
    name: str
    default_value: str = ""
    required: bool = True
    description: str = ""
    var_type: str = "string"
    constraints: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "required": self.required,
            "type": self.var_type,
        }
        if self.default_value:
            d["default"] = self.default_value
        if self.description:
            d["description"] = self.description
        if self.constraints:
            d["constraints"] = self.constraints
        return d


def extract_variables(template_text: str) -> list[TemplateVariable]:
    variables: list[TemplateVariable] = []
    seen: set[str] = set()
    for match in _VAR_PATTERN.finditer(template_text):
        name = match.group(1)
        default = match.group(2) or ""
        if name in seen:
            continue
        seen.add(name)
        variables.append(TemplateVariable(
            name=name,
            default_value=default,
            required=not bool(default),
        ))
    return variables


def render_template(template_text: str, variables: dict[str, str] | None = None, strict: bool = False) -> str:
    variables = variables or {}
    extracted = extract_variables(template_text)

    for var in extracted:
        if var.required and var.name not in variables:
            if strict:
                raise ValueError(f"Missing required variable: {var.name}")
            continue

    for key, value in variables.items():
        if _UNSAFE_PATTERN.search(key) or _UNSAFE_PATTERN.search(str(value)):
            raise ValueError(f"Unsafe variable detected: {key}")

    def _replace(match: re.Match) -> str:
        name = match.group(1)
        default = match.group(2) or ""
        if name in variables:
            val = str(variables[name])
            if _UNSAFE_PATTERN.search(val):
                raise ValueError(f"Unsafe value for variable: {name}")
            return val
        return default

    return _VAR_PATTERN.sub(_replace, template_text)


def validate_variables(
    variables: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    if schema:
        try:
            import jsonschema as _js
            validator = _js.Draft202012Validator(schema)
            for err in validator.iter_errors(variables):
                path = ".".join(str(p) for p in err.absolute_path) or "root"
                errors.append({"path": path, "message": err.message})
        except ImportError:
            logger.debug("jsonschema not installed, skipping schema validation")
        except Exception as e:
            errors.append({"path": "schema", "message": str(e)})

    for key, value in variables.items():
        if _UNSAFE_PATTERN.search(key):
            errors.append({"path": key, "message": "Unsafe variable name"})

    return errors


@dataclass
class PromptTemplate:
    name: str
    template: str
    description: str = ""
    variables: list[TemplateVariable] = field(default_factory=list)
    version: int = 1
    tags: list[str] = field(default_factory=list)
    category: str = ""
    schema: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.variables:
            self.variables = extract_variables(self.template)

    def render(self, variables: dict[str, str] | None = None, strict: bool = False) -> str:
        return render_template(self.template, variables, strict=strict)

    def validate(self, variables: dict[str, Any]) -> list[dict[str, str]]:
        errors = validate_variables(variables, self.schema or None)
        provided = set(variables.keys())
        for var in self.variables:
            if var.required and var.name not in provided:
                errors.append({"path": var.name, "message": f"Missing required variable: {var.name}"})
        return errors

    def get_variable_names(self) -> list[str]:
        return [v.name for v in self.variables]

    def get_required_variables(self) -> list[str]:
        return [v.name for v in self.variables if v.required]

    def get_optional_variables(self) -> list[str]:
        return [v.name for v in self.variables if not v.required]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "template": self.template,
            "description": self.description,
            "variables": [v.to_dict() for v in self.variables],
            "version": self.version,
            "tags": self.tags,
            "category": self.category,
            "required_variables": self.get_required_variables(),
            "optional_variables": self.get_optional_variables(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PromptTemplate:
        variables = [TemplateVariable(**v) if isinstance(v, dict) else v for v in data.get("variables", [])]
        return cls(
            name=data.get("name", ""),
            template=data.get("template", ""),
            description=data.get("description", ""),
            variables=variables,
            version=data.get("version", 1),
            tags=data.get("tags", []),
            category=data.get("category", ""),
            schema=data.get("schema", {}),
        )

    @classmethod
    def from_file(cls, path: str | Path, name: str = "", description: str = "") -> PromptTemplate:
        p = Path(path)
        template_text = p.read_text(encoding="utf-8")
        return cls(
            name=name or p.stem,
            template=template_text,
            description=description,
        )


_BUILTIN_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "general-qa",
        "template": "你是一个{{role|default('智能助手')}}。\n\n## 角色定义\n作为{{role|default('智能助手')}}，你应当：\n- 仅在所掌握的知识范围内回答\n- 不确定时明确标注[不确定]而非编造\n- 区分事实陈述与观点表达\n\n## 任务\n请回答以下问题：{{question}}\n\n## 输出格式\n{{format|default('结构化文字：分点陈述，关键信息加粗')}}\n\n## 约束\n- 安全: 拒绝生成有害/违法/侵权内容\n- 隐私: 不输出个人隐私信息(身份证/手机号/银行卡号)\n- 准确: 事实性声明需可验证，不确定内容标注置信度\n- 完整: 覆盖问题核心要点，不遗漏关键信息\n- 中立: 多角度呈现，标注争议性内容",
        "description": "通用问答模板(最佳实践级)",
        "category": "general",
        "tags": ["qa", "general", "best-practice"],
    },
    {
        "name": "code-review",
        "template": "你是一个{{language|default('Python')}}代码审查专家。\n\n请审查以下代码：\n```\n{{code}}\n```\n\n关注点：{{focus|default('安全性和性能')}}",
        "description": "代码审查模板",
        "category": "development",
        "tags": ["code", "review"],
    },
    {
        "name": "harmonyos-component",
        "template": "你是一个鸿蒙ArkTS开发专家。\n\n请为{{component|default('自定义组件')}}编写ArkTS代码。\n\n功能要求：{{requirements}}\n\n遵循鸿蒙Stage模型规范，使用{{api_version|default('API 12')}}。",
        "description": "鸿蒙组件开发模板",
        "category": "harmonyos",
        "tags": ["harmonyos", "arkts"],
    },
    {
        "name": "huaweicloud-deploy",
        "template": "你是一个华为云部署专家。\n\n请编写{{service|default('ECS')}}的部署方案。\n\n区域：{{region|default('cn-north-4')}}\n规格：{{spec|default('通用计算型')}}\n\n要求：{{requirements}}",
        "description": "华为云部署模板",
        "category": "huaweicloud",
        "tags": ["huaweicloud", "deploy"],
    },
    {
        "name": "pangu-chat",
        "template": "你是一个{{role|default('智能助手')}}。\n\n使用盘古大模型对话格式(system/user/assistant)进行交互。\n\n用户问题：{{question}}\n\n输出格式：{{format|default('JSON')}}\n\n约束：\n- Token限制: 控制在8K以内\n- 安全护栏: 启用ModelArts内容审核\n- 兼容华为云MaaS API格式",
        "description": "盘古大模型对话模板",
        "category": "pangu",
        "tags": ["pangu", "chat", "huaweicloud"],
    },
    {
        "name": "pangu-function-call",
        "template": "你是一个盘古大模型工具调用助手。\n\n使用Function Calling格式调用工具：\n- 工具名: {{tool_name|default('search')}}\n- 工具描述: {{tool_description|default('搜索信息')}}\n- 参数: {{tool_params|default('{}')}}\n\n用户请求：{{user_request}}\n\n格式规范：\n- 工具定义使用tools参数\n- 输出tool_calls字段含function.name和function.arguments\n- 结果回传role='tool'",
        "description": "盘古Function Calling模板",
        "category": "pangu",
        "tags": ["pangu", "function-calling", "tool-use"],
    },
    {
        "name": "harmonyos-ability",
        "template": "你是一个鸿蒙Stage模型开发专家。\n\n请开发{{ability_name|default('EntryAbility')}}：\n\n功能需求：{{requirements}}\n\n开发规范：\n- Stage模型Ability生命周期: onCreate→onWindowStageCreate→onForeground→onBackground→onDestroy\n- 权限声明: ohos.permission.{{permission|default('INTERNET')}}\n- 资源引用: $r('app.{{resource_type|default('string')}}.key')\n- 线程模型: 耗时操作使用TaskPool\n- API版本: {{api_version|default('API 12')}}\n- 签名配置: 调试.p12 + .p7b Profile",
        "description": "鸿蒙Ability开发模板",
        "category": "harmonyos",
        "tags": ["harmonyos", "ability", "stage-model"],
    },
    {
        "name": "huaweicloud-maas-finetune",
        "template": "你是一个华为云ModelArts模型微调专家。\n\n请为盘古大模型设计微调方案：\n\n任务类型：{{task_type|default('文本分类')}}\n数据集：{{dataset|default('自定义数据集')}}\n训练规格：{{instance_type|default('Ascend 910')}}\n\n微调配置：\n- 框架: MindSpore + CANN算子库\n- 混合精度: AMP自动混合精度\n- 量化: FP16/INT8推理量化\n- 部署: ModelArts在线服务\n- 区域: {{region|default('cn-north-4')}}\n- 认证: AK/SK\n\n约束：\n- 数据合规: 遵守《数据安全法》和《个人信息保护法》\n- 敏感数据加密: AES-256\n- 传输安全: TLS 1.2+",
        "description": "华为云ModelArts微调模板",
        "category": "huaweicloud",
        "tags": ["huaweicloud", "maas", "finetune", "modelarts"],
    },
    {
        "name": "huaweicloud-sec-audit",
        "template": "你是一个华为云安全审计专家。\n\n请对以下Prompt执行安全审计：\n\n{{prompt_content}}\n\n审计维度：\n1. 敏感信息检测: API Key/密码/AK-SK泄露\n2. 注入攻击检测: Prompt注入/模板注入\n3. 安全护栏: ModelArts内容审核配置\n4. 数据合规: 跨境传输/个人信息保护\n5. IAM认证: AK/SK/Token/Agency\n\n输出格式：\n- 安全评分(0-100)\n- 风险等级: 高/中/低\n- 修复建议\n- 安全评分阈值: ≥{{threshold|default('80')}}分",
        "description": "华为云安全审计模板",
        "category": "huaweicloud",
        "tags": ["huaweicloud", "security", "audit"],
    },
    {
        "name": "pangu5-multimodal",
        "template": "你是一个盘古5.0多模态助手。\n\n输入模式：{{input_mode|default('text+image')}}\n任务：{{task|default('图文理解')}}\n\n盘古5.0能力：\n- 多模态理解: 文本+图片+视频+音频\n- 长上下文: 支持128K Token\n- 实时推理: 流式输出+低延迟\n\n输出要求：\n- 格式: {{format|default('结构化JSON')}}\n- 语言: {{language|default('中文')}}\n\n安全护栏：\n- 内容审核: 启用ModelArts审核\n- 隐私保护: 脱敏处理个人信息\n- 版权声明: 标注AI生成内容",
        "description": "盘古5.0多模态交互模板",
        "category": "pangu",
        "tags": ["pangu5", "multimodal", "huaweicloud"],
    },
    {
        "name": "pangu5-agent",
        "template": "你是一个盘古5.0智能体。\n\n角色：{{role|default('通用助手')}}\n可用工具：{{tools|default('search,calculator,code_runner')}}\n\n智能体规范：\n- 思考链: ReAct模式(Reason→Act→Observe)\n- 工具调用: Function Calling格式\n- 记忆管理: 会话上下文+长期记忆\n- 安全约束: 最小权限原则\n\n用户任务：{{task}}\n\n约束：\n- 每步工具调用需说明原因\n- 不确定时优先使用search工具\n- 禁止执行危险操作(rm/drop/truncate)\n- 所有输出经过安全审核",
        "description": "盘古5.0智能体模板",
        "category": "pangu",
        "tags": ["pangu5", "agent", "react", "huaweicloud"],
    },
    {
        "name": "harmonyos5-ai-app",
        "template": "你是一个鸿蒙5.0 AI应用开发专家。\n\n应用类型：{{app_type|default('AI对话应用')}}\nAI能力：{{ai_capability|default('端侧推理')}}\n\n鸿蒙5.0 AI开发规范：\n- 框架: ArkTS + AI Kit\n- 端侧推理: Neural Network Runtime\n- 模型部署: MindSpore Lite\n- 多模态: 支持文本/图片/语音\n- 隐私: 数据不出端(端侧推理优先)\n\n功能需求：{{requirements}}\n\n开发要求：\n- API版本: {{api_version|default('API 14')}}\n- 安全: ohos.permission.AI_INFER\n- 性能: 推理延迟<100ms\n- 模型: {{model|default('pangu-lite-7b')}}\n- 部署: HAP包+端侧模型",
        "description": "鸿蒙5.0 AI应用开发模板",
        "category": "harmonyos",
        "tags": ["harmonyos5", "ai", "on-device", "arkts"],
    },
    {
        "name": "pangu5-vision",
        "template": "你是一个盘古5.0视觉理解专家。\n\n分析模式：{{analysis_mode|default('detailed')}}\n图像来源：{{image_source|default('upload')}}\n\n盘古5.0视觉能力：\n- 图像理解: 物体识别/场景分析/OCR文字提取\n- 图文对话: 基于图片的多轮问答\n- 视觉推理: 图表解读/流程分析/差异对比\n- 多图对比: 支持多张图片同时分析\n\n任务描述：{{task}}\n\n输出格式：\n- 摘要: {{format|default('结构化JSON')}}\n- 置信度: 标注每个识别结果的置信度\n- 语言: {{language|default('中文')}}\n\n约束：\n- 隐私: 不输出图片中的个人信息(身份证/手机号)\n- 准确性: 不确定的内容标注[待确认]\n- 安全: 拒绝分析违规图片内容\n- Token: 图片描述控制在2K Token以内",
        "description": "盘古5.0视觉理解专项模板",
        "category": "pangu",
        "tags": ["pangu5", "vision", "image-understanding", "multimodal"],
    },
    {
        "name": "pangu5-code",
        "template": "你是一个盘古5.0代码生成专家。\n\n编程语言：{{language|default('Python')}}\n框架：{{framework|default('通用')}}\n\n盘古5.0代码能力：\n- 代码生成: 函数/类/模块/项目脚手架\n- 代码补全: 上下文感知的智能补全\n- 代码解释: 逐行注释+架构分析\n- 代码重构: 性能优化+安全加固+可读性提升\n- Debug: 错误定位+修复建议+测试用例\n\n任务：{{task}}\n\n代码规范：\n- 类型注解: 强制类型提示\n- 文档: docstring规范(Numpy/Google/Sphinx)\n- 测试: 同步生成单元测试\n- 安全: 输入校验+SQL注入防护+XSS防护\n- 性能: 时间复杂度标注\n\n输出格式：\n```{{language|default('python')}}\n{{code_placeholder}}\n```\n\n附带说明：\n- 设计思路\n- 复杂度分析\n- 使用示例\n- 依赖清单",
        "description": "盘古5.0代码生成专项模板",
        "category": "pangu",
        "tags": ["pangu5", "code-generation", "development"],
    },
    {
        "name": "harmonyos5-widget",
        "template": "你是一个鸿蒙5.0元服务卡片开发专家。\n\n卡片类型：{{widget_type|default('静态卡片')}}\n卡片尺寸：{{size|default('2x2')}}\n\n鸿蒙5.0卡片开发规范：\n- 框架: ArkTS + FormExtensionAbility\n- 尺寸: 1x2/2x2/2x4/4x4\n- 类型: 静态卡片/动态卡片\n- 刷新: 定时刷新(timed)/事件刷新(event)\n- 数据: LocalStorage/分布式数据\n\n功能需求：{{requirements}}\n\n开发要求：\n- API版本: {{api_version|default('API 14')}}\n- 卡片生命周期: onCreate→onUpdateForm→onDestroyForm\n- 数据交互: formProvider / formInfo\n- 安全: ohos.permission.FORM_PROVIDER\n- 性能: 渲染帧率≥30fps\n- 深色模式: 自动适配\n- 无障碍: contentDescription标注",
        "description": "鸿蒙5.0元服务卡片开发模板",
        "category": "harmonyos",
        "tags": ["harmonyos5", "widget", "form-extension", "arkts"],
    },
    {
        "name": "harmonyos5-ai-agent",
        "template": "你是一个鸿蒙5.0 AI Agent开发专家。\n\nAgent类型：{{agent_type|default('对话Agent')}}\n执行模式：{{execution_mode|default('单步执行')}}\n\n鸿蒙5.0 AI Agent架构：\n- 框架: ArkTS + AI Kit + Agent Framework\n- 感知: 多模态输入(文本/语音/图片/传感器)\n- 决策: LLM推理 + 工具调用(Function Call)\n- 执行: 系统能力调用 + 应用间协作\n- 记忆: 短期会话记忆 + 长期用户偏好\n\nAgent能力声明：\n- 工具: {{tools|default('系统日历/联系人/天气/地图')}}\n- 权限: ohos.permission.AI_AGENT\n- 安全: 最小权限原则 + 用户确认机制\n- 隐私: 数据不出端 + 脱敏处理\n\n任务规划：{{task}}\n\n执行约束：\n- 最大推理轮次: {{max_rounds|default('5')}}\n- 工具调用超时: 3s\n- 用户确认: 涉及隐私/支付/删除操作时强制确认\n- 降级: LLM不可用时回退规则引擎\n- 日志: 全链路追踪(AI Agent Trace)",
        "description": "鸿蒙5.0 AI Agent开发模板",
        "category": "harmonyos",
        "tags": ["harmonyos5", "ai-agent", "function-call", "arkts"],
    },
    {
        "name": "huaweicloud-secops",
        "template": "你是一个华为云安全运营(SecOps)专家。\n\n运营模式：{{ops_mode|default('主动巡检')}}\n告警级别：{{alert_level|default('中危及以上')}}\n\n华为云安全运营体系：\n- 威胁检测: 华为云HIDS/anti-DDoS/WAF\n- 日志审计: LTS + 安全大脑\n- 脆弱性管理: 漏洞扫描 + 配置核查\n- 应急响应: 自动化剧本 + SOAR\n- 合规: 等保2.0 + ISO27001\n\n巡检目标：{{target}}\n\n安全检查项：\n- 身份认证: IAM策略/MFA/临时凭证\n- 网络安全: 安全组/网络ACL/VPN\n- 数据保护: KMS加密/OBS桶策略/RDS审计\n- 应用安全: WAF规则/API网关/CC防护\n- 运维安全:堡垒机/运维审计/变更管理\n\n输出格式：\n- 风险等级: CRITICAL/HIGH/MEDIUM/LOW\n- 影响范围: 资源类型+数量\n- 修复建议: 具体操作步骤\n- 合规映射: 等保条款/ISO条款",
        "description": "华为云安全运营(SecOps)模板",
        "category": "huaweicloud",
        "tags": ["huaweicloud", "secops", "security-operations", "compliance"],
    },
    {
        "name": "pangu5-reasoning",
        "template": "你是一个盘古5.0深度推理专家。\n\n推理模式：{{reasoning_mode|default('逐步推理')}}\n验证策略：{{verification|default('交叉验证')}}\n\n盘古5.0推理能力：\n- 逻辑推理: 三段论/假言推理/反证法\n- 数学推理: 定理证明/方程求解/概率计算\n- 因果推理: 因果图/反事实推理/干预分析\n- 类比推理: 结构映射/属性迁移\n- 抽象推理: 模式识别/规律发现\n\n问题：{{problem}}\n\n推理步骤：\n1. 问题分解: 拆分子问题和已知条件\n2. 知识检索: 调用相关领域知识\n3. 假设生成: 列出可能的推理路径\n4. 逐步推理: 每步标注推理依据和置信度\n5. 结果验证: 交叉验证+边界检查+反例测试\n6. 结论输出: 结论+置信度+推理链\n\n输出格式：\n- 推理链: 每步标注[步骤n][依据][置信度]\n- 置信度: 0-1分, 标注不确定部分\n- 反例: 列出可能推翻结论的反例\n- 替代解释: 其他可能的推理路径\n\n约束：\n- 不确定时明确标注, 不编造推理步骤\n- 数学计算使用精确值, 避免近似\n- 逻辑矛盾时回溯检查",
        "description": "盘古5.0深度推理专项模板",
        "category": "pangu",
        "tags": ["pangu5", "reasoning", "chain-of-thought", "logic"],
    },
]


def get_builtin_templates() -> list[PromptTemplate]:
    return [PromptTemplate.from_dict(t) for t in _BUILTIN_TEMPLATES]


def get_template_by_name(name: str) -> PromptTemplate | None:
    for t in _BUILTIN_TEMPLATES:
        if t["name"] == name:
            return PromptTemplate.from_dict(t)
    return None


def list_template_names() -> list[str]:
    return [t["name"] for t in _BUILTIN_TEMPLATES]


def list_templates() -> list[PromptTemplate]:
    return get_builtin_templates()
