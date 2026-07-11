# 压缩策略v2详细规范

> 版本：v16.0.0

---

## 1. 压缩技术详解

### 1.1 语义保持压缩

| 技术 | 输入 | 压缩输出 | 压缩率 | 语义等价证明 |
|------|------|---------|--------|-------------|
| 冗余去除 | "请分析需求，请仔细分析" | "请分析需求" | 50% | 幂等性 |
| 同义合并 | "检查/审查/审核代码" | "审查代码" | 67% | 同义词映射 |
| 引用展开 | 重复3次的相同约束 | 引用+1次定义 | 67% | 引用完整性 |
| 模板提取 | 10场景含相同前缀 | 模板+参数化 | 70% | 模板实例化 |
| 缩写映射 | "请按照以下步骤" | "步骤:" | 60% | 缩写表查找 |

### 1.2 结构化压缩

```yaml
# L0: 完整场景(1000 tokens)
scenario:
  id: S04
  name: "代码审查与质量保障"
  description: "请作为资深代码审查专家..."
  constraints:
    - "审查范围包括：代码规范、安全漏洞、性能问题、可维护性..."
    - "输出格式必须符合以下Schema..."
    - "每个发现必须包含：严重级别、位置、描述、建议..."
  steps:
    - "1. 获取变更的代码差异"
    - "2. 逐文件分析代码质量"
    - "3. 检测安全漏洞和敏感信息"
    - "4. 评估性能影响"
    - "5. 生成审查报告"

# L2: 压缩场景(400 tokens, 60%压缩)
s:
  id: S04
  n: "代码审查"
  d: "审查代码质量+安全+性能"
  c: [C04_审查范围, C04_输出格式, C04_发现格式]
  t: [获取diff→分析质量→检测安全→评估性能→生成报告]

# L3: 极致压缩(200 tokens, 80%压缩)
S04:审查→{C04}→[diff→qual→sec→perf→rpt]
```

### 1.3 压缩验证

```python
class CompressionValidator:
    """
    验证压缩后场景的语义保持性：
    1. Schema等价：输出Schema不变
    2. 约束等价：约束集逻辑等价
    3. 步骤等价：执行步骤语义等价
    4. 输出等价：给定相同输入，输出语义等价
    """
    def validate(self, original, compressed):
        checks = [
            self.schema_equivalent(original, compressed),
            self.constraints_equivalent(original, compressed),
            self.steps_equivalent(original, compressed),
            self.output_equivalent(original, compressed),
        ]
        return all(checks)
```

## 2. 场景间压缩

### 2.1 共享片段提取

```yaml
# 多场景共享的安全约束片段
shared_fragments:
  security_base:
    constraints:
      - "不得泄露敏感信息(API密钥/密码/令牌)"
      - "输出不得包含可执行的恶意代码"
      - "遵守最小权限原则"
    usage: [S04, S08, S26, S27, S28, S29, S30]
    
  output_schema_base:
    constraints:
      - "输出必须符合JSON Schema"
      - "所有字段必须有类型声明"
      - "必填字段不可为空"
    usage: [S01, S02, S03, S04, S05, S06, S07, S08, S09, S10]
```

### 2.2 继承压缩

```yaml
# 行业场景继承基础场景
financial_audit:
  extends: S08_安全审计
  overrides:
    constraints:
      +: "符合SOX/PCI-DSS金融合规"
      +: "交易数据加密验证"
    scenarios:
      +: "金融交易审计专项检查"
```

## 3. 运行时压缩

### 3.1 模型感知压缩

```python
class ModelAwareCompressor:
    """
    根据目标模型能力自动调整压缩：
    - GPT-4/Claude-3：L1(精简)，模型能理解简洁指令
    - Qwen/DeepSeek：L1-L2，中等压缩
    - 小模型(7B-)：L2-L3，高压缩，确保关键信息
    """
    MODEL_PROFILES = {
        "gpt-4-turbo": {"max_compression": "L1", "min_tokens": 200},
        "claude-3-opus": {"max_compression": "L1", "min_tokens": 200},
        "qwen-max": {"max_compression": "L2", "min_tokens": 150},
        "deepseek-v3": {"max_compression": "L2", "min_tokens": 150},
        "qwen-7b": {"max_compression": "L3", "min_tokens": 100},
    }
    
    def compress(self, scenario, model_id):
        profile = self.MODEL_PROFILES[model_id]
        level = self.select_level(scenario, profile)
        compressed = self.do_compress(scenario, level)
        assert len(compressed) >= profile["min_tokens"]
        return compressed
```

## 4. 压缩度量

| 指标 | 公式 | 目标 |
|------|------|------|
| 压缩率 | (original - compressed) / original | L1:20-30%, L2:40-60%, L3:60-80% |
| 信息损失率 | lost_info / total_info | L1:<2%, L2:<5%, L3:<10% |
| 语义等价率 | equivalent_outputs / total_outputs | >95%(L1), >90%(L2), >85%(L3) |
| 压缩时间 | compress_duration | <10ms(单场景) |
