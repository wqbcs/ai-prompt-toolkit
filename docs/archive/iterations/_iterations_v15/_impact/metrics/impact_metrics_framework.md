# 影响力度量体系设计

> 版本：v1.0 | 日期：2026-05-29

---

## 1. 五类影响力指标

### 1.1 指标体系总览

| 类别 | 指标代码 | 指标名称 | 数据源 | 更新频率 |
|------|---------|---------|--------|---------|
| 引用 | CIT-01 | 学术论文引用数 | Google Scholar/Semantic Scholar | 月度 |
| 引用 | CIT-02 | 技术博客引用数 | Google/Bing搜索 | 月度 |
| 引用 | CIT-03 | 标准文档引用数 | ISO/IEC/NIST文档 | 季度 |
| 下载 | DL-01 | SDK下载量 | PyPI/npm统计 | 日度 |
| 下载 | DL-02 | GitHub克隆/复刻数 | GitHub API | 日度 |
| 下载 | DL-03 | 文档页面浏览量 | 网站分析 | 日度 |
| 使用 | USE-01 | 生产环境部署数 | 社区调查+SDK遥测 | 季度 |
| 使用 | USE-02 | 企业采用数 | 会员+调查 | 季度 |
| 使用 | USE-03 | CI/CD集成数 | GitHub Actions统计 | 月度 |
| 衍生 | DRV-01 | 衍生项目数 | GitHub搜索 | 月度 |
| 衍生 | DRV-02 | 衍生标准/规范数 | 标准组织搜索 | 季度 |
| 衍生 | DRV-03 | 教学课程采用数 | 教育机构调查 | 年度 |
| 标准采纳 | STD-01 | 标准组织采纳数 | ISO/IEC/NIST | 季度 |
| 标准采纳 | STD-02 | 国家标准转化数 | 各国标准机构 | 年度 |
| 标准采纳 | STD-03 | 行业事实标准认可数 | 行业调查 | 年度 |

## 2. 影响力Dashboard数据模型

### 2.1 数据模型

```typescript
interface ImpactMetrics {
  timestamp: string;
  citations: {
    academic: number;        // CIT-01
    blog: number;            // CIT-02
    standard: number;        // CIT-03
    total: number;
    trend: TrendData;
  };
  downloads: {
    sdk_pypi: number;        // DL-01a
    sdk_npm: number;         // DL-01b
    github_clones: number;   // DL-02
    doc_views: number;       // DL-03
    total: number;
    trend: TrendData;
  };
  usage: {
    production_deployments: number;  // USE-01
    enterprise_adopters: number;     // USE-02
    cicd_integrations: number;       // USE-03
    total: number;
    trend: TrendData;
  };
  derivatives: {
    projects: number;        // DRV-01
    standards: number;       // DRV-02
    courses: number;         // DRV-03
    total: number;
    trend: TrendData;
  };
  standard_adoption: {
    organizations: number;   // STD-01
    national_standards: number;  // STD-02
    de_facto_recognition: number; // STD-03
    total: number;
    trend: TrendData;
  };
  composite_score: number;  // 综合影响力分数(0-100)
}

interface TrendData {
  current: number;
  previous: number;
  change_percent: number;
  history: DataPoint[];
}

interface DataPoint {
  date: string;
  value: number;
}
```

### 2.2 综合影响力分数计算

```
composite_score =
  w1 * normalize(citations.total) +
  w2 * normalize(downloads.total) +
  w3 * normalize(usage.total) +
  w4 * normalize(derivatives.total) +
  w5 * normalize(standard_adoption.total)

权重:
  w1 = 0.25 (引用：学术认可度)
  w2 = 0.15 (下载：传播广度)
  w3 = 0.25 (使用：实际影响)
  w4 = 0.15 (衍生：生态扩展)
  w5 = 0.20 (标准采纳：行业权威)

normalize函数(对数归一化):
  normalize(x) = min(log10(x + 1) / log10(target + 1), 1.0) * 100

target参考值(3年目标):
  citations: 500
  downloads: 100000
  usage: 1000
  derivatives: 100
  standard_adoption: 10
```

## 3. 影响力报告模板

### 3.1 年度报告结构

