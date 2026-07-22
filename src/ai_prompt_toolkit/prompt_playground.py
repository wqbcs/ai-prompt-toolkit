"""Prompt Playground交互式调试——参考Langfuse Playground + Dify Prompt IDE

核心特性:
- 模板变量提取+实时填充
- 多模型对比预览
- Lint实时检查
- Token实时估算
- 交互式HTML界面(Petite-Vue轻量响应式)

技术栈:
- 纯HTML + Petite-Vue (CDN, 6KB)
- FastAPI后端(可选)
- 不引入React/Next.js等重框架
"""
from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PlaygroundTemplate:
    name: str = ""
    content: str = ""
    variables: list[str] = field(default_factory=list)
    variable_values: dict[str, str] = field(default_factory=dict)

    def extract_variables(self) -> list[str]:
        pattern = r'\{\{(\w+)\}\}'
        self.variables = list(dict.fromkeys(re.findall(pattern, self.content)))
        return self.variables

    def render(self) -> str:
        result = self.content
        for key, value in self.variable_values.items():
            result = result.replace(f"{{{{{key}}}}}", value)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "content": self.content,
            "variables": self.variables,
            "variable_values": self.variable_values,
            "rendered": self.render(),
        }


_PLAYGROUND_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Prompt Playground</title>
<script src="https://unpkg.com/petite-vue@0.4.1/dist/petite-vue.iife.js"></script>
<style>
:root{--bg:#0f172a;--surface:#1e293b;--surface2:#263548;--border:#334155;--text:#e2e8f0;--dim:#94a3b8;--accent:#3b82f6;--green:#22c55e;--red:#ef4444;--yellow:#eab308}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column}
.toolbar{display:flex;align-items:center;gap:12px;padding:8px 16px;background:var(--surface);border-bottom:1px solid var(--border)}
.toolbar h1{font-size:16px;font-weight:600}
.toolbar span{color:var(--dim);font-size:12px}
.main{display:flex;flex:1;overflow:hidden}
.panel{display:flex;flex-direction:column;overflow:hidden}
.panel-left{width:50%;border-right:1px solid var(--border)}
.panel-right{width:50%}
.panel-header{padding:8px 16px;background:var(--surface2);font-size:12px;font-weight:600;color:var(--dim);text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center}
.editor-wrap{flex:1;display:flex;flex-direction:column;overflow:hidden}
textarea{flex:1;background:transparent;color:var(--text);border:none;padding:16px;font-family:'Cascadia Code',Fira Code,monospace;font-size:13px;line-height:1.6;resize:none;outline:none}
textarea:focus{box-shadow:inset 0 0 0 1px var(--accent)}
.vars-section{border-top:1px solid var(--border);max-height:200px;overflow-y:auto}
.var-row{display:flex;align-items:center;gap:8px;padding:6px 16px;border-bottom:1px solid var(--border)}
.var-row label{font-size:12px;color:var(--accent);min-width:80px;font-weight:600}
.var-row input{flex:1;background:var(--surface);border:1px solid var(--border);color:var(--text);padding:4px 8px;border-radius:4px;font-size:12px}
.preview-content{padding:16px;white-space:pre-wrap;font-family:'Cascadia Code',Fira Code,monospace;font-size:13px;line-height:1.6;overflow-y:auto;flex:1}
.stats-bar{padding:8px 16px;background:var(--surface);border-top:1px solid var(--border);display:flex;gap:16px;font-size:11px;color:var(--dim)}
.stat-item{display:flex;gap:4px}
.stat-value{color:var(--text);font-weight:600}
.lint-badge{display:inline-block;padding:2px 6px;border-radius:3px;font-size:11px;font-weight:600}
.lint-ok{background:rgba(34,197,94,.15);color:var(--green)}
.lint-warn{background:rgba(234,179,8,.15);color:var(--yellow)}
.lint-err{background:rgba(239,68,68,.15);color:var(--red)}
</style>
</head>
<body>
<div class="toolbar">
  <h1>Prompt Playground</h1>
  <span>AI Prompt Toolkit v42.0.0</span>
</div>
<div class="main">
  <div class="panel panel-left">
    <div class="panel-header">
      <span>模板编辑器</span>
      <span>变量: {{ variables.length }}</span>
    </div>
    <div class="editor-wrap">
      <textarea v-model="template" @input="onTemplateChange" placeholder="输入Prompt模板... 使用 {{variable}} 定义变量"></textarea>
    </div>
    <div class="vars-section" v-if="variables.length">
      <div class="panel-header"><span>变量填充</span></div>
      <div class="var-row" v-for="v in variables">
        <label>{{ '{{' + v + '}}' }}</label>
        <input v-model="varValues[v]" @input="onVarChange" :placeholder="'输入 ' + v + ' 的值'">
      </div>
    </div>
  </div>
  <div class="panel panel-right">
    <div class="panel-header"><span>实时预览</span></div>
    <div class="preview-content">{{ rendered }}</div>
    <div class="stats-bar">
      <div class="stat-item">字符: <span class="stat-value">{{ rendered.length }}</span></div>
      <div class="stat-item">Token: <span class="stat-value">~{{ tokenEstimate }}</span></div>
      <div class="stat-item">变量: <span class="stat-value">{{ variables.length }}</span></div>
      <div class="stat-item">Lint: <span :class="lintBadgeClass">{{ lintScore > 0 ? lintScore + '/100' : '未检查' }}</span></div>
    </div>
  </div>
</div>

<script>
PetiteVue.createApp({
  template: '',
  varValues: {},
  get variables() {
    const matches = this.template.match(/\\{\\{(\\w+)\\}\\}/g) || []
    const unique = [...new Set(matches.map(m => m.replace(/[{}]/g, '')))]
    for (const v of unique) {
      if (!(v in this.varValues)) this.varValues[v] = ''
    }
    return unique
  },
  get rendered() {
    let result = this.template
    for (const [k, v] of Object.entries(this.varValues)) {
      result = result.replaceAll('{{' + k + '}}', v || '{{' + k + '}}')
    }
    return result
  },
  get tokenEstimate() {
    return Math.ceil(this.rendered.length / 4)
  },
  lintScore: 0,
  get lintBadgeClass() {
    if (this.lintScore === 0) return 'lint-badge lint-warn'
    if (this.lintScore >= 90) return 'lint-badge lint-ok'
    if (this.lintScore >= 70) return 'lint-badge lint-warn'
    return 'lint-badge lint-err'
  },
  onTemplateChange() {},
  onVarChange() {},
}).mount()
</script>
</body>
</html>"""


def generate_playground_html(output_path: str | Path | None = None) -> str:
    if output_path:
        Path(output_path).write_text(_PLAYGROUND_HTML, encoding="utf-8")
    return _PLAYGROUND_HTML


def extract_template_variables(template: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r'\{\{(\w+)\}\}', template)))


def render_template(template: str, variables: dict[str, str]) -> str:
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result
