# LLM Provider 矩阵表（P5-09）

> 真源 = `src/ai_prompt_toolkit/ab_test/provider.py`（`ProviderType` 枚举 +
> `_PROVIDER_DEFAULT_ENDPOINTS` + `_PROVIDER_ENV_VARS`）；本表为其投影，
> 2026-10-15 R290 生成。注册表变更时以代码为准重新生成本表（本文件非真源）。
> 覆盖度与 README「25种LLM Provider」指标同源（门禁机器核对）。

## 调用模式（25 provider 通用）

- **无 API key 或 `SIMULATED_MODE` 开启** → 模拟结果（确定性、零真实调用、零
  成本）——CI/测试默认形态；
- **key 已配 + `SIMULATED_MODE` 关闭** → 真实调用（OpenAI 兼容
  `/chat/completions` 端点，成本跟踪 + 指数退避重试）。

## 矩阵表（25 provider，注册表枚举序）

| Provider | type 值 | 默认端点 | 环境变量 | 形态 |
|---|---|---|---|---|
| OpenAI | `openai` | https://api.openai.com/v1 | `OPENAI_API_KEY` | 云 |
| Anthropic | `anthropic` | https://api.anthropic.com/v1 | `ANTHROPIC_API_KEY` | 云 |
| 阿里云（通义） | `aliyun` | https://dashscope.aliyuncs.com/compatible-mode/v1 | `ALIYUN_API_KEY` | 云 |
| DeepSeek | `deepseek` | https://api.deepseek.com/v1 | `DEEPSEEK_API_KEY` | 云 |
| 华为 | `huawei` | https://modelarts.cn-north-4.myhuaweicloud.com/v1 | `HUAWEI_API_KEY` | 云 |
| 盘古 | `pangu` | https://pangu-api.cn-north-4.myhuaweicloud.com/v1 | `HUAWEI_CLOUD_AK` | 云 |
| Google | `google` | https://generativelanguage.googleapis.com/v1beta/openai | `GOOGLE_API_KEY` | 云 |
| Mistral | `mistral` | https://api.mistral.ai/v1 | `MISTRAL_API_KEY` | 云 |
| Cohere | `cohere` | https://api.cohere.com/v2 | `COHERE_API_KEY` | 云 |
| Groq | `groq` | https://api.groq.com/openai/v1 | `GROQ_API_KEY` | 云 |
| Together | `together` | https://api.together.xyz/v1 | `TOGETHER_API_KEY` | 云 |
| Fireworks | `fireworks` | https://api.fireworks.ai/inference/v1 | `FIREWORKS_API_KEY` | 云 |
| Perplexity | `perplexity` | https://api.perplexity.ai | `PERPLEXITY_API_KEY` | 云 |
| Ollama | `ollama` | http://localhost:11434/v1 | —（本地服务即端点） | 本地 |
| LM Studio | `lmstudio` | http://localhost:1234/v1 | —（本地服务即端点） | 本地 |
| 智谱 | `zhipu` | https://open.bigmodel.cn/api/paas/v4 | `ZHIPU_API_KEY` | 云 |
| Moonshot | `moonshot` | https://api.moonshot.cn/v1 | `MOONSHOT_API_KEY` | 云 |
| 百度 | `baidu` | https://qianfan.baidubce.com/v2 | `BAIDU_API_KEY` | 云 |
| MiniMax | `minimax` | https://api.minimax.chat/v1 | `MINIMAX_API_KEY` | 云 |
| 华为 ModelArts | `huawei_modelarts` | https://infer.cn-north-4.myhuaweicloud.com | `HUAWEI_CLOUD_AK` | 云 |
| 豆包 | `doubao` | https://ark.cn-beijing.volces.com/api/v3 | `DOUBAO_API_KEY` | 云 |
| 星火 | `spark` | https://spark-api-open.xf-yun.com/v1 | `SPARK_API_KEY` | 云 |
| 百川 | `baichuan` | https://api.baichuan-ai.com/v1 | `BAICHUAN_API_KEY` | 云 |
| SenseNova | `sensenova` | https://api.sensenova.cn/v1 | `SENSENOVA_API_KEY` | 云 |
| FunctionGraph | `functiongraph` | https://functiongraph.cn-north-4.myhuaweicloud.com | `HUAWEI_CLOUD_AK` | 云 |

## 备注（如实留痕）

- R291 注册表漂移修复：`HUAWEI` 条目原为百度文心旧路径（`aip.baidubce.com/.../wenxinworkshop`）、
  `PANGU` 条目原为 `infer` 域名——均与各 provider 代码真实调用默认不一致（本表从注册表
  生成，同步错）。已修正对齐 `providers/huawei.py`/`pangu.py` 并加 3 条漂移护栏测试
  （`HUAWEI_MODELARTS` 条目审计误报，原即正确）。漂移影响面 = `run_health_check`/
  `doctor` 端点展示+可达性探测，非真实调用路径（各 provider invoke 自带默认值）。
- `HUAWEI_CLOUD_AK` 为 3 个 provider 共享（PANGU / HUAWEI_MODELARTS /
  FUNCTIONGRAPH，华为云统一凭据）。
- 2 个本地 provider（OLLAMA / LMSTUDIO）无环境变量——本地服务地址即端点，
  天然适配 air-gap 场景（与 06 §4 镜像通道同场景）。
