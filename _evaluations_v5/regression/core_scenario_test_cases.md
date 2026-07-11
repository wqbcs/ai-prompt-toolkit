# 核心场景回归测试用例

> **版本**：v1.0.0
> **日期**：2026-05-29
> **迭代**：C11-迭代52
> **适用场景**：04_代码审查/08_安全审计/09_性能优化(每场景≥10个)

---

## 一、04_代码审查回归测试用例(12个)

| 用例ID | 用例名称 | 输入描述 | 期望输出关键词 | 优先级 |
|--------|---------|---------|--------------|--------|
| TC-04-01 | 单文件增量审查 | Java Spring Controller单个方法修改 | summary+issues+qualityScore | P0 |
| TC-04-02 | 多文件增量审查 | 3个关联文件同时修改(Service+DAO+Controller) | 跨文件关联问题识别 | P0 |
| TC-04-03 | 安全漏洞识别 | 含SQL注入风险的代码 | SQL注入+P0严重度+修复方案 | P0 |
| TC-04-04 | 性能问题识别 | 含N+1查询的JPA代码 | N+1查询+性能退化 | P1 |
| TC-04-05 | 空指针风险 | 缺null检查的链式调用 | NullPointerException+修复 | P1 |
| TC-04-06 | SOLID违反 | 上帝类(God Class)模式 | 单一职责违反+拆分建议 | P1 |
| TC-04-07 | 异常处理审查 | 吞异常的catch块 | 异常吞没+影响分析 | P1 |
| TC-04-08 | 并发安全审查 | 含竞态条件的多线程代码 | 竞态条件+同步方案 | P0 |
| TC-04-09 | JSON输出格式验证 | 任意代码变更 | 合法JSON+Schema合规 | P0 |
| TC-04-10 | DeepSeek适配验证 | DeepSeek专用审查指令 | CoT逐步推理+自纠错循环 | P1 |
| TC-04-11 | Qwen适配验证 | Qwen结构化输出指令 | JSON模式合规 | P1 |
| TC-04-12 | 大型PR审查 | 50+文件变更 | 分模块审查+总体评估 | P2 |

### TC-04-01 详细用例

```json
{
  "test_case_id": "TC-04-01",
  "scenario": "04-A 增量审查",
  "input": {
    "diff_content": "@@ -15,6 +15,8 @@ public class UserController {\n+  @PostMapping(\"/login\")\n+  public Response login(@RequestBody LoginRequest req) {\n+    String sql = \"SELECT * FROM users WHERE name='\" + req.getName() + \"'\";\n+    return execute(sql);\n+  }\n}",
    "language": "Java",
    "framework": "Spring Boot"
  },
  "expected_output": {
    "must_contain": ["SQL注入", "P0", "参数化查询", "PreparedStatement"],
    "format": "JSON",
    "schema_fields": ["summary", "issues", "quality_score", "recommendation"]
  }
}
```

---

## 二、08_安全审计回归测试用例(12个)

| 用例ID | 用例名称 | 输入描述 | 期望输出关键词 | 优先级 |
|--------|---------|---------|--------------|--------|
| TC-08-01 | OWASP Top10全面扫描 | Spring Boot应用完整配置 | OWASP+10项逐条检查 | P0 |
| TC-08-02 | STRIDE威胁建模 | 微服务API网关设计 | 6类威胁+攻击链 | P0 |
| TC-08-03 | 认证绕过检测 | 缺认证的API端点 | 认证缺失+Spoofing | P0 |
| TC-08-04 | 数据泄露风险 | 敏感数据明文传输 | 信息泄露+TLS+加密 | P0 |
| TC-08-05 | 权限提升检测 | 含越权风险的RBAC配置 | 提权+Elevation | P1 |
| TC-08-06 | 合规差距分析 | 等保2.0三级要求对照 | 等保条款+差距+整改 | P1 |
| TC-08-07 | CVE检索验证 | Log4j2依赖声明 | CVE-2021-44228+修复 | P0 |
| TC-08-08 | ERNIE合规增强验证 | ERNIE合规指令+国内法规 | 网安法/数安法/个保法标注 | P1 |
| TC-08-09 | Active-Prompt验证 | 不确定性驱动审查指令 | 不确定性评估+优先审查 | P1 |
| TC-08-10 | 纵深防御方案 | 被入侵系统加固方案 | 网络+应用+数据+监控四层 | P1 |
| TC-08-11 | JSON输出格式验证 | 任意审计输入 | 合法JSON+Schema合规 | P0 |
| TC-08-12 | 金融PCI-DSS合规 | 支付系统安全审计 | PCI-DSS 12要求+差距 | P2 |

---

## 三、09_性能优化回归测试用例(12个)

| 用例ID | 用例名称 | 输入描述 | 期望输出关键词 | 优先级 |
|--------|---------|---------|--------------|--------|
| TC-09-01 | 基线建立验证 | 应用性能指标输入 | QPS+延迟P95+错误率 | P0 |
| TC-09-02 | USL定律应用 | 并发性能数据分析 | X(N)公式+争用系数 | P0 |
| TC-09-03 | Little's Law验证 | 队列系统性能数据 | L=λ×W+等待时间 | P1 |
| TC-09-04 | Amdahl定律应用 | 串行瓶颈识别 | 最大加速比+串行比例 | P1 |
| TC-09-05 | N+1查询优化 | JPA N+1问题代码 | N+1+JOIN FETCH+批量 | P0 |
| TC-09-06 | GC压力分析 | 高GC频率Java应用 | GC压力+堆分析+调优 | P1 |
| TC-09-07 | 连接池优化 | 连接池耗尽问题 | 连接池+最大连接+超时 | P1 |
| TC-09-08 | 缓存策略优化 | 高频查询无缓存 | 缓存策略+命中率+失效 | P1 |
| TC-09-09 | PoT验证指令 | PoT可执行验证 | 验证函数+执行+结果调整 | P1 |
| TC-09-10 | DeepSeek适配验证 | DeepSeek性能优化指令 | CoT方法论+自纠错 | P1 |
| TC-09-11 | JSON输出格式验证 | 任意性能分析输入 | 合法JSON+Schema合规 | P0 |
| TC-09-12 | 全链路压测方案 | 微服务全链路 | 链路梳理+压测场景+容量 | P2 |

---

## 四、回归测试执行框架

```python
REGRESSION_TEST_SUITE = {
    "04_代码审查": {"test_cases": 12, "p0_count": 5, "p1_count": 5, "p2_count": 2},
    "08_安全审计": {"test_cases": 12, "p0_count": 5, "p1_count": 5, "p2_count": 2},
    "09_性能优化": {"test_cases": 12, "p0_count": 5, "p1_count": 5, "p2_count": 2},
    "total": {"test_cases": 36, "p0_count": 15, "p1_count": 15, "p2_count": 6}
}

PASS_CRITERIA = {
    "all_p0_pass": True,
    "p1_pass_rate": 0.9,
    "overall_pass_rate": 0.85
}
```

---

*本文件为C11批次迭代52产出，核心场景回归测试用例集(36个)。*
