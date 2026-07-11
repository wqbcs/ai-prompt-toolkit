# 医疗行业术语表

> **版本**：v1.0.0
> **覆盖**：医疗信息化、医疗AI、健康数据管理、医疗设备安全

---

| 序号 | 术语 | 英文 | 分类 | 定义 |
|------|------|------|------|------|
| 1 | 受保护健康信息 | PHI (Protected Health Information) | 合规 | HIPAA定义的与个人健康状态相关的可识别信息 |
| 2 | 电子健康记录 | EHR (Electronic Health Record) | 系统 | 医疗机构维护的患者数字化健康记录系统 |
| 3 | 电子病历 | EMR (Electronic Medical Record) | 系统 | 单个医疗机构内部的患者诊疗数字化记录 |
| 4 | 个人健康记录 | PHR (Personal Health Record) | 系统 | 患者自行管理的个人健康信息记录 |
| 5 | 健康信息交换 | HIE (Health Information Exchange) | 系统 | 医疗机构间电子健康信息的标准化交换 |
| 6 | 业务关联协议 | BAA (Business Associate Agreement) | 合规 | 与PHI处理方签署的合规协议，明确安全责任 |
| 7 | 最小必要原则 | Minimum Necessary | 合规 | 使用/披露PHI仅限于完成工作所需的最少信息 |
| 8 | 安全港方法 | Safe Harbor Method | 合规 | HIPAA脱敏方法，移除18种标识符使数据不可识别 |
| 9 | 有限数据集 | Limited Data Set | 合规 | 移除直接标识符但保留日期和部分地理信息的脱敏数据 |
| 10 | k-匿名 | k-Anonymity | 隐私 | 数据集中任意记录至少有k-1条其他记录在准标识符上相同 |
| 11 | l-多样性 | l-Diversity | 隐私 | k-匿名基础上，每个等价类中敏感属性至少有l个不同值 |
| 12 | t-接近性 | t-Closeness | 隐私 | l-多样性基础上，等价类敏感属性分布与总体分布距离<=t |
| 13 | 差分隐私 | Differential Privacy | 隐私 | 数学可证明的隐私保护，查询结果不显著改变个体是否在数据集中的概率 |
| 14 | 令牌化 | Tokenization | 脱敏 | 用不可逆令牌替换敏感标识符，令牌与原文映射存储在安全库中 |
| 15 | 合成数据 | Synthetic Data | 脱敏 | 基于真实数据统计特性人工生成的数据，不含任何真实个人信息 |
| 16 | 重新标识风险 | Re-identification Risk | 隐私 | 脱敏数据通过关联分析还原个体身份的风险 |
| 17 | 医疗AI | Clinical AI | AI | 应用于临床诊断/治疗/预后的AI系统 |
| 18 | 计算机辅助诊断 | CAD (Computer-Aided Diagnosis) | AI | AI辅助影像/病理/心电等诊断，输出辅助参考结果 |
| 19 | 数字孪生 | Digital Twin | AI | 患者或医疗过程的数字模型，用于模拟和预测 |
| 20 | 联邦学习 | Federated Learning | AI | 多医院在不共享原始数据下联合训练模型 |
| 21 | 模型可解释性 | Model Explainability | AI | AI决策过程可被人类理解和追溯的能力 |
| 22 | 反事实解释 | Counterfactual Explanation | AI | "如果输入变为X，预测将变为Y"形式的解释 |
| 23 | 医疗物联网 | IoMT (Internet of Medical Things) | 设备 | 连接互联网的医疗设备和健康监测设备 |
| 24 | 医疗设备软件 | SaMD (Software as a Medical Device) | 设备 | 独立于硬件医疗设备、用于医疗目的的软件 |
| 25 | DICOM | DICOM (Digital Imaging and Communications in Medicine) | 标准 | 医学影像的存储、传输和格式标准 |
| 26 | FHIR | FHIR (Fast Healthcare Interoperability Resources) | 标准 | HL7新一代医疗数据交换标准，基于RESTful API |
| 27 | ICD-11 | ICD-11 (International Classification of Diseases 11th) | 标准 | WHO发布的国际疾病分类第11版 |
| 28 | SNOMED CT | SNOMED CT (Systematized Nomenclature of Medicine) | 标准 | 国际系统化临床术语体系 |
| 29 | 510(k)审批 | 510(k) Clearance | 监管 | FDA医疗器械上市前通知，证明与已批准设备实质等效 |
| 30 | De Novo审批 | De Novo Pathway | 监管 | FDA新型中低风险医疗器械分类和审批路径 |
