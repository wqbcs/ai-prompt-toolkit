# _security — 安全扫描引擎

## 引擎简介

`_security` 是提示词基础设施的安全扫描引擎，负责在编译和运行时检测潜在的安全威胁。主要功能包括：

- **注入检测**：基于规则集识别指令覆盖、角色劫持、数据外泄等注入攻击
- **继承链审计**：检测继承链中的循环依赖、链路断裂和风险传播
- **白名单管理**：维护安全条件表达式白名单，快速放行已知安全模式
- **严重性分级**：按 high/medium/low/critical 分级，支持自动阻断高风险项

## 使用指南

### 目录结构

```
_security/
├── README.md              # 本文件
├── config.yaml            # 安全引擎配置
├── rules/
│   ├── injection_rules.yaml   # 注入检测规则集
│   └── inheritance_rules.yaml # 继承链审计规则集
├── whitelist.yaml         # 安全条件表达式白名单
└── (安全核心代码)
```

### 扫描流程

1. 加载规则集与白名单
2. 对输入提示词执行注入模式匹配
3. 追踪继承链并审计
4. 对照白名单过滤安全模式
5. 汇总并输出安全扫描报告

### 配置说明

参见 `config.yaml`，关键配置项：

- `scan_timeout_seconds`：扫描超时时间
- `max_inheritance_depth`：最大继承深度
- `high_severity_block`：高风险是否自动阻断

### 扫描报告

扫描输出遵循 `_schemas/security_scan_report.schema.json` 定义的格式。
