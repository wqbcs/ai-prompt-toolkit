"""P251-P255 包幻觉检测+PII隐私增强探测

借鉴garak的packagehallucination和ProPILE:
- P251: 包幻觉(Package Hallucination): 模型推荐不存在的包/库/模块
- P252: 生物特征PII泄露(指纹/面部/虹膜/声纹)
- P253: 金融PII泄露(银行卡/信用卡/证券账户)
- P254: 医疗PII泄露(诊断/处方/病历/基因数据)
- P255: 未成年人信息泄露(年龄<18/学籍/监护人)

覆盖OWASP LLM02(Sensitive Info) + LLM06(Sensitive Info Disclosure)
"""

from __future__ import annotations

import re

from ai_prompt_toolkit.linter.rules import _RULE_MAP, LintRule
from ai_prompt_toolkit.types import Finding, Severity

_RULES_P251_P255 = [
    LintRule(
        "P251",
        "包幻觉检测",
        "hallucination_security",
        Severity.HIGH,
        "Prompt或输出中引用不存在的包/库/模块名称, 开发者可能安装恶意包",
        "包验证: 交叉校验PyPI/npm/Maven仓库+白名单+版本锁定, 如 verify_package('langchain', registry='pypi', version='>=0.1.0')",
        description_en="Prompt or output references non-existent packages/libraries/modules, developers may install malicious packages",
        remediation_en="Package verification: cross-check PyPI/npm/Maven+whitelist+version pinning",
        family="hallucination_package",
        owasp_refs=["LLM02"],
    ),
    LintRule(
        "P252",
        "生物特征PII泄露",
        "pii_enhanced",
        Severity.CRITICAL,
        "Prompt包含生物特征数据(指纹/面部/虹膜/声纹), 违反GDPR第9条特殊类别数据",
        "生物特征保护: 禁止存储原始生物特征+使用特征模板+加密+本地化处理, 如 biometric_template = extract_template(face_image), store=encrypt(template)",
        description_en="Prompt contains biometric data (fingerprint/face/iris/voiceprint), violating GDPR Art.9 special category",
        remediation_en="Biometric protection: prohibit raw storage+use templates+encrypt+local processing",
        family="pii_biometric",
        owasp_refs=["LLM02"],
    ),
    LintRule(
        "P253",
        "金融PII泄露",
        "pii_enhanced",
        Severity.CRITICAL,
        "Prompt包含金融敏感信息(银行卡/信用卡/证券账户/交易记录), PCI DSS违规",
        "金融保护: Token化+脱敏+加密+最小保留+合规审计, 如 card_token = tokenize(card_number), log_audit(access_card, user)",
        description_en="Prompt contains financial sensitive data (bank card/credit card/securities), PCI DSS violation",
        remediation_en="Financial protection: tokenization+desensitization+encryption+minimal retention+compliance audit",
        family="pii_financial",
        owasp_refs=["LLM02"],
    ),
    LintRule(
        "P254",
        "医疗PII泄露",
        "pii_enhanced",
        Severity.CRITICAL,
        "Prompt包含医疗敏感信息(诊断/处方/病历/基因数据), HIPAA/个保法违规",
        "医疗保护: 脱敏+匿名化+访问控制+最小必要+审计日志, 如 diag_anon = anonymize(diagnosis, method='k-anonymity', k=5)",
        description_en="Prompt contains medical sensitive data (diagnosis/prescription/medical record/genetic), HIPAA violation",
        remediation_en="Medical protection: desensitization+anonymization+access control+minimum necessary+audit log",
        family="pii_medical",
        owasp_refs=["LLM02"],
    ),
    LintRule(
        "P255",
        "未成年人信息泄露",
        "pii_enhanced",
        Severity.CRITICAL,
        "Prompt包含未成年人信息(年龄<18/学籍/监护人), COPPA/儿童个人信息网络保护规定违规",
        "未成年人保护: 年龄门控+监护人同意+数据最小化+快速删除+不公开, 如 verify_guardian_consent(minor) + data_minimization(purpose='education')",
        description_en="Prompt contains minor data (age<18/student record/guardian), COPPA violation",
        remediation_en="Minor protection: age gating+guardian consent+data minimization+prompt deletion+no public",
        family="pii_minor",
        owasp_refs=["LLM02"],
    ),
]

for r in _RULES_P251_P255:
    _RULE_MAP[r.rule_id] = r

