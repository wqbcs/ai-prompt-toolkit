"""鸿蒙ArkTS代码片段模板生成器

基于Lint规则P121-P150的修复建议，生成鸿蒙Stage模型/ArkUI/分布式/卡片开发的
ArkTS/ArkUI代码片段模板，帮助开发者快速修复Lint发现的问题。

参考: HarmonyOS Stage Model Development Guide, ArkUI Best Practices
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ArkTSSnippet:
    rule_id: str
    title: str
    description: str
    code: str
    language: str = "arkts"
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "description": self.description,
            "code": self.code,
            "language": self.language,
            "tags": self.tags,
        }


_SNIPPETS: list[ArkTSSnippet] = [
    ArkTSSnippet(
        rule_id="P121",
        title="ArkTS严格模式声明",
        description="启用ArkTS严格模式，禁止动态类型和运行时类型修改",
        code="""// ArkTS严格模式 - 禁止any/dynamic类型
@Entry
@Component
struct StrictModeExample {
  @State message: string = 'Hello HarmonyOS'

  build() {
    Column() {
      Text(this.message)
        .fontSize(16)
    }
  }
}""",
        tags=["arkts", "strict-mode"],
    ),
    ArkTSSnippet(
        rule_id="P122",
        title="Stage模型生命周期声明",
        description="声明UIAbility完整生命周期管理",
        code="""// UIAbility生命周期管理
import { UIAbility, AbilityConstant, Want } from '@kit.AbilityKit'
import { window } from '@kit.ArkUI'

export default class EntryAbility extends UIAbility {
  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    console.info('[Lifecycle] onCreate')
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    console.info('[Lifecycle] onWindowStageCreate')
    windowStage.loadContent('pages/Index')
  }

  onForeground(): void {
    console.info('[Lifecycle] onForeground - 恢复交互')
  }

  onBackground(): void {
    console.info('[Lifecycle] onBackground - 暂停耗时操作')
  }

  onDestroy(): void {
    console.info('[Lifecycle] onDestroy - 释放资源')
  }
}""",
        tags=["stage-model", "lifecycle"],
    ),
    ArkTSSnippet(
        rule_id="P124",
        title="最小权限声明",
        description="仅声明应用实际需要的权限",
        code="""// module.json5 - 最小权限声明
{
  "module": {
    "name": "entry",
    "type": "entry",
    "requestPermissions": [
      {
        "name": "ohos.permission.INTERNET",
        "reason": "$string:internet_reason",
        "usedScene": { "abilities": ["EntryAbility"], "when": "inuse" }
      }
    ]
  }
}""",
        tags=["permission", "least-privilege"],
    ),
    ArkTSSnippet(
        rule_id="P146",
        title="UIAbility生命周期完整声明",
        description="Stage模型Prompt声明UIAbility生命周期管理",
        code="""// 完整UIAbility生命周期 - Stage模型
import { UIAbility, AbilityConstant, Want } from '@kit.AbilityKit'
import { window } from '@kit.ArkUI'

export default class MainAbility extends UIAbility {
  private resourceHolder: ResourceHolder | null = null

  onCreate(want: Want, launchParam: AbilityConstant.LaunchParam): void {
    // 初始化资源
    this.resourceHolder = new ResourceHolder()
    this.resourceHolder.init(want.parameters)
  }

  onWindowStageCreate(windowStage: window.WindowStage): void {
    // 设置UI内容
    windowStage.loadContent('pages/MainPage', (err, data) => {
      if (err.code) {
        console.error(`加载失败: ${err.message}`)
        return
      }
      console.info('UI加载成功')
    })
  }

  onForeground(): void {
    // 恢复交互：恢复定时器、刷新数据
    this.resourceHolder?.resumeTimers()
    this.resourceHolder?.refreshData()
  }

  onBackground(): void {
    // 暂停耗时操作：暂停定时器、保存状态
    this.resourceHolder?.pauseTimers()
    this.resourceHolder?.saveState()
  }

  onDestroy(): void {
    // 释放资源
    this.resourceHolder?.release()
    this.resourceHolder = null
  }
}""",
        tags=["stage-model", "lifecycle", "uiability"],
    ),
    ArkTSSnippet(
        rule_id="P147",
        title="ExtensionAbility使用边界约束",
        description="声明ServiceExtension/DataShareExtension/FormExtension用途限制",
        code="""// ServiceExtension - 仅用于后台服务
import { ServiceExtension } from '@kit.AbilityKit'

export default class BackgroundService extends ServiceExtension {
  onCreate(): void {
    console.info('[ServiceExtension] 仅用于后台数据处理')
  }

  onRequest(want): void {
    // 仅处理后台任务，禁止UI操作
    this.processBackgroundTask(want.parameters)
  }

  onDestroy(): void {
    this.cleanupResources()
  }

  private processBackgroundTask(params): void {
    // 最小权限: 仅访问必要数据
  }

