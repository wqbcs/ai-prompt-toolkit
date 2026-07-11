# Q1-05 JetBrains插件设计

> **迭代**：v20-Q1-05 | **日期**：2026-07-12

---

## 一、插件总体架构

### 1.1 目录结构

```
prompt-ide-jetbrains/
├── build.gradle.kts
├── src/
│   └── main/
│       ├── resources/
│       │   ├── META-INF/
│       │   │   └── plugin.xml
│       │   └── prompt-ide/
│       │       ├── colors/
│       │       │   ├── PromptDark.xml
│       │       │   ├── PromptLight.xml
│       │       │   └── PromptHC.xml
│       │       └── snippets/
│       │           └── prompt-live-templates.xml
│       └── kotlin/
│           └── com/
│               └── promptide/
│                   ├── PromptLanguage.kt
│                   ├── PromptFileType.kt
│                   ├── PromptParserDefinition.kt
│                   ├── highlight/
│                   │   ├── PromptSyntaxHighlighter.kt
│                   │   ├── PromptColorSettingsPage.kt
│                   │   └── PromptAnnotator.kt
│                   ├── completion/
│                   │   └── PromptCompletionContributor.kt
│                   ├── preview/
│                   │   ├── PromptPreviewToolWindow.kt
│                   │   └── PromptPreviewPanel.kt
│                   ├── debug/
│                   │   └── PromptDebugSupport.kt
│                   └── utils/
│                       ├── TokenCounter.kt
│                       └── TemplateRegistry.kt
```

### 1.2 plugin.xml

```xml
<idea-plugin>
  <id>com.promptide</id>
  <name>Prompt IDE - AI提示词开发环境</name>
  <vendor>AI Prompt System</vendor>
  <description><![CDATA[
    AI提示词一体化开发环境：语法高亮、代码补全、实时预览、调试执行
  ]]></description>

  <depends>com.intellij.modules.platform</depends>

  <extensions defaultExtensionNs="com.intellij">
    <fileType
      name="Prompt"
      implementationClass="com.promptide.PromptFileType"
      fieldName="INSTANCE"
      language="Prompt"
      extensions="prompt;pmt" />

    <lang.parserDefinition
      language="Prompt"
      implementationClass="com.promptide.PromptParserDefinition" />

    <lang.syntaxHighlighterFactory
      language="Prompt"
      implementationClass="com.promptide.highlight.PromptSyntaxHighlighterFactory" />

    <colorSettingsPage
      implementationClass="com.promptide.highlight.PromptColorSettingsPage" />

    <lang.annotator
      language="Prompt"
      implementationClass="com.promptide.highlight.PromptAnnotator" />

    <completion.contributor
      language="Prompt"
      implementationClass="com.promptide.completion.PromptCompletionContributor" />

    <toolWindow
      id="Prompt Preview"
      anchor="right"
      factoryClass="com.promptide.preview.PromptPreviewToolWindowFactory" />

    <defaultLiveTemplates
      file="/prompt-ide/snippets/prompt-live-templates.xml" />

    <additionalTextAttributes
      scheme="Dark"
      file="/prompt-ide/colors/PromptDark.xml" />

    <additionalTextAttributes
      scheme="Light"
      file="/prompt-ide/colors/PromptLight.xml" />

    <additionalTextAttributes
      scheme="High contrast"
      file="/prompt-ide/colors/PromptHC.xml" />
  </extensions>

  <actions>
    <group id="PromptIDE.Actions" text="Prompt IDE" popup="true">
      <add-to-group group-id="EditorPopupMenu" anchor="first" />
      <action id="PromptIDE.Run" class="com.promptide.actions.RunPromptAction" text="执行提示词" />
      <action id="PromptIDE.Debug" class="com.promptide.actions.DebugPromptAction" text="调试提示词" />
      <action id="PromptIDE.Preview" class="com.promptide.actions.PreviewPromptAction" text="预览提示词" />
      <action id="PromptIDE.Analyze" class="com.promptide.actions.AnalyzePromptAction" text="性能分析" />
    </group>
  </actions>
</idea-plugin>
```

---

## 二、语法高亮器

### 2.1 PromptSyntaxHighlighter.kt

