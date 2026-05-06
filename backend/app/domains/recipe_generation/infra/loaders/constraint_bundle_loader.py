"""
职责：
加载并组装 ConstraintBundle。

输入
pet life stage
maybe user profile / mode
输出
ConstraintBundle
为什么需要

你已经把约束模型放进了 contracts，那么具体配置实例就应该通过 loader 统一装配，而不是让每个 engine 自己 import 5 个 config 文件。
"""