# cross

跨 KG 调度层，负责人：云飞。

- `fact2cognition`：把事实层输出映射到认知层。
- `cognition2decision`：把认知层结果输入决策层。
- `scheduler`：编排全量、增量和依赖执行。
- `linker`：做实体 ID 对齐和关联。
- `synchronizer`：处理增量同步与事件触发。
