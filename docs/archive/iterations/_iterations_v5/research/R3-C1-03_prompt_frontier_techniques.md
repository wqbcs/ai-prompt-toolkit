# 调研3：Prompt前沿技术(PoT/Active-Prompt/APE/Agent-First)

> **版本**：v1.0.0
> **日期**：2026-05-29
> **批次**：C1-调研3
> **来源**：Prompt Engineering Guide(中文) + Anthropic Docs + 补充研究

---

## 一、Program-of-Thoughts (PoT)

### 1.1 核心概念
PoT将推理过程表达为可执行程序（Python代码），而非自然语言CoT。模型生成代码→执行代码→获得精确结果。

### 1.2 与CoT对比
| 维度 | CoT | PoT |
|------|-----|-----|
| 推理表达 | 自然语言 | 可执行代码 |
| 精确性 | 可能累积误差 | 精确计算 |
| 可验证性 | 难以验证 | 可直接执行验证 |
| 适用场景 | 推理/分析 | 计算/数据处理/数值验证 |
| 复杂度 | 低 | 中（需代码执行环境） |

### 1.3 在本体系中的应用场景
- **09_性能压测**：压测结果分析用PoT生成Python计算脚本
- **04_代码审查**：复杂度计算用PoT生成分析代码
- **06_CI_CD**：流水线配置验证用PoT生成检查脚本
- **07_监控告警**：容量规划用PoT生成计算模型

### 1.4 PoT Prompt模板
```markdown
请将以下分析任务转化为可执行的Python代码，然后执行代码获取精确结果。

## 任务
{task_description}

## 要求
1. 先用自然语言简述解题思路（2-3句）
2. 编写Python代码实现计算
3. 执行代码并输出结果
4. 解释结果的实际含义

## 输出格式
```python
# 分析思路：...
# 代码实现
...
```
结果：...
解释：...
```

---

## 二、Active-Prompt

### 2.1 核心概念
Active-Prompt通过主动选择最不确定/最有信息量的示例作为Few-shot样本，而非随机选择。核心是"不确定性估计"——选择模型最不确定如何回答的样例作为示范。

### 2.2 工作流程
1. 用零样本prompt对训练集推理，收集模型logits/输出
2. 计算每个样本的不确定性分数（熵/方差/分歧度）
3. 选择不确定性最高的K个样本作为Few-shot示例
4. 用选出的示例构建Few-shot prompt进行推理

### 2.3 在本体系中的应用场景
- **动态Few-shot选择**：为55个场景模板自动选择最优Few-shot示例
- **冷启动优化**：新场景模板上线时，用Active-Prompt选择最佳示范
- **评估集构建**：主动选择最具区分力的测试用例

### 2.4 Active-Prompt实施建议
```python
# 伪代码：Active-Prompt示例选择
def select_active_examples(scenario, candidate_pool, k=5):
    uncertainties = []
    for example in candidate_pool:
        response = llm.generate(scenario.prompt, example.input)
        entropy = compute_entropy(response.logits)
        uncertainties.append((example, entropy))
    uncertainties.sort(key=lambda x: x[1], reverse=True)
    return [ex for ex, _ in uncertainties[:k]]
```

---

## 三、自动提示词工程 (APE)

### 3.1 核心概念
APE使用LLM自动搜索/生成/优化prompt，替代人工设计。核心思想：将prompt视为可优化的参数，用LLM作为优化器搜索最优prompt。

### 3.2 APE方法分类
| 方法 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| 生成式APE | LLM生成候选prompt→评估→选择最优 | 创意性强 | 搜索空间大 |
| 梯度式APE | 基于评估反馈迭代修改prompt | 收敛快 | 可能局部最优 |
| 进化式APE | 种群+变异+选择进化prompt | 全局搜索 | 计算量大 |
| 反思式APE | LLM分析自身输出缺陷→修改prompt | 自我改进 | 反思可能不准 |

### 3.3 在本体系中的应用场景
- **场景模板优化**：对得分最低的15个模板用APE自动优化
- **评估Prompt优化**：用APE优化LLM-as-Judge的评估prompt
- **适配指令优化**：为国产模型自动生成最优适配指令

