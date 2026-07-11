# N1-4：多区域合规包(GDPR/CCPA/PIPL/LGPD/PDPA)

> 迭代：N1-4 | 层：N1-全球化部署包 | 日期：2026-05-29

---

## 1. 五大合规包架构

### 1.1 合规包统一结构

```
_i18n/compliance/
├── common/                    # 共通合规基础
│   ├── data_classification.json
│   ├── consent_management.json
│   └── audit_logging.json
├── gdpr/                      # 欧盟GDPR
│   ├── requirements.json
│   ├── data_subject_rights.json
│   ├── cross_border_transfer.json
│   └── pia_template.json
├── ccpa/                      # 加州CCPA
│   ├── requirements.json
│   ├── consumer_rights.json
│   └── opt_out_mechanism.json
├── pipl/                      # 中国PIPL
│   ├── requirements.json
│   ├── security_assessment.json
│   └── cross_border.json
├── lgpd/                      # 巴西LGPD
│   ├── requirements.json
│   └── dpo_requirements.json
└── pdpa/                      # 泰国PDPA
    ├── requirements.json
    └── consent_mechanism.json
```

### 1.2 GDPR合规包

```json
{
  "regulation": "GDPR",
  "region": "EU/EEA",
  "effective_date": "2018-05-25",
  "requirements": [
    {
      "id": "GDPR-01",
      "article": "Article 5",
      "title": "数据最小化",
      "description": "仅收集实现目的所必需的个人数据",
      "implementation": {
        "prompt_data": "仅记录提示词执行结果，不存储用户原始输入",
        "user_consent": "首次使用时获取明示同意",
        "retention": "执行结果保留30天后自动删除"
      },
      "verification": "数据流审计+保留策略检查"
    },
    {
      "id": "GDPR-02",
      "article": "Article 6",
      "title": "合法基础",
      "description": "每项数据处理活动必须有合法基础",
      "implementation": {
        "legal_bases": ["consent", "legitimate_interest", "contract"],
        "default_basis": "consent",
        "documentation": "每处理活动记录合法基础"
      },
      "verification": "合法基础映射完整性检查"
    },
    {
      "id": "GDPR-03",
      "article": "Article 13-14",
      "title": "透明度与信息提供",
      "description": "向数据主体提供清晰的处理信息",
      "implementation": {
        "privacy_notice": "多语言隐私声明",
        "data_controller": "明确控制者身份",
        "processing_purpose": "每场景声明处理目的"
      },
      "verification": "隐私声明覆盖完整性"
    },
    {
      "id": "GDPR-04",
      "article": "Article 15-22",
      "title": "数据主体权利",
      "description": "支持7项数据主体权利",
      "rights": ["访问", "更正", "删除(被遗忘)", "限制处理", "数据可携", "反对", "自动化决策反对"],
      "implementation": {
        "api_endpoints": "DSAR API (Data Subject Access Request)",
        "response_time": "≤30天",
        "format": "JSON+机器可读"
      }
    },
    {
      "id": "GDPR-05",
      "article": "Article 25",
      "title": "隐私设计(Privacy by Design)",
      "description": "在设计和默认中嵌入隐私保护",
      "implementation": {
        "default_no_collect": "默认不收集个人数据",
        "pseudonymization": "提示词执行结果假名化",
        "access_control": "最小权限访问"
      }
    }
  ],
  "cross_border": {
    "mechanism": ["SCC", "BCR", "adequacy_decision"],
    "default": "SCC",
    "countries_with_adequacy": ["日本", "韩国", "英国", "瑞士", "阿根廷"]
  },
  "dpo": {
    "required": true,
    "responsibilities": ["监控合规", "建议PIA", "配合监管机构", "处理DSAR"],
    "contact_channel": "dpo@prompt-system.org"
  }
}
```

### 1.3 PIPL合规包(中国特有)

```json
{
  "regulation": "PIPL",
  "region": "CN",
  "unique_requirements": [
    {
      "id": "PIPL-U01",
      "title": "网络安全审查",
      "description": "关键信息基础设施运营者采购网络产品和服务需安全审查",
      "trigger": "处理100万+个人信息 或 关键信息基础设施",
      "process": ["提交审查申请", "网络安全审查办公室审核", "30工作日内结果"]
    },
    {
      "id": "PIPL-U02",
      "title": "数据出境安全评估",
      "description": "向境外提供个人信息需安全评估",
      "trigger": "关键信息基础设施 或 100万+个人信息出境",
      "mechanisms": ["安全评估", "标准合同", "个人信息保护认证"]
    },
    {
      "id": "PIPL-U03",
      "title": "单独同意",
      "description": "敏感个人信息处理需获取单独同意",
      "sensitive_data": ["生物识别", "宗教信仰", "医疗健康", "金融账户", "行踪轨迹"],
      "implementation": "弹窗单独同意(非捆绑)"
    }
  ]
}
```

### 1.4 统一合规检查引擎

```typescript
interface ComplianceEngine {
  checkRegulation(regulation: Regulation, dataFlow: DataFlow): ComplianceResult;
  getHighestStandard(): Regulation;  // GDPR为最高标准基线
  overlayRegional(reqs: Requirement[]): Requirement[];  // 叠加区域特有
}

type Regulation = 'GDPR' | 'CCPA' | 'PIPL' | 'LGPD' | 'PDPA';

interface ComplianceResult {
  regulation: Regulation;
  totalRequirements: number;
  satisfied: number;
  gaps: ComplianceGap[];
  score: number;  // 0-100
}
```

## 2. 合规覆盖矩阵

| 合规要求 | GDPR | CCPA | PIPL | LGPD | PDPA | 统一实现 |
|----------|------|------|------|------|------|----------|
| 数据最小化 | ✓ | - | ✓ | ✓ | ✓ | 是 |
| 明示同意 | ✓ | - | ✓ | ✓ | ✓ | 是 |
| 选择退出 | - | ✓ | - | - | - | 是(区域条件) |
| 数据主体权利 | 7项 | 5项 | 8项 | 8项 | 7项 | 8项(全集) |
| 跨境传输 | SCC | 无限制 | 安全评估 | SCC | 同意+标准 | 分区域实现 |
| DPO/PIA | 必须 | 否 | 必须 | 必须 | 否 | 必须(GDPR+PIPL+LGPD) |
| 隐私设计 | ✓ | - | ✓ | - | - | 是 |
| 自动化决策 | 反对权 | - | 拒绝权 | - | - | 是 |
| 安全事件通知 | 72h | - | 立即 | 合理时间 | 72h | 72h |
| 审计日志 | ✓ | ✓ | ✓ | ✓ | ✓ | 是 |

## 3. 追溯记录

| 输入 | 输出 |
|------|------|
| R14-N1-01调研 | 5合规包+统一检查引擎 |
| v15.0.0安全原则 | 扩展为5区域合规 |
