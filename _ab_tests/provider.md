# 模型Provider接口设计

## 1. 架构总览

### 1.1 数据流图

```
┌───────────────────┐
│  A/B Test Engine   │
└─────────┬─────────┘
          │ invoke(request)
          ▼
┌─────────────────────┐
│  Provider Router     │────────── 凭证隔离层 (AES-256-GCM)
└─────────┬───────────┘
          │
    ┌─────┼──────┬──────────┐
    ▼     ▼      ▼          ▼
┌──────┐┌──────┐┌──────┐┌──────┐
│OpenAI││Anthro││Aliyun││Huawei│
│Prov. ││pic   ││Prov. ││Prov. │
└──┬───┘└──┬───┘└──┬───┘└──┬───┘
   │       │       │       │
   ▼       ▼       ▼       ▼
 API     API     API     API
调用    调用    调用    调用
```

### 1.2 核心流程

```
ProviderRequest → 凭证解密 → 速率限制检查 → HTTP请求 → 重试策略 → 响应验证 → ProviderResponse
```

---

## 2. Provider抽象接口

### 2.1 接口定义

```typescript
interface ProviderRequest {
  modelId: string;
  messages: ChatMessage[];
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  stopSequences?: string[];
  metadata?: Record<string, unknown>;
}

interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface ProviderResponse {
  id: string;
  modelId: string;
  content: string;
  usage: TokenUsage;
  latencyMs: number;
  finishReason: "stop" | "max_tokens" | "content_filter" | "error";
  rawResponse?: unknown;
}

interface TokenUsage {
  promptTokens: number;
  completionTokens: number;
  totalTokens: number;
}

interface CostEstimate {
  promptCost: number;
  completionCost: number;
  totalCost: number;
  currency: string;
}

interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

interface Provider {
  readonly name: string;
  readonly providerId: string;

  invoke(request: ProviderRequest): Promise<ProviderResponse>;
  validate(request: ProviderRequest): ValidationResult;
  estimateCost(request: ProviderRequest): CostEstimate;
  getSupportedModels(): ModelInfo[];
  healthCheck(): Promise<boolean>;
}

interface ModelInfo {
  modelId: string;
  displayName: string;
  contextWindow: number;
  maxOutputTokens: number;
  pricing: {
    promptPer1k: number;
    completionPer1k: number;
    currency: string;
  };
  capabilities: string[];
}
```

### 2.2 抽象基类

```typescript
abstract class BaseProvider implements Provider {
  abstract readonly name: string;
  abstract readonly providerId: string;

  protected credentialVault: CredentialVault;
  protected rateLimiter: RateLimiter;
  protected retryPolicy: RetryPolicy;
  protected httpClient: HttpClient;

  constructor(config: ProviderConfig) {
    this.credentialVault = new AES256GCMCredentialVault(config.encryptionKey);
    this.rateLimiter = new TokenBucketRateLimiter(config.rateLimits);
    this.retryPolicy = new ExponentialBackoffRetryPolicy(config.retryConfig);
    this.httpClient = new HttpClient(config.httpConfig);
  }

  abstract invoke(request: ProviderRequest): Promise<ProviderResponse>;
  abstract validate(request: ProviderRequest): ValidationResult;
  abstract estimateCost(request: ProviderRequest): CostEstimate;
  abstract getSupportedModels(): ModelInfo[];

  async healthCheck(): Promise<boolean> {
    try {
      const request: ProviderRequest = {
        modelId: this.getSupportedModels()[0].modelId,
        messages: [{ role: "user", content: "ping" }],
        maxTokens: 5
      };
      const response = await this.invoke(request);
      return response.finishReason !== "error";
    } catch {
      return false;
    }
  }

  protected async executeWithRetry(
    request: ProviderRequest,
    executor: () => Promise<ProviderResponse>
  ): Promise<ProviderResponse> {
    await this.rateLimiter.acquire();
    return this.retryPolicy.execute(executor);
  }

  protected async getCredential(key: string): Promise<string> {
    return this.credentialVault.decrypt(key);
  }
}
```

---

## 3. Provider实现

### 3.1 OpenAI Provider