### 3.4 APE实施框架
```markdown
## APE优化流程

### Phase 1: 候选生成
- 输入：当前prompt + 评估结果 + 改进方向
- LLM生成5-10个候选prompt变体

### Phase 2: 评估筛选
- 在评估数据集上运行每个候选prompt
- 用LLM-as-Judge对输出评分
- 记录每个候选的综合得分

### Phase 3: 反思改进
- 分析最优候选vs当前prompt的差异
- LLM反思改进方向是否正确
- 生成下一轮优化候选

### Phase 4: 确认部署
- 最优候选通过回归测试
- 更新prompt并记录变更
```

---

## 四、Agent-First架构

### 4.1 核心概念
Agent-First架构将AI应用设计为以Agent为核心，而非以prompt为核心。Agent=LLM+工具+记忆+规划，prompt只是Agent配置的一部分。

### 4.2 Agent核心组件
| 组件 | 职责 | 本体系对应 |
|------|------|-----------|
| LLM | 推理与决策 | 场景模板中的角色+推理指令 |
| Tools | 外部工具调用 | _interfaces定义的输入输出接口 |
| Memory | 上下文与知识 | _workflows定义的链式上下文 |
| Planning | 任务分解与规划 | 场景模板中的处理步骤 |
| Guardrails | 安全与约束 | 核心约束+验收标准 |

### 4.3 Agent架构模式
1. **ReAct**：Thought→Action→Observation循环（已在04_代码审查、08_安全审计中使用）
2. **Plan-and-Execute**：先规划任务步骤，再逐步执行
3. **Reflexion**：执行→反思→改进循环
4. **Multi-Agent**：多Agent协作（审查Agent+修复Agent+验证Agent）
5. **Deep Agent**：递归Agent，Agent可调用子Agent

### 4.4 Anthropic Agent设计要点（来自Anthropic文档）
- **工具使用优于提示**：能用工具解决的不用prompt硬编码
- **结构化输入/输出**：所有交互使用JSON Schema
- **显式边界**：明确定义Agent的能力边界和权限
- **优雅降级**：工具不可用时的备选策略
- **人类在环**：关键决策需人类确认

### 4.5 在本体系中的应用
| 现有模式 | Agent-First升级 | 效果 |
|---------|----------------|------|
| 静态CoT指令 | ReAct动态推理循环 | 从固定流程→自适应推理 |
| Few-shot示例 | Active-Prompt动态选择 | 从固定示例→最优示例 |
| 单prompt执行 | Multi-Agent协作 | 从单角色→多角色协作 |
| 人工评估 | LLM-as-Judge自动评估 | 从人工→规模化自动评估 |

---

## 五、前沿技术适配度评估维度

新增的第七评估维度"前沿技术适配度"评分标准：

| 分数 | 标准 |
|------|------|
| 5 | 完整集成PoT/Active-Prompt/APE/Agent-First中的3种以上 |
| 4 | 集成2种前沿技术，且运用合理 |
| 3 | 集成1种前沿技术，或2种但运用浅层 |
| 2 | 仅有传统CoT/Few-shot，未使用前沿技术 |
| 1 | 无任何高级提示工程技术 |

---

## 六、行业垂直化覆盖度评估维度

新增的第八评估维度"行业垂直化覆盖度"评分标准：

| 分数 | 标准 |
|------|------|
| 5 | 覆盖5+行业，含行业术语/合规/场景深度适配 |
| 4 | 覆盖3-4行业，行业适配较深 |
| 3 | 覆盖1-2行业，或3+行业但适配较浅 |
| 2 | 仅有通用场景，1个行业浅层适配 |
| 1 | 纯通用，无行业适配 |

### 覆盖行业清单（初始）
1. 互联网/SaaS
2. 金融/ fintech
3. 电商/零售
4. 制造/IoT
5. 医疗/健康
6. 教育/培训
7. 政府/公共服务
8. 游戏/娱乐

---

*本调研为C1批次八维度评估框架提供前沿技术维度基础，为C3批次国产模型适配提供技术方案。*
