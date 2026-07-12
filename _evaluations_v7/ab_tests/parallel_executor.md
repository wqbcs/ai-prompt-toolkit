# 并行执行调度器设计

> **版本**: v2.0.0 | **日期**: 2026-07-12 | **参考**: promptfoo/promptfoo Provider抽象层

---

## 一、架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                       并行执行调度器架构                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │ 配置加载器   │ ─→ │ 模型适配层   │ ─→ │ 并行调度器   │           │
│  │ ConfigLoader │    │ ModelAdapter │    │ Scheduler    │           │
│  └──────────────┘    └──────────────┘    └──────┬───────┘           │
│                                                  │                    │
│                           ┌──────────────────────┤                    │
│                           │                      │                    │
│                    ┌──────▼──────┐        ┌──────▼──────┐           │
│                    │ 成功处理器  │        │ 失败处理器  │           │
│                    │ SuccessHdlr │        │ FailureHdlr │           │
│                    └──────┬──────┘        └──────┬──────┘           │
│                           │                      │                    │
│                           └──────────┬───────────┘                   │
│                                      │                                │
│                              ┌───────▼───────┐                       │
│                              │ 结果聚合器   │                       │
│                              │ Aggregator    │                       │
│                              └───────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

## 二、模型适配层接口

### 2.1 统一Provider接口

```typescript
interface ModelProvider {
  id: string;
  provider: "openai" | "anthropic" | "aliyun" | "huawei" | "custom";
  endpoint: string;
  apiKeyEnvVar: string;

  invoke(prompt: string, params: InvokeParams): Promise<ModelResponse>;
  validate(): Promise<boolean>;
  estimateCost(tokens: number): number;
}

interface InvokeParams {
  max_tokens: number;
  temperature: number;
  top_p?: number;
  stop_sequences?: string[];
}

interface ModelResponse {
  model_id: string;
  content: string;
  tokens_used: number;
  latency_ms: number;
  finish_reason: "stop" | "length" | "error";
  error?: string;
  timestamp: string;  // ISO 8601
}
```

### 2.2 Provider实现映射

| Provider | SDK/API | 认证方式 | 速率限制 |
|----------|---------|----------|----------|
| openai | OpenAI API v1 | Bearer Token | 60 RPM (Tier1) |
| anthropic | Messages API | x-api-key | 50 RPM |
| aliyun | DashScope API | Authorization Bearer | 60 RPM |
| huawei | PanGu API | X-Auth-Token | 30 RPM |
| custom | OpenAI-compatible | 自定义 | 自定义 |

## 三、并行调度流程

### 3.1 Promise.allSettled调度模式

```typescript
async function executeParallelTest(
  config: ABTestV2Config,
  dataset: TestDataset
): Promise<ParallelExecutionResult> {

  const modelResults = await Promise.allSettled(
    config.models.map(async (modelConfig) => {
      const provider = createProvider(modelConfig);
      const results: ModelResult[] = [];

      for (const sample of dataset.samples) {
        const startTime = Date.now();
        try {
          const response = await Promise.race([
            provider.invoke(sample.input, modelConfig.params),
            createTimeout(modelConfig.timeout_per_model)
          ]);
          results.push({
            sample_id: sample.id,
            model_id: modelConfig.id,
            response: response.content,
            tokens_used: response.tokens_used,
            latency_ms: Date.now() - startTime,
            status: "success"
          });
        } catch (error) {
          results.push({
            sample_id: sample.id,
            model_id: modelConfig.id,
            response: null,
            tokens_used: 0,
            latency_ms: Date.now() - startTime,
            status: "error",
            error: error.message
          });
        }
      }

      return { model_id: modelConfig.id, results };
    })
  );

  return aggregateResults(modelResults);
}
```

### 3.2 超时与重试策略

| 参数 | 值 | 说明 |
|------|-----|------|
| 单模型单次超时 | 30,000ms | 单个样本调用超时 |
| 单模型总超时 | 300,000ms | 单个模型所有样本总超时 |
| 重试次数 | 1次 | 仅对网络错误重试，不重试业务错误 |
| 重试延迟 | 1,000ms | 固定延迟，非指数退避 |
| 并发限制 | 8个模型同时 | 受API速率限制约束 |

### 3.3 错误隔离机制

```
模型A ──→ 调用成功 ──→ 结果收集 ✓
模型B ──→ 调用失败 ──→ 标记"测试失败"，继续其他模型 ✓
模型C ──→ 部分成功 ──→ 收集成功样本，标注失败样本 ✓
模型D ──→ 超时 ──→ 标记"超时"，继续其他模型 ✓
```

**隔离原则**：
1. 单模型失败不阻断其他模型测试
2. 单样本失败不中断同模型其他样本测试
3. 所有失败均记录详细错误信息
4. 最终报告标注所有失败项

## 四、进度追踪机制

### 4.1 进度事件

```typescript
interface ProgressEvent {
  test_id: string;
  timestamp: string;  // ISO 8601
  phase: "config_loaded" | "model_started" | "sample_completed" | "model_completed" | "test_completed";
  model_id?: string;
  sample_id?: string;
  progress: {
    completed_models: number;
    total_models: number;
    completed_samples: number;
    total_samples: number;
  };
  estimated_remaining_ms?: number;
}
```

### 4.2 进度计算

```
总进度 = (已完成模型数 / 总模型数) × 100%
单模型进度 = (已完成样本数 / 总样本数) × 100%
预估剩余时间 = 平均单样本耗时 × 剩余样本数
```

## 五、性能目标

| 指标 | 目标 | 说明 |
|------|------|------|
| N模型并发耗时 | ≤ 1.5 × 单模型耗时 | 并行度≥2时 |
| 单模型失败恢复 | ≤ 1s | 切换到下一模型 |
| 内存占用 | ≤ 2GB | 10000样本×8模型 |
| 进度更新频率 | ≤ 1s | 事件驱动 |

## 六、数据流图

```
ab_test_v2_config.yaml
         │
         ▼
  ┌──────────────┐     ┌──────────────┐
  │ ConfigLoader │ ──→ │ 校验引擎     │
  │ 配置加载器   │     │ (2-8模型,    │
  └──────────────┘     │  30-10000样本)│
                       └──────┬───────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │ Provider  │  │ Provider  │  │ Provider  │
        │ OpenAI    │  │ Anthropic │  │ Aliyun    │
        └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
              │               │               │
              └───────────────┼───────────────┘
                              │
                     ┌────────▼────────┐
                     │ 结果聚合器      │
                     │ Aggregator      │
                     └────────┬────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
        │ 统计评估  │  │ 胜率矩阵  │  │ 最优匹配  │
        │ 引擎      │  │ 生成器    │  │ 推荐器    │
        └───────────┘  └───────────┘  └───────────┘
```
