负责真正的计算。

也就是：

- L1 生成候选组合
- L2 优化克数
- preset scale 做缩放
- analysis 做营养分析与 warning
不负责什么
- 不读 HTTP request
- 不拼 explain payload
- 不做数据库访问策略决定
- 不做跨 mode 编排