```kotlin
package com.promptide.highlight

import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.psi.tree.IElementType

class PromptSyntaxHighlighter : SyntaxHighlighterBase() {

  companion object {
    val DIRECTIVE = TextAttributesKey.createTextAttributesKey(
      "PROMPT_DIRECTIVE", DefaultLanguageHighlighterColors.KEYWORD
    )
    val VARIABLE = TextAttributesKey.createTextAttributesKey(
      "PROMPT_VARIABLE", DefaultLanguageHighlighterColors.STRING
    )
    val VARIABLE_DELIMITER = TextAttributesKey.createTextAttributesKey(
      "PROMPT_VARIABLE_DELIMITER", DefaultLanguageHighlighterColors.OPERATION_SIGN
    )
    val ROLE = TextAttributesKey.createTextAttributesKey(
      "PROMPT_ROLE", DefaultLanguageHighlighterColors.PREDEFINED_SYMBOL
    )
    val CONSTRAINT = TextAttributesKey.createTextAttributesKey(
      "PROMPT_CONSTRAINT", DefaultLanguageHighlighterColors.METADATA
    )
    val COMMENT = TextAttributesKey.createTextAttributesKey(
      "PROMPT_COMMENT", DefaultLanguageHighlighterColors.LINE_COMMENT
    )
    val CODE_BLOCK = TextAttributesKey.createTextAttributesKey(
      "PROMPT_CODE_BLOCK", DefaultLanguageHighlighterColors.TEMPLATE_LANGUAGE_COLOR
    )
    val LIST_MARKER = TextAttributesKey.createTextAttributesKey(
      "PROMPT_LIST_MARKER", DefaultLanguageHighlighterColors.DOT
    )
  }

  override fun getHighlightingLexer(): Lexer {
    return PromptLexerAdapter()
  }

  override fun getTokenHighlights(tokenType: IElementType): Array<TextAttributesKey> {
    return when (tokenType) {
      PromptTypes.DIRECTIVE -> pack(DIRECTIVE)
      PromptTypes.VARIABLE_NAME -> pack(VARIABLE)
      PromptTypes.VARIABLE_OPEN, PromptTypes.VARIABLE_CLOSE -> pack(VARIABLE_DELIMITER)
      PromptTypes.ROLE_KEYWORD -> pack(ROLE)
      PromptTypes.CONSTRAINT_KEYWORD -> pack(CONSTRAINT)
      PromptTypes.COMMENT -> pack(COMMENT)
      PromptTypes.CODE_BLOCK -> pack(CODE_BLOCK)
      PromptTypes.LIST_MARKER -> pack(LIST_MARKER)
      else -> emptyArray()
    }
  }
}
```

### 2.2 PromptAnnotator.kt

```kotlin
package com.promptide.highlight

import com.intellij.lang.annotation.AnnotationHolder
import com.intellij.lang.annotation.Annotator
import com.intellij.lang.annotation.HighlightSeverity
import com.intellij.psi.PsiElement

class PromptAnnotator : Annotator {

  override fun annotate(element: PsiElement, holder: AnnotationHolder) {
    when (element.node?.elementType) {
      PromptTypes.VARIABLE_NAME -> {
        val varName = element.text
        if (varName.isBlank()) {
          holder.newAnnotation(HighlightSeverity.ERROR, "变量名不能为空")
            .range(element.textRange).create()
        }
        if (varName.contains(' ')) {
          holder.newAnnotation(HighlightSeverity.WARNING, "变量名不应包含空格")
            .range(element.textRange).create()
        }
      }
      PromptTypes.DIRECTIVE -> {
        val validDirectives = setOf(
          "system", "user", "assistant", "context",
          "constraint", "example", "output", "model",
          "temperature", "max_tokens"
        )
        val directiveName = element.text.removePrefix("@")
        if (directiveName !in validDirectives) {
          holder.newAnnotation(HighlightSeverity.WARNING, "未知指令: @$directiveName")
            .range(element.textRange)
            .tooltip("可用指令: ${validDirectives.joinToString(", ") { "@$it" }}")
            .create()
        }
      }
    }
  }
}
```

---

## 三、代码补全

### 3.1 PromptCompletionContributor.kt

