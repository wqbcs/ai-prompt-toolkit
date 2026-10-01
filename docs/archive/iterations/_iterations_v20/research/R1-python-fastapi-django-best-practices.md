# 调研报告R1 - Python/FastAPI/Django最佳实践

> **日期**：2026-07-12 | **来源**：fastapi.tiangolo.com + docs.djangoproject.com + 社区最佳实践

---

## 一、FastAPI核心特性（调研日期：2026-07-12）

### 1.1 架构设计
- 基于Starlette（Web层）+ Pydantic（数据层）双引擎架构
- 原生async/await支持，性能与NodeJS/Go持平
- 自动生成OpenAPI/Swagger/ReDoc文档
- 依赖注入系统（Depends）支持子依赖、全局依赖、yield依赖

### 1.2 关键最佳实践
1. **类型注解驱动**：用Python标准类型注解声明参数，自动验证+文档生成
2. **Pydantic v2模型**：使用BaseModel定义请求/响应体，支持嵌套、验证器、序列化
3. **依赖注入**：Depends()实现认证、数据库会话、配置注入
4. **中间件栈**：CORS、异常处理、请求日志中间件链式组合
5. **后台任务**：BackgroundTasks处理非阻塞操作（邮件/通知/日志）
6. **SSE/WebSocket**：实时通信支持Server-Sent Events和WebSocket
7. **Lifespan事件**：应用启动/关闭生命周期管理（数据库连接池/缓存预热）

### 1.3 FastAPI 2026新特性
- FastAPI Cloud一键部署
- FastAPI CLI（fastapi dev/run）
- 严格Content-Type检查
- JSON Base64 Bytes支持
- AI扩展性（Language Model Tool/Chat Participant）

### 1.4 提示词场景映射
| 场景 | 提示词要点 |
|------|-----------|
| FastAPI RESTful API | 路由设计+Pydantic模型+依赖注入+错误处理 |
| FastAPI异步编程 | async/await+并发控制+后台任务+SSE |
| FastAPI安全认证 | OAuth2+JWT+Scope+HTTPS中间件 |
| FastAPI测试 | TestClient+依赖覆盖+异步测试+数据库测试 |
| FastAPI部署 | Docker+Uvicorn Worker+健康检查+监控 |

---

## 二、Django核心特性

### 2.1 架构设计
- MVT（Model-View-Template）架构
- ORM+Admin+Middleware+Signal四层体系
- 内置Auth/CMS/Session/Cache组件

### 2.2 关键最佳实践
1. **Apps模块化**：每个功能独立app，可复用可插拔
2. **QuerySet优化**：select_related/prefetch_related避免N+1查询
3. **中间件栈**：请求/响应处理链，自定义中间件遵循规范
4. **Signal解耦**：post_save/pre_delete信号实现松耦合
5. **Celery异步**：耗时任务（邮件/报表/爬虫）异步执行
6. **DRF序列化**：Django REST Framework Serializer+ViewSet

### 2.3 提示词场景映射
| 场景 | 提示词要点 |
|------|-----------|
| Django项目架构 | Apps拆分+URL路由+Settings分层+环境变量 |
| Django ORM | 模型设计+迁移+QuerySet优化+事务 |
| Django REST API | DRF序列化+视图集+权限+分页+过滤 |
| Django部署 | Gunicorn+Nginx+静态文件+监控 |
| Django安全 | CSRF/XSS/SQL注入防护+HTTPS+安全中间件 |

---

## 三、数据科学/ML最佳实践

### 3.1 数据科学
- Pandas/Numpy数据处理管道
- Jupyter Notebook交互式分析
- Matplotlib/Seaborn可视化
- 特征工程+数据清洗标准化流程

### 3.2 机器学习
- Scikit-learn训练管道（Pipeline+GridSearch）
- PyTorch/TensorFlow模型训练+推理
- MLflow实验追踪+模型注册
- 数据版本化（DVC）+实验可复现

### 3.3 自动化测试
- pytest+fixtures+parametrize
- pytest-asyncio异步测试
- pytest-cov覆盖率
- hypothesis属性测试
- Locust/k6性能测试

---

## 四、V20提示词设计建议

1. **Python专项5场景**需覆盖FastAPI/Django/数据科学/ML/自动化测试
2. 每场景含：常见陷阱+性能提示+安全提示
3. 代码示例统一2空格缩进+snake_case键名
4. Python类型注解为提示词核心表达方式
5. FastAPI依赖注入模式映射到提示词参数化设计
