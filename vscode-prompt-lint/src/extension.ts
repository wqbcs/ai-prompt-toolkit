import * as vscode from 'vscode';
import { spawn } from 'child_process';

const DIAGNOSTIC_SOURCE = 'prompt-lint';
const DEBOUNCE_MS = 300;

interface LintFinding {
  rule_id: string;
  severity: string;
  description: string;
  location?: string;
  remediation?: string;
}

interface ScanFinding {
  severity: string;
  rule_id: string;
  description: string;
  location?: string;
  remediation?: string;
}

interface EvaluateResult {
  score: number;
  dimensions: Record<string, number>;
  summary: string;
}

let diagnosticCollection: vscode.DiagnosticCollection;
let lintResultsCache: Map<string, LintFinding[]> = new Map();
let debounceTimers: Map<string, NodeJS.Timeout> = new Map();
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
  diagnosticCollection = vscode.languages.createDiagnosticCollection('prompt-lint');
  context.subscriptions.push(diagnosticCollection);

  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = 'promptLint.lintActiveFile';
  context.subscriptions.push(statusBarItem);
  updateStatusBarIdle();

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.lintActiveFile', () => {
      runLintOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.scanActiveFile', () => {
      runScanOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.compileActiveFile', () => {
      runCompileOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.evaluateActiveFile', () => {
      runEvaluateOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.showLintScore', () => {
      showLintScore();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.qualityGate', () => {
      runQualityGateOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.piiScan', () => {
      runPiiScanOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.openTemplate', (templateId: string) => {
      openTemplatePreview(templateId);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.searchTemplates', async () => {
      const query = await vscode.window.showInputBox({
        prompt: '搜索模板（名称/场景/行业）',
        placeHolder: '例如: 翻译、代码、华为云...',
      });
      if (query) {
        searchAndShowTemplates(query);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.fix', (docUri: vscode.Uri, ruleId: string) => {
      applyQuickFix(docUri, ruleId);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.abTest', () => {
      runAbTestOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.tokenAnalyze', () => {
      runTokenAnalyzeOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.versionDiff', () => {
      runVersionDiffOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.scorecard', () => {
      runScorecardOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.fusionEngine', () => {
      runFusionEngineOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand('promptLint.badge', () => {
      runBadgeOnActiveFile();
    })
  );

  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider(
      { language: 'markdown', scheme: 'file' },
      new PromptCodeLensProvider()
    )
  );

  context.subscriptions.push(
    vscode.languages.registerCodeActionsProvider(
      { language: 'markdown', scheme: 'file' },
      new PromptQuickFixProvider(),
      { providedCodeActionKinds: PromptQuickFixProvider.providedCodeActionKinds }
    )
  );

  const treeProvider = new PromptLintTreeDataProvider();
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider('promptLintSidebar', treeProvider)
  );

  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      const config = vscode.workspace.getConfiguration('promptLint');
      if (config.get<boolean>('lintOnSave') && isMarkdownFile(doc)) {
        runLint(doc);
        treeProvider.refresh();
        if (config.get<boolean>('securityScan')) {
          runScan(doc);
        }
      }
    })
  );

  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((e) => {
      const config = vscode.workspace.getConfiguration('promptLint');
      if (config.get<boolean>('lintOnType') && isMarkdownFile(e.document)) {
        debouncedLint(e.document, treeProvider);
      }
    })
  );

  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument((doc) => {
      const config = vscode.workspace.getConfiguration('promptLint');
      if (config.get<boolean>('lintOnSave') && isMarkdownFile(doc)) {
        runLint(doc);
        treeProvider.refresh();
      }
    })
  );

  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      if (editor && isMarkdownFile(editor.document)) {
        updateStatusBarForDoc(editor.document);
      } else {
        updateStatusBarIdle();
      }
    })
  );
}

function debouncedLint(doc: vscode.TextDocument, treeProvider: PromptLintTreeDataProvider) {
  const key = doc.uri.toString();
  const existing = debounceTimers.get(key);
  if (existing) {
    clearTimeout(existing);
  }
  debounceTimers.set(key, setTimeout(() => {
    runLint(doc);
    treeProvider.refresh();
    debounceTimers.delete(key);
  }, DEBOUNCE_MS));
}

function updateStatusBarIdle() {
  statusBarItem.text = '$(check) Prompt Lint';
  statusBarItem.tooltip = 'Prompt Lint — 就绪';
  statusBarItem.show();
}

function updateStatusBarLinting() {
  statusBarItem.text = '$(loading~spin) Prompt Lint...';
  statusBarItem.tooltip = 'Prompt Lint — 检查中';
}

function updateStatusBarForDoc(doc: vscode.TextDocument) {
  const findings = lintResultsCache.get(doc.uri.toString()) || [];
  const total = 50;
  const passed = total - findings.length;
  const score = Math.round((passed / total) * 100);
  const errorCount = findings.filter(f => f.severity === 'high' || f.severity === 'critical').length;
  const warnCount = findings.filter(f => f.severity === 'medium').length;
  if (errorCount > 0) {
    statusBarItem.text = `$(error) Prompt: ${score}/100 (${errorCount} err, ${warnCount} warn)`;
    statusBarItem.tooltip = `Prompt Lint Score: ${score}/100 — ${errorCount} 错误, ${warnCount} 警告`;
  } else if (warnCount > 0) {
    statusBarItem.text = `$(warning) Prompt: ${score}/100 (${warnCount} warn)`;
    statusBarItem.tooltip = `Prompt Lint Score: ${score}/100 — ${warnCount} 警告`;
  } else {
    statusBarItem.text = `$(check) Prompt: ${score}/100`;
    statusBarItem.tooltip = `Prompt Lint Score: ${score}/100 — 无问题`;
  }
  statusBarItem.show();
}

