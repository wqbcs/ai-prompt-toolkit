# R221-C1: 确定性签名 Feed 设计（不实现 — 方案先行）

> 状态: **设计稿（DESIGN ONLY）**— 本文档只定义目标/边界/接口/信任链，
> 不含实现代码。实现前置条件见 §10。
> 核心价值锚: 签名演化快（jailbreak techniques evolve fast, refresh
> periodically — 调研痛点 3），但**工具升级节奏跟不上威胁演化**。签名 feed
> 让检测签名可热更新，且**更新过程本身保持确定性 + 可审计**（与"零 LLM 成本
> 确定性 CI 门禁"核心定位同构 — feed 是门禁的弹药补给线，不是第二套裁决器）。

---

## 1. 定位反问（鬼才 PM 过滤，写进设计防漂移）

| 问 | 答 |
|---|---|
| 这服务核心价值吗？ | 是 — 核心价值="确定性可复现的 CI 门禁"。签名老化 = 门禁漏检老化，feed 是**维护门禁可信度**的机制，不是新能力 |
| 是不是 scope bloat？ | 边界已锁死（§2 非目标）：feed **只供给签名**（正则/字符集），**不做语义裁决**、**不引入 LLM**、**不改内置 261 规则** |
| 谁在用？没有用户为什么设计？ | 发布前必须就绪（C2 发布是下一战略件）：竞品 prompt-shield-signatures 证明"签名 feed + 签名校验"是市场已验证模式；我们自己 33 条扩样里 8 条注入/越狱探针的签名会随时间老化 |
| 低价值打磨风险？ | 若把 feed 做成"自动拉取+自动生效" = 供应链攻击面 + 门禁非确定性（同一 prompt 两次 CI 因 feed 更新不同而翻裁决）。**本设计强制 opt-in + 版本锁定 + 签名校验，三者缺一不落地** |

## 2. 目标 / 非目标

**目标**
1. 攻击签名（注入标记/越狱话术/编码形态的正则签名）可**热更新**，不升工具版本
2. feed 更新**不破坏确定性**：同一 (prompt, 工具版本, feed 版本) 三元组 → 逐字节一致裁决
3. feed 供应链安全：未通过 ed25519 签名校验的 feed **拒绝加载**（fail-closed）
4. feed 质量可度量：feed 自带 golden 探针子集，加载后跑漏检/FP 双基线

**非目标（明确不做）**
- ❌ 不改内置 261 规则的判定逻辑（feed 只**新增** CUSTOM* 规则，内置规则冻结）
- ❌ 不自动从网络拉取（默认离线；拉取是用户显式动作 `prompt-cli feed update`）
- ❌ 不做 LLM 语义裁决（与零 LLM 核心矛盾）
- ❌ 不跨工具共享 feed 格式（格式私有，避免被别家 feed 污染）
- ❌ 不做行级 waiver（feed 规则沿用现有文件级 waiver，L3-13 落地后统一升级）

## 3. 复用现有地基（不造轮子清单）

| 组件 | 现有位置 | feed 复用方式 |
|---|---|---|
| YAML 规则热加载 | `linter/rule_loader_yaml.py` `load_rules_from_yaml` | feed 文件 = 该格式 + 签名头扩展（§4），**零新加载器** |
| 自定义规则执行 | `linter/custom_rules.py` + `lint --config` | feed 规则以 CUSTOM* 前缀并入，走既有执行路径 |
| 规则 ID 命名 | P + 三位数字顺延（L3-3 只增不跳） | feed 规则用 `F` + 四位（F0001…），与 P 系**命名空间隔离**（防 ID 冲突） |
| waiver 机制 | `linter/waivers.py`（`promptlint:ignore F0001`） | feed 规则自动继承（`_RULE_ID_RE` 需扩 `^F\d{4}$`） |
| 双基线 | `check_false_positives.py` / `check_miss_rate.py` | feed 自带探针 → 加载时验证（§6.4），CI 可断言"feed 更新不升误报" |
| 棘轮纪律 | `check_mypy_ratchet.py` 模式 | feed 版本棘轮：只升不降（CI 环境锁版本） |
| 版本一致性 | `check_version_consistency.py` | feed 版本进 lint report 元数据（审计链） |

**参考（调研结论，非依赖）**: prompt-shield-signatures（ed25519 签名威胁情报 feed，
每日刷新）— 验证了"签名 feed + 校验"模式的市场可行性；garak YAML probe 配置 —
验证了 YAML 作为检测配置载体的工程惯例。**不引入其代码**（license/API 未验证，
实现前须单独核实）。

## 4. Feed 文件格式（草案 v1）

```yaml
# feed 文件头（签名校验对象 = 整个文件字节序列, 头内 signature 字段除外）
feed:
  version: "2026.10.02-001"     # 日期+序号, 只升不降
  schema: 1                      # 格式版本号（向前兼容契约）
  publisher: "ai-prompt-toolkit"
  min_tool_version: "67.34.6"    # 防降级攻击: 旧工具拒绝新 schema
  signed_at: "2026-10-02T00:00:00Z"
  ed25519_pubkey_id: "apt-2026-root-1"
  signature: "<base64 ed25519 签名>"   # 覆盖文件其余全部字节

rules:                           # 复用 rule_loader_yaml 的 rules 块
  - id: F0001
    name: 新增注入标记-XXX
    category: injection
    severity: high
    description: "..."
    remediation: "..."
    pattern: "..."
    flags: ["ignorecase"]
    enabled: true
    source: "CVE/issue/红队实测引用"   # 必填: 签名来源可追溯

probes:                          # feed 自带的验证探针（§6.4 质量门禁）
  - name: feed_fp_check_001
    text: "<干净样本>"
    expect_none: true            # 该样本在 feed 规则下必须 0 命中
  - name: feed_tp_check_001
    text: "<攻击样本>"
    expect: ["F0001"]
```