  private cleanupResources(): void {
    // 释放所有资源
  }
}""",
        tags=["extension", "boundary", "service"],
    ),
    ArkTSSnippet(
        rule_id="P148",
        title="分布式数据同步安全策略",
        description="声明分布式数据同步的加密/分级/冲突解决策略",
        code="""// 分布式数据同步 - 安全策略
import { distributedData } from '@kit.ArkData'

const STORE_CONFIG: distributedData.StoreConfig = {
  name: 'secure_distributed_store',
  securityLevel: distributedData.SecurityLevel.S3, // 数据分级: S3=敏感
  encrypt: true, // 启用加密
}

class DistributedDataManager {
  private store: distributedData.SingleKVStore | null = null

  async init(context: Context): Promise<void> {
    this.store = await distributedData.createKVManager(context)
      .getKVStore(STORE_CONFIG)

    // 数据同步策略: 仅同步S1级别数据到其他设备
    this.store.on('syncComplete', (result) => {
      console.info(`同步完成: ${JSON.stringify(result)}`)
    })
  }

  // 冲突解决: last-write-wins
  async put(key: string, value: string): Promise<void> {
    await this.store?.put(key, value)
  }
}""",
        tags=["distributed", "security", "encryption"],
    ),
    ArkTSSnippet(
        rule_id="P149",
        title="ArkUI声明式范式模板",
        description="遵循ArkUI声明式开发范式，使用@State/@Prop/@Link驱动UI",
        code="""// ArkUI声明式范式 - 数据驱动单向数据流
@Entry
@Component
struct DeclarativeExample {
  @State dataList: string[] = []      // 数据源: @State驱动UI
  @State isLoading: boolean = false

  build() {
    Column() {
      // 条件渲染: 声明式
      if (this.isLoading) {
        LoadingProgress()
          .color(Color.Blue)
      } else {
        // 列表渲染: 声明式ForEach
        List() {
          ForEach(this.dataList, (item: string) => {
            ListItem() {
              Text(item)
                .fontSize(16)
            }
          }, (item: string) => item)
        }
      }
    }
    .width('100%')
    .height('100%')
  }

  // 状态修改通过回调, 避免命令式操作DOM
  aboutToAppear(): void {
    this.loadData()
  }

  private async loadData(): Promise<void> {
    this.isLoading = true
    this.dataList = await this.fetchData()
    this.isLoading = false
  }

  private async fetchData(): Promise<string[]> {
    return ['Item1', 'Item2', 'Item3']
  }
}""",
        tags=["arkui", "declarative", "state-driven"],
    ),
    ArkTSSnippet(
        rule_id="P150",
        title="卡片(Widget)更新策略声明",
        description="声明鸿蒙元服务卡片的更新策略",
        code="""// FormExtension - 卡片更新策略
import { formProvider } from '@kit.AbilityKit'

@Entry
@Component
struct WidgetCard {
  @State currentTime: string = ''

  build() {
    Column() {
      Text(this.currentTime)
        .fontSize(24)
        .fontWeight(FontWeight.Bold)
    }
    .width('100%')
    .height('100%')
    .padding(16)
  }
}

// 卡片更新策略配置
// form_config.json
{
  "forms": [{
    "name": "timeWidget",
    "displayName": "时钟卡片",
    "description": "实时时间展示",
    "updateDuration": 1,          // 定时更新: 1小时(最小30分钟)
    "updateEnabled": true,
    "scheduledUpdateTime": "10:30", // 定时更新时间点
    "formVisibleNotify": true,
    "isDynamic": true
  }]
}