```typescript
class OpenAIProvider extends BaseProvider {
  readonly name = "OpenAI";
  readonly providerId = "openai";

  private static readonly MODELS: ModelInfo[] = [
    {
      modelId: "gpt-4o",
      displayName: "GPT-4o",
      contextWindow: 128000,
      maxOutputTokens: 16384,
      pricing: { promptPer1k: 0.0025, completionPer1k: 0.01, currency: "USD" },
      capabilities: ["chat", "function_calling", "json_mode", "vision"]
    },
    {
      modelId: "gpt-4o-mini",
      displayName: "GPT-4o Mini",
      contextWindow: 128000,
      maxOutputTokens: 16384,
      pricing: { promptPer1k: 0.00015, completionPer1k: 0.0006, currency: "USD" },
      capabilities: ["chat", "function_calling", "json_mode"]
    },
    {
      modelId: "o3",
      displayName: "o3",
      contextWindow: 200000,
      maxOutputTokens: 100000,
      pricing: { promptPer1k: 0.002, completionPer1k: 0.008, currency: "USD" },
      capabilities: ["chat", "function_calling", "reasoning"]
    }
  ];

  async invoke(request: ProviderRequest): Promise<ProviderResponse> {
    const apiKey = await this.getCredential("openai_api_key");
    const startTime = Date.now();

    return this.executeWithRetry(request, async () => {
      const response = await this.httpClient.post(
        "https://api.openai.com/v1/chat/completions",
        {
          model: request.modelId,
          messages: request.messages,
          temperature: request.temperature ?? 0.7,
          max_tokens: request.maxTokens ?? 4096,
          top_p: request.topP,
          stop: request.stopSequences
        },
        { Authorization: `Bearer ${apiKey}` }
      );

      return {
        id: response.id,
        modelId: response.model,
        content: response.choices[0].message.content,
        usage: {
          promptTokens: response.usage.prompt_tokens,
          completionTokens: response.usage.completion_tokens,
          totalTokens: response.usage.total_tokens
        },
        latencyMs: Date.now() - startTime,
        finishReason: response.choices[0].finish_reason,
        rawResponse: response
      };
    });
  }

  validate(request: ProviderRequest): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const model = OpenAIProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) {
      errors.push(`不支持的模型: ${request.modelId}`);
    }

    if (request.temperature !== undefined && (request.temperature < 0 || request.temperature > 2)) {
      errors.push("temperature 范围: 0-2");
    }

    if (request.messages.length === 0) {
      errors.push("messages 不能为空");
    }

    if (model && request.maxTokens && request.maxTokens > model.maxOutputTokens) {
      warnings.push(`maxTokens ${request.maxTokens} 超过模型上限 ${model.maxOutputTokens}`);
    }

    return { valid: errors.length === 0, errors, warnings };
  }

  estimateCost(request: ProviderRequest): CostEstimate {
    const model = OpenAIProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) return { promptCost: 0, completionCost: 0, totalCost: 0, currency: "USD" };

    const estimatedPromptTokens = request.messages.reduce(
      (sum, m) => sum + Math.ceil(m.content.length / 4), 0
    );
    const estimatedCompletionTokens = request.maxTokens ?? 4096;

    const promptCost = (estimatedPromptTokens / 1000) * model.pricing.promptPer1k;
    const completionCost = (estimatedCompletionTokens / 1000) * model.pricing.completionPer1k;

    return {
      promptCost,
      completionCost,
      totalCost: promptCost + completionCost,
      currency: model.pricing.currency
    };
  }

  getSupportedModels(): ModelInfo[] {
    return OpenAIProvider.MODELS;
  }
}
```

### 3.2 Anthropic Provider

