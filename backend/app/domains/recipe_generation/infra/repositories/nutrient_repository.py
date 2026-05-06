"""
职责：
读取 nutrient matrix、nutrient info、conversion factor 之类的营养数据源。

典型能力
    get_nutrient_matrix(ingredient_ids)
    get_nutrient_info()
    get_conversion_factors(life_stage)
为什么不塞进 ingredient repository

因为“食材元信息”和“营养矩阵读法”在维护上不是同一类关注点。
"""
