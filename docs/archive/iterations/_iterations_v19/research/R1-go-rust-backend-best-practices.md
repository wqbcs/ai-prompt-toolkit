# R1-Go/Rust后端开发最佳实践与提示词需求调研

> **调研日期**：2026-07-12 | **调研来源**：go.dev/doc/ | go.dev/doc/effective_go | doc.rust-lang.org/book/

---

## 一、Go语言开发关键实践

### 1.1 并发编程范式
- Goroutine+Channel是Go核心并发原语
- `select`多路复用实现超时和非阻塞
- `sync.WaitGroup`/`sync.Mutex`/`sync.Once`同步原语
- Context包实现取消/超时/值传递
- 生成器模式：`func generator() <-chan T`

### 1.2 错误处理最佳实践
- `if err != nil` 惯用模式（非panic）
- 自定义错误类型实现`error`接口
- `errors.Is()`/`errors.As()`错误链检查
- `fmt.Errorf("%w", err)`错误包装
- 哨兵错误：`var ErrNotFound = errors.New("not found")`

### 1.3 接口设计
- 隐式实现（duck typing）
- 小接口原则（io.Reader/io.Writer单方法）
- 接口分离原则（ISP）
- 接口组合优于继承

### 1.4 项目结构
- `cmd/`可执行入口
- `internal/`私有包
- `pkg/`公共库
- `api/`协议定义
- `configs/`配置文件
- `deployments/`部署配置

### 1.5 微服务开发
- Gin/Echo/Fiber框架
- gRPC+Protobuf通信
- 中间件链（日志/认证/限流/恢复）
- 配置管理（Viper）
- 服务发现与注册

### 1.6 测试
- 表驱动测试（Table-Driven Tests）
- `testing.T`标准测试
- `testify`断言库
- Mock接口替代
- 基准测试`Benchmark`

## 二、Rust语言开发关键实践

### 2.1 所有权系统
- 所有权三大规则（单一所有者/移动语义/作用域释放）
- 借用检查器（&T只读引用/&mut T可变引用）
- 生命周期标注（'a）
- Rc/Arc智能指针（共享所有权）
- RefCell/Mutex内部可变性

### 2.2 异步编程
- async/await语法
- Tokio异步运行时
- Future trait
- 异步流（Stream）
- Select并发模式

### 2.3 错误处理
- Result<T, E>枚举
- `?`操作符传播错误
- thiserror/anyhow库
- 自定义Error类型
- From trait转换

### 2.4 Web开发
- Axum/Actix-web框架
- Tower中间件
- SQLx/SeaORM数据库
- Serde序列化
- 请求路由与提取器

### 2.5 嵌入式开发
- no_std环境
- embedded-hal抽象层
- 交叉编译目标
- 内存映射寄存器
- 实时中断处理

### 2.6 FFI（外部函数接口）
- `extern "C"`声明
- `#[no_mangle]`导出
- cbindgen头文件生成
- 安全封装（unsafe隔离）
- PyO3 Python绑定

## 三、提示词场景需求提炼

### 3.1 Go 5场景
1. **微服务开发**：Gin路由+中间件+gRPC通信+配置管理
2. **并发编程**：Goroutine池+Channel管道+Context取消+Select超时
3. **Gin框架**：RESTful API+中间件链+参数绑定+错误处理
4. **ORM/数据库**：sqlx/GORM+事务+迁移+连接池
5. **部署运维**：Docker多阶段构建+K8s部署+优雅关停+健康检查

### 3.2 Rust 5场景
1. **所有权与借用**：生命周期标注+借用规则+智能指针+内部可变性
2. **异步编程**：Tokio运行时+async/await+Stream+Select
3. **Web开发**：Axum路由+Tower中间件+SQLx数据库+Serde序列化
4. **嵌入式开发**：no_std+embedded-hal+交叉编译+中断处理
5. **FFI互操作**：C绑定+cbindgen+安全封装+PyO3

## 四、调研结论
Go和Rust作为现代系统级语言，提示词需求集中在：类型安全、并发模型、错误处理惯用法、项目结构规范、生态工具链。提示词模板应融入语言特定最佳实践，而非通用编程建议。