```typescript
class AnthropicProvider extends BaseProvider {
  readonly name = "Anthropic";
  readonly providerId = "anthropic";

  private static readonly MODELS: ModelInfo[] = [
    {
      modelId: "claude-sonnet-4-20250514",
      displayName: "Claude Sonnet 4",
      contextWindow: 200000,
      maxOutputTokens: 64000,
      pricing: { promptPer1k: 0.003, completionPer1k: 0.015, currency: "USD" },
      capabilities: ["chat", "tool_use", "vision", "extended_thinking"]
    },
    {
      modelId: "claude-3-5-haiku-20241022",
      displayName: "Claude 3.5 Haiku",
      contextWindow: 200000,
      maxOutputTokens: 8192,
      pricing: { promptPer1k: 0.001, completionPer1k: 0.005, currency: "USD" },
      capabilities: ["chat", "tool_use"]
    }
  ];

  async invoke(request: ProviderRequest): Promise<ProviderResponse> {
    const apiKey = await this.getCredential("anthropic_api_key");
    const startTime = Date.now();

    const systemMessage = request.messages.find(m => m.role === "system");
    const nonSystemMessages = request.messages.filter(m => m.role !== "system");

    return this.executeWithRetry(request, async () => {
      const body: Record<string, unknown> = {
        model: request.modelId,
        messages: nonSystemMessages.map(m => ({ role: m.role, content: m.content })),
        max_tokens: request.maxTokens ?? 4096,
        temperature: request.temperature ?? 0.7,
        top_p: request.topP,
        stop_sequences: request.stopSequences
      };
      if (systemMessage) {
        body.system = systemMessage.content;
      }

      const response = await this.httpClient.post(
        "https://api.anthropic.com/v1/messages",
        body,
        {
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
          "content-type": "application/json"
        }
      );

      return {
        id: response.id,
        modelId: response.model,
        content: response.content[0].text,
        usage: {
          promptTokens: response.usage.input_tokens,
          completionTokens: response.usage.output_tokens,
          totalTokens: response.usage.input_tokens + response.usage.output_tokens
        },
        latencyMs: Date.now() - startTime,
        finishReason: response.stop_reason === "end_turn" ? "stop" : response.stop_reason,
        rawResponse: response
      };
    });
  }

  validate(request: ProviderRequest): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const model = AnthropicProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) {
      errors.push(`不支持的模型: ${request.modelId}`);
    }

    if (request.maxTokens === undefined || request.maxTokens <= 0) {
      errors.push("Anthropic API 要求 max_tokens > 0");
    }

    if (request.temperature !== undefined && (request.temperature < 0 || request.temperature > 1)) {
      errors.push("temperature 范围: 0-1");
    }

    return { valid: errors.length === 0, errors, warnings };
  }

  estimateCost(request: ProviderRequest): CostEstimate {
    const model = AnthropicProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) return { promptCost: 0, completionCost: 0, totalCost: 0, currency: "USD" };

    const estimatedPromptTokens = request.messages.reduce(
      (sum, m) => sum + Math.ceil(m.content.length / 4), 0
    );
    const estimatedCompletionTokens = request.maxTokens ?? 4096;

    const promptCost = (estimatedPromptTokens / 1000) * model.pricing.promptPer1k;
    const completionCost = (estimatedCompletionTokens / 1000) * model.pricing.completionPer1k;

    return { promptCost, completionCost, totalCost: promptCost + completionCost, currency: model.pricing.currency };
  }

  getSupportedModels(): ModelInfo[] {
    return AnthropicProvider.MODELS;
  }
}
```

### 3.3 Aliyun Provider

