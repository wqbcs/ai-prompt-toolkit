# Q3-01~07 Python专项5场景

> **迭代**：v20-Q3-01~07 | **日期**：2026-07-12

---

## 一、FastAPI RESTful API场景提示词（Q3-01）

### 1.1 场景提示词模板

```markdown
@system
你是一位Python FastAPI后端开发专家，拥有5年以上RESTful API设计经验。

@context
- 技术栈：FastAPI + Pydantic v2 + SQLAlchemy 2.0 + Alembic
- 数据库：PostgreSQL / MySQL
- 运行时：Python 3.10+ (async/await)
- 部署：Docker + Uvicorn Workers

@constraint
- 遵循RESTful规范（资源命名用复数名词，HTTP方法语义化，状态码准确）
- 请求/响应使用Pydantic BaseModel，严格类型注解
- 依赖注入管理数据库会话、认证、配置
- 统一错误响应格式（status_code + detail + timestamp）
- 所有API自动生成OpenAPI文档（Swagger + ReDoc）
- 分页/过滤/排序标准化（Offset/Limit + 字段过滤 + 排序参数）
- 异步优先（async def + async session）
- CORS配置、请求日志中间件
- 编写完整测试用例（pytest + httpx AsyncClient）

@output
请输出以下内容：
1. API路由设计表（Method | Path | 描述 | 请求体 | 响应体）
2. Pydantic模型定义（CreateRequest / UpdateRequest / Response / ListResponse）
3. 完整代码实现（main.py / routers/ / models/ / schemas/ / dependencies.py）
4. Alembic迁移脚本
5. Dockerfile + docker-compose.yml
6. 测试用例（pytest-asyncio + httpx）
```

### 1.2 常见陷阱

| # | 陷阱 | 原因 | 解决方案 |
|---|------|------|---------|
| 1 | 同步函数阻塞事件循环 | 在async应用中使用同步IO | 所有IO操作使用async版本（asyncpg/aiomysql） |
| 2 | Pydantic模型复用导致信息泄露 | 同一模型同时用于请求和响应 | 分离CreateModel/UpdateModel/ResponseModel |
| 3 | 依赖注入未使用yield | 数据库会话未正确关闭 | 使用`yield`依赖确保会话关闭 |
| 4 | CORS配置过于宽松 | 允许所有源导致安全风险 | 限制allow_origins为具体域名 |
| 5 | 未处理数据库连接池耗尽 | 高并发下连接池满 | 设置pool_size + max_overflow + timeout |

### 1.3 性能提示

| # | 优化点 | 量化效果 | 实现方式 |
|---|--------|---------|---------|
| 1 | 使用async数据库驱动 | 吞吐量提升3-5x | asyncpg替代psycopg2 |
| 2 | 查询集优化 | 响应时间降低40% | select_related/prefetch_related避免N+1 |
| 3 | 响应缓存 | 重复请求延迟降低90% | Redis缓存 + Cache-Control头 |
| 4 | 分页查询优化 | 大偏移量查询提速10x | cursor-based分页替代offset |
| 5 | 连接池配置 | 并发处理提升2x | pool_size=20, max_overflow=10 |

### 1.4 安全提示

| # | 风险 | 影响 | 防护措施 |
|---|------|------|---------|
| 1 | SQL注入 | 数据泄露 | 使用ORM参数化查询，禁止字符串拼接 |
| 2 | 未认证API端点 | 越权访问 | 全局依赖注入认证，RBAC权限控制 |
| 3 | 敏感信息日志泄露 | 隐私泄露 | 日志脱敏，过滤password/token字段 |
| 4 | 请求体过大 | DoS攻击 | 限制request body size，设置max_tokens |
| 5 | 速率限制缺失 | 暴力攻击 | slowapi限流，按IP/API Key限制 |

---

## 二、Django项目架构场景提示词（Q3-02）

### 2.1 场景提示词模板

```markdown
@system
你是一位Django全栈开发专家，精通Django 5.x + DRF + Celery。

@context
- 技术栈：Django 5.x + DRF + Celery + Redis + PostgreSQL
- 项目类型：{{project_type}}（SaaS平台/电商/内容管理/数据服务）
- 用户量级：{{user_scale}}

@constraint
- Apps模块化设计（每个功能独立app，可复用可插拔）
- Django Settings分层（base/dev/test/prod）
- DRF ViewSet + Serializer + Permission
- Celery异步任务（邮件/报表/数据处理）
- 环境变量管理（django-environ）
- 数据库迁移（makemigrations + migrate）
- 测试（django test + factory_boy + pytest-django）

@output
1. 项目目录结构
2. Settings分层配置
3. App设计（models/views/serializers/urls/admin）
4. Celery任务配置
5. Docker部署配置
6. 测试用例
```

### 2.2 常见陷阱

| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | Django ORM N+1查询 | select_related/prefetch_related |
| 2 | Settings中硬编码密钥 | django-environ + .env文件 |
| 3 | 同步视图阻塞 | 异步视图(ASGI) + Celery |
| 4 | 迁移文件冲突 | 小步迁移，不修改已应用迁移 |
| 5 | 静态文件未收集 | collectstatic + WhiteNoise/CDN |

### 2.3 性能提示

| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | QuerySet优化 | 响应时间降低60% |
| 2 | 缓存框架(Redis) | 重复查询延迟降低95% |
| 3 | 数据库索引 | 查询速度提升10x |
| 4 | 分页优化 | 大数据集内存降低80% |
| 5 | Gunicorn Workers | 并发处理提升4x |

### 2.4 安全提示

| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | CSRF攻击 | Django CSRF中间件 |
| 2 | XSS攻击 | 模板自动转义 + CSP头 |
| 3 | SQL注入 | ORM参数化查询 |
| 4 | 会话劫持 | SECURE_COOKIE + HTTPS |
| 5 | 点击劫持 | X-Frame-Options中间件 |

---

## 三、数据科学场景提示词（Q3-03）

### 3.1 场景提示词模板

```markdown
@system
你是一位Python数据科学专家，精通Pandas/Numpy/Matplotlib/Seaborn。

@context
- 数据源：{{data_source}}（CSV/Excel/数据库/API）
- 分析目标：{{analysis_goal}}
- 输出格式：{{output_format}}（Jupyter Notebook/Python脚本/报告）

@constraint
- 数据清洗标准化流程（缺失值→异常值→重复值→类型转换）
- 可复现分析（固定random_state + 版本声明）
- Pandas链式操作（method chaining）
- 可视化遵循数据墨水比原则
- 代码模块化（数据加载/清洗/分析/可视化分离）

@output
1. 数据加载与检查
2. 数据清洗代码
3. 探索性分析(EDA)
4. 可视化图表
5. 分析结论与建议
```

### 3.2 常见陷阱

| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | 链式赋值SettingWithCopyWarning | 使用.copy()或.loc[] |
| 2 | 忽略数据类型推断 | 显式指定dtype |
| 3 | 大文件一次性加载 | 分块读取(chunksize) |
| 4 | 缺失值盲目填充 | 分析缺失机制后选择策略 |
| 5 | 可视化误导性 | 遵循数据墨水比，不从零截断 |

### 3.3 性能提示

| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | 向量化操作替代循环 | 速度提升100x |
| 2 | 分类数据类型 | 内存降低90% |
| 3 | 分块处理大数据 | 内存可控 |
| 4 | PyArrow后端 | 速度提升2-5x |
| 5 | 并行计算(multiprocessing) | CPU利用率提升4x |

### 3.4 安全提示

| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | pickle反序列化 | 仅加载可信来源 |
| 2 | SQL注入(pd.read_sql) | 参数化查询 |
| 3 | 数据泄露 | 脱敏处理，输出前检查 |
| 4 | 敏感数据日志 | 日志脱敏 |
| 5 | 不安全临时文件 | tempfile模块+自动清理 |

---

## 四、机器学习场景提示词（Q3-04）

### 4.1 场景提示词模板

```markdown
@system
你是一位机器学习工程师，精通Scikit-learn/PyTorch/MLflow。

@context
- 任务类型：{{task_type}}（分类/回归/聚类/NLP/CV）
- 数据集：{{dataset_description}}
- 评估指标：{{metrics}}

@constraint
- 完整ML Pipeline（数据→特征→训练→评估→部署）
- 实验可追踪（MLflow tracking + 参数/指标/模型记录）
- 数据版本化（DVC或类似工具）
- 模型版本管理（MLflow Model Registry）
- 避免数据泄露（训练/验证/测试严格分离）
- 超参搜索标准化（GridSearch/RandomSearch/Optuna）

@output
1. 数据加载与预处理Pipeline
2. 特征工程代码
3. 模型训练代码（含超参搜索）
4. 模型评估报告
5. MLflow实验记录
6. 模型部署代码
```

### 4.2 常见陷阱

| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | 数据泄露 | 严格train/val/test分离，预处理仅fit训练集 |
| 2 | 过拟合 | 交叉验证 + 正则化 + 早停 |
| 3 | 特征选择偏差 | 在交叉验证内做特征选择 |
| 4 | 评估指标选择错误 | 根据业务目标选择（精确率/召回率/F1/AUC） |
| 5 | 模型部署漂移 | 持续监控 + 自动重训 |

### 4.3 性能提示

| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | 数据加载优化 | 训练启动快5x |
| 2 | GPU训练 | 速度提升10-50x |
| 3 | 混合精度训练 | 内存降低50%+速度提升2x |
| 4 | 批处理推理 | 吞吐量提升10x |
| 5 | 模型量化 | 推理速度提升4x+内存降低75% |