**确定性契约**: 裁决输入 = (prompt 文本, 工具版本, feed 版本)。三者任一变化
裁决可能不同，但**三元组内逐字节一致** — 与现有"同输入同裁决"口径同构，
只是把 feed 版本显式纳入输入域。lint report 的 metadata 必须携带 feed 版本
（未加载 feed 时记 `none`）。

## 5. 信任链设计

```
发布方私钥(离线) ──签名──> feed 文件 ──用户分发──> 用户机
用户机校验:
  1. 公钥锚定: 公钥内置于工具代码(随版本更新), 不接受 feed 自带公钥
     (防"feed 自带新公钥自我认证"攻击)
  2. 签名校验: ed25519.verify(pubkey, file_bytes_without_sig, signature)
     失败 → 拒绝加载 + 明确报错(fail-closed), 绝不降级为"警告后加载"
     ⚠️ R221 安全审查约束: 校验对象必须是**文件原始字节**(定位 signature
     字段起止偏移, 取其余字节段), **禁止** yaml.safe_load 后重新序列化再
     签/验 — 重序列化会改变字节序, 使"验过的对象"与"执行的对象"脱钩
     (实现陷阱, 此处提前钉死)
  3. 版本单调: feed.version < 本机已记录版本 → 拒绝(防降级攻击)
  4. schema/min_tool_version 门: 不匹配 → 拒绝
  5. 全部通过 → 规则并入 CUSTOM 执行路径
```

**供应链攻击面审计**（对抗性视角）:
- feed 被投毒（签名有效但内容恶意）→ 缓解: 规则只**增**不删不改内置 + waiver 审计
  + `--fail-on-waiver` 可锁"禁新增豁免"；检测: 签名发布流程的私钥隔离（发布纪律，
  文档级承诺 + 后续可上 Sigstore 类透明日志）
- 中间人替换 feed → 签名校验失败 → fail-closed
- 旧 feed 降级 → 版本单调拒绝
- feed 规则误报淹没 CI → §6.4 feed 自带 FP 探针 + CI 棘轮"feed 加载后全局 FP
  不得高于 1%"

## 6. 集成点与质量门禁

1. **CLI**: `prompt-cli feed validate <file>`（离线校验签名+格式，不加载）/
   `prompt-cli feed update --from <file>`（显式加载，拒绝 URL 直传 v1）
2. **配置**: `.prompt-toolkit-rules/feed.yml`（与现有规则目录同址）；CI 可 pin
   `--feed <versioned-file>`
3. **report**: lint report metadata 加 `feed_version`（审计链闭环）
4. **双基线联动**: feed 的 probes 块 → `check_miss_rate`/`check_false_positives`
   可选并入（flag 开关，默认 CI 不并入 feed 探针 — feed 质量由 feed 发布方担保，
   工具侧只验签名 + §6.4 探针跑通即加载）

## 7. 安全设计要点（供 security-reviewer 审查锚点）

- fail-closed 优先级 > 可用性：签名校验任何异常 = 不加载
- 私钥纪律：发布方离线签名；工具侧只内置公钥
- 规则命名空间隔离（F 系 vs P 系）：feed 无法覆盖/改写内置规则
- waiver 继承 + 审计：feed 规则的豁免同样进 `waived_rules` 审计
- ReDoS：feed 正则加载前跑现有 ReDoS 静态检查（R214 纪律：简单 alternation +
  单量词，嵌套量词拒绝加载）

## 8. 实现前置条件（不满足不启动编码）

1. **C2 发布落地**（git remote + PyPI）— 无分发渠道的 feed 无消费者，先做是
   低价值打磨（鬼才 PM 过滤结论）
2. 发布方签名流程就绪（私钥托管/操作纪律文档）
3. 首版 feed 内容源：至少 10 条来自真实威胁情报（CVE/红队实测）的签名，
   每条带 source 字段 — 无真实内容的 feed 是空壳
4. license 核实：prompt-shield-signatures 的格式思路可参考，**代码不可直接拷贝**
   （实现前单独核实其 license，不凭调研快照下结论）

## 9. 分阶段路线（每阶段独立可验证）

| 阶段 | 内容 | 验收 |
|---|---|---|
| F1 | feed 格式 + 签名校验 + `feed validate`（离线） | 篡改 1 字节必拒；合法 feed 必过 |
| F2 | feed 规则并入 lint（F 系命名空间 + waiver 继承） | 内置 261 规则双基线零变化 |
| F3 | report 审计链（feed_version 进 metadata）+ CI pin | 同三元组重跑逐字节一致 |
| F4 | `feed update` + 版本单调 + 降级拒绝 | 旧版本 feed 必拒 |
| F5 | feed 自带探针质量门禁 | FP 探针全 0 命中才加载 |

## 10. 风险与回滚

- **风险**: feed 生态若无人生产（发布方即唯一发布者），价值退化为"签名补丁"
  → 缓解: 格式公开 + `feed validate` 开放，允许第三方自签名 feed（用户自担风险，
  显式 `--insecure-feed` 标记 + report 标注 unverified）
- **回滚**: 删除 `.prompt-toolkit-rules/feed.yml` 即回到纯内置 261 规则，
  无残留状态（feed 不落库、无缓存写盘 — v1 刻意简化）
