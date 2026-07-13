import * as vscode from 'vscode';
import { spawn } from 'child_process';
import * as path from 'path';

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

let diagnosticCollection: vscode.DiagnosticCollection;

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

  vscode.workspace.onDidSaveTextDocument((doc) => {
    const config = vscode.workspace.getConfiguration('promptLint');
    if (config.get<boolean>('lintOnSave') && isMarkdownFile(doc)) {
      runLint(doc);
      if (config.get<boolean>('securityScan')) {
        runScan(doc);
      }
    }
  });

  vscode.workspace.onDidChangeTextDocument((e) => {
    const config = vscode.workspace.getConfiguration('promptLint');
    if (config.get<boolean>('lintOnType') && isMarkdownFile(e.document)) {
      runLint(e.document);
    }
  });
}

function isMarkdownFile(doc: vscode.TextDocument): boolean {
  return doc.languageId === 'markdown' || doc.fileName.endsWith('.md');
}

function severityToVscode(severity: string): vscode.DiagnosticSeverity {
  const config = vscode.workspace.getConfiguration('promptLint');
  const overrides = config.get<Record<string, string>>('severityOverrides') || {};

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

    for (const result of results) {
      for (const finding of result.findings) {
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

export function deactivate() {
  diagnosticCollection.dispose();
}