### 4.4 安全提示

| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | 对抗样本攻击 | 对抗训练 + 输入验证 |
| 2 | 模型逆向工程 | 输出概率截断 + 差分隐私 |
| 3 | 训练数据投毒 | 数据质量检查 + 异常检测 |
| 4 | 模型窃取 | API限流 + 输出噪声 |
| 5 | 偏见与公平性 | 公平性评估 + 偏见缓解 |

---

## 五、自动化测试场景提示词（Q3-05）

### 5.1 场景提示词模板

```markdown
@system
你是一位Python测试专家，精通pytest/pytest-asyncio/hypothesis/locust。

@context
- 被测项目：{{project_description}}
- 测试框架：pytest + {{test_framework}}
- 测试类型：{{test_type}}（单元/集成/E2E/性能）

@constraint
- 遵循AAA模式（Arrange-Act-Assert）
- 测试命名：test_{{function}}_{{scenario}}_{{expected_result}}
- 每个测试只验证一个行为
- Mock外部依赖，不Mock被测逻辑
- 参数化测试覆盖边界条件
- 异步测试使用pytest-asyncio
- 覆盖率目标：≥80%
- 使用conftest.py管理共享fixtures

@output
1. conftest.py（共享fixtures）
2. 测试用例代码
3. 覆盖率报告配置
4. CI测试配置
```

### 5.2 常见陷阱

| # | 陷阱 | 解决方案 |
|---|------|---------|
| 1 | 测试间相互依赖 | 独立fixtures，不依赖执行顺序 |
| 2 | Mock过度导致测试无效 | 只Mock外部依赖，不Mock被测逻辑 |
| 3 | 测试代码重复 | 提取共享fixtures和helper函数 |
| 4 | 异步测试忘记await | pytest-asyncio + @pytest.mark.asyncio |
| 5 | 硬编码测试数据 | 使用factory_boy动态生成 |

### 5.3 性能提示

| # | 优化点 | 量化效果 |
|---|--------|---------|
| 1 | 并行测试执行 | 测试时间降低70% |
| 2 | 测试选择性执行 | 日常开发快5x |
| 3 | 内存数据库测试 | 测试速度提升10x |
| 4 | Fixture作用域优化 | 重复初始化降低90% |
| 5 | 测试分层（单元快/集成慢） | CI时间降低60% |

### 5.4 安全提示

| # | 风险 | 防护措施 |
|---|------|---------|
| 1 | 测试数据泄露 | 使用假数据，不使用生产数据 |
| 2 | 密钥硬编码 | 环境变量 + .env.test |
| 3 | 测试API暴露 | 测试环境网络隔离 |
| 4 | 测试日志泄露 | 日志脱敏 + CI环境隔离 |
| 5 | 依赖漏洞 | 定期pip-audit扫描 |

---

## 六、Python专项检查清单（Q3-06）

| # | 检查项 | 类别 |
|---|--------|------|
| 1 | 类型注解完整（Python 3.10+语法） | 代码质量 |
| 2 | 使用async/await（FastAPI/Django异步） | 性能 |
| 3 | Pydantic v2模型分离（Request/Response） | 安全 |
| 4 | 依赖注入管理共享资源 | 架构 |
| 5 | 统一错误处理格式 | 体验 |
| 6 | 环境变量管理（非硬编码） | 安全 |
| 7 | 日志标准化（structlog/logging） | 运维 |
| 8 | 测试覆盖率≥80% | 质量 |
| 9 | Docker多阶段构建 | 部署 |
| 10 | CI/CD流水线配置 | 工程化 |

---

## 七、Python常见陷阱+性能提示+安全提示汇总（Q3-07）

所有5个场景的陷阱/性能/安全提示已在各场景中完整定义。汇总统计：

| 场景 | 陷阱数 | 性能提示数 | 安全提示数 |
|------|--------|-----------|-----------|
| FastAPI | 5 | 5 | 5 |
| Django | 5 | 5 | 5 |
| 数据科学 | 5 | 5 | 5 |
| 机器学习 | 5 | 5 | 5 |
| 自动化测试 | 5 | 5 | 5 |
| **合计** | **25** | **25** | **25** |

---

## 八、Q3验收项

- [x] FastAPI RESTful API场景（含陷阱5+性能5+安全5）
- [x] Django项目架构场景（含陷阱5+性能5+安全5）
- [x] 数据科学场景（含陷阱5+性能5+安全5）
- [x] 机器学习场景（含陷阱5+性能5+安全5）
- [x] 自动化测试场景（含陷阱5+性能5+安全5）
- [x] Python专项检查清单（10项）
- [x] Python陷阱/性能/安全汇总（25+25+25=75项）
- [x] Q3全部7次迭代完成
