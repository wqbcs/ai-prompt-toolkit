# promptfoo 共存集成指南（双轨 CI 模式）

> 状态：R231 落地（P1-13）。定位：**互补不互替**——本工具做 PR gate 的确定性静态层，
> promptfoo 做 eval/红队的统计层。两者检测面不重叠，组合后覆盖"静态结构 + 语义行为"。

---

## 1. 分工边界（检测面矩阵）

| 维度 | prompt-cli（本工具） | promptfoo |
|---|---|---|
| 检测层 | 静态文本/代码内嵌面（prompt 结构、注入模式、供应链声明、可移植性、缓存友好度） | 行为面（LLM 实际输出的 pass/fail/安全断言） |
| 需要 LLM | 否（零调用，离线可跑） | 是（eval 需 API key 或本地模型） |
| 确定性 | 逐字节一致（重跑 1000 次裁决相同） | 采样方差（官方文档明说 non-deterministic，需 `repeat:3`+`repeat-min-pass:2` 对冲） |
| 延迟/成本 | <100ms/文件，0 token | 秒级/样本，按 token 计费 |
| CI 时机 | **每次 PR**（gate 红即阻） | **PR 后 / nightly**（结果进 artifact，阈值门禁可选） |
| 标准映射 | OWASP LLM Top 10 2026 + MITRE ATLAS + 等保 2.0 | OWASP/NIST 报告生成（合规报告面） |
| 典型失败信号 | 硬编码凭据/注入模式/声明矛盾/缓存不友好/供应链无来源校验 | 越狱成功/答案质量下降/输出格式漂移 |

**组合逻辑**：静态层挡"结构性已知模式"（便宜、快速、可复现），统计层挡"语义层未知行为"
（贵、慢、有方差）。只跑其一都有盲区；双轨组合=行业双轨共识（08 发现 2）的落地形态。

## 2. CI 双轨 workflow（可直接用）

```yaml
# .github/workflows/prompt-quality.yml
name: Prompt Quality (dual-track)

on:
  pull_request:
    paths:
      - 'prompts/**'
      - '**/*.prompt'
      - '**/*.prompt.md'
      - 'promptfooconfig.yaml'

jobs:
  # 轨道 1：确定性静态门禁（PR 必跑，阻塞合并）
  static-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0   # 增量需要 git 历史
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ai-prompt-toolkit
      # 增量门禁：只拦相对 base 的 NEW findings（brownfield 友好）
      - run: |
          prompt-cli lint prompts/ --incremental \
            --baseline baselines/templates-baseline.json \
            --gate
      # SARIF 进 Code Scanning（可选）
      - run: prompt-cli lint prompts/ --format sarif -o pr-sarif.sarif
      - uses: github/codeql-action/upload-sarif@v4
        if: always()
        with:
          sarif_file: pr-sarif.sarif

  # 轨道 2：promptfoo 行为评估（不阻塞合并，产出趋势数据）
  behavior-eval:
    runs-on: ubuntu-latest
    needs: static-gate   # 静态层红了不浪费 eval token
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
      - uses: actions/cache@v4
        with:
          path: ~/.cache/promptfoo
          key: ${{ runner.os }}-promptfoo-${{ hashFiles('prompts/**', 'promptfooconfig.yaml') }}
      - run: npx promptfoo@latest eval -c promptfooconfig.yaml --share -o results.json -o report.html
      # 质量门：失败数>0 只告警不阻（轨道 2 语义=趋势数据，不是门禁）
      - run: |
          FAILURES=$(jq '.results.stats.failures' results.json)
          if [ "$FAILURES" -gt 0 ]; then
            echo "::warning::promptfoo eval: $FAILURES failures (see report.html)"
          fi
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: promptfoo-results
          path: |
            results.json
            report.html
```

**轨道语义（为什么轨道 2 不阻塞合并）**：promptfoo eval 有采样方差，直接 gate 会制造
统计误红（garak 实践：no-op PR 误红率约 54% 的量级）。把方差层放在"趋势+告警"位、把
确定性层放在"门禁"位，是双轨分工的本质。若你的 eval 配置足够稳（`repeat-min-pass` 已校准），
可把轨道 2 改 `--fail-on-error` 阻塞，但需承担方差成本。

## 3. 本地双轨（开发循环）

```bash
# 每次改 prompt 后（<2s，可进 pre-commit）
prompt-cli lint -s my-prompt.md --gate

# 每次 PR 前（分钟级，需 API key）
npx promptfoo eval -c promptfooconfig.yaml
```

## 4. 与 promptfoo code-scans 的区别

promptfoo 官方 `code-scans`（2026 新增）是**其托管扫描服务**（需 PROMPTFOO_API_KEY），
检测面偏 prompt 文件的注入模式——与本工具静态面部分重叠。区别：

| | prompt-cli lint | promptfoo code-scans |
|---|---|---|
| 运行位置 | 本地/自有 CI（air-gap 可用） | promptfoo 托管（数据出域） |
| 确定性 | 逐字节可复现 | 未公开复现性承诺 |
| 标准映射 | OWASP 2026+ATLAS+等保 2.0 三标准 | 未公开 |
| 增量门禁 | `--incremental --baseline --gate` 本地闭环 | `--base` 分支对比 |
| 双基线公开 | 误报/漏检时间序列可下载复现 | 无 |

共存无冲突：数据敏感（air-gap/信创）场景用本工具静态层；已用 promptfoo 生态的团队
两套并存，检测面取并集即可（重复 finding 以本工具裁决为准——确定性裁决可审计）。

## 5. 边界诚实声明

- 本工具静态层**挡不住**语义层创意越狱（需要 eval 层/promptfoo 或运行时防护）
- promptfoo eval **挡不住**静态结构缺陷（硬编码凭据、声明矛盾——输出正确也可能带雷）
- 两者组合仍**挡不住**运行时隐式投毒（MCP-ITP 类，见 README MCP 边界声明）
