# stdio 协议规范（P1-05a）

`prompt-cli lint --stdio` 启动一个**常驻 server**，通过 stdin/stdout 按行 JSON
与编辑器 bridge 通信。设计目标：编辑器"保存即 lint"场景下零进程启动开销
（每次 spawn CLI ~300ms Python 启动不可用），同时让 VS Code / JetBrains /
Neovim 各端复用**同一份协议**——新端只需实现本协议的 bridge，内核零改动
（04 §5 协议纪律）。

## 1. 传输

- 编码 UTF-8，**每行一个 JSON 对象**（行边界是唯一同步点）
- 请求从 stdin 读，响应写 stdout（每请求**恰好一行**响应）
- 启动时 server 先发一行 **hello**（bridge 据此握手）
- stderr 不承载协议（诊断信息用）
- 空行/空白行忽略（编辑器换行噪声）

## 2. 消息

### hello（server → bridge，启动首行）

```json
{"ok": true, "id": null, "hello": "prompt-cli-stdio", "protocol": 1, "version": "67.34.16"}
```

`protocol` 为不兼容变更计数器（当前=1）。bridge 必须校验 `hello=="prompt-cli-stdio"`。

### lint 请求

```json
{"op": "lint", "id": 1, "path": "a.prompt", "text": "prompt 全文", "rules": ["P16"], "exclude": ["P005"]}
```

| 字段 | 类型 | 必填 | 语义 |
|---|---|---|---|
| `op` | `"lint"` | ✓ | 操作 |
| `id` | number/string | ✓ | 请求 id，响应原样回带（配对用；服务端不解释值） |
| `path` | string | ✓ | 显示名（finding 的 template_id），bridge 传真实路径 |
| `text` | string | ✓ | prompt 全文（**bridge 读文件，server 不碰磁盘**——协议面零 I/O 依赖） |
| `rules` | string[] | ✗ | 规则过滤，**与 CLI `--rules` 同语义**：逗号/数组均支持前缀（`"P16"`→P16x 族）；未知名 fail-safe 忽略 |
| `exclude` | string[] | ✗ | 同 `rules`，忽略指定规则 |

### lint 响应

```json
{"ok": true, "id": 1, "result": { /* LintResult.to_dict() 全量 */ }}
```

`result` = 内核 `lint_template(path, text, apply_waivers=True).to_dict()`——
与 `prompt-cli lint -s` 同一内核同一真源（e2e 断言：逐字段一致，仅
`lint_time_ms` 墙钟除外）。关键字段：`findings[]`（rule_id/severity/
description/location/remediation）、`failed_count`、`waived_rules`、`score`。

### ping / exit

```json
{"op": "ping", "id": 2}                    → {"ok": true, "id": 2, "pong": true, "version": "67.34.16"}
{"op": "exit"}                             → （无响应行）进程以 exit 0 退出
```

bridge 端心跳建议 30s；ping 超时 N 次判定 server 死，重启并重新握手。

### 错误响应（server 恒活契约）

```json
{"ok": false, "id": null, "error": "invalid request: Expecting value ..."}
{"ok": false, "id": 3, "error": "unknown op: 'frobnicate'"}
{"ok": false, "id": 4, "error": "text 必须为字符串"}
```

**契约：任何单请求失败（非法 JSON / 未知 op / 规则异常）只产生错误响应，
绝不杀死 server。** `id` 在请求无法解析时为 `null`。

## 3. 并发与顺序

单线程串行：响应顺序 = 请求到达顺序（e2e 断言）。bridge 端若需并发，
自行排队——协议不定义并发请求语义。

## 4. 确定性

相同 `(text, rules, exclude)` 的两次 lint，响应 `result` 逐字节一致
（楔子 e2e 断言，`lint_time_ms` 除外）。

## 5. 退出与生命周期

| 事件 | 行为 |
|---|---|
| `{"op":"exit"}` | 立即退出，exit 0 |
| stdin EOF | 退出，exit 0 |
| 单请求异常 | 错误响应，继续服务 |
| 进程崩溃 | bridge 检测管道断裂 → 重启 + 重新握手（bridge 职责） |

## 6. 参考实现

- e2e：`tests/e2e/test_stdio_protocol.py`（真子进程，10 条覆盖上述全部契约）
- 协议变更流程：不兼容变更 → `protocol` 递增 + 本文档 + 旧版兼容期 2 个主版本

## 7. 已知边界

- 无行级定位（finding 为文件级，`location="1:1"`）——P2-06 落地后
  critical/high finding 将带 `line` 字段（前向兼容：bridge 无 `line` 时
  回退文件级显示）
- 无增量/baseline 语义——CI 场景走 CLI；编辑器场景全量 lint（单文件 <100ms）
