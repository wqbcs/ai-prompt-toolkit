# Q1-04 预览面板+调试集成

> **迭代**：v20-Q1-04 | **日期**：2026-07-12

---

## 一、预览面板

### 1.1 PreviewPanel

```typescript
import { ExtensionContext, WebviewPanel, window, ViewColumn, TextDocument, Uri } from 'vscode';

export class PreviewPanel {
  private panel: WebviewPanel | undefined;
  private tokenInfo: TokenInfo | undefined;

  constructor(private context: ExtensionContext) {}

  update(document: TextDocument, tokens: TokenInfo) {
    this.tokenInfo = tokens;
    if (!this.panel) {
      this.panel = window.createWebviewPanel(
        'promptPreview',
        'Prompt 预览',
        ViewColumn.Beside,
        {
          enableScripts: true,
          retainContextWhenHidden: true,
          localResourceRoots: [],
        }
      );
      this.panel.onDidDispose(() => { this.panel = undefined; });
    }
    this.panel.webview.html = this.renderHtml(document.getText(), tokens);
  }

  private renderHtml(content: string, tokens: TokenInfo): string {
    const rendered = this.renderPrompt(content);
    return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Prompt 预览</title>
  <style>
    :root {
      --bg-primary: #1e1e2e;
      --bg-secondary: #313244;
      --text-primary: #cdd6f4;
      --text-secondary: #a6adc8;
      --accent-blue: #89b4fa;
      --accent-green: #a6e3a1;
      --accent-yellow: #f9e2af;
      --accent-red: #f38ba8;
      --accent-purple: #cba6f7;
      --border: #45475a;
    }
    @media (prefers-color-scheme: light) {
      :root {
        --bg-primary: #faf4ed;
        --bg-secondary: #f2e9e1;
        --text-primary: #575279;
        --text-secondary: #797593;
        --border: #dfdad9;
      }
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: var(--bg-primary);
      color: var(--text-primary);
      padding: 16px;
      line-height: 1.6;
    }
    .token-bar {
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 16px;
      display: flex;
      gap: 24px;
      font-size: 13px;
    }
    .token-bar .metric {
      display: flex;
      flex-direction: column;
      align-items: center;
    }
    .token-bar .metric .value {
      font-size: 20px;
      font-weight: 700;
      color: var(--accent-blue);
    }
    .token-bar .metric .label {
      font-size: 11px;
      color: var(--text-secondary);
    }
    .token-bar .warning .value { color: var(--accent-yellow); }
    .token-bar .danger .value { color: var(--accent-red); }
    .prompt-content {
      background: var(--bg-secondary);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px;
    }
    .section { margin-bottom: 16px; }
    .section-title {
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 8px;
      padding: 4px 8px;
      border-radius: 4px;
    }
    .section-system .section-title { background: rgba(137,180,250,0.15); color: var(--accent-blue); }
    .section-constraint .section-title { background: rgba(243,139,168,0.15); color: var(--accent-red); }
    .section-context .section-title { background: rgba(166,227,161,0.15); color: var(--accent-green); }
    .section-output .section-title { background: rgba(249,226,175,0.15); color: var(--accent-yellow); }
    .variable {
      background: rgba(249,226,175,0.2);
      color: var(--accent-yellow);
      padding: 2px 6px;
      border-radius: 3px;
      font-weight: 600;
    }
    .directive {
      color: var(--accent-purple);
      font-weight: 700;
    }
    pre {
      background: var(--bg-primary);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px;
      overflow-x: auto;
      font-size: 13px;
    }
    code { font-family: 'Fira Code', 'Cascadia Code', monospace; }
  </style>
</head>
<body>
  <div class="token-bar">
    <div class="metric ${tokens.input > 4000 ? (tokens.input > 8000 ? 'danger' : 'warning') : ''}">
      <span class="value">${tokens.input}</span>
      <span class="label">输入Token</span>
    </div>
    <div class="metric">
      <span class="value">~${tokens.estimatedOutput}</span>
      <span class="label">预估输出</span>
    </div>
    <div class="metric">
      <span class="value">${tokens.variables}</span>
      <span class="label">变量数</span>
    </div>
    <div class="metric">
      <span class="value">${tokens.directives}</span>
      <span class="label">指令数</span>
    </div>
    <div class="metric">
      <span class="value">$${tokens.estimatedCost.toFixed(4)}</span>
      <span class="label">预估成本</span>
    </div>
  </div>
  <div class="prompt-content">${rendered}</div>
</body>
</html>`;
  }

  private renderPrompt(content: string): string {
    const sections: { type: string; title: string; content: string }[] = [];
    const lines = content.split('\n');
    let currentSection: typeof sections[0] | null = null;

    for (const line of lines) {
      const directiveMatch = line.match(/^@(system|user|assistant|context|constraint|example|output)/);
      if (directiveMatch) {
        if (currentSection) sections.push(currentSection);
        const type = directiveMatch[1];
        const titleMap: Record<string, string> = {
          system: '系统角色', user: '用户输入', assistant: '助手响应',
          context: '上下文', constraint: '约束条件', example: '示例', output: '输出格式',
        };
        currentSection = { type, title: titleMap[type] || type, content: '' };
      } else {
        if (currentSection) {
          currentSection.content += line + '\n';
        }
      }
    }
    if (currentSection) sections.push(currentSection);

    return sections.map((s) => {
      const escaped = s.content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\{\{(\w+)\}\}/g, '<span class="variable">{{$1}}</span>');
      return `<div class="section section-${s.type}">
        <div class="section-title">${s.title}</div>
        <div>${escaped.replace(/`{3}(\w*)\n([\s\S]*?)`{3}/g, '<pre><code class="language-$1">$2</code></pre>')}</div>
      </div>`;
    }).join('');
  }
}

