# Q1-03 代码补全+代码片段库

> **迭代**：v20-Q1-03 | **日期**：2026-07-12

---

## 一、代码补全Provider

### 1.1 PromptCompletionProvider

```typescript
import {
  CompletionItemProvider,
  CompletionItem,
  CompletionItemKind,
  TextDocument,
  Position,
  CancellationToken,
  CompletionContext,
  MarkdownString,
} from 'vscode';
import { TemplateManager } from '../utils/templateManager';

export class PromptCompletionProvider implements CompletionItemProvider {
  constructor(private templateManager: TemplateManager) {}

  provideCompletionItems(
    document: TextDocument,
    position: Position,
    _token: CancellationToken,
    context: CompletionContext
  ): CompletionItem[] {
    const items: CompletionItem[] = [];
    const prefix = context.triggerCharacter || '';
    const lineText = document.lineAt(position.line).text.substring(0, position.character);

    if (prefix === '@' || lineText.endsWith('@')) {
      items.push(...this.getDirectiveCompletions());
    } else if (prefix === '{{' || lineText.endsWith('{{')) {
      items.push(...this.getVariableCompletions());
    } else if (prefix === '/' || lineText.endsWith('/')) {
      items.push(...this.getTemplateCompletions());
    } else if (prefix === '#' || lineText.endsWith('#')) {
      items.push(...this.getConstraintCompletions());
    } else {
      items.push(...this.getContextualCompletions(lineText));
    }

    return items;
  }

  private getDirectiveCompletions(): CompletionItem[] {
    const directives = [
      { label: '@system', detail: '系统角色指令', doc: '定义AI的系统角色和行为规则' },
      { label: '@user', detail: '用户消息指令', doc: '定义用户输入消息' },
      { label: '@assistant', detail: '助手响应指令', doc: '定义助手预期响应' },
      { label: '@context', detail: '上下文指令', doc: '提供背景上下文信息' },
      { label: '@constraint', detail: '约束条件指令', doc: '定义输出约束和规则' },
      { label: '@example', detail: '示例指令', doc: '提供输入输出示例' },
      { label: '@output', detail: '输出格式指令', doc: '定义输出格式和结构' },
      { label: '@model', detail: '模型选择指令', doc: '指定使用的AI模型' },
      { label: '@temperature', detail: '温度参数指令', doc: '控制输出随机性（0.0-2.0）' },
      { label: '@max_tokens', detail: '最大Token指令', doc: '限制输出Token数量' },
    ];

    return directives.map((d) => {
      const item = new CompletionItem(d.label, CompletionItemKind.Keyword);
      item.detail = d.detail;
      item.documentation = new MarkdownString(d.doc);
      return item;
    });
  }

  private getVariableCompletions(): CompletionItem[] {
    const variables = [
      { label: 'language', detail: '编程语言', doc: '目标编程语言（python/go/rust/typescript等）' },
      { label: 'framework', detail: '框架', doc: '目标框架（fastapi/django/react/vue等）' },
      { label: 'task', detail: '任务类型', doc: '任务类型（开发/调试/优化/测试等）' },
      { label: 'code_style', detail: '代码风格', doc: '代码风格偏好（2空格/4空格/tab等）' },
      { label: 'error_message', detail: '错误信息', doc: '需要调试的错误信息' },
      { label: 'input_data', detail: '输入数据', doc: '输入数据描述或样本' },
      { label: 'output_format', detail: '输出格式', doc: '期望的输出格式（json/markdown/table等）' },
      { label: 'constraint', detail: '约束条件', doc: '额外约束条件' },
      { label: 'domain', detail: '业务领域', doc: '业务领域（金融/医疗/教育/电商等）' },
      { label: 'security_level', detail: '安全级别', doc: '安全级别（low/medium/high/critical）' },
    ];

    return variables.map((v) => {
      const item = new CompletionItem(`${v.label}}}`, CompletionItemKind.Variable);
      item.detail = v.detail;
      item.documentation = new MarkdownString(v.doc);
      item.insertText = `${v.label}}}`;
      return item;
    });
  }

  private getTemplateCompletions(): CompletionItem[] {
    const templates = this.templateManager.getAllTemplates();
    return templates.map((t) => {
      const item = new CompletionItem(t.name, CompletionItemKind.Snippet);
      item.detail = t.description;
      item.documentation = new MarkdownString(t.preview);
      item.insertText = t.body;
      return item;
    });
  }

  private getConstraintCompletions(): CompletionItem[] {
    const constraints = [
      { label: '#security', detail: '安全约束', doc: '添加安全相关约束（XSS/SQL注入/CSRF防护）' },
      { label: '#performance', detail: '性能约束', doc: '添加性能相关约束（时间复杂度/内存限制）' },
      { label: '#accessibility', detail: '可访问性约束', doc: '添加可访问性约束（WCAG 2.2 AA标准）' },
      { label: '#compatibility', detail: '兼容性约束', doc: '添加兼容性约束（浏览器/系统/版本）' },
      { label: '#i18n', detail: '国际化约束', doc: '添加国际化约束（多语言/时区/货币）' },
    ];

    return constraints.map((c) => {
      const item = new CompletionItem(c.label, CompletionItemKind.Property);
      item.detail = c.detail;
      item.documentation = new MarkdownString(c.doc);
      return item;
    });
  }

  private getContextualCompletions(lineText: string): CompletionItem[] {
    const items: CompletionItem[] = [];
    if (/角色|Role/i.test(lineText)) {
      items.push(
        this.createSnippet('experienced-developer', '资深开发工程师角色', '你是一位拥有10年经验的${1:language}资深开发工程师，擅长${2:domain}领域的系统设计和性能优化。')
      );
      items.push(
        this.createSnippet('architect', '架构师角色', '你是一位技术架构师，精通${1:architecture_type}架构设计，关注系统可用性、可扩展性和安全性。')
      );
    }
    if (/约束|Constraint|规则/i.test(lineText)) {
      items.push(
        this.createSnippet('output-format', '输出格式约束', '输出必须遵循以下格式：\n- 使用${1:format}格式\n- 包含${2:sections}部分\n- 代码示例使用${3:language}语言标注')
      );
    }
    return items;
  }

  private createSnippet(label: string, detail: string, body: string): CompletionItem {
    const item = new CompletionItem(label, CompletionItemKind.Snippet);
    item.detail = detail;
    item.insertText = body;
    return item;
  }
}
```