```markdown
# PEA影响力年度报告 {year}

## 执行摘要
- 综合影响力分数：{score}/100
- 同比变化：{change}%
- 关键里程碑：{milestones}

## 1. 引用指标
### 1.1 学术引用
- 总引用数：{cit_01}
- 高影响论文引用：{h_index_citations}
- 引用机构数：{institutions}

### 1.2 技术引用
- 博客/文章引用：{cit_02}
- 主要引用来源：{top_sources}

### 1.3 标准引用
- 被引用的标准文档：{cit_03}

## 2. 下载与传播
### 2.1 SDK下载
- PyPI：{dl_01a} | npm：{dl_01b}
- 月度趋势图

### 2.2 文档访问
- 页面浏览量：{dl_03}
- 独立访客：{unique_visitors}

## 3. 生产使用
### 3.1 企业采用
- 采用企业数：{use_02}
- 行业分布：{industry_distribution}
- 典型案例：{case_studies}

## 4. 衍生生态
### 4.1 衍生项目
- 项目数：{drv_01}
- 领域分布：{domain_distribution}

## 5. 标准采纳
### 5.1 标准组织
- 采纳标准数：{std_01}
- 推进中标准：{in_progress}

## 6. 三年趋势
[趋势图表]

## 7. 展望
{outlook}
```

### 3.2 季度报告(简化版)

```markdown
# PEA影响力季度报告 {year}-Q{quarter}

## 关键指标变化
| 指标 | 上季度 | 本季度 | 变化 |
|------|--------|--------|------|
| 综合分数 | {prev} | {curr} | {delta} |
| 学术引用 | {prev} | {curr} | {delta} |
| SDK下载 | {prev} | {curr} | {delta} |
| 企业采用 | {prev} | {curr} | {delta} |

## 本季度亮点
- {highlight_1}
- {highlight_2}

## 下季度目标
- {target_1}
- {target_2}
```

## 4. 当前体系影响力基线

### 4.1 基线评估(2026-05-29)

| 类别 | 指标 | 当前值 | 数据来源 | 置信度 |
|------|------|--------|---------|--------|
| 引用 | CIT-01 学术引用 | 3 | 已发表论文 | 高 |
| 引用 | CIT-02 博客引用 | 15 | 估算 | 中 |
| 引用 | CIT-03 标准引用 | 2 | ISO/IEC提案 | 高 |
| 下载 | DL-01 SDK下载 | 0 | SDK未发布 | 高 |
| 下载 | DL-02 GitHub | 0 | 未开源 | 高 |
| 下载 | DL-03 文档浏览 | 500 | 估算 | 低 |
| 使用 | USE-01 生产部署 | 5 | 内部使用 | 高 |
| 使用 | USE-02 企业采用 | 3 | 内部团队 | 高 |
| 使用 | USE-03 CI/CD集成 | 2 | 内部CI | 高 |
| 衍生 | DRV-01 衍生项目 | 0 | 未开源 | 高 |
| 衍生 | DRV-02 衍生标准 | 1 | NIST补充 | 中 |
| 衍生 | DRV-03 课程采用 | 1 | 内部培训 | 高 |
| 标准采纳 | STD-01 组织采纳 | 2 | ISO/IEC+NIST | 高 |
| 标准采纳 | STD-02 国家标准 | 0 | 未转化 | 高 |
| 标准采纳 | STD-03 事实标准 | 0 | 早期阶段 | 高 |

### 4.2 综合基线分数

```
composite_score =
  0.25 * normalize(20) +    // 引用(3+15+2)
  0.15 * normalize(500) +   // 下载(0+0+500)
  0.25 * normalize(10) +    // 使用(5+3+2)
  0.15 * normalize(2) +     // 衍生(0+1+1)
  0.20 * normalize(2)       // 标准(2+0+0)

= 0.25 * 17.2 + 0.15 * 36.2 + 0.25 * 12.0 + 0.15 * 10.4 + 0.20 * 17.3
= 4.3 + 5.4 + 3.0 + 1.6 + 3.5
= 17.8 / 100
```

**当前综合影响力分数：17.8/100**（早期阶段，3年目标80+）

## 5. 影响力增长策略

| 策略 | 目标指标 | 行动 |
|------|---------|------|
| 开源发布 | DL-01, DRV-01 | SDK Beta发布+GitHub开源 |
| 学术发表 | CIT-01 | 持续论文发表+会议演讲 |
| 标准推进 | STD-01, STD-02 | ISO/IEC NP提交+国家标准镜像 |
| 企业拓展 | USE-01, USE-02 | 创始会员招募+案例建设 |
| 社区建设 | DL-03, DRV-01 | 大使计划+黑客松+文档优化 |