function isMarkdownFile(doc: vscode.TextDocument): boolean {
  return doc.languageId === 'markdown' || doc.languageId === 'prompt-markdown' || doc.fileName.endsWith('.md') || doc.fileName.endsWith('.prompt.md');
}

function severityToVscode(severity: string): vscode.DiagnosticSeverity {
  switch (severity) {
    case 'critical':
    case 'high':
      return vscode.DiagnosticSeverity.Error;
    case 'medium':
      return vscode.DiagnosticSeverity.Warning;
    case 'low':
    case 'info':
    default:
      return vscode.DiagnosticSeverity.Information;
  }
}

function applySeverityOverrides(severity: string, overrides: Record<string, string>): string {
  return overrides[severity] || severity;
}

async function runLintOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  await runLint(editor.document);
}

async function runScanOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  await runScan(editor.document);
}

async function runQualityGateOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  try {
    const output = await executeCli(['lint', '-t', filePath, '--format', 'json', '--gate']);
    vscode.window.showInformationMessage(`Quality Gate: ${output.trim()}`);
  } catch (err: any) {
    const msg = err.message || String(err);
    if (msg.includes('FAIL') || msg.includes('exit code')) {
      vscode.window.showErrorMessage(`Quality Gate: FAIL — ${msg}`);
    } else {
      vscode.window.showWarningMessage(`Quality Gate: ${msg}`);
    }
  }
}

async function runPiiScanOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  try {
    const output = await executeCli(['scan', '-t', filePath, '--format', 'json']);
    const report = JSON.parse(output);
    const findings: ScanFinding[] = report.findings || [];
    const piiFindings = findings.filter(f => f.rule_id?.startsWith('PII'));
    if (piiFindings.length === 0) {
      vscode.window.showInformationMessage('PII隐私检测: 未发现个人隐私信息泄露');
    } else {
      vscode.window.showWarningMessage(`PII隐私检测: 发现 ${piiFindings.length} 处隐私信息泄露风险`);
      const doc = editor.document;
      const existing: vscode.Diagnostic[] = [...(diagnosticCollection.get(doc.uri) || [])];
      for (const finding of piiFindings) {
        // R218: location 契约(scan finding 无 location → 文件级, 不猜行)
        const range = rangeFromLocation(doc, finding.location);
        const diag = new vscode.Diagnostic(
          range,
          `[${finding.rule_id}] PII风险: ${finding.description}`,
          vscode.DiagnosticSeverity.Error
        );
        diag.source = 'prompt-pii';
        diag.code = finding.rule_id;
        diag.tags = [vscode.DiagnosticTag.Unnecessary];
        existing.push(diag);
      }
      diagnosticCollection.set(doc.uri, existing);
    }
  } catch (err: any) {
    vscode.window.showErrorMessage(`PII隐私检测失败: ${err.message}`);
  }
}

async function runCompileOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const doc = editor.document;
  const filePath = doc.uri.fsPath;

  try {
    const result = await executeCli(['compile', '-s', filePath, '--output', filePath + '.compiled']);
    vscode.window.showInformationMessage(`Prompt Lint: 编译完成 — ${result}`);
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: 编译失败 — ${err.message}`);
  }
}

async function runEvaluateOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;

  try {
    const output = await executeCli(['evaluate', '--target', filePath, '--format', 'json']);
    const report = JSON.parse(output);
    const score = report.overall_score ?? report.score ?? 0;
    const panel = vscode.window.createWebviewPanel(
      'promptEvaluate',
      `评估结果 — ${path.basename(filePath)}`,
      vscode.ViewColumn.Beside,
      { enableScripts: true }
    );
    panel.webview.html = renderEvaluateHtml(report, score);
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: 评估失败 — ${err.message}`);
  }
}

async function showLintScore() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) { return; }
  const findings = lintResultsCache.get(editor.document.uri.toString()) || [];
  const total = 50;
  const passed = total - findings.length;
  const score = Math.round((passed / total) * 100);
  vscode.window.showInformationMessage(`Prompt Lint Score: ${score}/100 (${findings.length} issues)`);
}