```kotlin
package com.promptide.completion

import com.intellij.codeInsight.completion.CompletionContributor
import com.intellij.codeInsight.completion.CompletionParameters
import com.intellij.codeInsight.completion.CompletionProvider
import com.intellij.codeInsight.completion.CompletionType
import com.intellij.codeInsight.lookup.LookupElementBuilder
import com.intellij.patterns.PlatformPatterns
import com.intellij.util.ProcessingContext
import com.promptide.PromptLanguage

class PromptCompletionContributor : CompletionContributor() {

  init {
    extend(
      CompletionType.BASIC,
      PlatformPatterns.psiElement().withLanguage(PromptLanguage.INSTANCE),
      DirectiveCompletionProvider()
    )
  }

  class DirectiveCompletionProvider : CompletionProvider<CompletionParameters>() {
    override fun addCompletions(
      params: CompletionParameters,
      context: ProcessingContext,
      result: com.intellij.codeInsight.completion.CompletionResultSet
    ) {
      val position = params.position
      val prefix = position.text.trim()

      if (prefix.startsWith("@") || prefix.isEmpty()) {
        for (directive in DIRECTIVES) {
          result.addElement(
            LookupElementBuilder.create("@${directive.key}")
              .withTypeText(directive.value.type)
              .withTailText(" - ${directive.value.description}", true)
              .withIcon(com.intellij.icons.AllIcons.Nodes.Tag)
          )
        }
      }

      if (prefix.contains("{{")) {
        for (variable in VARIABLES) {
          result.addElement(
            LookupElementBuilder.create("{{${variable.key}}}")
              .withTypeText("变量")
              .withTailText(" - ${variable.value}", true)
          )
        }
      }
    }
  }

  companion object {
    private val DIRECTIVES = mapOf(
      "system" to DirectiveInfo("指令", "定义AI系统角色和行为规则"),
      "user" to DirectiveInfo("指令", "定义用户输入消息"),
      "assistant" to DirectiveInfo("指令", "定义助手预期响应"),
      "context" to DirectiveInfo("指令", "提供背景上下文信息"),
      "constraint" to DirectiveInfo("指令", "定义输出约束和规则"),
      "example" to DirectiveInfo("指令", "提供输入输出示例"),
      "output" to DirectiveInfo("指令", "定义输出格式和结构"),
      "model" to DirectiveInfo("参数", "指定AI模型"),
      "temperature" to DirectiveInfo("参数", "控制输出随机性"),
      "max_tokens" to DirectiveInfo("参数", "限制输出Token数"),
    )

    private val VARIABLES = mapOf(
      "language" to "编程语言",
      "framework" to "框架",
      "task" to "任务类型",
      "code_style" to "代码风格",
      "error_message" to "错误信息",
      "input_data" to "输入数据",
      "output_format" to "输出格式",
      "constraint" to "约束条件",
      "domain" to "业务领域",
      "security_level" to "安全级别",
    )
  }
}

data class DirectiveInfo(val type: String, val description: String)
```

---

## 四、预览ToolWindow

### 4.1 PromptPreviewToolWindow.kt

```kotlin
package com.promptide.preview

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.components.JBPanel
import com.intellij.ui.components.JBScrollPane
import com.intellij.ui.components.JBLabel
import com.intellij.ui.components.JBTextArea
import java.awt.BorderLayout
import java.awt.FlowLayout
import javax.swing.JButton

class PromptPreviewToolWindowFactory : ToolWindowFactory {
  override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
    val panel = PromptPreviewPanel(project)
    val content = toolWindow.contentManager.factory.createContent(panel, "预览", false)
    toolWindow.contentManager.addContent(content)
  }
}

class PromptPreviewPanel(project: Project) : JBPanel<JBPanel<*>>(BorderLayout()) {

  private val statsPanel = JBPanel<JBPanel<*>>(FlowLayout(FlowLayout.LEFT))
  private val previewArea = JBTextArea()

  init {
    val tokenLabel = JBLabel("Token: 0")
    val costLabel = JBLabel("成本: $0.0000")
    val varLabel = JBLabel("变量: 0")
    val refreshBtn = JButton("刷新预览")

    statsPanel.add(tokenLabel)
    statsPanel.add(costLabel)
    statsPanel.add(varLabel)
    statsPanel.add(refreshBtn)

    previewArea.isEditable = false
    previewArea.lineWrap = true
    previewArea.wrapStyleWord = true

    add(statsPanel, BorderLayout.NORTH)
    add(JBScrollPane(previewArea), BorderLayout.CENTER)
  }
}
```

---

## 五、验收项

- [x] JetBrains插件目录结构设计
- [x] plugin.xml完整配置（8个扩展点+4个Action）
- [x] 语法高亮器（8种Token类型）
- [x] Annotator（变量名验证+指令验证）
- [x] CompletionContributor（指令补全+变量补全）
- [x] 预览ToolWindow（统计面板+预览区+刷新按钮）
- [x] Live Templates支持
- [x] 3种主题颜色配置