```typescript
class AliyunProvider extends BaseProvider {
  readonly name = "阿里云百炼";
  readonly providerId = "aliyun";

  private static readonly MODELS: ModelInfo[] = [
    {
      modelId: "qwen-max",
      displayName: "通义千问-Max",
      contextWindow: 32768,
      maxOutputTokens: 8192,
      pricing: { promptPer1k: 0.02, completionPer1k: 0.06, currency: "CNY" },
      capabilities: ["chat", "function_calling", "json_mode"]
    },
    {
      modelId: "qwen-plus",
      displayName: "通义千问-Plus",
      contextWindow: 131072,
      maxOutputTokens: 8192,
      pricing: { promptPer1k: 0.004, completionPer1k: 0.012, currency: "CNY" },
      capabilities: ["chat", "function_calling", "json_mode"]
    },
    {
      modelId: "qwen-turbo",
      displayName: "通义千问-Turbo",
      contextWindow: 131072,
      maxOutputTokens: 8192,
      pricing: { promptPer1k: 0.003, completionPer1k: 0.006, currency: "CNY" },
      capabilities: ["chat", "function_calling"]
    }
  ];

  async invoke(request: ProviderRequest): Promise<ProviderResponse> {
    const apiKey = await this.getCredential("aliyun_api_key");
    const startTime = Date.now();

    return this.executeWithRetry(request, async () => {
      const response = await this.httpClient.post(
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        {
          model: request.modelId,
          messages: request.messages,
          temperature: request.temperature ?? 0.7,
          max_tokens: request.maxTokens ?? 4096,
          top_p: request.topP,
          stop: request.stopSequences
        },
        { Authorization: `Bearer ${apiKey}` }
      );

      return {
        id: response.id,
        modelId: response.model,
        content: response.choices[0].message.content,
        usage: {
          promptTokens: response.usage.prompt_tokens,
          completionTokens: response.usage.completion_tokens,
          totalTokens: response.usage.total_tokens
        },
        latencyMs: Date.now() - startTime,
        finishReason: response.choices[0].finish_reason,
        rawResponse: response
      };
    });
  }

  validate(request: ProviderRequest): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const model = AliyunProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) {
      errors.push(`不支持的模型: ${request.modelId}`);
    }

    if (request.temperature !== undefined && (request.temperature < 0 || request.temperature > 2)) {
      errors.push("temperature 范围: 0-2");
    }

    return { valid: errors.length === 0, errors, warnings };
  }

  estimateCost(request: ProviderRequest): CostEstimate {
    const model = AliyunProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) return { promptCost: 0, completionCost: 0, totalCost: 0, currency: "CNY" };

    const estimatedPromptTokens = request.messages.reduce(
      (sum, m) => sum + Math.ceil(m.content.length / 3), 0
    );
    const estimatedCompletionTokens = request.maxTokens ?? 4096;

    const promptCost = (estimatedPromptTokens / 1000) * model.pricing.promptPer1k;
    const completionCost = (estimatedCompletionTokens / 1000) * model.pricing.completionPerk;

    return { promptCost, completionCost, totalCost: promptCost + completionCost, currency: model.pricing.currency };
  }

  getSupportedModels(): ModelInfo[] {
    return AliyunProvider.MODELS;
  }
}
```

### 3.4 Huawei Provider

```typescript
class HuaweiProvider extends BaseProvider {
  readonly name = "华为云盘古";
  readonly providerId = "huawei";

  private static readonly MODELS: ModelInfo[] = [
    {
      modelId: "pangu-ultra",
      displayName: "盘古-Ultra",
      contextWindow: 32768,
      maxOutputTokens: 4096,
      pricing: { promptPer1k: 0.012, completionPer1k: 0.036, currency: "CNY" },
      capabilities: ["chat", "function_calling"]
    },
    {
      modelId: "pangu-pro",
      displayName: "盘古-Pro",
      contextWindow: 32768,
      maxOutputTokens: 4096,
      pricing: { promptPer1k: 0.006, completionPer1k: 0.018, currency: "CNY" },
      capabilities: ["chat", "function_calling"]
    }
  ];

  async invoke(request: ProviderRequest): Promise<ProviderResponse> {
    const apiKey = await this.getCredential("huawei_api_key");
    const startTime = Date.now();

    return this.executeWithRetry(request, async () => {
      const response = await this.httpClient.post(
        "https://pangu-api.myhuaweicloud.com/v1/chat/completions",
        {
          model: request.modelId,
          messages: request.messages,
          temperature: request.temperature ?? 0.7,
          max_tokens: request.maxTokens ?? 4096,
          top_p: request.topP
        },
        { "X-Auth-Token": apiKey }
      );

      return {
        id: response.id,
        modelId: response.model,
        content: response.choices[0].message.content,
        usage: {
          promptTokens: response.usage.prompt_tokens,
          completionTokens: response.usage.completion_tokens,
          totalTokens: response.usage.total_tokens
        },
        latencyMs: Date.now() - startTime,
        finishReason: response.choices[0].finish_reason,
        rawResponse: response
      };
    });
  }

  validate(request: ProviderRequest): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    const model = HuaweiProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) {
      errors.push(`不支持的模型: ${request.modelId}`);
    }

    if (request.temperature !== undefined && (request.temperature < 0 || request.temperature > 1)) {
      errors.push("temperature 范围: 0-1");
    }

    return { valid: errors.length === 0, errors, warnings };
  }

  estimateCost(request: ProviderRequest): CostEstimate {
    const model = HuaweiProvider.MODELS.find(m => m.modelId === request.modelId);
    if (!model) return { promptCost: 0, completionCost: 0, totalCost: 0, currency: "CNY" };

    const estimatedPromptTokens = request.messages.reduce(
      (sum, m) => sum + Math.ceil(m.content.length / 3), 0
    );
    const estimatedCompletionTokens = request.maxTokens ?? 4096;

    const promptCost = (estimatedPromptTokens / 1000) * model.pricing.promptPer1k;
    const completionCost = (estimatedCompletionTokens / 1000) * model.pricing.completionPer1k;

    return { promptCost, completionCost, totalCost: promptCost + completionCost, currency: model.pricing.currency };
  }

  getSupportedModels(): ModelInfo[] {
    return HuaweiProvider.MODELS;
  }
}
```