function renderEvaluateHtml(report: any, score: number): string {
  const dims = report.dimension_scores || report.dimensions || {};
  const dimEntries = Object.entries(dims).map(([k, v]) =>
    `<tr><td>${k}</td><td>${Number(v).toFixed(1)}</td></tr>`
  ).join('');

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>
  body { font-family: -apple-system, sans-serif; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
  .score { font-size: 48px; font-weight: bold; color: ${score >= 80 ? '#4ec9b0' : score >= 60 ? '#dcdcaa' : '#f44747'}; }
  table { border-collapse: collapse; width: 100%; margin-top: 16px; }
  th, td { border: 1px solid #444; padding: 8px 12px; text-align: left; }
  th { background: #264f78; }
  h2 { color: #569cd6; }
</style></head>
<body>
  <h2>评估结果</h2>
  <div class="score">${score.toFixed(1)}</div>
  <p>综合评分</p>
  <h2>维度得分</h2>
  <table><tr><th>维度</th><th>得分</th></tr>${dimEntries}</table>
</body></html>`;
}

async function applyQuickFix(docUri: vscode.Uri, ruleId: string) {
  const doc = await vscode.workspace.openTextDocument(docUri);
  const editor = await vscode.window.showTextDocument(doc);
  const text = doc.getText();

  const autoFixRules: Record<string, string> = {
    'P005': '\n\n请按照以上要求进行回答。',
    'P025': '\n\n请将回答控制在500字以内。',
    'P026': "\n\n如果无法确定，请回复'信息不足，无法判断'而不编造。",
    'P029': '\n\n（请对输入进行校验）',
  };

  const fixText = autoFixRules[ruleId];
  if (!fixText) {
    vscode.window.showWarningMessage(`Prompt Lint: 规则 ${ruleId} 暂不支持自动修复`);
    return;
  }

  await editor.edit((editBuilder) => {
    const lastLine = doc.lineCount - 1;
    const lastChar = doc.lineAt(lastLine).text.length;
    editBuilder.insert(new vscode.Position(lastLine, lastChar), fixText);
  });

  vscode.window.showInformationMessage(`Prompt Lint: 已应用 ${ruleId} 自动修复`);
}

async function runAbTestOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  try {
    const providers = await vscode.window.showQuickPick(
      ['openai', 'anthropic', 'deepseek', 'qwen', 'pangu', 'zhipu', 'moonshot', 'baichuan', 'minimax', 'all'],
      { placeHolder: '选择A/B测试Provider', canPickMany: true }
    );
    if (!providers || providers.length === 0) { return; }
    const providerStr = providers.includes('all') ? '' : providers.join(',');
    const args = ['ab-test', '--target', filePath, '--format', 'json'];
    if (providerStr) { args.push('--providers', providerStr); }
    const output = await executeCli(args);
    const report = JSON.parse(output);
    const panel = vscode.window.createWebviewPanel(
      'promptAbTest',
      `A/B测试结果 — ${path.basename(filePath)}`,
      vscode.ViewColumn.Beside,
      { enableScripts: true }
    );
    panel.webview.html = renderAbTestHtml(report);
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: A/B测试失败 — ${err.message}`);
  }
}

async function runTokenAnalyzeOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  try {
    const output = await executeCli(['lint', '-t', filePath, '--format', 'json']);
    const report = JSON.parse(output);
    const results = report.results || [];
    const text = editor.document.getText();
    const charCount = text.length;
    const lineCount = editor.document.lineCount;
    const cnCount = (text.match(/[\u4e00-\u9fff]/g) || []).length;
    const enWordCount = (text.match(/[a-zA-Z]+/g) || []).length;
    const estimatedTokens = Math.ceil(cnCount * 1.5 + enWordCount * 1.3);
    const panel = vscode.window.createWebviewPanel(
      'promptTokenAnalyze',
      `Token分析 — ${path.basename(filePath)}`,
      vscode.ViewColumn.Beside,
      { enableScripts: true }
    );
    panel.webview.html = renderTokenHtml(charCount, lineCount, cnCount, enWordCount, estimatedTokens);
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: Token分析失败 — ${err.message}`);
  }
}

async function runVersionDiffOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  try {
    const templateId = path.basename(filePath, path.extname(filePath));
    const output = await executeCli(['version', '--action', 'list', '--template', templateId, '--format', 'json']);
    const versions = JSON.parse(output);
    if (!versions.versions || versions.versions.length < 2) {
      vscode.window.showInformationMessage('Prompt Lint: 需要至少2个版本才能对比');
      return;
    }
    const items: vscode.QuickPickItem[] = versions.versions.map((v: any, i: number) => ({
      label: `v${i + 1}: ${v.timestamp || v.created_at || 'unknown'}`,
      description: v.hash ? v.hash.substring(0, 8) : '',
    }));
    const from = await vscode.window.showQuickPick(items, { placeHolder: '选择起始版本' });
    if (!from) { return; }
    const to = await vscode.window.showQuickPick(items, { placeHolder: '选择目标版本' });
    if (!to) { return; }
    const fromIdx = items.indexOf(from);
    const toIdx = items.indexOf(to);
    const diffOutput = await executeCli(['version', '--action', 'diff', '--template', templateId, '--version-a', String(fromIdx + 1), '--version-b', String(toIdx + 1), '--format', 'json']);
    const panel = vscode.window.createWebviewPanel(
      'promptVersionDiff',
      `版本Diff — ${path.basename(filePath)}`,
      vscode.ViewColumn.Beside,
      { enableScripts: true }
    );
    panel.webview.html = renderDiffHtml(diffOutput, from.label, to.label);
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: 版本Diff失败 — ${err.message}`);
  }
}

