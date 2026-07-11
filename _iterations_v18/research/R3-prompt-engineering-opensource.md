# 调研3：提示词工程开源项目参考

> **日期**：2026-07-11 | **版本**：v1.0

---

## 1. promptfoo（23.1k Stars）

### 1.1 核心能力
- **LLM评估框架**：声明式配置+命令行+CI/CD集成
- **红队测试**：漏洞扫描+渗透测试+安全评估
- **模型对比**：GPT/Claude/Gemini/DeepSeek等横向对比
- **代码扫描**：PR级别的LLM安全合规审查
- **本地运行**：100%本地执行，隐私保护

### 1.2 可借鉴设计
1. **声明式评估配置**：YAML定义prompts+providers+tests
2. **断言系统**：equals/contains/regex/llm-rubric/javascript
3. **红队攻击向量**：jailbreak/leakage/hallucination/bias
4. **CI/CD集成**：GitHub Actions/Pre-commit hooks
5. **Web查看器**：评估结果可视化对比

### 1.3 对本项目的启发
- 提示词体系应设计可编程评估接口，支持自动化质量验证
- 红队测试方法可纳入安全审计提示词
- CI/CD集成模式可用于循环改进引擎

---

## 2. DSPy（36k Stars）

### 2.1 核心能力
- **编程而非提示**：用Python代码替代脆弱的提示词
- **自动优化**：GEPA（Reflective Prompt Evolution）可超越RL
- **模块化**：Signature → Module → Optimizer三层架构
- **编译器**：将声明式LM调用编译为自改进管线
- **Assertions**：计算约束+自精炼管线

### 2.2 可借鉴设计
1. **Signature模式**：输入字段→输出字段的声明式定义
2. **Module体系**：Predict/ChainOfThought/ReAct/ProgramOfThought
3. **Optimizer算法**：BootstrapFewShot/MIPROv2/COPRO
4. **Assertions机制**：dspy.Assert/dspy.Suggest约束输出
5. **Teleprompter**：自动选择最佳few-shot示例

### 2.3 对本项目的启发
- 提示词体系可引入"编程接口"层，支持Signature式声明
- 优化器算法可启发循环改进引擎的优化策略
- Assertions机制可转化为检查清单的自动验证
- 模块化设计可参考为"自定义组合器"接口

---

## 3. 对提示词体系的综合改进建议

1. **引入UPPL编译层**：参考DSPy的Signature模式设计UPPL语言
2. **自动化评估框架**：参考promptfoo的声明式评估+断言系统
3. **红队安全测试**：集成promptfoo的攻击向量到安全审计提示词
4. **CI/CD集成方案**：设计Git Hooks+GitHub Actions集成模板
5. **优化器策略库**：参考DSPy的Optimizer算法设计提示词优化策略

---

## 4. 调研来源
- promptfoo GitHub：https://github.com/promptfoo/promptfoo（MIT License, 23.1k Stars）
- DSPy GitHub：https://github.com/stanfordnlp/dspy（MIT License, 36k Stars）