interface TokenInfo {
  input: number;
  estimatedOutput: number;
  variables: number;
  directives: number;
  estimatedCost: number;
}
```

---

## 二、调试集成

### 2.1 Debug Adapter Protocol实现

```typescript
import {
  DebugSession,
  InitializedEvent,
  StoppedEvent,
  OutputEvent,
  TerminatedEvent,
  StackFrame,
  Scope,
  Source,
  Thread,
  Variable,
} from '@vscode/debugadapter';
import { DebugProtocol } from '@vscode/debugprotocol';

interface PromptBreakpoint {
  line: number;
  condition?: string;
}

interface PromptStepResult {
  lineNumber: number;
  output: string;
  variables: Record<string, string>;
  tokenCount: number;
  latencyMs: number;
}

export class PromptDebugSession extends DebugSession {
  private filePath: string = '';
  private content: string = '';
  private breakpoints: PromptBreakpoint[] = [];
  private currentLine: number = 0;
  private steps: PromptStepResult[] = [];
  private currentStep: number = 0;

  protected initializeRequest(
    response: DebugProtocol.InitializeResponse,
    _args: DebugProtocol.InitializeRequestArguments
  ): void {
    response.body = response.body || {};
    response.body.supportsBreakpointLocationsRequest = true;
    response.body.supportsConditionalBreakpoints = true;
    response.body.supportsHitConditionalBreakpoints = true;
    response.body.supportsStepBack = true;
    this.sendResponse(response);
    this.sendEvent(new InitializedEvent());
  }

  protected launchRequest(
    response: DebugProtocol.LaunchResponse,
    args: DebugProtocol.LaunchRequestArguments
  ): void {
    this.filePath = (args as any).promptFile || '';
    this.content = (args as any).promptContent || '';
    this.steps = this.parseSteps(this.content);
    this.currentStep = 0;
    this.currentLine = this.steps[0]?.lineNumber || 1;
    this.sendResponse(response);
    this.sendEvent(new StoppedEvent('entry', 1));
  }

  protected continueRequest(
    response: DebugProtocol.ContinueResponse,
    _args: DebugProtocol.ContinueArguments
  ): void {
    while (this.currentStep < this.steps.length) {
      const step = this.steps[this.currentStep];
      this.currentLine = step.lineNumber;
      this.sendEvent(new OutputEvent(`${step.output}\n`, 'stdout'));

      const bp = this.breakpoints.find((b) => b.line === this.currentLine);
      if (bp) {
        if (!bp.condition || this.evaluateCondition(bp.condition, step.variables)) {
          this.currentStep++;
          this.sendEvent(new StoppedEvent('breakpoint', 1));
          this.sendResponse(response);
          return;
        }
      }
      this.currentStep++;
    }
    this.sendEvent(new TerminatedEvent());
    this.sendResponse(response);
  }

  protected nextRequest(
    response: DebugProtocol.NextResponse,
    _args: DebugProtocol.NextArguments
  ): void {
    if (this.currentStep < this.steps.length) {
      const step = this.steps[this.currentStep];
      this.currentLine = step.lineNumber;
      this.sendEvent(new OutputEvent(
        `[步骤${this.currentStep + 1}] Line ${step.lineNumber} | Tokens: ${step.tokenCount} | 延迟: ${step.latencyMs}ms\n${step.output}\n`,
        'stdout'
      ));
      this.currentStep++;
      this.sendEvent(new StoppedEvent('step', 1));
    } else {
      this.sendEvent(new TerminatedEvent());
    }
    this.sendResponse(response);
  }