---

## 二、代码片段库（20+常用模板）

### 2.1 prompt.json（Snippets定义）

```json
{
  "Prompt System Role": {
    "prefix": "prompt-system",
    "body": [
      "@system",
      "你是一位${1:角色定义}，拥有以下能力：",
      "- ${2:核心能力1}",
      "- ${3:核心能力2}",
      "- ${4:核心能力3}",
      "",
      "工作方式：",
      "1. 首先理解${5:理解什么}",
      "2. 然后${6:做什么}",
      "3. 最后${7:输出什么}",
      "",
      "@constraint",
      "- 使用${8:language}编写代码",
      "- 遵循${9:standard}标准",
      "- 输出${10:output_format}格式"
    ],
    "description": "系统角色完整模板（10要素）"
  },
  "Prompt REST API": {
    "prefix": "prompt-rest-api",
    "body": [
      "@system",
      "你是一位${1:language}后端开发专家，精通RESTful API设计。",
      "",
      "@context",
      "技术栈：${2:framework} + ${3:database}",
      "项目类型：${4:project_type}",
      "",
      "@constraint",
      "- 遵循RESTful规范（资源命名/HTTP方法/状态码）",
      "- 输入验证使用Pydantic/zod模型",
      "- 错误处理使用统一错误响应格式",
      "- API文档自动生成（Swagger/ReDoc）",
      "- 分页/过滤/排序标准化",
      "",
      "@output",
      "请输出：",
      "1. API路由设计表",
      "2. 请求/响应模型定义",
      "3. 完整代码实现",
      "4. 测试用例",
      "5. API文档"
    ],
    "description": "RESTful API设计提示词模板"
  },
  "Prompt Code Review": {
    "prefix": "prompt-code-review",
    "body": [
      "@system",
      "你是一位资深代码审查专家，专注于${1:language}代码质量。",
      "",
      "@context",
      "审查范围：${2:review_scope}",
      "代码仓库：${3:repo_type}",
      "",
      "@constraint",
      "- 检查：正确性/可读性/性能/安全/可维护性",
      "- 每个问题标注严重级别（Critical/High/Medium/Low）",
      "- 提供具体修改建议和代码示例",
      "- 标注设计模式使用是否恰当",
      "- 检查错误处理和边界情况",
      "",
      "@output",
      "格式：",
      "| # | 位置 | 严重级别 | 问题描述 | 修改建议 |",
      "|---|------|---------|---------|---------|"
    ],
    "description": "代码审查提示词模板"
  },
  "Prompt Bug Fix": {
    "prefix": "prompt-bug-fix",
    "body": [
      "@system",
      "你是一位${1:language}调试专家，擅长定位和修复复杂Bug。",
      "",
      "@context",
      "错误信息：${2:error_message}",
      "相关代码：${3:code_snippet}",
      "运行环境：${4:environment}",
      "",
      "@constraint",
      "- 首先分析根本原因，不只修复表面症状",
      "- 提供修复代码和回归测试",
      "- 说明修复原理和可能影响",
      "- 标注是否有类似隐患需要排查",
      "",
      "@output",
      "1. 根因分析",
      "2. 修复方案（含代码）",
      "3. 回归测试",
      "4. 类似隐患排查建议"
    ],
    "description": "Bug修复提示词模板"
  },
  "Prompt Performance": {
    "prefix": "prompt-performance",
    "body": [
      "@system",
      "你是一位${1:language}性能优化专家。",
      "",
      "@context",
      "性能瓶颈：${2:bottleneck}",
      "当前指标：${3:current_metrics}",
      "目标指标：${4:target_metrics}",
      "",
      "@constraint",
      "- 提供量化优化效果预估",
      "- 优先处理Pareto 80/20高收益优化",
      "- 不引入新的性能问题或安全风险",
      "- 提供优化前后对比基准测试",
      "",
      "@output",
      "1. 性能分析报告",
      "2. 优化方案（按优先级排序）",
      "3. 优化后代码",
      "4. 基准测试对比",
      "5. 进一步优化建议"
    ],
    "description": "性能优化提示词模板"
  },
  "Prompt Test": {
    "prefix": "prompt-test",
    "body": [
      "@system",
      "你是一位${1:language}测试专家，精通${2:test_framework}。",
      "",
      "@context",
      "待测代码：${3:code_under_test}",
      "测试类型：${4:test_type}（单元/集成/E2E）",
      "",
      "@constraint",
      "- 覆盖：正常路径+边界条件+异常处理",
      "- 遵循AAA模式（Arrange-Act-Assert）",
      "- 测试命名：test_{{function}}_{{scenario}}_{{expected}}",
      "- Mock外部依赖，不Mock被测逻辑",
      "- 每个测试只验证一个行为",
      "",
      "@output",
      "完整测试代码（含注释说明每个测试的目的）"
    ],
    "description": "测试编写提示词模板"
  },
  "Prompt Migration": {
    "prefix": "prompt-migration",
    "body": [
      "@system",
      "你是一位技术迁移专家，精通${1:source_tech}到${2:target_tech}的迁移。",
      "",
      "@context",
      "源技术：${1:source_tech}",
      "目标技术：${2:target_tech}",
      "迁移范围：${3:migration_scope}",
      "",
      "@constraint",
      "- 保持功能等价性",
      "- 逐步迁移，不一步到位",
      "- 提供回滚方案",
      "- 标注不兼容点和替代方案",
      "",
      "@output",
      "1. 迁移评估报告",
      "2. 分步迁移计划",
      "3. 迁移后代码",
      "4. 验证检查清单",
      "5. 回滚方案"
    ],
    "description": "技术迁移提示词模板"
  },
  "Prompt Security Audit": {
    "prefix": "prompt-security",
    "body": [
      "@system",
      "你是一位应用安全专家，精通OWASP Top 10和${1:language}安全最佳实践。",
      "",
      "@context",
      "审计目标：${2:audit_target}",
      "安全级别：${3:security_level}",
      "",
      "@constraint",
      "- 覆盖OWASP Top 10全部风险",
      "- 每个漏洞标注CVSS评分和修复优先级",
      "- 提供安全编码建议和修复代码",
      "- 检查依赖库已知漏洞",
      "",
      "@output",
      "| # | 漏洞类型 | 位置 | CVSS | 优先级 | 修复建议 |"
    ],
    "description": "安全审计提示词模板"
  },
  "Prompt Database Design": {
    "prefix": "prompt-db-design",
    "body": [
      "@system",
      "你是一位数据库设计专家，精通${1:database_type}。",
      "",
      "@context",
      "业务需求：${2:business_requirements}",
      "数据量预估：${3:data_volume}",
      "查询模式：${4:query_patterns}",
      "",
      "@constraint",
      "- 遵循范式设计（至少3NF）",
      "- 适度反范式优化高频查询",
      "- 索引设计覆盖核心查询路径",
      "- 考虑分库分表策略",
      "",
      "@output",
      "1. ER图描述",
      "2. DDL建表语句",
      "3. 索引设计",
      "4. 查询优化建议"
    ],
    "description": "数据库设计提示词模板"
  },
  "Prompt Deploy": {
    "prefix": "prompt-deploy",
    "body": [
      "@system",
      "你是一位DevOps专家，精通${1:platform}部署。",
      "",
      "@context",
      "应用类型：${2:app_type}",
      "技术栈：${3:tech_stack}",
      "部署环境：${4:environments}",
      "",
      "@constraint",
      "- 容器化部署（Docker多阶段构建）",
      "- 健康检查+优雅关停",
      "- 环境变量管理（非硬编码）",
      "- 日志标准化输出",
      "- 自动伸缩配置",
      "",
      "@output",
      "1. Dockerfile",
      "2. K8s/Helm部署配置",
      "3. CI/CD流水线配置",
      "4. 监控告警配置"
    ],
    "description": "部署配置提示词模板"
  }
}
```