---

## 4. 凭证隔离（AES-256-GCM加密）

### 4.1 凭证存储架构

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Provider    │────▶│  CredentialVault  │────▶│  Encrypted Store │
│  (请求凭证) │     │  (加解密层)       │     │  (磁盘/内存)     │
└─────────────┘     └──────────────────┘     └─────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Master Key │
                    │  (环境变量) │
                    └─────────────┘
```

### 4.2 凭证隔离接口

```typescript
interface CredentialVault {
  encrypt(plaintext: string, keyId: string): EncryptedCredential;
  decrypt(keyId: string): Promise<string>;
  rotateKey(oldKeyId: string, newKeyId: string): void;
  revoke(keyId: string): void;
}

interface EncryptedCredential {
  keyId: string;
  algorithm: "AES-256-GCM";
  iv: string;
  ciphertext: string;
  authTag: string;
  createdAt: string;
}

class AES256GCMCredentialVault implements CredentialVault {
  private masterKey: Buffer;
  private cache: Map<string, EncryptedCredential>;
  private decryptedCache: Map<string, string>;

  constructor(masterKeyHex: string) {
    this.masterKey = Buffer.from(masterKeyHex, "hex");
    this.cache = new Map();
    this.decryptedCache = new Map();
  }

  encrypt(plaintext: string, keyId: string): EncryptedCredential {
    const iv = crypto.randomBytes(12);
    const cipher = crypto.createCipheriv("aes-256-gcm", this.masterKey, iv);

    let ciphertext = cipher.update(plaintext, "utf8", "hex");
    ciphertext += cipher.final("hex");

    const authTag = cipher.getAuthTag();

    const credential: EncryptedCredential = {
      keyId,
      algorithm: "AES-256-GCM",
      iv: iv.toString("hex"),
      ciphertext,
      authTag: authTag.toString("hex"),
      createdAt: new Date().toISOString()
    };

    this.cache.set(keyId, credential);
    this.decryptedCache.delete(keyId);
    return credential;
  }

  async decrypt(keyId: string): Promise<string> {
    const cached = this.decryptedCache.get(keyId);
    if (cached) return cached;

    const credential = this.cache.get(keyId);
    if (!credential) throw new Error(`凭证不存在: ${keyId}`);

    const iv = Buffer.from(credential.iv, "hex");
    const authTag = Buffer.from(credential.authTag, "hex");

    const decipher = crypto.createDecipheriv("aes-256-gcm", this.masterKey, iv);
    decipher.setAuthTag(authTag);

    let plaintext = decipher.update(credential.ciphertext, "hex", "utf8");
    plaintext += decipher.final("utf8");

    this.decryptedCache.set(keyId, plaintext);
    return plaintext;
  }

  rotateKey(oldKeyId: string, newKeyId: string): void {
    const credential = this.cache.get(oldKeyId);
    if (!credential) throw new Error(`凭证不存在: ${oldKeyId}`);
    this.cache.set(newKeyId, { ...credential, keyId: newKeyId });
    this.cache.delete(oldKeyId);
    this.decryptedCache.delete(oldKeyId);
    this.decryptedCache.delete(newKeyId);
  }

  revoke(keyId: string): void {
    this.cache.delete(keyId);
    this.decryptedCache.delete(keyId);
  }
}
```

### 4.3 凭证隔离规则

| 规则             | 描述                                              |
|------------------|---------------------------------------------------|
| 凭证不落盘       | 解密后的凭证仅存在于内存，永不写入磁盘              |
| Provider隔离     | 每个Provider使用独立的keyId，凭证不跨Provider共享    |
| 短期缓存         | 解密缓存TTL=5min，超时自动清除                      |
| 主密钥轮换       | 支持主密钥轮换，旧密钥解密后用新密钥重新加密          |
| 审计日志         | 所有凭证访问操作记录审计日志                          |

---

## 5. 速率限制与重试

### 5.1 Token Bucket速率限制器

```typescript
interface RateLimitConfig {
  requestsPerSecond: number;
  requestsPerMinute: number;
  tokensPerMinute: number;
  burstSize: number;
}

