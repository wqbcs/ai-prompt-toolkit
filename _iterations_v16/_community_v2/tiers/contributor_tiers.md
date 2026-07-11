# 贡献者等级体系

> 版本：v16.0.0 | 5级+特殊角色

---

## 1. 等级定义

### 1.1 Bronze(铜级)

| 项目 | 详情 |
|------|------|
| 条件 | 1-3个PR合并 或 5+个有效Issue报告 |
| 贡献分 | 1-99分 |
| 徽章 | 🥉 |
| 权益 | 社区徽章 + Good First Issue优先分配 + 社区论坛发帖权 |
| 考核 | 首次贡献完成后自动授予 |
| 晋升 | 4个PR合并或100分 → Silver |

### 1.2 Silver(银级)

| 项目 | 详情 |
|------|------|
| 条件 | 4-10个PR合并 + 至少1次有效Review |
| 贡献分 | 100-499分 |
| 徽章 | 🥈 |
| 权益 | Bronze权益 + Review权(非Approver) + 社区投票权 + 月度社区会议参与权 |
| 考核 | 季度活跃度评估(至少1个贡献/季度) |
| 晋升 | 11个PR+5 Review或500分 → Gold |

### 1.3 Gold(金级)

| 项目 | 详情 |
|------|------|
| 条件 | 11-30个PR合并 + 5+次有效Review + 至少1个中等难度Issue |
| 贡献分 | 500-1999分 |
| 徽章 | 🥇 |
| 权益 | Silver权益 + Approver权(特定模块) + 社区会议演讲权 + 新贡献者导师资格 |
| 考核 | 半年活跃度评估(至少3个贡献/半年) |
| 晋升 | 31个PR+核心贡献或2000分 → Platinum |

### 1.4 Platinum(铂金级)

| 项目 | 详情 |
|------|------|
| 条件 | 31-100个PR合并 + 核心模块贡献 + 持续6月+活跃 |
| 贡献分 | 2000-9999分 |
| 徽章 | 💎 |
| 权益 | Gold权益 + Maintainer候选资格 + 项目方向投票权 + 技术决策参与权 + 峁会赞助资格 |
| 考核 | 年度评估(持续核心贡献+社区影响力) |
| 晋升 | 100+PR+长期核心贡献或10000分 → Diamond |

### 1.5 Diamond(钻石级)

| 项目 | 详情 |
|------|------|
| 条件 | 100+个PR合并 + 12月+持续核心贡献 + 社区公认专家 |
| 贡献分 | 10000+分 |
| 徽章 | 💠 |
| 权益 | Platinum权益 + Maintainer权限 + 技术委员会候选 + 基金会代表资格 + 线下峰会邀请 |
| 考核 | 年度同行评审(需3+Diamond级推荐) |

## 2. 贡献分计算

```python
class ContributionScorer:
    SCORES = {
        "pr_merged": 10,          # 每个合并的PR
        "pr_review": 5,           # 每次有效Review
        "issue_report": 3,        # 每个有效Issue报告
        "issue_resolve": 2,       # 协助解决他人Issue
        "doc_improvement": 4,     # 文档改进
        "translation": 3,         # 翻译贡献
        "mentor_session": 5,      # 导师指导会
        "community_event": 8,     # 组织社区活动
        "blog_post": 6,           # 技术博客
        "security_report": 15,    # 安全漏洞报告
        "first_pr_bonus": 20,     # 首次PR奖励
    }
    
    DIFFICULTY_MULTIPLIER = {
        "good_first_issue": 0.8,
        "normal": 1.0,
        "hard": 1.5,
        "critical": 2.0,
    }
    
    def calculate_score(self, contribution):
        base = self.SCORES[contribution.type]
        multiplier = self.DIFFICULTY_MULTIPLIER[contribution.difficulty]
        return base * multiplier
```

## 3. 特殊角色

| 角色 | 职责 | 任命条件 | 任期 |
|------|------|---------|------|
| Maintainer | 模块/项目维护，合并PR，发布版本 | Diamond级+社区投票 | 1年(可连任) |
| Reviewer | 代码评审，质量把关 | Gold级+Maintainer指派 | 持续(活跃则保留) |
| Mentor | 新贡献者1:1指导 | Silver级+培训通过 | 6月(可续) |
| Release Manager | 版本发布管理 | Platinum级+流程培训 | 按版本 |
| Community Manager | 社区运营，活动组织 | Silver级+运营培训 | 1年 |
| Security Officer | 安全响应，漏洞处理 | Platinum级+安全培训 | 1年 |

## 4. 等级权益矩阵

| 权益 | Bronze | Silver | Gold | Platinum | Diamond |
|------|--------|--------|------|----------|---------|
| 社区徽章 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Good Issue优先 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 论坛发帖 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 代码Review | - | ✅ | ✅ | ✅ | ✅ |
| 社区投票权 | - | ✅ | ✅ | ✅ | ✅ |
| Approver权 | - | - | ✅ | ✅ | ✅ |
| 导师资格 | - | - | ✅ | ✅ | ✅ |
| 演讲资格 | - | - | ✅ | ✅ | ✅ |
| Maintainer候选 | - | - | - | ✅ | ✅ |
| 技术决策权 | - | - | - | ✅ | ✅ |
| 基金会代表 | - | - | - | - | ✅ |
| 峰会邀请 | - | - | - | - | ✅ |
