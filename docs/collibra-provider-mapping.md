# Collibra Provider 接入约定

当前 POC 只实现 `LocalFileMetadataProvider`。未来的 `CollibraMetadataProvider`
应实现相同的 `load_catalog(source_config) -> Catalog` 协议，让问答、语义配置和 UI
无需了解元数据来自哪里。

建议映射：

| Collibra 概念 | DataChat 模型 |
| --- | --- |
| Community / Domain | Catalog 范围及来源标签 |
| Database / Schema asset | Catalog.name / schema_name |
| Table / View asset | Table |
| Column asset | Column |
| Description attribute | description |
| Data type / nullable / PK attributes | Column 技术属性 |
| Relation | Relation.left / right |
| Classification / Tag | 后续扩展 tags |

Provider 负责分页、鉴权、重试、增量同步和 Collibra 标识映射。它不得把用户名、密码或
Token 写入 Space 配置；Space 只保存环境变量或 Secret Manager 引用。

