负责把外部数据源变成领域对象。

它不做业务决策，不做 LP，不做模式分流。
它只负责：

- 从数据库 / 配置里把 ingredient、preset recipe、nutrient matrix 拿出来
- 映射成 IngredientRef / IngredientProfile / PresetRecipeSpec / ConstraintBundle
- 给 orchestration 或 engine 提供干净输入
不负责什么
- 不决定这次 recipe 该走哪个 mode
- 不拼 request
- 不做 slot 依赖判断
- 不直接调用 solver