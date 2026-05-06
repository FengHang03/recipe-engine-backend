负责把一次 recipe generation 请求串起来。

也就是：

- 校验 request
- 根据 RecipeGenerationMode 分流
- 让 infra 准备数据
- 调用对应 engine
- 统一封装 RecipeGenerationResult
- 需要时生成 explain payload
不负责什么
- 不写 LP 约束
- 不直接写 SQL
- 不自己计算 nutrient totals
- 不直接生成 LLM 文案