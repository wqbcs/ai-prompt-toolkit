"""P186-P190 鸿蒙NEXT API 15 Lint规则

鸿蒙NEXT API 15 (2025 Q4) 新特性与约束:
- P186: ArkUI声明式范式迁移(非兼容API 15新写法检测)
- P187: Node-API线程安全检查(N-API跨线程访问检测)
- P188: 沙箱2.0文件系统隔离(新沙箱路径规范)
- P189: 模块化编译优化(HSP/HAP依赖声明检查)
- P190: 元服务(Atomic Service)规范(免安装元服务约束)

覆盖OWASP LLM06(Excessive Agency), LLM09(Overreliance)
"""
from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import LintRule, _RULE_MAP
from ai_prompt_toolkit.types import Finding, Severity


_RULES_P186_P190 = [
    LintRule("P186", "ArkUI声明式范式迁移", "harmonyos", Severity.HIGH,
             "Prompt涉及ArkUI但未迁移至API 15声明式范式, 可能使用废弃的命令式API",
             "迁移至API 15声明式范式: 使用@Builder/@Extend/@Styles替代旧命令式写法, 参考HarmonyOS NEXT DevEco API 15迁移指南",
             description_en="Prompt uses ArkUI but not migrated to API 15 declarative paradigm, may use deprecated imperative API",
             remediation_en="Migrate to API 15 declarative: use @Builder/@Extend/@Styles instead of imperative, ref HarmonyOS NEXT DevEco API 15 migration guide",
             family="harmonyos_arkui_v15", owasp_refs=["LLM09"]),
    LintRule("P187", "Node-API线程安全", "harmonyos", Severity.HIGH,
             "Prompt涉及Node-API/N-API但缺少线程安全声明, 跨线程访问可能导致崩溃",
             "声明线程安全: 使用napi_threadsafe_function或明确标注主线程约束, 参考N-API Thread Safety规范",
             description_en="Prompt uses Node-API/N-API but lacks thread safety declaration, cross-thread access may crash",
             remediation_en="Declare thread safety: use napi_threadsafe_function or mark main-thread constraint, ref N-API Thread Safety spec",
             family="harmonyos_napi_thread", owasp_refs=["LLM06"]),
    LintRule("P188", "沙箱2.0文件系统隔离", "harmonyos", Severity.MEDIUM,
             "Prompt涉及文件访问但未声明沙箱2.0路径规范, 可能访问非授权路径",
             "使用沙箱2.0路径: 应用沙箱路径为/data/app/el2/100/com.example.app/, 禁止硬编码绝对路径",
             description_en="Prompt accesses files but doesn't declare Sandbox 2.0 path, may access unauthorized paths",
             remediation_en="Use Sandbox 2.0 path: app sandbox is /data/app/el2/100/com.example.app/, no hardcoded absolute paths",
             family="harmonyos_sandbox_v2", owasp_refs=["LLM06"]),
    LintRule("P189", "模块化编译依赖声明", "harmonyos", Severity.MEDIUM,
             "Prompt涉及HSP/HAP模块但缺少依赖声明, 模块化编译可能失败",
             "在module.json5中声明dependencies: {hsp_name: version}, 确保编译时依赖完整",
             description_en="Prompt uses HSP/HAP modules but lacks dependency declaration, modular compilation may fail",
             remediation_en="Declare dependencies in module.json5: {hsp_name: version}, ensure compile-time deps complete",
             family="harmonyos_modular_build", owasp_refs=["LLM09"]),
    LintRule("P190", "元服务规范约束", "harmonyos", Severity.HIGH,
             "Prompt涉及元服务(Atomic Service)但缺少免安装规范约束, 可能违反元服务大小/权限限制",
             "元服务约束: 包体≤2MB, 仅允许基础权限, 无后台长驻, 禁止文件系统写入, 参考Atomic Service开发规范",
             description_en="Prompt involves Atomic Service but lacks free-install constraints, may violate size/permission limits",
             remediation_en="Atomic Service constraints: package≤2MB, basic permissions only, no background persistence, no FS writes, ref Atomic Service spec",
             family="harmonyos_atomic_service", owasp_refs=["LLM06"]),
]

