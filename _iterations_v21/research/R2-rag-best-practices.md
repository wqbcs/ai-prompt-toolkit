# 调研报告R2：RAG最佳实践（基于LlamaIndex生态）

> **日期**：2026-07-12 | **版本**：v21-R2

---

## 一、RAG核心架构

### 1. RAG Pipeline五阶段

| 阶段 | 功能 | LlamaIndex组件 |
|------|------|----------------|
| Loading | 数据摄入 | Data Connectors / SimpleDirectoryReader / LlamaParse |
| Indexing | 索引构建 | VectorStoreIndex / PropertyGraphIndex / SummaryIndex |
| Storing | 持久化 | Vector Stores / DocStores / Index Stores / KV Stores |
| Querying | 检索+生成 | Retriever / ResponseSynthesizer / QueryEngine |
| Evaluating | 评估 | Faithfulness / Relevancy / Retrieval Metrics |

### 2. 核心抽象

- **Document**：数据源容器（metadata+text）
- **Node**：文档分块（chunk），LlamaIndex最小处理单元
- **Index**：数据结构化中间表示
- **Retriever**：检索接口（向量/BM25/混合/递归/路由）
- **ResponseSynthesizer**：响应合成（refine/compact/tree_summarize）
- **QueryEngine**：端到端查询接口
- **ChatEngine**：多轮对话接口

### 3. 支持的向量数据库（60+）

Milvus / Qdrant / Chroma / Pinecone / Weaviate / Redis / pgvector / Elasticsearch / FAISS / LanceDB / MongoDB Atlas / ClickHouse / TiDB / OceanBase 等

### 4. 支持的LLM（80+）

OpenAI / Anthropic / Azure / Bedrock / Gemini / DeepSeek / Qwen(DashScope) / Ollama / vLLM / LM Studio / Groq / Cerebras 等

---

## 二、RAG最佳实践

### 1. 文档加载最佳实践
- LlamaParse解析PDF/PPT/Word（保留表格/图片）
- 元数据提取（文件名/日期/页码/章节）
- 增量加载（避免全量重建索引）

### 2. 分块策略最佳实践
- SentenceSplitter：语义分块（默认）
- SemanticSplitter：基于嵌入相似度分块
- HierarchicalNodeParser：父子层级分块
- 分块大小：512-1024 tokens，重叠10-20%
- 元数据传播：父节点元数据传递到子节点

### 3. 检索策略最佳实践
- 向量检索：余弦相似度+MMR去重
- BM25关键词检索：稀疏检索补充
- 混合检索：向量+BM25融合（Reciprocal Rank Fusion）
- 递归检索：小chunk→大chunk上下文
- 自动检索：LLM生成查询过滤器
- 路由检索：QueryRouter分发到不同检索器

### 4. 响应合成最佳实践
- refine模式：逐chunk精炼（高精度）
- compact模式：压缩上下文+精炼（平衡）
- tree_summarize模式：层级摘要（长文档）
- 结构化输出：Pydantic模型强制格式

### 5. 评估最佳实践
- Faithfulness评估：回答是否忠于检索内容
- Relevancy评估：回答是否与问题相关
- Retrieval评估：命中率/MRR/NDCG
- RAGAS框架：综合评估4维度

---

## 三、RAG五场景提示词设计

### 场景1：文档检索场景
- 用户描述检索需求→推荐检索策略→分块+索引+检索配置
- 对比：纯向量/纯BM25/混合检索适用场景
- 华为云OBS+ES混合检索方案

### 场景2：向量数据库场景
- 用户描述数据规模+查询模式→推荐向量库→部署+调优配置
- 对比：Milvus/Qdrant/Chroma/Redis/pgvector选型
- 华为云GaussDB向量能力

### 场景3：混合检索场景
- 向量+BM25+知识图谱三路检索→RRF融合→重排序
- CohereRerank/BGE-Reranker集成
- 查询改写+HyDE增强

### 场景4：RAG评估场景
- 自动评估流水线→Faithfulness+Relevancy+Retrieval三维度
- 基准数据集构建→A/B测试框架
- LLM-as-Judge评估模式

### 场景5：RAG优化场景
- 检索优化：查询扩展/重写/HyDE/Step-back
- 索引优化：分层索引/元数据过滤/多模态索引
- 生成优化：Citation/结构化输出/幻觉检测
- 性能优化：缓存/预计算/异步检索

---

## 四、关键发现

1. LlamaIndex是当前最完整的RAG框架，60+向量库+80+LLM集成
2. 混合检索（向量+BM25+Rerank）是生产级RAG标配
3. 分块策略对检索质量影响最大，需根据文档类型定制
4. 评估体系是RAG迭代优化的基础，Faithfulness最关键
5. LlamaParse解析能力最强，支持复杂PDF/表格/图片
