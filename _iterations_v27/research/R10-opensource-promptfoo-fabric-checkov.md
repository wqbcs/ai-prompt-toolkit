# R10调研报告 - AI提示词体系第十轮成熟度循环

> **轮次**: R10 | **日期**: 2026-07-12 | **版本**: v1.0 | **范围**: v26.0.0→v27.0.0

---

## 调研一：promptfoo v0.121.18+（已加入OpenAI）+ Python SDK调研

### 调研目标
了解promptfoo最新版本的功能演进和Python支持情况，为A/B测试v2 Python实现和Prompt Linter提供参考。

### 调研来源
- **promptfoo GitHub**: https://github.com/promptfoo/promptfoo
- **promptfoo PyPI**: https://pypi.org/project/promptfoo/

### 关键发现

1. **promptfoo已加入OpenAI**: 2026年promptfoo成为OpenAI旗下开源项目，仍保持MIT开源协议。这一变化意味着项目将获得更稳定的维护支持，但不影响其作为开源工具的使用。

2. **pip安装支持**: promptfoo现已支持`pip install promptfoo`安装方式，除传统的npm安装外新增Python生态入口。这对本项目A/B测试v2的Python实现提供了直接参考——可复用其Python SDK的Provider抽象模式。

3. **Code Scanning功能**: 新增代码扫描功能，可在CI/CD中自动检查LLM相关代码的安全和合规问题。这一模式与R10规划的Prompt Linter高度吻合——都是静态分析+规则引擎的架构。

4. **Red Teaming漏洞扫描**: 新增红队测试能力，自动检测提示词注入、越狱、数据泄露等安全漏洞。这与R9安全扫描器v2的注入检测5条规则直接对应，R10可参考其扫描规则扩展模式。

5. **per-test repeat选项**: 支持对单个测试用例设置重复次数，提高统计显著性。这与R9 A/B测试v2的最小样本控制规则一致。

6. **CLI与Web Viewer**: 支持CLI评估+Web查看器双模式，评估结果可通过`promptfoo view`在浏览器中查看。R10的CLI统一入口可参考此模式。

### 对R10的指导意义

| promptfoo特性 | 映射到R10功能 |
|--------------|--------------|
| pip install promptfoo | A/B测试v2 Python包结构(pyproject.toml) |
| Code Scanning | Prompt Linter规则引擎架构 |
| Red Teaming | 安全扫描器v3规则扩展(INJ-006/007/008) |
| per-test repeat | A/B测试v2样本控制 |
| CLI + Web Viewer | prompt-cli统一入口+Playground |
| 多模型Provider | Provider抽象接口(OpenAI/Anthropic/Huawei) |
| Promise.allSettled | asyncio.gather并行调度 |

---

## 调研二：Fabric v1.4.447+ 国际化(i18n)实践调研

### 调研目标
了解Fabric最新的国际化实现方式，为R10 i18n框架提供架构参考。

### 调研来源
- **Fabric GitHub**: https://github.com/danielmiessler/fabric
- **Fabric README**: v1.4.447+ (2026-04-16)

### 关键发现

1. **完整i18n支持(v1.4.356)**: Fabric在2025年12月完成完整国际化，支持10种语言（en/es/de/fa/fr/it/ja/pt/zh/ko），覆盖setup prompts全流程。其实现方式为：
   - 每种语言独立的locale文件
   - BCP 47 locale标准化（如pt-BR和pt-PT智能区分）
   - 智能回退链：目标语言→父语言→英语

2. **i18n环境变量处理**: Fabric使用`FABRIC_LANGUAGE`环境变量控制语言偏好，且与系统locale自动检测联动。当环境变量与系统locale冲突时，以环境变量优先。

3. **M365 Copilot集成(v1.4.380)**: Fabric新增Microsoft 365 Copilot支持，企业用户可利用组织内的M365数据（邮件/文档/会议）进行AI增强。这表明AI提示词工具正在向企业场景深度渗透。

4. **Azure AI Gateway插件(v1.4.417)**: 新增Azure AI Gateway插件，通过统一APIM网关支持AWS Bedrock/Azure OpenAI/Google Vertex AI多后端。这对R10的Provider抽象有参考价值。

5. **OpenAI Codex插件(v1.4.437)**: 支持使用OpenAI Codex作为后端，扩展了AI执行能力。

6. **高频迭代节奏**: Fabric保持457+版本的高频迭代，平均每周2-3个版本，其i18n功能从首次支持到完整10语言覆盖仅用3个月，展示了"增量扩展"的实践路径。

### 对R10的指导意义

| Fabric i18n特性 | 映射到R10 i18n框架 |
|----------------|-------------------|
| BCP 47 locale标准化 | i18n语言代码规范(zh-CN/en-US) |
| 智能回退链 | 翻译回退链(zh→en→zh) |
| FABRIC_LANGUAGE环境变量 | PROMPT_LANGUAGE环境变量 |
| locale文件结构 | i18n资源文件JSON结构 |
| 增量扩展(1→10语言) | i18n框架先支持zh+en，预留扩展接口 |