function renderAbTestHtml(report: any): string {
  const results = report.results || [];
  const rows = results.map((r: any) =>
    `<tr><td>${r.provider || ''}</td><td>${r.model || ''}</td><td>${r.score?.toFixed(2) || 'N/A'}</td><td>${r.latency_ms?.toFixed(0) || 'N/A'}ms</td><td>${r.tokens || 'N/A'}</td></tr>`
  ).join('');
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
  body{font-family:-apple-system,sans-serif;padding:20px;background:#1e1e1e;color:#d4d4d4}
  table{border-collapse:collapse;width:100%;margin-top:16px}
  th,td{border:1px solid #444;padding:8px 12px;text-align:left}
  th{background:#264f78}h2{color:#569cd6}
  </style></head><body>
  <h2>A/B测试结果</h2><table><tr><th>Provider</th><th>模型</th><th>评分</th><th>延迟</th><th>Tokens</th></tr>${rows}</table>
  </body></html>`;
}

function renderTokenHtml(charCount: number, lineCount: number, cnCount: number, enWordCount: number, estTokens: number): string {
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
  body{font-family:-apple-system,sans-serif;padding:20px;background:#1e1e1e;color:#d4d4d4}
  .metric{display:inline-block;margin:12px;padding:16px;background:#252526;border-radius:8px;min-width:120px;text-align:center}
  .metric .val{font-size:28px;font-weight:700;color:#4ec9b0}.metric .label{font-size:11px;color:#858585;margin-top:4px}
  h2{color:#569cd6}.note{margin-top:16px;padding:12px;background:#1a3a1a;border-radius:6px;color:#6a9955;font-size:12px}
  </style></head><body>
  <h2>Token用量分析</h2>
  <div class="metric"><div class="val">${estTokens}</div><div class="label">预估Tokens</div></div>
  <div class="metric"><div class="val">${charCount}</div><div class="label">总字符数</div></div>
  <div class="metric"><div class="val">${lineCount}</div><div class="label">总行数</div></div>
  <div class="metric"><div class="val">${cnCount}</div><div class="label">中文字符</div></div>
  <div class="metric"><div class="val">${enWordCount}</div><div class="label">英文单词</div></div>
  <div class="note">Token估算: 中文×1.5 + 英文×1.3（实际以tiktoken为准）</div>
  </body></html>`;
}

function renderDiffHtml(diffText: string, fromLabel: string, toLabel: string): string {
  const escaped = diffText.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const lines = escaped.split('\n').map((line: string) => {
    if (line.startsWith('+') && !line.startsWith('+++')) return `<span style="color:#6a9955">${line}</span>`;
    if (line.startsWith('-') && !line.startsWith('---')) return `<span style="color:#f44747">${line}</span>`;
    return line;
  }).join('\n');
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
  body{font-family:'Fira Code',monospace;padding:20px;background:#1e1e1e;color:#d4d4d4;font-size:13px}
  pre{white-space:pre-wrap;word-break:break-all}h2{color:#569cd6;font-family:-apple-system,sans-serif}
  .header{font-family:-apple-system,sans-serif;margin-bottom:12px;font-size:12px;color:#858585}
  </style></head><body>
  <h2>版本Diff对比</h2>
  <div class="header">${fromLabel} → ${toLabel}</div>
  <pre>${lines}</pre></body></html>`;
}

async function runLint(doc: vscode.TextDocument) {
  const config = vscode.workspace.getConfiguration('promptLint');
  if (!config.get<boolean>('enable')) {
    return;
  }

  updateStatusBarLinting();
  const filePath = doc.uri.fsPath;
  const severityOverrides = config.get<Record<string, string>>('severityOverrides') || {};

  try {
    const output = await executeCli(['lint', '-t', filePath, '--format', 'json']);
    const report = JSON.parse(output);
    const results: Array<{ findings: LintFinding[]; template_id: string }> = report.results || [];

    const diagnostics: vscode.Diagnostic[] = [];
    const allFindings: LintFinding[] = [];

    for (const result of results) {
      for (const finding of result.findings) {
        allFindings.push(finding);
        // R218: location 契约(空 = 文件级 → 不猜行; 删除旧 parseInt+description子串搜索 hack)
        const range = rangeFromLocation(doc, finding.location);

        const effectiveSeverity = applySeverityOverrides(finding.severity, severityOverrides);
        const diag = new vscode.Diagnostic(
          range,
          `[${finding.rule_id}] ${finding.description}${finding.remediation ? ` — 修复: ${finding.remediation}` : ''}`,
          severityToVscode(effectiveSeverity)
        );
        diag.source = DIAGNOSTIC_SOURCE;
        diag.code = finding.rule_id;

        if (finding.severity === 'info' || finding.severity === 'low') {
          diag.tags = [vscode.DiagnosticTag.Unnecessary];
        }

        const relatedInfo = buildRelatedInfo(doc.uri, finding, doc);
        if (relatedInfo) {
          diag.relatedInformation = [relatedInfo];
        }

        diagnostics.push(diag);
      }
    }

    lintResultsCache.set(doc.uri.toString(), allFindings);
    diagnosticCollection.set(doc.uri, diagnostics);
    updateStatusBarForDoc(doc);
  } catch (err: any) {
    if (err.message && !err.message.includes('ENOENT')) {
      vscode.window.showWarningMessage(`Prompt Lint: ${err.message}`);
    }
    updateStatusBarIdle();
  }
}

function buildRelatedInfo(
  uri: vscode.Uri,
  finding: LintFinding,
  doc: vscode.TextDocument
): vscode.DiagnosticRelatedInformation | undefined {
  const ruleDescriptions: Record<string, string> = {
    'P001': '提示词应包含明确的角色定义',
    'P005': '缺少输出格式约束',
    'P006': '可能存在注入风险',
    'P016': '提示词过于模糊，建议增加具体约束',
    'P025': '缺少长度限制',
    'P026': '缺少幻觉防护',
  };
  const hint = ruleDescriptions[finding.rule_id];
  if (!hint) {
    return undefined;
  }
  // R218: location 契约
  const range = rangeFromLocation(doc, finding.location);
  return new vscode.DiagnosticRelatedInformation(
    new vscode.Location(uri, range),
    hint
  );
}

async function runScan(doc: vscode.TextDocument) {
  const filePath = doc.uri.fsPath;

  try {
    const output = await executeCli(['scan', '-t', filePath, '--format', 'json']);
    const report = JSON.parse(output);
    const findings: ScanFinding[] = report.findings || [];

    const existing: vscode.Diagnostic[] = [...(diagnosticCollection.get(doc.uri) || [])];

    for (const finding of findings) {
      // R218: location 契约(scan finding 无 location → 文件级, 不猜行)
      const range = rangeFromLocation(doc, finding.location);

      const diag = new vscode.Diagnostic(
        range,
        `[${finding.rule_id}] ⚠ 安全风险: ${finding.description}${finding.remediation ? ` — 修复: ${finding.remediation}` : ''}`,
        severityToVscode(finding.severity)
      );
      diag.source = 'prompt-scan';
      diag.code = finding.rule_id;
      if (finding.severity === 'critical') {
        diag.tags = [vscode.DiagnosticTag.Deprecated];
      }
      existing.push(diag);
    }

    diagnosticCollection.set(doc.uri, existing);
  } catch {
    // silent fail for scan
  }
}

// R218: location 契约 — 与 Python 端 types.parse_location 同语义(单一事实源):
//   "" = 文件级发现(消费端不得猜行) | "L:<line>" | "L:<line>:C:<col>" (均 1-based)
//   兼容旧 "line:col" 纯数字形式。非法/空 → null(按文件级处理)。
function parseLocation(location?: string): { line: number | null; col: number | null } {
  const loc = (location || '').trim();
  if (!loc) return { line: null, col: null };
  const raw = loc.startsWith('L:') ? loc.slice(2) : loc;
  const parts = raw.split(':C:');
  const line = Number.parseInt(parts[0], 10);
  const col = parts.length > 1 ? Number.parseInt(parts[1], 10) : null;
  if (!Number.isInteger(line) || line < 1) return { line: null, col: null };
  return { line, col: col !== null && Number.isInteger(col) ? col : null };
}

// 契约 → 诊断 Range: 行级定位收敛到该行(1-based→0-based); 文件级 → 首行0宽标记(不猜行不覆盖全文)
function rangeFromLocation(doc: vscode.TextDocument, location?: string): vscode.Range {
  const { line, col } = parseLocation(location);
  if (line === null) {
    return new vscode.Range(0, 0, 0, 0);
  }
  const lineIdx = Math.min(line - 1, Math.max(0, doc.lineCount - 1));
  const lineLen = doc.lineAt(lineIdx).text.length;
  const startCol = Math.min(Math.max(0, (col ?? 1) - 1), lineLen);
  const endCol = Math.min(startCol + Math.max(1, Math.min(20, lineLen - startCol)), lineLen);
  return new vscode.Range(lineIdx, startCol, lineIdx, endCol);
}

function executeCli(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const cliPath = getCliPath();
    const proc = spawn(cliPath, args, {
      timeout: 30000,
    });

    let stdout = '';
    let stderr = '';

    proc.stdout?.on('data', (data: Buffer) => {
      stdout += data.toString('utf-8');
    });

    proc.stderr?.on('data', (data: Buffer) => {
      stderr += data.toString('utf-8');
    });

    proc.on('close', (code: number | null) => {
      if (code === 0 || code === 1) {
        resolve(stdout);
      } else {
        reject(new Error(stderr || `Exit code: ${code}`));
      }
    });

    proc.on('error', (err: Error) => {
      reject(err);
    });
  });
}

function getCliPath(): string {
  const config = vscode.workspace.getConfiguration('promptLint');
  const customPath = config.get<string>('cliPath');
  if (customPath) {
    return customPath;
  }
  return 'prompt-cli';
}

class PromptCodeLensProvider implements vscode.CodeLensProvider {
  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const lenses: vscode.CodeLens[] = [];
    const findings = lintResultsCache.get(document.uri.toString()) || [];
    const total = 50;
    const passed = total - findings.length;
    const score = Math.round((passed / total) * 100);

    lenses.push(new vscode.CodeLens(
      new vscode.Range(0, 0, 0, 0),
      {
        title: `$(check) Prompt Score: ${score}/100`,
        command: 'promptLint.showLintScore',
      }
    ));

    if (findings.length > 0) {
      lenses.push(new vscode.CodeLens(
        new vscode.Range(0, 0, 0, 0),
        {
          title: `$(error) ${findings.length} issues`,
          command: 'promptLint.lintActiveFile',
        }
      ));
    }

    lenses.push(new vscode.CodeLens(
      new vscode.Range(0, 0, 0, 0),
      {
        title: '$(play) Evaluate',
        command: 'promptLint.evaluateActiveFile',
      }
    ));

    lenses.push(new vscode.CodeLens(
      new vscode.Range(0, 0, 0, 0),
      {
        title: '$(shield) Quality Gate',
        command: 'promptLint.qualityGate',
      }
    ));

    return lenses;
  }
}

class PromptQuickFixProvider implements vscode.CodeActionProvider {
  static providedCodeActionKinds = [vscode.CodeActionKind.QuickFix];

  provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
  ): vscode.CodeAction[] {
    const actions: vscode.CodeAction[] = [];
    const autoFixRules = new Set(['P005', 'P016', 'P006', 'P025', 'P026', 'P029']);

    for (const diag of context.diagnostics) {
      if (diag.source !== DIAGNOSTIC_SOURCE && diag.source !== 'prompt-scan' && diag.source !== 'prompt-pii') {
        continue;
      }
      const ruleId = typeof diag.code === 'string' ? diag.code : String(diag.code || '');

      if (autoFixRules.has(ruleId)) {
        const action = new vscode.CodeAction(
          `修复 ${ruleId}`,
          vscode.CodeActionKind.QuickFix
        );
        action.diagnostics = [diag];
        action.command = {
          command: 'promptLint.fix',
          title: `应用 ${ruleId} 自动修复`,
          arguments: [document.uri, ruleId],
        };
        action.isPreferred = true;
        actions.push(action);
      }

      if (diag.source === 'prompt-scan') {
        const viewDetailAction = new vscode.CodeAction(
          `查看 ${ruleId} 安全详情`,
          vscode.CodeActionKind.QuickFix
        );
        viewDetailAction.diagnostics = [diag];
        viewDetailAction.command = {
          command: 'promptLint.scanActiveFile',
          title: `查看安全扫描详情`,
        };
        actions.push(viewDetailAction);
      }

      const dismissAction = new vscode.CodeAction(
        `忽略 ${ruleId} (本次)`,
        vscode.CodeActionKind.QuickFix
      );
      dismissAction.diagnostics = [diag];
      actions.push(dismissAction);
    }

    return actions;
  }
}

class PromptLintTreeDataProvider implements vscode.TreeDataProvider<PromptTreeItem> {
  private _onDidChangeTreeData = new vscode.EventEmitter<PromptTreeItem | undefined>();
  readonly onDidChangeTreeData = this._onDidChangeTreeData.event;

  refresh(): void {
    this._onDidChangeTreeData.fire(undefined);
  }

  getTreeItem(element: PromptTreeItem): vscode.TreeItem {
    return element;
  }

  async getChildren(element?: PromptTreeItem): Promise<PromptTreeItem[]> {
    if (!element) {
      return [
        new PromptTreeItem('📂 工作区 Prompt', vscode.TreeItemCollapsibleState.Collapsed, 'workspace-root', 'root-folder'),
        new PromptTreeItem('🎯 场景模板推荐', vscode.TreeItemCollapsibleState.Collapsed, 'templates-root', 'star'),
        new PromptTreeItem('🔍 Lint 规则 (57条)', vscode.TreeItemCollapsibleState.Collapsed, 'rules', 'checklist'),
        new PromptTreeItem('🛡️ 安全扫描', vscode.TreeItemCollapsibleState.Collapsed, 'security', 'shield'),
      ];
    }

    if (element.contextValue === 'workspace-root') {
      return getWorkspacePromptFiles();
    }

    if (element.contextValue === 'templates-root') {
      return getTemplateCategories();
    }

    if (element.contextValue === 'template-category') {
      return getTemplatesByCategory(element.meta?.category || '');
    }

    if (element.contextValue === 'template-item') {
      return [];
    }

    if (element.contextValue === 'rules') {
      return [
        new PromptTreeItem('结构类 P001-P005', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('安全类 P006-P010', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('性能类 P011-P015', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('质量类 P016-P020', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('扩展类 P021-P030', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('Agent/RAG/多模态 P031-P040', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('lintlang参考 P041-P047', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('中文特有 P048-P050', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('多模态 MM001-MM007', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
      ];
    }
    if (element.contextValue === 'security') {
      return [
        new PromptTreeItem('注入检测 INJ-001~015', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('中文注入 INJ-ZH-001~015', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
        new PromptTreeItem('Unicode/Canary/Defender', vscode.TreeItemCollapsibleState.None, 'rule-group', 'folder'),
      ];
    }
    return [];
  }
}

async function getWorkspacePromptFiles(): Promise<PromptTreeItem[]> {
  const files = await vscode.workspace.findFiles('**/*.md', '**/node_modules/**', 100);
  const promptFiles = files.filter(f =>
    f.fsPath.endsWith('.md') || f.fsPath.endsWith('.prompt.md') || f.fsPath.endsWith('.prompt')
  );
  if (promptFiles.length === 0) {
    return [new PromptTreeItem('(无Prompt文件)', vscode.TreeItemCollapsibleState.None, 'empty-hint', 'info')];
  }
  return promptFiles.slice(0, 50).map(f => {
    const name = path.basename(f.fsPath);
    const relPath = vscode.workspace.asRelativePath(f);
    const item = new PromptTreeItem(relPath, vscode.TreeItemCollapsibleState.None, 'workspace-file', 'file');
    item.resourceUri = f;
    item.command = {
      command: 'vscode.open',
      title: '打开文件',
      arguments: [f],
    };
    item.tooltip = f.fsPath;
    return item;
  });
}

interface TemplateInfo {
  id: string;
  name: string;
  category: string;
  industry: string;
  lintScore: number;
  models: string[];
}

const BUILTIN_TEMPLATES: TemplateInfo[] = [
  { id: 'general-assistant', name: '通用助手', category: 'general', industry: '通用', lintScore: 92, models: ['gpt-4', 'claude-3', 'deepseek'] },
  { id: 'code-reviewer', name: '代码审查', category: 'development', industry: '科技', lintScore: 88, models: ['gpt-4', 'claude-3'] },
  { id: 'translator-pro', name: '专业翻译', category: 'translation', industry: '通用', lintScore: 95, models: ['gpt-4', 'deepseek', 'qwen'] },
  { id: 'data-analyst', name: '数据分析', category: 'analytics', industry: '金融', lintScore: 85, models: ['gpt-4', 'claude-3'] },
  { id: 'doc-writer', name: '文档撰写', category: 'writing', industry: '通用', lintScore: 90, models: ['gpt-4', 'qwen', 'deepseek'] },
  { id: 'security-auditor', name: '安全审计', category: 'security', industry: '科技', lintScore: 82, models: ['gpt-4', 'claude-3'] },
  { id: 'huawei-cloud-assistant', name: '华为云助手', category: 'cloud', industry: '华为云', lintScore: 93, models: ['qwen', 'deepseek', 'pangu'] },
  { id: 'rag-assistant', name: 'RAG助手', category: 'retrieval', industry: '通用', lintScore: 87, models: ['gpt-4', 'claude-3', 'qwen'] },
  { id: 'customer-service', name: '客服助手', category: 'service', industry: '电商', lintScore: 91, models: ['qwen', 'deepseek'] },
  { id: 'education-tutor', name: '教育辅导', category: 'education', industry: '教育', lintScore: 89, models: ['gpt-4', 'qwen'] },
  { id: 'medical-assistant', name: '医疗助手', category: 'medical', industry: '医疗', lintScore: 86, models: ['gpt-4', 'pangu'] },
  { id: 'legal-advisor', name: '法律顾问', category: 'legal', industry: '法律', lintScore: 84, models: ['gpt-4', 'claude-3'] },
  { id: 'creative-writer', name: '创意写作', category: 'creative', industry: '媒体', lintScore: 88, models: ['gpt-4', 'claude-3'] },
  { id: 'api-doc-generator', name: 'API文档生成', category: 'development', industry: '科技', lintScore: 91, models: ['gpt-4', 'deepseek'] },
  { id: 'harmonyos-dev', name: '鸿蒙开发助手', category: 'development', industry: '华为云', lintScore: 90, models: ['qwen', 'pangu'] },
];

function getTemplateCategories(): PromptTreeItem[] {
  const categories = [...new Set(BUILTIN_TEMPLATES.map(t => t.category))];
  return categories.map(cat => {
    const count = BUILTIN_TEMPLATES.filter(t => t.category === cat).length;
    const item = new PromptTreeItem(
      `${cat} (${count})`,
      vscode.TreeItemCollapsibleState.Collapsed,
      'template-category',
      'folder'
    );
    item.meta = { category: cat };
    return item;
  });
}

function getTemplatesByCategory(category: string): PromptTreeItem[] {
  return BUILTIN_TEMPLATES
    .filter(t => t.category === category)
    .map(t => {
      const item = new PromptTreeItem(
        `${t.name} (${t.lintScore}分)`,
        vscode.TreeItemCollapsibleState.None,
        'template-item',
        'file'
      );
      item.tooltip = `行业: ${t.industry}\n评分: ${t.lintScore}/100\n适配模型: ${t.models.join(', ')}`;
      item.description = t.industry;
      item.command = {
        command: 'promptLint.openTemplate',
        title: '打开模板',
        arguments: [t.id],
      };
      return item;
    });
}

class PromptTreeItem extends vscode.TreeItem {
  meta?: Record<string, string>;

  constructor(
    label: string,
    collapsibleState: vscode.TreeItemCollapsibleState,
    contextValue: string,
    iconName?: string,
  ) {
    super(label, collapsibleState);
    this.contextValue = contextValue;
    if (iconName) {
      this.iconPath = new vscode.ThemeIcon(iconName);
    }
  }
}

const path = require('path');

const TEMPLATE_CONTENT: Record<string, string> = {
  'general-assistant': `---
template_id: general-assistant
name: 通用助手
category: general
industry: 通用
---

# 角色
你是一个专业的AI助手，擅长回答各类问题。

# 约束
- 回答需准确、有条理
- 不确定时明确说明
- 使用简洁清晰的语言

# 输出格式
请按照以下格式输出：
1. 核心回答
2. 详细说明
3. 补充建议`,

  'code-reviewer': `---
template_id: code-reviewer
name: 代码审查
category: development
industry: 科技
---

# 角色
你是一位资深代码审查专家，擅长发现代码中的问题和改进机会。

# 约束
- 关注安全性、性能、可读性
- 给出具体修改建议
- 按严重程度分级(Critical/Major/Minor)

# 输出格式
## 审查结果
| 严重程度 | 文件:行号 | 问题描述 | 修改建议 |
|---------|----------|---------|---------|`,

  'translator-pro': `---
template_id: translator-pro
name: 专业翻译
category: translation
industry: 通用
---

# 角色
你是专业翻译专家，精通中英日韩多语言互译。

# 约束
- 保持原文语义和风格
- 专业术语准确翻译
- 标注翻译不确定处

# 输出格式
## 译文
[翻译内容]

## 术语表
| 原文 | 译文 | 说明 |
|-----|------|------|`,

  'huawei-cloud-assistant': `---
template_id: huawei-cloud-assistant
name: 华为云助手
category: cloud
industry: 华为云
---

# 角色
你是华为云技术专家，精通ECS/OBS/RDS/ModelArts等核心服务。

# 约束
- 优先推荐华为云最佳实践
- 提供具体操作步骤
- 注意区域和规格限制

# 输出格式
## 解决方案
1. 问题分析
2. 操作步骤
3. 验证方法`,

  'rag-assistant': `---
template_id: rag-assistant
name: RAG助手
category: retrieval
industry: 通用
---

# 角色
你是RAG检索增强生成专家，擅长基于检索结果生成高质量回答。

# 约束
- 仅基于检索结果回答
- 明确标注信息来源
- 检索结果不足时说明

# 输出格式
## 回答
[基于检索结果的回答]

## 来源
- [文档1]: 相关段落
- [文档2]: 相关段落`,
};

function openTemplatePreview(templateId: string): void {
  const content = TEMPLATE_CONTENT[templateId];
  if (!content) {
    vscode.window.showWarningMessage(`模板 ${templateId} 预览内容暂未提供`);
    return;
  }
  const panel = vscode.window.createWebviewPanel(
    'templatePreview',
    `模板预览 — ${templateId}`,
    vscode.ViewColumn.Beside,
    { enableScripts: false }
  );
  const lines = content.split('\n');
  const htmlBody = lines.map(line => {
    const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    if (escaped.startsWith('# ')) return `<h2>${escaped.slice(2)}</h2>`;
    if (escaped.startsWith('## ')) return `<h3>${escaped.slice(3)}</h3>`;
    if (escaped.startsWith('- ')) return `<li>${escaped.slice(2)}</li>`;
    if (escaped.startsWith('| ')) return `<tr><td>${escaped.split('|').filter(c=>c.trim()).join('</td><td>')}</td></tr>`;
    if (escaped.trim() === '') return '<br>';
    return `<p>${escaped}</p>`;
  }).join('\n');

  panel.webview.html = `<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><style>
  body { font-family: -apple-system, 'Segoe UI', sans-serif; padding: 20px; background: #1e1e1e; color: #d4d4d4; max-width: 800px; margin: 0 auto; }
  h2 { color: #4ec9b0; border-bottom: 1px solid #333; padding-bottom: 8px; }
  h3 { color: #569cd6; }
  table { border-collapse: collapse; width: 100%; margin: 8px 0; }
  th, td { border: 1px solid #444; padding: 6px 10px; text-align: left; }
  tr:first-child { background: #264f78; font-weight: bold; }
  li { margin: 4px 0; }
  code { background: #2d2d2d; padding: 2px 6px; border-radius: 3px; }
  .actions { position: fixed; top: 20px; right: 20px; }
  .btn { background: #0e639c; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-left: 8px; }
</style></head>
<body>
<div class="actions">
  <button class="btn" onclick="applyTemplate()">应用模板</button>
</div>
${htmlBody}
<script>
const vscode = acquireVsCodeApi();
function applyTemplate() {
  vscode.postMessage({ command: 'apply' });
}
</script>
</body></html>`;
}

async function searchAndShowTemplates(query: string): Promise<void> {
  const q = query.toLowerCase();
  const matches = BUILTIN_TEMPLATES.filter(t =>
    t.name.toLowerCase().includes(q) ||
    t.category.toLowerCase().includes(q) ||
    t.industry.toLowerCase().includes(q) ||
    t.id.toLowerCase().includes(q) ||
    t.models.some(m => m.toLowerCase().includes(q))
  );
  if (matches.length === 0) {
    vscode.window.showInformationMessage(`未找到匹配"${query}"的模板`);
    return;
  }
  const items = matches.map(t => ({
    label: `${t.name} (${t.lintScore}分)`,
    description: `${t.category} | ${t.industry}`,
    detail: `适配模型: ${t.models.join(', ')}`,
    templateId: t.id,
  }));
  const selected = await vscode.window.showQuickPick(items, {
    placeHolder: `搜索结果: "${query}" (${matches.length}个匹配)`,
  });
  if (selected) {
    openTemplatePreview(selected.templateId);
  }
}

async function runScorecardOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  try {
    const output = await executeCli(['score', '--target', filePath, '--format', 'json']);
    const card = JSON.parse(output);
    const gc: Record<string,string> = {'A':'#22c55e','B':'#3b82f6','C':'#f59e0b','D':'#ef4444','F':'#dc2626'};
    const color = gc[card.grade] || '#6b7280';
    const dimRows = (card.dimensions || []).map((d: any) =>
      `<tr><td>${d.name}</td><td style="color:${d.ratio>=0.8?'#22c55e':d.ratio>=0.5?'#f59e0b':'#ef4444'}">${d.earned}/${d.max_points}</td><td>${Math.round(d.ratio*100)}%</td></tr>`
    ).join('');
    const panel = vscode.window.createWebviewPanel(
      'promptScorecard',
      `安全评分卡 — ${path.basename(filePath)}`,
      vscode.ViewColumn.Beside,
      { enableScripts: false }
    );
    panel.webview.html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
    body{font-family:-apple-system,sans-serif;padding:20px;background:#1e1e1e;color:#d4d4d4;text-align:center}
    .score{font-size:64px;font-weight:800;color:${color}}.grade{font-size:24px;font-weight:600;color:${color}}
    .decision{font-size:14px;margin-top:8px}table{border-collapse:collapse;width:100%;margin-top:16px}
    th,td{border:1px solid #444;padding:8px 12px;text-align:left}th{background:#264f78}
    .summary{font-size:12px;color:#999;margin-top:12px}
    </style></head><body>
    <div class="score">${card.overall_score}</div><div class="grade">Grade ${card.grade}</div>
    <div class="decision">决策: <b>${card.decision.toUpperCase()}</b></div>
    <table><tr><th>维度</th><th>得分</th><th>比率</th></tr>${dimRows}</table>
    <div class="summary">${card.summary || ''}</div>
    </body></html>`;
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: 评分卡失败 — ${err.message}`);
  }
}

async function runFusionEngineOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  try {
    const output = await executeCli(['engine', '--target', filePath, '--format', 'json']);
    const result = JSON.parse(output);
    const dc: Record<string,string> = {'allow':'#22c55e','warn':'#f59e0b','block':'#dc2626'};
    const color = dc[result.decision] || '#6b7280';
    const layerRows = (result.layer_results || []).map((lr: any) =>
      `<tr><td>${lr.layer}</td><td style="color:${lr.score<0.1?'#22c55e':lr.score<0.5?'#f59e0b':'#dc2626'}">${lr.score.toFixed(4)}</td><td>${lr.latency_ms.toFixed(2)}ms</td><td style="color:#999;font-size:11px">${(lr.evidence||[]).slice(0,2).join('; ')}</td></tr>`
    ).join('');
    const panel = vscode.window.createWebviewPanel(
      'promptEngine',
      `融合引擎分析 — ${path.basename(filePath)}`,
      vscode.ViewColumn.Beside,
      { enableScripts: false }
    );
    panel.webview.html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
    body{font-family:-apple-system,sans-serif;padding:20px;background:#1e1e1e;color:#d4d4d4;text-align:center}
    .decision{font-size:48px;font-weight:800;color:${color}}
    .scores{font-size:12px;color:#999;margin-top:8px}table{border-collapse:collapse;width:100%;margin-top:16px}
    th,td{border:1px solid #444;padding:6px 10px;text-align:left}th{background:#264f78}
    </style></head><body>
    <div class="decision">${result.decision.toUpperCase()}</div>
    <div class="scores">风险: ${result.risk_score.toFixed(4)} | 校准: ${result.calibrated_score.toFixed(4)} | 置信度: ${result.confidence.toFixed(4)} | 耗时: ${result.scan_time_ms.toFixed(2)}ms</div>
    <table><tr><th>层</th><th>分数</th><th>延迟</th><th>证据</th></tr>${layerRows}</table>
    </body></html>`;
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: 融合引擎分析失败 — ${err.message}`);
  }
}

async function runBadgeOnActiveFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || !isMarkdownFile(editor.document)) {
    vscode.window.showWarningMessage('Prompt Lint: 请打开一个Markdown文件');
    return;
  }
  const filePath = editor.document.uri.fsPath;
  const badgePath = filePath.replace(/\.md$/, '.badge.svg');
  try {
    await executeCli(['badge', '--target', filePath, '--output', badgePath]);
    const panel = vscode.window.createWebviewPanel(
      'promptBadge',
      `安全评分徽章 — ${path.basename(filePath)}`,
      vscode.ViewColumn.Beside,
      { enableScripts: false }
    );
    panel.webview.html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><style>
    body{font-family:-apple-system,sans-serif;padding:20px;background:#1e1e1e;color:#d4d4d4;text-align:center}
    img{max-width:400px}
    </style></head><body>
    <img src="file:///${badgePath.replace(/\\/g,'/')}" alt="Security Badge">
    <p style="font-size:11px;color:#999;margin-top:12px">徽章已保存到: ${badgePath}</p>
    </body></html>`;
  } catch (err: any) {
    vscode.window.showErrorMessage(`Prompt Lint: 徽章生成失败 — ${err.message}`);
  }
}

export function deactivate() {
  for (const timer of debounceTimers.values()) {
    clearTimeout(timer);
  }
  debounceTimers.clear();
  diagnosticCollection.dispose();
  statusBarItem.dispose();
}