// 按需更新: 仅在数据变化时触发
function triggerFormUpdate(formId: string): void {
  // 仅在时间变化时更新卡片
  formProvider.updateForm(formId, formBindingData)
}""",
        tags=["widget", "form-extension", "update-strategy"],
    ),
]


def get_snippets_by_rule(rule_id: str) -> list[ArkTSSnippet]:
    return [s for s in _SNIPPETS if s.rule_id == rule_id]


def get_all_snippets() -> list[ArkTSSnippet]:
    return list(_SNIPPETS)


def get_snippets_by_tag(tag: str) -> list[ArkTSSnippet]:
    return [s for s in _SNIPPETS if tag in s.tags]


def get_template(rule_id: str) -> str | None:
    snippets = get_snippets_by_rule(rule_id)
    if not snippets:
        return None
    return snippets[0].code


def generate_deveco_config(
    *,
    project_name: str = "MyHarmonyApp",
    bundle_name: str = "com.example.myapp",
    min_api: int = 12,
    target_api: int = 14,
    enable_prompt_lint: bool = True,
    enable_security_scan: bool = True,
    enable_output_scan: bool = True,
    enable_redteam: bool = False,
    lint_gate_score: float = 80.0,
    custom_rules: list[str] | None = None,
) -> dict[str, Any]:
    """生成DevEco Studio项目集成的ai-prompt-toolkit配置

    产出:
    - .deveco/prompt-toolkit.json — 主配置
    - build-profile.json5 集成钩子 — 构建时自动lint
    - hvigorfile.ts 集成脚本 — 构建流水线
    """
    config = {
        "$schema": "https://ai-prompt-toolkit.dev/schemas/deveco-config/v1.json",
        "version": "1.0.0",
        "project": {
            "name": project_name,
            "bundleName": bundle_name,
            "minAPI": min_api,
            "targetAPI": target_api,
        },
        "lint": {
            "enabled": enable_prompt_lint,
            "gateScore": lint_gate_score,
            "rules": custom_rules or ["P001-P170"],
            "failOn": "high",
            "format": "sarif",
            "outputPath": "build/prompt-lint-results.sarif",
            "semanticCache": True,
            "fix": False,
        },
        "security": {
            "enabled": enable_security_scan,
            "scanners": ["injection", "pii", "supply_chain", "unicode", "defender", "structural", "anomaly"],
            "engine": {
                "enabled": True,
                "layers": ["l1_regex", "l2_classifier", "l3_similarity", "l4_structural", "l5_anomaly"],
                "blockThreshold": 0.7,
                "warnThreshold": 0.35,
            },
        },
        "outputScan": {
            "enabled": enable_output_scan,
            "scanners": ["no_refusal", "bias", "toxicity", "relevance", "factual_consistency", "citation"],
        },
        "redteam": {
            "enabled": enable_redteam,
            "probes": ["encoding", "glitch", "prompt_injection", "jailbreak"],
            "detectors": ["refusal", "error", "quality"],
        },
        "harmonyos": {
            "stageModel": True,
            "arkuiDeclarative": True,
            "distributedSecurity": True,
            "permissionLeastPrivilege": True,
            "lifecycleManagement": True,
            "widgetUpdateStrategy": True,
        },
        "cicd": {
            "preCommit": enable_prompt_lint,
            "preBuild": enable_security_scan,
            "postBuild": enable_output_scan,
            "githubAction": True,
            "sarifUpload": True,
        },
    }
    return config


def generate_deveco_build_hook() -> str:
    """生成hvigorfile.ts构建钩子脚本"""
    return """// hvigorfile.ts - ai-prompt-toolkit构建集成
// 在HarmonyOS构建流水线中自动执行Prompt安全检查
import { hvigorfile, appTask } from '@ohos/hvigor';

export default appTask({
  onLoad: () => {
    console.info('[prompt-toolkit] Build hook loaded');
  },
  onApply: () => {
    console.info('[prompt-toolkit] Running pre-build prompt security scan...');
  }
});

// 自定义任务: prompt-lint
appTask('prompt-lint', async () => {
  const { execSync } = require('child_process');
  try {
    const result = execSync('prompt lint ./entry/src/main/resources/prompts/ --format sarif --gate --fail-on high', {
      encoding: 'utf-8',
      cwd: process.cwd()
    });
    console.info('[prompt-toolkit] Lint passed:', result);
  } catch (error) {
    console.error('[prompt-toolkit] Lint failed - blocking build');
    throw error;
  }
});

// 自定义任务: prompt-scan
appTask('prompt-scan', async () => {
  const { execSync } = require('child_process');
  try {
    const result = execSync('prompt scan ./entry/src/main/resources/prompts/ --format json', {
      encoding: 'utf-8',
      cwd: process.cwd()
    });
    const report = JSON.parse(result);
    if (report.risk_level === 'critical' || report.risk_level === 'high') {
      throw new Error('Security scan failed: ' + report.risk_level);
    }
    console.info('[prompt-toolkit] Security scan passed');
  } catch (error) {
    console.error('[prompt-toolkit] Security scan failed - blocking build');
    throw error;
  }
});
"""


def generate_deveco_workflow_yaml() -> str:
    """生成GitHub Actions工作流YAML(鸿蒙项目专用)"""
    return """name: HarmonyOS Prompt Security CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'entry/src/main/resources/prompts/**'
      - '**/*.prompt.md'
  pull_request:
    branches: [main]

jobs:
  prompt-security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install ai-prompt-toolkit
        run: pip install ai-prompt-toolkit
      - name: Prompt Lint
        run: |
          prompt lint entry/src/main/resources/prompts/ \\
            --format sarif \\
            --gate \\
            --fail-on high \\
            --output build/prompt-lint-results.sarif
      - name: Prompt Security Scan
        run: |
          prompt scan entry/src/main/resources/prompts/ \\
            --format json \\
            --depth full
      - name: Upload SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: build/prompt-lint-results.sarif
          category: prompt-security
      - name: Compliance Report
        run: |
          prompt compliance entry/src/main/resources/prompts/ \\
            --format json \\
            --output build/compliance-report.json
"""
