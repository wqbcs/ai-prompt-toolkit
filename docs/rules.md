# ai-prompt-toolkit 规则文档

> 版本: v56.0.0 | 总规则: 225 | 可自动修复: 166

## 规则类别统计

- **agent**: 7条
- **agent_security**: 5条
- **compliance**: 7条
- **harmonyos**: 15条
- **harmonyos_v16**: 5条
- **inference2security**: 1条
- **inference_security**: 4条
- **multimodal**: 3条
- **multimodal_security**: 5条
- **operations**: 5条
- **performance**: 14条
- **quality**: 64条
- **rag**: 3条
- **rag_security**: 5条
- **security**: 51条
- **structure**: 24条
- **supply_chain**: 5条
- **toolchain**: 2条

## 严重等级统计

- **critical**: 6条
- **high**: 93条
- **low**: 28条
- **medium**: 98条

---

## 规则详细列表

### agent (7条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P031 | Agent缺失工具调用约束 | high | No | LLM01,LLM05 | Agent型Prompt未定义工具调用的安全边界和权限限制 |
| P032 | Agent缺失错误处理策略 | medium | No | LLM01,LLM05 | Agent型Prompt未定义工具调用失败时的降级策略 |
| P033 | Agent缺失上下文边界 | high | No | LLM01,LLM05 | Agent型Prompt未限制上下文传递范围，可能导致信息泄露 |
| P034 | Agent缺失审批机制 | medium | No | LLM01,LLM05 | Agent型Prompt未对高风险操作设置人工审批流程 |
| P041 | 工具描述模糊性(H1) | high | No | LLM02,LLM06,LLM07 | Agent型Prompt中工具/函数描述模糊或过于简短，模型可能无法正确选择和调用 |
| P042 | 缺失约束脚手架(H2) | high | No | LLM02,LLM06,LLM07 | Agent型Prompt缺少条件分支和边界约束脚手架，模型在异常情况下行为不可预测 |
| P043 | Schema-Intent不匹配(H3) | medium | No | LLM02,LLM06,LLM07 | Agent型Prompt中工具参数Schema与功能意图描述不匹配 |

### agent_security (5条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P191 | Agent权限边界未声明 | high | Yes | LLM06,LLM01 | AI Agent缺少权限边界声明, 可能执行超出预期的操作 |
| P192 | Agent工具调用约束缺失 | high | Yes | LLM06,LLM01 | AI Agent工具调用缺少约束(参数验证/频率限制/超时), 可能被滥用 |
| P193 | Agent思维链泄露风险 | medium | Yes | LLM02,LLM01 | Agent思维链(CoT)推理过程可能泄露给用户, 暴露内部逻辑和敏感信息 |
| P194 | 多Agent协调安全缺失 | high | Yes | LLM06,LLM01 | 多Agent协调通信缺少安全机制(加密/认证/消息验证), 可能被中间人攻击 |
| P195 | Agent记忆隔离不足 | medium | Yes | LLM02,LLM01 | Agent长期记忆未隔离脱敏, 可能跨用户泄露或累积敏感信息 |

### compliance (7条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P079 | 华为云数据合规跨境声明缺失 | high | Yes | LLM01 | 涉及数据处理或存储的华为云Prompt未声明数据合规和跨境传输要求 |
| P095 | 鸿蒙应用签名规范缺失 | medium | Yes | LLM02 | 鸿蒙应用发布Prompt未声明签名证书和Profile配置 |
| P201 | 数据合规声明缺失 | high | Yes | LLM02,LLM01 | Prompt未声明数据处理合规性(如GDPR/个人信息保护法/数据安全法) |
| P202 | 用户同意机制缺失 | high | Yes | LLM02,LLM01 | Prompt未设置用户数据使用同意流程, 违反GDPR第6条合法依据要求 |
| P203 | AI输出标识缺失 | medium | Yes | LLM07,LLM06 | AI生成内容未标注'AI生成'标识, 违反EU AI Act第52条透明度义务 |
| P204 | 偏见公平声明缺失 | medium | Yes | LLM07,LLM06 | Prompt未声明模型偏见缓解措施, 可能导致歧视性输出 |
| P205 | 数据留存策略缺失 | high | Yes | LLM02,LLM01 | 未定义用户数据存储/删除策略, 违反GDPR第5条存储限制原则 |

