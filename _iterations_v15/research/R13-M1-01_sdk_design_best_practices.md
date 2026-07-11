# 调研报告：SDK设计最佳实践

> 编号：R13-M1-01 | 日期：2026-05-29 | 轮次：第十三轮

---

## 1. 调研目标

分析主流AI/提示词SDK的设计模式与最佳实践，为Python/TypeScript提示词引擎SDK提供设计参考。

## 2. 调研对象

| SDK | 版本 | 语言 | Stars | 定位 |
|-----|------|------|-------|------|
| LangChain | 0.2.x | Python/TS | 85k+ | LLM应用编排框架 |
| LlamaIndex | 0.10.x | Python/TS | 32k+ | RAG数据框架 |
| DSPy | 2.x | Python | 15k+ | 提示词编程框架 |
| Semantic Kernel | 1.x | C#/Python/Java | 21k+ | 企业AI编排 |
| Haystack | 2.x | Python | 15k+ | NLP管道框架 |
| Promptfoo | 0.x | TypeScript | 4k+ | 提示词评估 |

## 3. 核心设计模式分析

### 3.1 LangChain SDK架构

```
LangChain
├── core/              # 抽象基类+接口
│   ├── language_models/   # BaseLLM, BaseChatModel
│   ├── prompts/           # PromptTemplate, ChatPromptTemplate
│   ├── output_parsers/    # BaseOutputParser
│   └── runnables/         # Runnable序列化
├── community/         # 社区集成
├── standard/          # 标准集成
└── smith/             # LangSmith可观测性
```

**关键模式**：
- **Runnable协议**：统一`invoke/ainvoke/batch/abatch/stream/astream`接口
- **LCEL(LangChain Expression Language)**：`prompt | llm | parser`管道语法
- **模块化集成**：core定义抽象，community提供实现
- **可观测性内置**：LangSmith追踪集成

### 3.2 LlamaIndex SDK架构

```
LlamaIndex
├── core/              # 核心抽象
│   ├── base_query_engine/  # 查询引擎
│   ├── base_retriever/     # 检索器
│   └── prompt/             # 提示词模板
├── llms/              # LLM集成
├── embeddings/        # 嵌入模型
└── vector_stores/     # 向量存储
```

**关键模式**：
- **查询引擎抽象**：统一query/aquery接口
- **模块化设计**：核心+集成分离
- **回调管理器**：统一事件回调
- **Settings单例**：全局配置管理

### 3.3 DSPy框架架构

```
DSPy
├── primitives/        # Signature, Module, Example
├── modules/           # Predict, ChainOfThought, ReAct
├── teleprompt/        # 自动优化器
├── evaluate/          # 评估器
└── utils/             # 工具
```

**关键模式**：
- **Signature声明式**：`"question -> answer"`类型化签名
- **Module组合**：类似PyTorch的forward模式
- **自动优化(Teleprompt)**：编译期提示词优化
- **类型化Example**：结构化输入输出

### 3.4 Promptfoo评估框架

**关键模式**：
- **声明式配置**：YAML定义测试用例
- **多模型对比**：同一提示词跨模型评估
- **断言系统**：内置+自定义断言
- **CLI优先**：命令行工具+CI/CD集成

## 4. 最佳实践总结

### 4.1 架构模式

| 模式 | 描述 | 来源 | 推荐度 |
|------|------|------|--------|
| 核心-集成分离 | 核心定义抽象，集成提供实现 | LangChain/LlamaIndex | ★★★★★ |
| Runnable协议 | 统一同步/异步/批量/流式接口 | LangChain | ★★★★★ |
| 管道组合 | 函数式管道组合操作 | LangChain(LCEL) | ★★★★ |
| Module-Forward | 声明式模块+前向执行 | DSPy | ★★★★ |
| 回调/钩子系统 | 统一事件回调机制 | LlamaIndex | ★★★★ |

### 4.2 API设计原则

1. **渐进式复杂度**：简单API 3行代码启动，高级API暴露全部控制
2. **类型安全**：TypeScript严格类型+Python Type Hints+Pydantic
3. **异步优先**：原生async/await支持，同步为语法糖
4. **不可变配置**：配置对象创建后不可变，修改返回新实例
5. **零依赖核心**：核心包零外部依赖，集成按需安装
6. **序列化友好**：所有对象支持JSON序列化/反序列化

### 4.3 提示词引擎特有模式

| 模式 | 描述 | 适用场景 |
|------|------|---------|
| Scenario加载器 | 场景模板+变量绑定+约束验证 | 多场景管理 |
| Evaluator评估器 | 自动评估+回归+A/B测试 | 质量保障 |
| Combinator组合器 | 变体生成+组合优化+冲突检测 | 提示词优化 |
| Adapter适配器 | 模型特定适配+格式转换 | 多模型支持 |
| Runtime运行时 | 加载→绑定→验证→执行→输出验证 | 安全执行 |

## 5. 对本体系SDK的启示

### 5.1 必须采用
- 核心抽象+集成实现分离架构
- Runnable统一协议(invoke/ainvoke/batch/stream)
- Pydantic数据模型+TypeScript严格类型
- 回调/事件系统用于可观测性
- 声明式场景定义(类似DSPy Signature)

### 5.2 建议采用
- 管道组合语法(prompt→adapter→llm→parser)
- 渐进式API(简单→高级)
- CLI工具+CI/CD集成(类似Promptfoo)
- 内置评估+回归测试框架

### 5.3 差异化特色
- UPPL编译集成(UPPL→自然语言/JSON/Agent)
- 约束系统内置(安全/合规/性能约束前置)
- 96子维度评估集成
- 行业场景模板库内置
- 运行时沙箱执行

## 6. 参考资料

- LangChain Docs: https://python.langchain.com/
- LlamaIndex Docs: https://docs.llamaindex.ai/
- DSPy Docs: https://dspy-docs.vercel.app/
- Semantic Kernel: https://learn.microsoft.com/semantic-kernel
- Promptfoo: https://promptfoo.dev/