---

## 调研三：Checkov静态分析架构+Handlebars性能基准调研

### 调研目标
了解IaC静态分析工具Checkov的规则引擎架构，为Prompt Linter提供参考；了解Handlebars.js最新性能基准测试方法，为条件编译Python运行时的性能验证提供参考。

### 调研来源
- **Checkov GitHub**: https://github.com/bridgecrewio/checkov
- **Handlebars.js GitHub**: https://github.com/handlebars-lang/handlebars.js

### 关键发现

#### Checkov（Prompt Linter参考）

1. **规则引擎架构**: Checkov采用注册器(Registry)模式管理检测规则，每条规则是独立的Python类，实现`scan()`方法。其核心流程为：
   ```
   加载IaC文件 → 规则注册器匹配 → 图遍历扫描 → 检测结果聚合 → 报告输出
   ```

2. **规则分类体系**: Checkov将规则按云平台和资源类型分类（如CKV_AWS_21、CKV_GCP_10），编号格式为`CKV_{平台}_{序号}`。R10 Prompt Linter可参考此编号模式，使用`PL_{类别}_{序号}`格式。

3. **CLI输出格式**: 
   ```
   Passed Checks: 1, Failed Checks: 1, Suppressed Checks: 0
   Check: "规则描述"
   File: /path/to/file:行号
   ```
   简洁直观，R10 CLI输出可参考此格式。

4. **自定义策略**: 支持通过Python类或YAML文件添加自定义检测规则，R10可参考此模式实现Prompt Linter的规则扩展。

5. **pip安装**: Checkov通过pip安装，支持`pip3 install checkov`和`brew install checkov`，R10的prompt-cli可参考此安装体验。

#### Handlebars.js（性能基准参考）

1. **tinybench基准框架**: Handlebars采用tinybench驱动性能基准测试，测量compilation/execution/precompilation/end-to-end四类性能指标，输出ops/sec和p50/p75/p99延迟。

2. **分支对比模式**: 支持`pnpm run bench:compare`自动对比main分支与feature分支的性能差异，使用p75延迟作为基准（过滤异常值），变化>2%标记`!`，>5%标记`!!`。

3. **性能优势**: Handlebars预编译模板性能为Mustache的5-7倍，三阶段架构(compile→opcodes→execute)的设计使预编译模板运行时仅执行函数调用。

4. **对R10的指导**: 条件编译Python运行时应建立类似的性能基准测试，测量Lexer/Parser/Evaluator/Renderer各阶段耗时，目标：缓存命中<10ms，全量编译<50ms。

### 对R10的指导意义

| Checkov特性 | 映射到R10 Prompt Linter |
|------------|------------------------|
| Registry模式 | RuleLoader规则注册器 |
| CKV_{平台}_{序号}编号 | PL_{类别}_{序号}规则编号 |
| CLI Passed/Failed输出 | prompt-cli lint彩色输出 |
| 自定义策略(Python/YAML) | 自定义Lint规则(custom_rules/) |
| pip安装 | pip install -e .开发模式 |

| Handlebars特性 | 映射到R10条件编译运行时 |
|---------------|----------------------|
| compile→opcodes→execute | Lexer→Parser→Evaluator→Renderer |
| tinybench基准 | pytest-benchmark性能测试 |
| 分支对比模式 | v26 vs v27编译性能对比 |
| 预编译缓存 | LRU缓存(SHA-256键) |

---

## 调研总结

| 调研项 | 核心收获 | 指导的R10功能 |
|--------|---------|--------------|
| promptfoo v0.121.18+ | 已加入OpenAI、pip安装、Code Scanning、Red Teaming | F2 A/B测试v2 Python+ F4 Prompt Linter |
| Fabric v1.4.447+ | 完整i18n 10语言、BCP 47标准化、智能回退链 | F5 i18n框架 |
| Checkov | Registry规则引擎、CKV编号、CLI输出、自定义策略 | F4 Prompt Linter |
| Handlebars.js | tinybench基准、分支对比、5-7倍性能 | F1 条件编译Python运行时性能验证 |

### 推荐开源项目

| 功能 | 推荐项目 | 理由 |
|------|---------|------|
| A/B测试v2 Python | promptfoo/promptfoo | 已加入OpenAI，pip安装支持，Python SDK可直接参考 |
| Prompt Linter | bridgecrewio/checkov | Registry规则引擎+自定义策略+CLI输出，架构完全匹配 |
| i18n框架 | danielmiessler/fabric | 10语言完整i18n实践，BCP 47+回退链可直接参考 |
| 条件编译Python | handlebars-lang/handlebars.js | 三阶段编译+缓存+基准测试，性能目标验证参考 |
| CLI彩色输出 | Textualize/rich | Python终端美化事实标准，进度条+彩色输出+表格 |
| Python异步HTTP | aio-libs/aiohttp | asyncio HTTP客户端，A/B测试v2并行调用基础 |
| Python统计检验 | scipy/scipy | Shapiro-Wilk/t检验/Mann-Whitney U/Cohen's d全支持 |
