import * as vscode from 'vscode';
import { spawn } from 'child_process';

const DIAGNOSTIC_SOURCE = 'prompt-lint';

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
  remediation?: string;
}

interface EvaluateResult {
  score: number;
  dimensions: Record<string, number>;
  summary: string;
}

let diagnosticCollection: vscode.DiagnosticCollection;
let lintResultsCache: Map<string, LintFinding[]> = new Map();

export function activate(context: vscode.ExtensionContext) {
  diagnosticCollection = vscode.languages.createDiagnosticCollection('prompt-lint');
  context.subscriptions.push(diagnosticCollection);

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
    vscode.commands.registerCommand('promptLint.fix', (docUri: vscode.Uri, ruleId: string) => {
      applyQuickFix(docUri, ruleId);
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

  vscode.workspace.onDidSaveTextDocument((doc) => {
    const config = vscode.workspace.getConfiguration('promptLint');
    if (config.get<boolean>('lintOnSave') && isMarkdownFile(doc)) {
      runLint(doc);
      treeProvider.refresh();
      if (config.get<boolean>('securityScan')) {
        runScan(doc);
      }
    }
  });

  vscode.workspace.onDidChangeTextDocument((e) => {
    const config = vscode.workspace.getConfiguration('promptLint');
    if (config.get<boolean>('lintOnType') && isMarkdownFile(e.document)) {
      runLint(e.document);
      treeProvider.refresh();
    }
  });
}

function isMarkdownFile(doc: vscode.TextDocument): boolean {
  return doc.languageId === 'markdown' || doc.fileName.endsWith('.md');
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
  const total = 30;
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

async function runLint(doc: vscode.TextDocument) {
  const config = vscode.workspace.getConfiguration('promptLint');
  if (!config.get<boolean>('enable')) {
    return;
  }

  const filePath = doc.uri.fsPath;
  const text = doc.getText();

  try {
    const output = await executeCli(['lint', '-t', filePath, '--format', 'json']);
    const report = JSON.parse(output);
    const results: Array<{ findings: LintFinding[]; template_id: string }> = report.results || [];

    const diagnostics: vscode.Diagnostic[] = [];
    const allFindings: LintFinding[] = [];

    for (const result of results) {
      for (const finding of result.findings) {
        allFindings.push(finding);
        const line = findLineNumber(text, finding.description);
        const range = new vscode.Range(
          new vscode.Position(line, 0),
          new vscode.Position(line, finding.description.length)
        );

        const diag = new vscode.Diagnostic(
          range,
          `[${finding.rule_id}] ${finding.description}${finding.remediation ? ` — 修复: ${finding.remediation}` : ''}`,
          severityToVscode(finding.severity)
        );
        diag.source = DIAGNOSTIC_SOURCE;
        diag.code = finding.rule_id;
        diagnostics.push(diag);
      }
    }

    lintResultsCache.set(doc.uri.toString(), allFindings);
    diagnosticCollection.set(doc.uri, diagnostics);
  } catch (err: any) {
    if (err.message && !err.message.includes('ENOENT')) {
      vscode.window.showWarningMessage(`Prompt Lint: ${err.message}`);
    }
  }
}

async function runScan(doc: vscode.TextDocument) {
  const filePath = doc.uri.fsPath;
  const text = doc.getText();

  try {
    const output = await executeCli(['scan', '-t', filePath, '--format', 'json']);
    const report = JSON.parse(output);
    const findings: ScanFinding[] = report.findings || [];

    const existing = diagnosticCollection.get(doc.uri) || [];

    for (const finding of findings) {
      const line = findLineNumber(text, finding.description);
      const range = new vscode.Range(
        new vscode.Position(line, 0),
        new vscode.Position(line, Math.min(finding.description.length, 80))
      );

      const diag = new vscode.Diagnostic(
        range,
        `[${finding.rule_id}] ⚠ 安全风险: ${finding.description}${finding.remediation ? ` — 修复: ${finding.remediation}` : ''}`,
        severityToVscode(finding.severity)
      );
      diag.source = 'prompt-scan';
      diag.code = finding.rule_id;
      existing.push(diag);
    }

    diagnosticCollection.set(doc.uri, existing);
  } catch {
    // silent fail for scan
  }
}

function findLineNumber(text: string, searchStr: string): number {
  if (!searchStr) return 0;
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes(searchStr.substring(0, 30))) {
      return i;
    }
  }
  return 0;
}

function executeCli(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const cliPath = getCliPath();
    const proc = spawn(cliPath, args, {
      encoding: 'utf-8',
      timeout: 30000,
    });

    let stdout = '';
    let stderr = '';

    proc.stdout?.on('data', (data: Buffer) => {
      stdout += data.toString();
    });

    proc.stderr?.on('data', (data: Buffer) => {
      stderr += data.toString();
    });

    proc.on('close', (code) => {
      if (code === 0 || code === 1) {
        resolve(stdout);
      } else {
        reject(new Error(stderr || `Exit code: ${code}`));
      }
    });

    proc.on('error', (err) => {
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
    const total = 30;
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

    return lenses;
  }
}

class PromptQuickFixProvider implements vscode.CodeActionsProvider {
  static providedCodeActionKinds = [vscode.CodeActionKind.QuickFix];

  provideCodeActions(
    document: vscode.TextDocument,
    range: vscode.Range | vscode.Selection,
    context: vscode.CodeActionContext,
  ): vscode.CodeAction[] {
    const actions: vscode.CodeAction[] = [];
    const autoFixRules = new Set(['P005', 'P016', 'P006', 'P025', 'P026', 'P029']);

    for (const diag of context.diagnostics) {
      if (diag.source !== DIAGNOSTIC_SOURCE && diag.source !== 'prompt-scan') {
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

  getChildren(element?: PromptTreeItem): PromptTreeItem[] {
    if (!element) {
      return [
        new PromptTreeItem('Lint 规则 (30条)', vscode.TreeItemCollapsibleState.Collapsed, 'rules'),
        new PromptTreeItem('安全扫描 (15条)', vscode.TreeItemCollapsibleState.Collapsed, 'security'),
      ];
    }
    if (element.contextValue === 'rules') {
      return [
        new PromptTreeItem('结构类 P001-P005', vscode.TreeItemCollapsibleState.None, 'rule-group'),
        new PromptTreeItem('安全类 P006-P010', vscode.TreeItemCollapsibleState.None, 'rule-group'),
        new PromptTreeItem('性能类 P011-P015', vscode.TreeItemCollapsibleState.None, 'rule-group'),
        new PromptTreeItem('质量类 P016-P020', vscode.TreeItemCollapsibleState.None, 'rule-group'),
        new PromptTreeItem('扩展类 P021-P030', vscode.TreeItemCollapsibleState.None, 'rule-group'),
      ];
    }
    if (element.contextValue === 'security') {
      return [
        new PromptTreeItem('注入检测 INJ-001~015', vscode.TreeItemCollapsibleState.None, 'rule-group'),
      ];
    }
    return [];
  }
}

class PromptTreeItem extends vscode.TreeItem {
  constructor(
    label: string,
    collapsibleState: vscode.TreeItemCollapsibleState,
    contextValue: string,
  ) {
    super(label, collapsibleState);
    this.contextValue = contextValue;
    if (contextValue === 'rules') {
      this.iconPath = new vscode.ThemeIcon('checklist');
    } else if (contextValue === 'security') {
      this.iconPath = new vscode.ThemeIcon('shield');
    } else if (contextValue === 'rule-group') {
      this.iconPath = new vscode.ThemeIcon('folder');
    }
  }
}

const path = require('path');

export function deactivate() {
  diagnosticCollection.dispose();
}