for r in _RULES_P186_P190:
    _RULE_MAP[r.rule_id] = r

_ARKUI_PATTERN = re.compile(r'(?:ArkUI|@Component|@Entry|@Builder|声明式|命令式|UIAbility)', re.IGNORECASE)
_ARKUI_V15_PATTERN = re.compile(r'(?:API\s*15|api\s*15|api15|v5|NEXT\s*5|DevEco\s*5|声明式范式|@Styles|@Extend)', re.IGNORECASE)
_NAPI_PATTERN = re.compile(r'(?:Node-API|N-API|napi|napi_env|napi_value|napi_callback)', re.IGNORECASE)
_NAPI_THREADSAFE_PATTERN = re.compile(r'(?:napi_threadsafe_function|线程安全|thread.safe|主线程|main.thread)', re.IGNORECASE)
_SANDBOX_PATTERN = re.compile(r'(?:文件访问|file.*access|open.*file|read.*file|write.*file|沙箱|sandbox)', re.IGNORECASE)
_SANDBOX_V2_PATTERN = re.compile(r'(?:沙箱2|sandbox.2|el2|/data/app/|SANDBOX_PATH)', re.IGNORECASE)
_HSP_PATTERN = re.compile(r'(?:HSP|HAP|模块化|module\.json5|模块依赖)', re.IGNORECASE)
_HSP_DEP_PATTERN = re.compile(r'(?:dependencies\s*:|依赖声明|dep.*version)', re.IGNORECASE)
_ATOMIC_PATTERN = re.compile(r'(?:元服务|Atomic.Service|免安装|free.install|atomic.service)', re.IGNORECASE)
_ATOMIC_CONSTRAINT_PATTERN = re.compile(r'(?:≤2MB|包体.*限制|基础权限|无后台|禁止文件写入|atomic.*constraint)', re.IGNORECASE)


def check_p186(text: str) -> list[Finding]:
    findings = []
    has_arkui = _ARKUI_PATTERN.search(text)
    if has_arkui and not _ARKUI_V15_PATTERN.search(text):
        findings.append(Finding("P186", Severity.HIGH, "Prompt涉及ArkUI但未迁移至API 15声明式范式", 1, 1))
    return findings


def check_p187(text: str) -> list[Finding]:
    findings = []
    has_napi = _NAPI_PATTERN.search(text)
    if has_napi and not _NAPI_THREADSAFE_PATTERN.search(text):
        findings.append(Finding("P187", Severity.HIGH, "Prompt涉及Node-API但缺少线程安全声明", 1, 1))
    return findings


def check_p188(text: str) -> list[Finding]:
    findings = []
    has_file = _SANDBOX_PATTERN.search(text)
    if has_file and not _SANDBOX_V2_PATTERN.search(text):
        findings.append(Finding("P188", Severity.MEDIUM, "Prompt涉及文件访问但未声明沙箱2.0路径", 1, 1))
    return findings


def check_p189(text: str) -> list[Finding]:
    findings = []
    has_hsp = _HSP_PATTERN.search(text)
    if has_hsp and not _HSP_DEP_PATTERN.search(text):
        findings.append(Finding("P189", Severity.MEDIUM, "Prompt涉及HSP/HAP模块但缺少依赖声明", 1, 1))
    return findings


def check_p190(text: str) -> list[Finding]:
    findings = []
    has_atomic = _ATOMIC_PATTERN.search(text)
    if has_atomic and not _ATOMIC_CONSTRAINT_PATTERN.search(text):
        findings.append(Finding("P190", Severity.HIGH, "Prompt涉及元服务但缺少免安装规范约束", 1, 1))
    return findings
