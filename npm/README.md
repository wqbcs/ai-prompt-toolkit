# ai-prompt-toolkit (npm)

AI prompt lint / security scan / quality gate — deterministic, zero-LLM.

本包是 **PyPI 包 [`ai-prompt-toolkit`](https://pypi.org/project/ai-prompt-toolkit/) 的薄包装器**
（零 npm 依赖，纯 Node 内建模块）：为 JS/TS 生态提供 `npx` 体验，
全部检测逻辑在 Python 包内（单一真源），版本 1:1 镜像。

## 用法

```bash
# 零安装（npx 自动拉取包装器 + 首次运行自动装 Python 包到 ~/.cache/ai-prompt-toolkit/npm）
npx ai-prompt-toolkit lint -t your-prompt.md
npx ai-prompt-toolkit scan -t .
npx ai-prompt-toolkit baseline

# 项目内固定（package.json devDependencies）
npm install -D ai-prompt-toolkit
npx ai-prompt-toolkit lint -t prompts/ --gate
```

## 环境要求

- Node.js >= 18（仅跑包装器）
- Python 3.10+（在 PATH 中；包装器自动定位 `python3`/`python`/`py -3`）

## 环境变量

| 变量 | 作用 |
|---|---|
| `AIPROMPT_TOOLKIT_CACHE` | 覆盖 Python 包缓存目录（默认 `~/.cache/ai-prompt-toolkit/npm`） |
| `AIPROMPT_TOOLKIT_VERSION` | 覆盖安装的 Python 包版本（默认 pin 到与包装器同版本） |
| `PIP_INDEX_URL` | 私有 PyPI 镜像/代理透传 |

## CI 示例（Node 项目, GitHub Actions）

```yaml
- name: Prompt gate
  run: npx ai-prompt-toolkit lint -t prompts/ --gate
  env:
    PIP_INDEX_URL: https://pypi.org/simple/
```

> 无 Python 的 CI runner：先加 `actions/setup-python@v5`，
> 或改用 uvx 形态 `uvx --from ai-prompt-toolkit prompt-cli ...`（配 `setup-uv`）。

## 边界

- 本包不做任何检测逻辑；行为 = 同版本 PyPI 包（确定性可复现）；
- 升级 = `npm update ai-prompt-toolkit`（与 PyPI 版本锁步发布）。