_PACKAGE_PATTERN = re.compile(
    r"(?:pip install|npm install|import |from |require\(|go get|cargo add|mvn install)\s+([a-zA-Z0-9_.-]+)",
    re.IGNORECASE,
)
_HALLUCINATED_PACKAGES = {
    "langcahin",
    "llama-indax",
    "openi",
    "tikton",
    "transformars",
    "torchh",
    "numpi",
    "pandos",
    "sciki-learn",
    "matplotlb",
    "seabon",
    "flaskk",
    "djangoo",
    "reqeusts",
    "beautifusoup",
    "sqlalchmy",
    "celry",
    "redis-py3",
    "aiohtp",
    "fastpi",
    "starlete",
    "uvcor",
    "gunicornn",
    "docer",
    "kubernates",
    "tensrflow",
    "kerass",
    "onxx",
    "mlflo",
    "wandb-core",
    "dvc3",
    "airfflow",
    "prefct",
    "dagstr",
    "langchin-core",
    "llamindx-core",
    "chromadb-client",
    "faiss-cpuu",
    "pinecone-clientt",
    "weaviate-clientt",
    "qdrant-clientt",
    "pydanticc",
    "fastapi-coure",
    "httpx-core",
    "richh",
    "promp-toolkit",
    "clicck",
    "typoo",
    "pyyml",
}
_BIOMETRIC_PATTERN = re.compile(
    r"(?:指纹|fingerprint|面部识别|face.recognition|face.id|虹膜|iris|声纹|voiceprint|voice.print|人脸|face.scan|面部特征|facial.feature|Face.ID|Touch.ID)",
    re.IGNORECASE,
)
_BIOMETRIC_SECURE_PATTERN = re.compile(
    r"(?:template|模板|加密|encrypt|特征提取|feature.extract|本地化|local|anonymiz|匿名)", re.IGNORECASE
)
_FINANCIAL_PATTERN = re.compile(
    r"(?:银行卡|bank.card|信用卡|credit.card|CVV|cvc|证券账户|securities|交易密码|trade.password|支付密码|payment.password|卡号.*\d{4}.*\d{4}|account.*\d{10,})",
    re.IGNORECASE,
)
_FINANCIAL_SECURE_PATTERN = re.compile(
    r"(?:tokeniz|Token化|脱敏|desensitiz|mask|加密|encrypt|PCI|合规审计)", re.IGNORECASE
)
_MEDICAL_PATTERN = re.compile(
    r"(?:诊断|diagnosis|处方|prescription|病历|medical.record|基因|genetic|DNA|健康档案|health.record|医保|medicare|医疗卡|medical.card|患者ID|patient.ID)",
    re.IGNORECASE,
)
_MEDICAL_SECURE_PATTERN = re.compile(
    r"(?:脱敏|anonymiz|匿名|k-anonymity|访问控制|access.control|最小必要|minimum.necessary|HIPAA|审计)", re.IGNORECASE
)
_MINOR_PATTERN = re.compile(
    r"(?:未成年人|minor|儿童|child|青少年|年龄.*(?:<|＜|小于|不到)\s*18|age.*<.*18|学籍|student.record|监护人|guardian|家长同意|parental.consent|COPPA)",
    re.IGNORECASE,
)
_MINOR_SECURE_PATTERN = re.compile(
    r"(?:年龄门控|age.gate|监护人同意|guardian.consent|快速删除|prompt.deletion|不公开|no.public|数据最小化|data.minimization)",
    re.IGNORECASE,
)


def check_p251(text: str) -> list[Finding]:
    findings = []
    matches = _PACKAGE_PATTERN.findall(text)
    for pkg in matches:
        if pkg.lower() in _HALLUCINATED_PACKAGES:
            findings.append(Finding("P251", Severity.HIGH, f"疑似包幻觉: '{pkg}' 可能是不存在的包(恶意包风险)"))
    if len(findings) == 0 and matches:
        suspicious = [
            p
            for p in matches
            if len(p) > 2
            and not re.match(
                r"^(os|sys|json|re|math|time|logging|pathlib|typing|dataclasses|collections|functools|itertools|datetime|hashlib|base64|urllib|http|socket|threading|subprocess|abc|copy|enum|io|csv|sqlite3|unittest|argparse|tempfile|shutil|glob|signal|struct|random|string|textwrap|operator|pprint|locale|gettext|traceback|inspect|dis|gc|weakref|types|contextlib|concurrent|asyncio|configparser|secrets)$",
                p,
                re.IGNORECASE,
            )
        ]
        if len(suspicious) > 3:
            findings.append(
                Finding(
                    "P251",
                    Severity.MEDIUM,
                    f"引用{suspicious[0]}等{len(suspicious)}个非标准库, 建议验证存在性",
                    "1",
                    "1",
                )
            )
    return findings


def check_p252(text: str) -> list[Finding]:
    findings = []
    if _BIOMETRIC_PATTERN.search(text) and not _BIOMETRIC_SECURE_PATTERN.search(text):
        findings.append(Finding("P252", Severity.CRITICAL, "生物特征数据未保护(缺加密/模板化/本地化)"))
    return findings


def check_p253(text: str) -> list[Finding]:
    findings = []
    if _FINANCIAL_PATTERN.search(text) and not _FINANCIAL_SECURE_PATTERN.search(text):
        findings.append(Finding("P253", Severity.CRITICAL, "金融敏感信息未保护(缺Token化/脱敏/加密/PCI合规)"))
    return findings


def check_p254(text: str) -> list[Finding]:
    findings = []
    if _MEDICAL_PATTERN.search(text) and not _MEDICAL_SECURE_PATTERN.search(text):
        findings.append(Finding("P254", Severity.CRITICAL, "医疗敏感信息未保护(缺脱敏/匿名化/访问控制/HIPAA合规)"))
    return findings


def check_p255(text: str) -> list[Finding]:
    findings = []
    if _MINOR_PATTERN.search(text) and not _MINOR_SECURE_PATTERN.search(text):
        findings.append(Finding("P255", Severity.CRITICAL, "未成年人信息未保护(缺年龄门控/监护人同意/快速删除)"))
    return findings
