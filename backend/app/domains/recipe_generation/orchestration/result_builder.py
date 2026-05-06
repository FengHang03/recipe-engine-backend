"""
职责：
把 engine 原始结果统一规范成 RecipeGenerationResult。

为什么需要它

因为将来不同 engine 可能会返回不同内部 shape：

L2 optimize 固定集合
L2 optimize 用户选材
scaling engine
未来 preset with tolerance

如果不单独有一个 result builder，generate_recipe_service.py 会到处写 shape patching。
"""