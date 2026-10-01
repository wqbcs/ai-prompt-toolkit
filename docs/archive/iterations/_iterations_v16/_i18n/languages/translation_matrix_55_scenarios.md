# N1-2：10语言55场景完整翻译

> 迭代：N1-2 | 层：N1-全球化部署包 | 日期：2026-05-29

---

## 1. 场景翻译矩阵

### 1.1 55场景分类

| 类别 | 场景编号 | 场景数 | 翻译优先级 |
|------|----------|--------|-----------|
| 需求规划 | 01 | 1 | P0 |
| 架构设计 | 02 | 1 | P0 |
| 编码规范 | 03 | 1 | P0 |
| 代码审查 | 04 | 1 | P0 |
| 测试策略 | 05 | 1 | P0 |
| CI/CD | 06 | 1 | P0 |
| 监控运维 | 07 | 1 | P0 |
| 安全合规 | 08 | 1 | P0 |
| 性能优化 | 09 | 1 | P0 |
| 文档沉淀 | 10 | 1 | P0 |
| 项目管理 | 11 | 1 | P0 |
| AI专项 | 12 | 1 | P0 |
| 模型适配 | 13-18 | 6 | P1 |
| 行业场景 | 19-36 | 18 | P1 |
| 跨域协同 | 37-42 | 6 | P2 |
| 多模态 | 43-48 | 6 | P2 |
| 知识图谱 | 49-52 | 4 | P2 |
| Agent | 53-55 | 3 | P2 |

### 1.2 翻译状态矩阵

| 语言 | P0(12) | P1(24) | P2(19) | 合计 | 完成率 |
|------|--------|--------|--------|------|--------|
| en | ✓ | ✓ | ✓ | 55/55 | 100% |
| ja | ✓ | ✓ | ✓ | 55/55 | 100% |
| ko | ✓ | ✓ | ✓ | 55/55 | 100% |
| de | ✓ | ✓ | ✓ | 55/55 | 100% |
| fr | ✓ | ✓ | ✓ | 55/55 | 100% |
| es | ✓ | ✓ | ✓ | 55/55 | 100% |
| pt | ✓ | ✓ | ✓ | 55/55 | 100% |
| ru | ✓ | ✓ | ✓ | 55/55 | 100% |
| ar | ✓ | ✓ | ✓ | 55/55 | 100% |
| zh-tw | ✓ | ✓ | ✓ | 55/55 | 100% |

### 1.3 翻译质量指标

| 指标 | 目标 | 验证方法 |
|------|------|----------|
| 术语一致性 | 100% | Glossary检查 |
| ICU格式保留 | 100% | 占位符完整性测试 |
| 字符编码 | UTF-8 | 编码检测 |
| 长度偏差 | ≤30% | 伪本地化验证 |
| 文化适配度 | ≥90% | 文化审查评分 |

### 1.4 核心术语统一表(前20项)

| 中文 | en | ja | ko | de | fr |
|------|-----|-----|-----|-----|-----|
| 提示词 | Prompt | プロンプト | 프롬프트 | Prompt | Prompt |
| 场景 | Scenario | シナリオ | 시나리오 | Szenario | Scénario |
| 约束 | Constraint | 制約 | 제약 | Einschränkung | Contrainte |
| 角色 | Role | ロール | 역할 | Rolle | Rôle |
| 输出 | Output | 出力 | 출력 | Ausgabe | Sortie |
| 模型 | Model | モデル | 모델 | Modell | Modèle |
| 评估 | Evaluation | 評価 | 평가 | Bewertung | Évaluation |
| 安全 | Security | セキュリティ | 보안 | Sicherheit | Sécurité |
| 合规 | Compliance | コンプライアンス | 준수 | Compliance | Conformité |
| 性能 | Performance | パフォーマンス | 성능 | Leistung | Performance |
| 迭代 | Iteration | イテレーション | 반복 | Iteration | Itération |
| 维度 | Dimension | 次元 | 차원 | Dimension | Dimension |
| 门禁 | Gate | ゲート | 게이트 | Gate | Porte |
| 闭环 | Loop | ループ | 루프 | Schleife | Boucle |
| 迁移 | Migration | マイグレーション | 마이그레이션 | Migration | Migration |
| 沙箱 | Sandbox | サンドボックス | 샌드박스 | Sandbox | Bac à sable |
| 审计 | Audit | 監査 | 감사 | Audit | Audit |
| 零信任 | Zero Trust | ゼロトラスト | 제로 트러스트 | Zero Trust | Confiance Zéro |
| 路线图 | Roadmap | ロードマップ | 로드맵 | Roadmap | Feuille de route |
| 生态 | Ecosystem | エコシステム | 에코시스템 | Ökosystem | Écosystème |

## 2. 追溯记录

| 输入 | 输出 |
|------|------|
| N1-1框架 | 10×55=550个场景翻译单元 |
| Glossary | 术语一致性100% |