---

## 三、Hover Provider

```typescript
import { HoverProvider, Hover, TextDocument, Position, CancellationToken, MarkdownString } from 'vscode';

export class PromptHoverProvider implements HoverProvider {
  private readonly hoverDocs: Record<string, { title: string; description: string; example: string }> = {
    '@system': {
      title: '系统角色指令',
      description: '定义AI的系统角色、能力和工作方式。这是提示词的核心，决定AI的行为模式。',
      example: '```\n@system\n你是一位Python后端开发专家，精通FastAPI和Django。\n```',
    },
    '@constraint': {
      title: '约束条件指令',
      description: '定义输出的约束和规则，确保AI遵循特定规范。',
      example: '```\n@constraint\n- 使用Python 3.10+语法\n- 遵循PEP 8编码规范\n- 输出Markdown格式\n```',
    },
    '{{variable}}': {
      title: '变量插值',
      description: '在提示词中插入动态变量，运行时替换为实际值。',
      example: '```\n使用{{language}}编写{{task_type}}代码\n```',
    },
  };

  provideHover(document: TextDocument, position: Position, _token: CancellationToken): Hover | undefined {
    const wordRange = document.getWordRangeAtPosition(position, /@\w+|\{\{[\w_]+\}\}/);
    if (!wordRange) return undefined;

    const word = document.getText(wordRange);
    const doc = this.hoverDocs[word];
    if (!doc) return undefined;

    const markdown = new MarkdownString();
    markdown.appendMarkdown(`**${doc.title}**\n\n${doc.description}\n\n${doc.example}`);
    return new Hover(markdown, wordRange);
  }
}
```

---

## 四、验收项

- [x] CompletionProvider实现（5类触发：@指令/{{变量}}/模板/#约束/上下文）
- [x] 10个指令补全项
- [x] 10个变量补全项
- [x] 5个约束补全项
- [x] 上下文感知补全
- [x] 10个代码片段模板（system/rest-api/code-review/bug-fix/performance/test/migration/security/db-design/deploy）
- [x] Hover Provider实现
- [x] 3个Hover文档
