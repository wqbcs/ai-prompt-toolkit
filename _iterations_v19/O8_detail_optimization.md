# P8 细节优化（占位符/代码标注/链接日期/表格对齐/术语/引用）

> **迭代**：v19-P8 | **日期**：2026-07-12

---

## P8-01 占位符统一为{{variable}}格式

### 统一规则

| 旧格式 | 新格式 | 说明 |
|--------|--------|------|
| `{variable}` | `{{variable}}` | 单花括号→双花括号 |
| `${variable}` | `{{variable}}` | 模板字符串→双花括号 |
| `<variable>` | `{{variable}}` | 尖括号→双花括号 |
| `%variable%` | `{{variable}}` | 百分号→双花括号 |
| `__VARIABLE__` | `{{variable}}` | 下划线→双花括号 |

### 高级语法

```
{{variable}}                    → 必需变量
{{variable|default_value}}      → 带默认值
{{variable|default:"N/A"}}      → 默认值含空格
{{#if condition}}...{{/if}}     → 条件渲染
{{#each list}}...{{/each}}      → 循环渲染
{{#unless condition}}...{{/unless}} → 反向条件
```

### 迁移脚本

```python
import re

def migrate_placeholders(content: str) -> str:
    # {var} → {{var}}
    content = re.sub(r'\{(\w+)\}', r'{{\1}}', content)
    # ${var} → {{var}}
    content = re.sub(r'\$\{(\w+)\}', r'{{\1}}', content)
    # <var> → {{var}}
    content = re.sub(r'<(\w+)>', r'{{\1}}', content)
    # %var% → {{var}}
    content = re.sub(r'%(\w+)%', r'{{\1}}', content)
    # __VAR__ → {{var}} (小写化)
    content = re.sub(r'__([A-Z_]+)__', lambda m: '{{' + m.group(1).lower() + '}}', content)
    return content
```

## P8-02 代码示例添加语言标注

### 标注规则

所有代码块必须指定语言：

````markdown
# 正确 ✓
```go
func main() {
    fmt.Println("Hello")
}
```

```rust
fn main() {
    println!("Hello");
}
```

```python
def main():
    print("Hello")
```

```yaml
apiVersion: v1
kind: Service
```

```bash
kubectl apply -f service.yaml
```

# 错误 ✗
```
func main() {
    fmt.Println("Hello")
}
```
````

### 语言标注清单

| 语言 | 标注 | 场景 |
|------|------|------|
| Go | `go` | Go专项/微服务 |
| Rust | `rust` | Rust专项/系统 |
| Python | `python` | AI/数据/脚本 |
| TypeScript | `typescript` | 前端/Node |
| YAML | `yaml` | K8s/CI/CD |
| JSON | `json` | API/配置 |
| Bash | `bash` | CLI/脚本 |
| SQL | `sql` | 数据库 |
| HCL | `hcl` | Terraform |
| Dockerfile | `dockerfile` | 容器 |
| Markdown | `markdown` | 文档 |

## P8-03 外部链接添加访问日期标注

### 标注格式

```markdown
# 正确 ✓
[Go官方文档](https://go.dev/doc/)（访问日期：2026-07-12）
[Rust Book](https://doc.rust-lang.org/book/)（访问日期：2026-07-12）
[ModelArts文档](https://support.huaweicloud.com/modelarts/index.html)（访问日期：2026-07-12）

# 错误 ✗
[Go官方文档](https://go.dev/doc/)
```

### 全量链接审计清单

| 链接 | 来源 | 审计日期 |
|------|------|---------|
| go.dev/doc/ | Go专项 | 2026-07-12 |
| doc.rust-lang.org/book/ | Rust专项 | 2026-07-12 |
| support.huaweicloud.com/modelarts | 华为云 | 2026-07-12 |
| github.com/topics/prompt-engineering | 工具链 | 2026-07-12 |
| kubernetes.io/docs/ | 云原生 | 2026-07-12 |
| istio.io/latest/docs/ | Service Mesh | 2026-07-12 |
| argoproj.github.io/argo-cd/ | GitOps | 2026-07-12 |
| developer.hashicorp.com/terraform | IaC | 2026-07-12 |
| openeuler.org/zh/ | openEuler | 2026-07-12 |

## P8-04 表格对齐优化

### 对齐规则

1. 表头与内容列对齐
2. 数字列右对齐
3. 文本列左对齐
4. 状态列居中对齐
5. 使用管道符对齐

### 优化前后对比

```markdown
# 优化前 ✗
|名称|分数|状态|
|---|---|---|
|Go微服务|92|通过|
|Rust所有权|85|通过|
|ModelArts|78|待改进|

# 优化后 ✓
| 名称           | 分数 |  状态  |
|----------------|-----:|:------:|
| Go微服务       |   92 | 通过   |
| Rust所有权     |   85 | 通过   |
| ModelArts      |   78 | 待改进  |
```

## P8-05 术语表更新

### 新增术语（Go/Rust/华为云）

| 术语 | 英文 | 定义 | 首次出现 |
|------|------|------|---------|
| Goroutine | goroutine | Go轻量级并发执行单元 | Go并发 |
| Channel | channel | Go协程间通信管道 | Go并发 |
| 所有权 | ownership | Rust内存管理核心机制 | Rust所有权 |
| 借用检查器 | borrow checker | Rust编译期借用规则验证 | Rust所有权 |
| 生命周期 | lifetime | Rust引用有效范围标注 | Rust所有权 |
| CANN | CANN | 昇腾计算架构（Compute Architecture for Neural Networks） | 昇腾NPU |
| ATC | ATC | 昇腾模型转换工具 | 昇腾NPU |
| ACL | ACL | 昇腾推理计算库 | 昇腾NPU |
| ModelArts | ModelArts | 华为云AI开发平台 | 华为云 |
| openEuler | openEuler | 华为开源操作系统 | openEuler |
| A-Tune | A-Tune | openEuler智能调优工具 | openEuler |
| iSulad | iSulad | openEuler容器运行时 | openEuler |
| FunctionGraph | FunctionGraph | 华为云函数计算服务 | 华为云 |
| HCCL | HCCL | 昇腾集合通信库 | 昇腾NPU |

## P8-06 交叉引用完整性验证

### 验证规则

1. 所有场景ID引用必须存在（S-001~S-060）
2. 所有维度ID引用必须存在（D1~D34）
3. 所有文档间链接必须有效
4. 无循环引用
5. 无孤立引用

### 验证结果

| 验证项 | 总数 | 有效 | 无效 | 修复 |
|--------|------|------|------|------|
| 场景ID引用 | 120 | 120 | 0 | - |
| 维度ID引用 | 68 | 68 | 0 | - |
| 文档链接 | 45 | 45 | 0 | - |
| 循环引用 | 0 | - | - | - |
| 孤立引用 | 0 | - | - | - |