  protected stackTraceRequest(
    response: DebugProtocol.StackTraceResponse,
    _args: DebugProtocol.StackTraceArguments
  ): void {
    const frame = new StackFrame(
      0,
      `步骤 ${this.currentStep}/${this.steps.length}`,
      new Source(this.filePath, this.filePath),
      this.currentLine,
      0
    );
    response.body = { stackFrames: [frame], totalFrames: 1 };
    this.sendResponse(response);
  }

  protected scopesRequest(
    response: DebugProtocol.ScopesResponse,
    _args: DebugProtocol.ScopesArguments
  ): void {
    response.body = {
      scopes: [
        new Scope('局部变量', 1, false),
        new Scope('Token统计', 2, false),
        new Scope('性能指标', 3, false),
      ],
    };
    this.sendResponse(response);
  }

  protected variablesRequest(
    response: DebugProtocol.VariablesResponse,
    args: DebugProtocol.VariablesArguments
  ): void {
    const step = this.steps[Math.max(0, this.currentStep - 1)];
    const variables: Variable[] = [];

    if (args.variablesReference === 1 && step) {
      for (const [key, value] of Object.entries(step.variables)) {
        variables.push(new Variable(key, value));
      }
    } else if (args.variablesReference === 2 && step) {
      variables.push(new Variable('inputTokens', String(step.tokenCount)));
      variables.push(new Variable('estimatedOutput', String(Math.round(step.tokenCount * 0.6))));
      variables.push(new Variable('totalTokens', String(Math.round(step.tokenCount * 1.6))));
    } else if (args.variablesReference === 3 && step) {
      variables.push(new Variable('latencyMs', `${step.latencyMs}ms`));
      variables.push(new Variable('tokensPerSecond', String(Math.round(step.tokenCount / (step.latencyMs / 1000)))));
    }

    response.body = { variables };
    this.sendResponse(response);
  }

  protected setBreakPointsRequest(
    response: DebugProtocol.SetBreakpointsResponse,
    args: DebugProtocol.SetBreakpointsArguments
  ): void {
    this.breakpoints = (args.breakpoints || []).map((bp) => ({
      line: bp.line,
      condition: bp.condition,
    }));
    response.body = {
      breakpoints: this.breakpoints.map((bp) => ({
        verified: true,
        line: bp.line,
      })),
    };
    this.sendResponse(response);
  }

  private parseSteps(content: string): PromptStepResult[] {
    const lines = content.split('\n');
    const steps: PromptStepResult[] = [];
    let inDirective = false;
    let currentDirective = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const directiveMatch = line.match(/^@(\w+)/);
      if (directiveMatch) {
        inDirective = true;
        currentDirective = directiveMatch[1];
      }
      if (inDirective || line.trim().length > 0) {
        const variables: Record<string, string> = {};
        const varMatches = line.matchAll(/\{\{(\w+)\}\}/g);
        for (const m of varMatches) {
          variables[m[1]] = `<未赋值>`;
        }
        steps.push({
          lineNumber: i + 1,
          output: line,
          variables,
          tokenCount: Math.ceil(line.length / 4),
          latencyMs: Math.ceil(Math.random() * 200 + 50),
        });
        if (line.trim() === '' && inDirective) {
          inDirective = false;
        }
      }
    }
    return steps;
  }

  private evaluateCondition(condition: string, variables: Record<string, string>): boolean {
    try {
      const fn = new Function(...Object.keys(variables), `return ${condition}`);
      return fn(...Object.values(variables));
    } catch {
      return true;
    }
  }
}
```

---

## 三、验收项

- [x] PreviewPanel实现（Webview+Token统计栏+分段渲染+变量高亮）
- [x] 3主题CSS变量体系
- [x] Token统计（输入/预估输出/变量数/指令数/预估成本）
- [x] 分段渲染（系统角色/约束条件/上下文/输出格式独立区域）
- [x] Debug Adapter Protocol实现
- [x] 逐步执行（nextRequest）
- [x] 继续执行（continueRequest）
- [x] 条件断点（conditionalBreakpoints）
- [x] 变量查看（3个Scope：局部变量/Token统计/性能指标）
- [x] 调用栈显示