class TokenBucketRateLimiter {
  private tokens: number;
  private lastRefillTime: number;
  private readonly maxTokens: number;
  private readonly refillRate: number;
  private minuteCounter: { count: number; resetTime: number };

  constructor(config: RateLimitConfig) {
    this.maxTokens = config.burstSize;
    this.tokens = config.burstSize;
    this.refillRate = config.requestsPerSecond;
    this.lastRefillTime = Date.now();
    this.minuteCounter = { count: 0, resetTime: Date.now() + 60000 };
  }

  async acquire(): Promise<void> {
    this.refill();

    if (this.minuteCounter.count >= this.minuteCounter.resetTime) {
      throw new Error("速率限制: 超过每分钟请求上限");
    }

    if (this.tokens < 1) {
      const waitTime = (1 - this.tokens) / this.refillRate * 1000;
      await new Promise(resolve => setTimeout(resolve, waitTime));
      this.refill();
    }

    this.tokens -= 1;
    this.minuteCounter.count += 1;
  }

  private refill(): void {
    const now = Date.now();
    const elapsed = (now - this.lastRefillTime) / 1000;
    this.tokens = Math.min(this.maxTokens, this.tokens + elapsed * this.refillRate);
    this.lastRefillTime = now;

    if (now > this.minuteCounter.resetTime) {
      this.minuteCounter = { count: 0, resetTime: now + 60000 };
    }
  }
}
```

### 5.2 指数退避重试策略

```typescript
interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
  backoffMultiplier: number;
  retryableStatusCodes: number[];
  jitterFactor: number;
}

class ExponentialBackoffRetryPolicy {
  private config: RetryConfig;

  constructor(config: Partial<RetryConfig> = {}) {
    this.config = {
      maxRetries: 3,
      baseDelayMs: 1000,
      maxDelayMs: 30000,
      backoffMultiplier: 2,
      retryableStatusCodes: [429, 500, 502, 503, 504],
      jitterFactor: 0.25,
      ...config
    };
  }

  async execute<T>(fn: () => Promise<T>): Promise<T> {
    let lastError: Error | null = null;

    for (let attempt = 0; attempt <= this.config.maxRetries; attempt++) {
      try {
        return await fn();
      } catch (error) {
        lastError = error as Error;

        if (!this.isRetryable(error) || attempt === this.config.maxRetries) {
          throw error;
        }

        const delay = this.calculateDelay(attempt);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }

    throw lastError;
  }

  private calculateDelay(attempt: number): number {
    const baseDelay = this.config.baseDelayMs * Math.pow(this.config.backoffMultiplier, attempt);
    const jitter = baseDelay * this.config.jitterFactor * (Math.random() * 2 - 1);
    return Math.min(this.config.maxDelayMs, Math.max(0, baseDelay + jitter));
  }

  private isRetryable(error: unknown): boolean {
    if (error instanceof HttpError) {
      return this.config.retryableStatusCodes.includes(error.statusCode);
    }
    if (error instanceof NetworkError) {
      return true;
    }
    return false;
  }
}
```

---

## 6. 性能目标

| 指标                    | 目标值          | 测量方法                           |
|-------------------------|-----------------|------------------------------------|
| Provider初始化耗时      | < 50ms          | 从构造函数调用到就绪               |
| 凭证解密耗时            | < 1ms           | AES-256-GCM单次解密                |
| 速率限制检查耗时        | < 0.1ms         | Token Bucket令牌获取               |
| 单次invoke端到端延迟    | 取决于模型API   | 不含网络时间< 5ms                  |
| 并发Provider调用        | > 50 并发       | 同时调用不同Provider无阻塞         |
| 凭证缓存命中率          | > 90%           | 5分钟TTL内的缓存命中               |
| 重试成功率              | > 95%           | 在可重试错误下的最终成功率          |