### harmonyos (15条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P146 | Stage模型UIAbility生命周期缺失 | high | Yes | LLM06 | Stage模型Prompt未声明UIAbility生命周期管理(onCreate/onForeground/onBack... |
| P147 | Stage模型ExtensionAbility滥用 | medium | Yes | LLM06 | Stage模型Prompt未声明ExtensionAbility使用边界(ServiceExtension/DataSh... |
| P148 | 鸿蒙分布式数据同步安全缺失 | high | Yes | LLM06 | 涉及分布式数据同步的鸿蒙Prompt未声明安全策略(数据加密/端到端加密/可信执行环境/数据分级/冲突解决) |
| P149 | 鸿蒙ArkUI声明式范式违规 | medium | Yes | LLM10 | 鸿蒙ArkUI Prompt未遵循声明式开发范式(数据驱动/单向数据流/状态不可变/无副作用) |
| P150 | 鸿蒙卡片(Widget)更新策略缺失 | medium | Yes | LLM03 | 鸿蒙元服务Prompt未声明卡片更新策略(刷新频率/定时更新/按需更新/数据源声明) |
| P171 | ArkUI@Builder安全校验 | high | Yes | LLM06 | Prompt生成@Builder装饰器代码缺少参数类型校验, 可能导致运行时类型错误 |
| P172 | LazyForEach数据源安全 | high | Yes | LLM06 | Prompt使用LazyForEach但未实现IDataSource接口的变更通知方法, 数据更新不会触发UI刷新 |
| P173 | @Reusable复用安全 | medium | Yes | LLM06 | Prompt使用@Reusable装饰器但未处理组件复用时状态重置, 可能导致脏数据残留 |
| P174 | UIAbility生命周期管理 | high | Yes | LLM06 | Prompt生成UIAbility代码缺少onForeground/onBackground状态处理, 应用切换可能丢失... |
| P175 | 分布式数据同步安全 | high | Yes | LLM06 | Prompt使用分布式数据但未配置数据权限和加密, 跨设备同步可能泄露敏感信息 |
| P186 | ArkUI声明式范式迁移 | high | Yes | LLM09,LLM01 | Prompt涉及ArkUI但未迁移至API 15声明式范式, 可能使用废弃的命令式API |
| P187 | Node-API线程安全 | high | Yes | LLM06,LLM01 | Prompt涉及Node-API/N-API但缺少线程安全声明, 跨线程访问可能导致崩溃 |
| P188 | 沙箱2.0文件系统隔离 | medium | Yes | LLM06,LLM01 | Prompt涉及文件访问但未声明沙箱2.0路径规范, 可能访问非授权路径 |
| P189 | 模块化编译依赖声明 | medium | Yes | LLM09,LLM01 | Prompt涉及HSP/HAP模块但缺少依赖声明, 模块化编译可能失败 |
| P190 | 元服务规范约束 | high | Yes | LLM06,LLM01 | Prompt涉及元服务(Atomic Service)但缺少免安装规范约束, 可能违反元服务大小/权限限制 |

### harmonyos_v16 (5条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P211 | ArkUI懒加载缺失 | high | Yes | LLM06,LLM01 | 鸿蒙NEXT长列表未使用LazyForEach懒加载, 可能导致内存溢出和渲染卡顿 |
| P212 | ObservedV2装饰器误用 | medium | Yes | LLM06,LLM01 | @ObservedV2/@Trace装饰器使用不当, 状态更新可能无法正确触发UI刷新 |
| P213 | 原生绑定安全 | high | Yes | LLM06,LLM01 | NAPI/FFI调用未做参数校验和边界检查, 可能导致内存越界/类型混淆 |
| P214 | 元服务权限过度 | medium | Yes | LLM06,LLM01 | 元服务声明过多系统权限, 增加攻击面和用户信任成本 |
| P215 | 分布式数据同步安全 | high | Yes | LLM06,LLM01 | 分布式数据同步未加密/未校验, 跨设备传输可能泄露敏感信息 |

### inference2security (1条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P197 | LLM输出长度失控 | high | Yes | LLM09,LLM01,LLM10 | LLM推理未限制max_tokens, 输出长度失控可能致成本暴增 |

### inference_security (4条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P196 | LLM推理超时风险 | high | Yes | LLM09,LLM01,LLM10 | LLM推理未设置timeout, 可能导致无限等待和资源耗尽 |
| P198 | LLM温度参数不当 | medium | Yes | LLM06 | LLM温度参数>1.5, 输出过于随机不可控, 降低输出质量稳定性 |
| P199 | LLM采样参数冲突 | medium | Yes | LLM06 | LLM同时设置top_p和temperature, 双重随机性叠加导致输出极度不稳定 |
| P200 | LLM流式响应安全 | high | Yes | LLM06,LLM01 | LLM流式输出未做实时内容审核, 恶意/敏感内容可能逐token泄露给用户 |

### multimodal (3条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P038 | 多模态缺失输入类型验证 | high | No | LLM01 | 多模态Prompt未验证输入的类型(图片/音频/视频)和大小限制 |
| P039 | 多模态缺失内容安全检查 | high | No | LLM01,LLM08 | 多模态Prompt未对非文本输入进行内容安全检查 |
| P040 | 多模态缺失降级策略 | medium | No | LLM01,LLM08 | 多模态Prompt未定义非文本输入不可用时的降级方案 |

### multimodal_security (5条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P216 | 图像注入风险 | high | Yes | LLM06,LLM01 | 图像输入可能包含隐藏指令/对抗样本, 多模态模型可能执行图像中嵌入的恶意指令 |
| P217 | 音频指令注入 | high | Yes | LLM06,LLM01 | 语音输入可能嵌入人类不可听但模型可解析的隐藏指令(超声波/低频注入) |
| P218 | 跨模态信息泄露 | high | Yes | LLM02 | 多模态上下文中, 一种模态的敏感信息可能通过另一种模态泄露(如图片中的文字被OCR提取) |
| P219 | 模态降级安全 | medium | Yes | LLM06,LLM01 | 降级到纯文本模式时, 原多模态安全约束可能丢失(如图片审核约束在文本模式下不生效) |
| P220 | 多模态输出验证 | high | Yes | LLM02 | 模型生成图像/音频等输出未经内容审核, 可能包含不当内容/深度伪造 |

### operations (5条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P181 | 版本声明缺失 | high | Yes | LLM09,LLM01 | Prompt缺少版本声明, 生产环境无法追踪变更和回滚 |
| P182 | 依赖声明缺失 | high | Yes | LLM09,LLM01 | Prompt缺少外部依赖声明(模型/API/工具), 变更时无法评估影响范围 |
| P183 | 环境隔离不足 | medium | Yes | LLM06,LLM01 | Prompt缺少环境隔离配置, 生产/测试/开发环境可能混用导致意外行为 |
| P184 | 降级策略缺失 | high | Yes | LLM09,LLM01 | Prompt缺少降级策略, 当主模型不可用时无备用方案, 服务可能中断 |
| P185 | 灰度发布配置缺失 | medium | Yes | LLM06,LLM01 | Prompt缺少灰度发布配置, 新版本全量上线无法控制风险暴露面 |

### performance (14条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P011 | Token 浪费 | low | No | LLM10 | Prompt 中存在大量无意义的填充文本 |
| P012 | 冗余重复 | medium | No | LLM10 | Prompt 中存在重复的指令或描述 |
| P013 | 无效示例 | medium | No | LLM10 | Prompt 中包含无效或低质量示例 |
| P014 | 嵌套过深 | medium | No | LLM10 | Prompt 中的条件/逻辑嵌套超过 3 层 |
| P015 | 约束过多 | low | No | LLM09 | Prompt 中约束条件超过 10 条，可能导致模型困惑 |
| P049 | Token消耗预警 | medium | No | LLM03 | Prompt预计Token消耗超过阈值，可能导致成本失控或截断 |
| P066 | 多轮对话上下文窗口溢出风险 | medium | Yes | LLM02 | 多轮对话Prompt未设定上下文截断或摘要策略 |
| P070 | Token预算超限风险 | medium | No | LLM06 | Prompt文本过长可能导致Token预算超限(>4000 tokens) |
| P072 | 昇腾NPU适配声明缺失 | medium | Yes | LLM05 | 涉及模型训练或推理的Prompt未声明昇腾NPU适配信息 |
| P092 | 鸿蒙线程模型声明缺失 | medium | Yes | LLM02 | 鸿蒙耗时操作Prompt未声明TaskPool/Worker线程模型 |
| P097 | 盘古Token限制风险 | high | Yes | LLM01,LLM04,LLM08 | Prompt可能超出盘古模型上下文窗口限制(8K/32K/128K) |
| P135 | 多模态Token预算缺失 | medium | Yes | LLM01 | 多模态Prompt未声明Token/资源预算限制(图像Token消耗/音频处理时间) |
| P144 | Agent上下文窗口管理缺失 | medium | Yes | LLM06,LLM10 | Agent Prompt未声明上下文窗口管理策略(截断/摘要/遗忘/滑动窗口) |
| P153 | Prompt速率限制缺失 | medium | Yes | LLM10 | Prompt未声明调用频率/速率限制(防止资源耗尽) |

### quality (64条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P016 | 歧义表述 | high | Yes | LLM09 | Prompt 中存在模糊、歧义的表述 |
| P017 | 矛盾指令 | high | No | LLM09 | Prompt 中存在相互矛盾的指令 |
| P018 | 缺失 Few-shot | medium | No | LLM09 | Prompt 缺少 Few-shot 示例引导 |
| P019 | CoT 缺失 | low | No | LLM09 | 复杂推理任务缺少 Chain-of-Thought 引导 |
| P020 | 无评估标准 | medium | No | LLM09 | Prompt 缺少输出质量评估标准 |
| P023 | 指令冲突 | high | No | LLM10 | Prompt 中存在正向与负向指令指向同一动作对象 |
| P024 | 示例与指令不一致 | medium | No | LLM02,LLM03,LLM07 | Prompt Few-shot 示例行为与文本指令约束不一致 |
| P027 | 文化敏感内容 | low | No | LLM09 | Prompt 中可能包含冒犯特定文化的表述 |
| P028 | 链式指令缺失 | medium | No | LLM09 | 多步骤推理任务缺少 step-by-step 引导 |
| P030 | 过度依赖 | low | No | LLM06 | Prompt 过度依赖特定模型/平台未声明兼容性 |
| P045 | 隐式指令失败(H5) | medium | No | LLM02,LLM06 | Prompt中存在隐含但未明确表达的期望，模型可能无法正确理解 |
| P047 | 角色混淆(H7) | high | No | LLM03 | 多角色Prompt中角色定义存在冲突或重叠，模型行为边界不清晰 |
| P048 | 中文标点混用 | low | Yes | LLM03 | Prompt中存在中英文标点混用，可能导致模型理解偏差 |
| P050 | 中文冗余表述 | low | No | LLM06 | Prompt中存在中文冗余叠词或重复表述 |
| P052 | 缺少输出格式约束 | medium | No | LLM05 | 长Prompt未指定输出格式要求 |
| P053 | 模糊指令检测 | low | Yes | LLM05 | Prompt中存在模糊表述(等等/之类的/可能/适当等) |
| P056 | Markdown层级过深 | low | No | LLM09 | Prompt中Markdown标题层级超过4级，影响可读性 |
| P057 | 输出非确定性风险 | medium | No | LLM09 | Prompt中存在导致非确定性输出的措辞但未设定约束 |
| P058 | 多语言指令冲突 | medium | No | LLM09 | 同一Prompt中混用中英文指令但未明确指定输出语言 |
| P059 | Agent工具描述不完整 | high | No | LLM09 | Agent型Prompt中工具定义缺少必要的参数说明或返回值描述 |
| P060 | RAG引用格式不规范 | medium | No | LLM09 | RAG型Prompt中未定义检索结果的引用格式 |
| P061 | 空行规范 | low | Yes | LLM09 | Prompt中存在3个及以上连续空行 |
| P062 | 条件编译语法错误 | high | No | LLM09 | 条件编译指令存在未闭合或嵌套错误 |
| P064 | Prompt模板版本迁移提示缺失 | low | Yes | LLM01 | 模板使用旧版frontmatter格式但未声明兼容迁移信息 |
| P065 | 链式调用缺失错误隔离 | high | Yes | LLM01 | 多步骤链式指令中缺少单步失败时的隔离和恢复机制 |
| P067 | 知识截止日期缺失 | medium | Yes | LLM02 | 涉及事实性知识的Prompt未声明知识截止日期 |
| P068 | 幻觉预防指令缺失 | high | Yes | LLM02 | 事实性Prompt中缺少防止模型编造信息的约束 |
| P069 | 输出格式与示例不一致 | medium | No | LLM06 | Prompt中声明的输出格式与Few-shot示例的实际格式不匹配 |
| P074 | 鸿蒙API版本兼容性声明缺失 | medium | Yes | LLM06 | 鸿蒙开发Prompt未声明目标API版本和最低兼容版本 |
| P075 | 华为云区域未指定 | low | Yes | LLM06 | 涉及华为云部署的Prompt未指定目标部署区域 |
| P076 | ModelArts模型部署配置缺失 | medium | Yes | LLM01,LLM05 | 涉及ModelArts的Prompt未声明模型部署规格和资源配置 |
| P077 | 华为云服务配额限制提示缺失 | low | Yes | LLM01,LLM05 | 涉及华为云资源使用的Prompt未提示服务配额和限流策略 |
| P080 | 华为云SLA降级策略缺失 | low | Yes | LLM04 | 涉及华为云服务依赖的Prompt未声明SLA降级和服务降级策略 |
| P081 | 模板变量完整性缺失 | medium | Yes | LLM02 | 使用{{var}}模板变量的Prompt缺少变量默认值声明 |
| P082 | Trace可观测性缺失 | low | Yes | LLM02 | 复杂Prompt(>500字符)缺少Trace可观测性声明 |
| P083 | Doctor健康检查建议 | low | Yes | LLM02 | Prompt缺少Doctor诊断检查，建议运行prompt-doctor |
| P084 | 输出格式规范缺失 | medium | Yes | LLM07 | Prompt声明了JSON/Markdown输出但缺少格式约束 |
| P085 | 模型兼容性风险 | medium | Yes | LLM07 | Prompt使用了特定模型语法但未声明目标模型 |
| P086 | ArkTS语法兼容性风险 | medium | Yes | LLM01 | 鸿蒙Prompt中使用了非ArkTS兼容语法(TypeScript高级特性) |
| P088 | Ability生命周期回调缺失 | medium | Yes | LLM01 | 鸿蒙开发Prompt缺少Ability生命周期回调(onCreate/onDestroy等) |
| P090 | 鸿蒙UI组件版本兼容性 | low | Yes | LLM01 | 鸿蒙Prompt使用了特定版本ArkUI组件但未声明最低API版本 |
| P091 | 鸿蒙资源引用规范缺失 | low | Yes | LLM01 | 鸿蒙Prompt引用资源未使用$r/$rawfile标准引用方式 |
| P093 | 鸿蒙数据管理规范缺失 | medium | Yes | LLM02 | 鸿蒙数据存储Prompt未声明使用关系型数据库/偏好数据/分布式数据 |
| P096 | 盘古模型格式兼容性风险 | high | Yes | LLM01,LLM04,LLM08 | Prompt使用了非盘古兼容的对话格式(如ChatML/Llama格式) |
| P099 | 盘古多模态兼容性风险 | medium | Yes | LLM03,LLM04,LLM05 | Prompt涉及多模态(图文)输入但未声明盘古多模态格式兼容性 |
| P101 | 语义冗余检测 | medium | Yes | LLM09 | Prompt中存在重复或冗余的表述，可能降低模型注意力效率 |
| P102 | 逻辑矛盾检测 | high | Yes | LLM09 | Prompt中存在自相矛盾的指令，可能导致模型行为混乱 |
| P103 | 指令冲突检测 | high | Yes | LLM09 | Prompt中存在相互冲突的约束条件 |
| P104 | 角色一致性问题 | medium | No | LLM09 | Prompt中的角色定义与行为指令不一致 |
| P106 | 负面示例缺失 | low | Yes | LLM09 | Prompt仅提供正面示例而缺少反例/负面示例，模型可能无法识别错误模式 |
| P108 | 多语言一致性问题 | low | Yes | LLM09 | Prompt中中英混排时存在术语不一致或表达风格切换问题 |
| P109 | RAG检索增强规范缺失 | medium | Yes | LLM09 | RAG场景Prompt缺少检索增强声明(上下文引用/置信度/来源标注) |
| P111 | 思维链CoT规范缺失 | medium | Yes | LLM09 | 推理类Prompt未要求Chain-of-Thought逐步推理，可能导致推理跳跃 |
| P112 | Few-Shot示例质量不足 | low | No | LLM09 | Few-Shot示例数量不足或缺乏多样性，可能影响模型泛化能力 |
| P115 | 可解释性声明缺失 | low | No | LLM02 | 决策类Prompt未要求输出可解释性说明，用户无法理解决策依据 |
| P116 | 情感极性偏移风险 | medium | No | LLM07 | Prompt中存在明显情感倾向性表述，可能导致模型输出产生偏见 |
| P117 | 事实性约束缺失 | medium | Yes | LLM07 | 知识密集型Prompt未声明事实性约束，模型可能产生幻觉 |
| P118 | 知识截止声明缺失 | low | Yes | LLM09 | Prompt未声明模型知识截止日期，用户可能误判信息时效性 |
| P119 | 模型能力边界声明缺失 | low | Yes | LLM09 | Prompt未声明模型能力局限性，可能导致用户对输出有过高期望 |
| P121 | ArkTS严格模式合规缺失 | high | Yes | LLM06 | 鸿蒙开发Prompt未声明ArkTS严格模式合规要求 |
| P125 | 多设备适配声明缺失 | medium | Yes | LLM06 | 鸿蒙开发Prompt未声明多设备(手机/平板/手表/2in1)适配策略 |
| P126 | 无障碍访问规范缺失 | medium | Yes | LLM06 | 鸿蒙开发Prompt未声明无障碍访问规范(屏幕阅读器/无障碍组件) |
| P129 | 元服务卡片规范缺失 | medium | Yes | LLM06 | 鸿蒙开发Prompt涉及卡片/元服务但未声明FormExtension规范 |
| P134 | 跨模态一致性声明缺失 | medium | Yes | LLM01 | 多模态Prompt未声明跨模态输出一致性校验(图像描述与文本描述是否一致) |

### rag (3条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P035 | RAG缺失检索源验证 | high | No | LLM04,LLM08 | RAG型Prompt未验证检索内容的可信度和来源 |
| P036 | RAG缺失幻觉检测提示 | medium | No | LLM04,LLM08 | RAG型Prompt未指示模型在检索结果不包含答案时承认不知 |
| P037 | RAG缺失引用标注要求 | medium | No | LLM04,LLM08 | RAG型Prompt未要求模型标注答案来源的引用 |

### rag_security (5条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P206 | 检索注入风险 | high | Yes | LLM08,LLM01 | RAG检索结果未做输入净化, 外部数据源可能注入恶意内容 |
| P207 | 幻觉检测缺失 | high | Yes | LLM09 | RAG未配置事实性检查/来源验证, 模型可能生成无根据内容 |
| P208 | 来源溯源缺失 | medium | Yes | LLM09 | 检索结果未标注来源, 无法追溯信息出处, 降低可信度 |
| P209 | 上下文窗口溢出 | high | Yes | LLM08,LLM01 | 检索结果可能超过上下文窗口, 导致截断丢失关键信息 |
| P210 | 嵌入偏移风险 | medium | Yes | LLM08,LLM01 | 嵌入模型版本未固定, 模型更新可能导致检索结果偏移/降质 |

### security (51条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P006 | 敏感信息暴露 | high | Yes | LLM01,LLM02,LLM07 | Prompt 中可能包含 API Key、密码等敏感信息 |
| P007 | 注入风险 | high | No | LLM01,LLM05 | Prompt 中存在可被注入的开放输入点 |
| P008 | 权限过宽 | medium | No | LLM05,LLM06 | Prompt 赋予模型过宽的操作权限 |
| P009 | 无审计日志 | low | No | LLM02,LLM07 | Prompt 未包含审计/追踪相关指令 |
| P010 | 无回退策略 | medium | Yes | LLM01 | Prompt 缺少错误处理和回退策略 |
| P021 | 编码混淆 | high | No | LLM09 | Prompt 中存在 Base64/Unicode/Hex 编码混淆内容 |
| P022 | 模板注入标记 | critical | No | LLM09 | Prompt 中存在模板注入标记 {{}}/${} |
| P029 | 变量未转义 | medium | No | LLM04 | Prompt 中用户输入变量未进行转义/校验 |
| P044 | 上下文边界侵蚀(H4) | high | No | LLM02,LLM06 | Agent型Prompt中上下文传递缺乏边界约束，可能导致敏感信息泄露 |
| P051 | 硬编码凭据检测 | high | No | LLM04 | Prompt中存在硬编码的密码/API密钥/Token |
| P063 | Agent系统Prompt泄露风险 | high | Yes | LLM01 | Agent型Prompt中系统指令可能被用户输入覆盖或泄露 |
| P071 | 华为云API Endpoint缺失校验 | medium | Yes | LLM05 | 涉及华为云API调用的Prompt未声明具体的endpoint地址 |
| P073 | 华为云IAM认证方式未指定 | high | Yes | LLM05 | 涉及华为云服务调用的Prompt未指定IAM认证方式 |
| P078 | 鸿蒙应用沙箱权限声明缺失 | medium | Yes | LLM01,LLM05 | 鸿蒙应用开发Prompt未声明应用沙箱和权限边界 |
| P089 | 鸿蒙权限声明缺失 | high | Yes | LLM01 | 鸿蒙应用Prompt未声明所需权限(ohos.permission.*) |
| P094 | 鸿蒙网络安全规范缺失 | high | Yes | LLM02 | 鸿蒙网络请求Prompt未声明HTTPS/证书锁定/网络安全配置 |
| P100 | 盘古安全护栏声明缺失 | high | Yes | LLM03 | 使用盘古模型的Prompt未声明华为云ModelArts安全护栏和内容审核配置 |
| P113 | 系统提示注入防御缺失 | high | Yes | LLM01 | 系统Prompt缺少注入攻击防御声明，可能被用户输入劫持 |
| P114 | 数据隐私GDPR对齐缺失 | high | Yes | LLM02 | Prompt涉及个人数据处理但缺少GDPR/隐私合规声明 |
| P124 | 权限最小化声明缺失 | high | Yes | LLM06 | 鸿蒙开发Prompt涉及权限请求但未声明最小化原则 |
| P127 | 鸿蒙安全沙箱声明缺失 | high | Yes | LLM06 | 鸿蒙开发Prompt涉及数据存储/共享但未声明安全沙箱数据隔离 |
| P130 | 鸿蒙网络安全规范缺失 | high | Yes | LLM06 | 鸿蒙开发Prompt涉及网络请求但未声明HTTPS/证书/网络安全规范 |
| P132 | 图像安全校验缺失 | high | Yes | LLM01 | 涉及图像输入的Prompt未声明图像安全校验(NSFW/恶意内容/隐写检测) |
| P133 | 音频内容过滤缺失 | high | Yes | LLM01 | 涉及音频输入的Prompt未声明音频内容过滤(隐藏指令/超声频段/语音注入) |
| P138 | 多模态链式攻击防护缺失 | high | Yes | LLM08 | 多模态Prompt未声明跨模态组合攻击防护(图像注入+文本泄露/音频注入+越狱) |
| P139 | 多模态数据隔离缺失 | high | Yes | LLM02 | 多模态Prompt未声明模态间数据隔离(防止跨模态信息泄露/敏感数据通过图像外泄) |
| P140 | 多模态审计追踪缺失 | medium | Yes | LLM07 | 多模态Prompt未声明多模态审计追踪(记录各模态输入/输出/决策过程) |
| P142 | 工具调用权限越界 | high | Yes | LLM06 | Agent Prompt的工具调用未声明最小权限(可调API/可访问资源/权限范围) |
| P143 | Agent循环调用防护缺失 | high | Yes | LLM06 | Agent Prompt未声明最大迭代次数或递归深度限制(防止无限循环/递归调用) |
| P145 | 多Agent协作冲突防护缺失 | medium | Yes | LLM06 | 多Agent Prompt未声明协作协议/冲突解决/死锁防护 |
| P151 | Prompt输入边界校验缺失 | high | Yes | LLM05 | Prompt未声明输入边界校验(长度/格式/范围/类型校验) |
| P152 | Prompt输出编码转义缺失 | high | Yes | LLM07 | Prompt未声明输出编码转义(防止XSS/注入二次攻击) |
| P154 | Prompt审计日志缺失 | medium | Yes | LLM06 | Prompt未声明关键操作审计追踪(调用记录/结果日志/异常告警) |
| P158 | Prompt数据脱敏声明缺失 | high | Yes | LLM07 | Prompt未声明数据脱敏策略(PII检测/字段掩码/日志脱敏) |
| P159 | Prompt沙箱隔离声明缺失 | high | Yes | LLM06,LLM08 | Prompt未声明沙箱隔离(执行环境隔离/资源限制/网络白名单) |
| P160 | Prompt回滚机制声明缺失 | medium | Yes | LLM10 | Prompt未声明回滚机制(版本回滚/快照恢复/自动回滚触发条件) |
| P161 | Prompt模板注入防护缺失 | critical | Yes | LLM01,LLM05 | Prompt未声明模板注入防护(变量转义/沙箱渲染/指令隔离) |
| P162 | Prompt缓存投毒防护缺失 | high | Yes | LLM07 | Prompt未声明缓存投毒防护(缓存键验证/内容签名/过期策略) |
| P163 | Prompt模型越狱防护缺失 | critical | Yes | LLM01 | Prompt未声明模型越狱防护(系统指令固化0/角色锚定/拒绝策略) |
| P164 | Prompt指令提取防护缺失 | high | Yes | LLM05 | Prompt未声明指令提取防护(输出过滤/指令不可见/反提取措辞C) |
| P165 | Prompt侧信道泄露防护缺失 | high | Yes | LLM07 | Prompt未声明侧信道泄露防护(时间恒定/错误统一/日志脱敏) |
| P166 | Prompt输出内容过滤声明缺失 | high | Yes | LLM01 | Prompt未声明输出内容过滤(禁止类型/格式验证/长度限制) |
| P167 | Prompt幻觉防护声明缺失 | high | Yes | LLM01,LLM09 | Prompt未声明幻觉防护(事实核查/来源引用/不确定性标注) |
| P168 | Prompt偏见检测声明缺失 | medium | Yes | LLM02 | Prompt未声明偏见检测(公平性/代表性/中立性) |
| P169 | Prompt毒性内容过滤声明缺失 | high | Yes | LLM02 | Prompt未声明毒性内容过滤(仇恨言论/骚扰/自残/暴力) |
| P170 | Prompt引用验证声明缺失 | medium | Yes | LLM09 | Prompt未声明引用验证(来源可追溯/URL可达性/事实一致性) |
| P176 | 多轮对话上下文污染 | critical | Yes | LLM01 | Prompt存在多轮对话上下文污染风险, 攻击者可通过历史消息注入恶意指令(参考garak continuation p... |
| P177 | Base64编码混淆注入 | critical | Yes | LLM01 | Prompt包含Base64/十六进制/Unicode编码内容, 可能混淆绕过安全检测(参考garak encoding... |
| P178 | 影子指令注入 | high | Yes | LLM01,LLM06 | Prompt包含隐藏在格式化标记(HTML/Markdown/注释)中的影子指令, 可能被模型执行 |
| P179 | 输出格式劫持 | high | Yes | LLM01,LLM06 | Prompt存在输出格式劫持风险, 攻击者可强制模型输出特定格式(如JSON/SQL)绕过输出过滤 |
| P180 | 链式Prompt注入 | critical | Yes | LLM01,LLM02 | Prompt存在跨步骤链式注入传播风险, 恶意内容可从步骤N传播到步骤N+1(参考promptfoo chain sca... |

### structure (24条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P001 | 缺失角色定义 | high | No | LLM09 | Prompt 未定义角色(Role)，模型可能无法聚焦预期行为 |
| P002 | 缺失输出格式 | medium | No | LLM09 | Prompt 未指定输出格式要求，模型输出可能不一致 |
| P003 | 缺失约束条件 | medium | Yes | LLM09 | Prompt 缺少约束/限制条件，模型行为边界不明确 |
| P004 | Prompt 过长 | medium | No | LLM10 | Prompt 超过 2000 字符，可能导致模型注意力分散 |
| P005 | Prompt 过短 | low | Yes | LLM09 | Prompt 不足 50 字符，指令可能不够明确 |
| P025 | 输出长度未指定 | low | Yes | LLM09 | Prompt 未指定输出字数/段落/Token 范围 |
| P026 | 缺少错误恢复指引 | medium | No | LLM09 | Prompt 未指定不确定时的回退行为 |
| P046 | 模板格式契约违反(H6) | medium | No | LLM02,LLM06 | Prompt中模板变量使用与格式规范不一致 |
| P087 | Stage模型Ability声明缺失 | high | Yes | LLM01 | 鸿蒙Stage模型Prompt缺少Ability声明和入口配置 |
| P098 | 盘古工具调用规范缺失 | medium | Yes | LLM03,LLM04,LLM08 | Prompt涉及工具/函数调用但未声明盘古Function Calling格式规范 |
| P105 | 输出格式约束不完整 | medium | Yes | LLM09 | 输出格式声明缺少完整规范(如缺少字段说明/示例/边界值) |
| P107 | 条件分支覆盖不足 | medium | Yes | LLM09 | Prompt缺少对边界条件/异常情况的分支处理 |
| P110 | 工具调用链规范缺失 | medium | Yes | LLM09 | 多步骤工具调用场景缺少调用链声明(顺序/依赖/超时/错误恢复) |
| P120 | 多轮对话状态管理缺失 | medium | Yes | LLM09 | 对话类Prompt未声明多轮对话状态管理策略(上下文/记忆/会话) |
| P122 | Stage模型生命周期规范缺失 | high | Yes | LLM06 | 鸿蒙开发Prompt未声明Stage模型生命周期管理规范 |
| P123 | Ability路由声明缺失 | medium | Yes | LLM06 | 鸿蒙开发Prompt涉及页面导航但未声明Ability路由规范 |
| P128 | 分布式数据管理规范缺失 | medium | Yes | LLM06 | 鸿蒙开发Prompt涉及分布式场景但未声明分布式数据管理规范 |
| P131 | 多模态输入声明缺失 | high | Yes | LLM01 | 多模态Prompt未声明输入模态类型(文本/图像/音频/视频) |
| P136 | 多模态降级策略缺失 | medium | Yes | LLM08 | 多模态Prompt未声明模态降级/回退策略(图像不可用时的文本回退) |
| P137 | 多模态输出格式规范缺失 | medium | Yes | LLM08 | 多模态Prompt未声明输出格式规范(图像输出尺寸/格式/质量/音频输出参数) |
| P141 | Agent目标声明缺失 | high | Yes | LLM06 | Agent Prompt未声明可执行操作的边界和目标约束(目标范围/禁止行为/退出条件) |
| P155 | Prompt降级策略缺失 | medium | Yes | LLM10 | Prompt未声明异常降级策略(超时降级/模型切换/缓存回退) |
| P156 | Prompt版本管理缺失 | medium | Yes | LLM06 | Prompt未声明版本管理(语义版本/变更日志/兼容性标注) |
| P157 | Prompt灰度发布策略缺失 | medium | Yes | LLM06 | Prompt未声明灰度发布策略(流量百分比/AB测试/逐步放量) |

### supply_chain (5条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P221 | 模型来源未验证 | high | Yes | LLM03 | 使用未验证来源的LLM模型/微调权重, 可能包含后门/恶意行为 |
| P222 | 第三方依赖审计缺失 | high | Yes | LLM03 | Prompt管道中集成的第三方API/插件/工具未做安全审计, 可能泄露数据 |
| P223 | 数据溯源链断裂 | medium | Yes | LLM03 | 训练/微调/评估数据来源不可追溯, 无法验证数据质量和合规性 |
| P224 | 模型版本未锁定 | high | Yes | LLM03 | 生产环境模型版本未固定, 可能被提供商静默更新导致行为变化 |
| P225 | 供应链签名缺失 | medium | Yes | LLM03 | 模型/数据/配置文件缺少签名或校验和, 无法验证完整性 |

### toolchain (2条)

| ID | 名称 | 严重等级 | 可修复 | OWASP | 描述 |
|----|------|----------|--------|-------|------|
| P054 | 鸿蒙兼容性检查 | medium | No | LLM06 | Prompt中包含Android专用API/组件 |
| P055 | 版本标记缺失 | low | No | LLM06 | Prompt缺少版本标记/Front Matter |
