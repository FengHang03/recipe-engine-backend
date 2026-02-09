# 食材表增量更新功能说明

## 概述

原代码的问题：每次运行都会为所有食材生成新的 UUID，导致数据库中的记录无法正确关联。

改进后的功能：
- ✅ 自动检测已存在的记录（基于 `fdc_id`）
- ✅ 保留现有记录的 `id` 和 `created_at`
- ✅ 更新所有记录的其他字段和 `updated_at`
- ✅ 支持多种合并策略

## 功能对比

### 原代码行为

```python
# 第一次运行
fdc_id  | id (UUID)           | created_at
--------|---------------------|------------------
123     | abc-def-123         | 2024-01-01
456     | xyz-789-456         | 2024-01-01

# 第二次运行（相同的 fdc_id）
fdc_id  | id (UUID)           | created_at
--------|---------------------|------------------
123     | NEW-UUID-111  ❌    | 2024-01-02  ❌
456     | NEW-UUID-222  ❌    | 2024-01-02  ❌
```

**问题**: ID 变了，数据库中的外键关联全部失效！

### 新代码行为

```python
# 第一次运行
fdc_id  | id (UUID)           | created_at          | updated_at
--------|---------------------|---------------------|-------------------
123     | abc-def-123         | 2024-01-01 10:00    | 2024-01-01 10:00
456     | xyz-789-456         | 2024-01-01 10:00    | 2024-01-01 10:00

# 第二次运行（相同的 fdc_id）
fdc_id  | id (UUID)           | created_at          | updated_at
--------|---------------------|---------------------|-------------------
123     | abc-def-123  ✅     | 2024-01-01 10:00 ✅ | 2024-01-02 14:30 ✅
456     | xyz-789-456  ✅     | 2024-01-01 10:00 ✅ | 2024-01-02 14:30 ✅
789     | NEW-UUID-333 ✅     | 2024-01-02 14:30 ✅ | 2024-01-02 14:30 ✅

# 第三次运行（新增 fdc_id = 789）
```

**优势**: 
- ✅ ID 保持不变
- ✅ 创建时间保留
- ✅ 更新时间自动刷新
- ✅ 新记录正常添加

## 使用方法

### 方法1: 基础版本（推荐）

直接替换原函数，无需修改调用代码：

```python
from ingredients_generator_incremental import table_ingredients_generation

# 完全兼容原有调用方式
df = table_ingredients_generation(
    input_file_path='data/food.csv',
    output_file_path='data/food_new.csv'
)
```

**自动行为**:
- 如果 `food_new.csv` **不存在** → 创建新文件
- 如果 `food_new.csv` **已存在** → 增量更新
  - 已存在的 fdc_id → 保留 id 和 created_at
  - 新的 fdc_id → 生成新的 id 和 created_at

### 方法2: 高级版本（自定义选项）

支持更灵活的合并策略：

```python
from ingredients_generator_incremental import table_ingredients_generation_with_merge_options

df = table_ingredients_generation_with_merge_options(
    input_file_path='data/food.csv',
    output_file_path='data/food_new.csv',
    merge_strategy='update',  # 合并策略
    preserve_fields=['id', 'created_at']  # 保留字段
)
```

## 合并策略详解

### 策略1: `update`（默认推荐）

**行为**: 更新已存在记录，添加新记录

```python
merge_strategy='update'
```

**适用场景**:
- ✅ 常规的数据更新
- ✅ 食材描述或分类有变化
- ✅ 需要保持数据库关联

**示例**:
```
现有数据:
  fdc_id=123: Chicken Breast, Raw
  
输入数据:
  fdc_id=123: Chicken Breast, Cooked  # 描述变了
  fdc_id=456: Turkey Breast, Raw      # 新食材

结果:
  fdc_id=123: Chicken Breast, Cooked  ← 更新描述，保留ID
  fdc_id=456: Turkey Breast, Raw      ← 新增记录
```

### 策略2: `replace`

**行为**: 完全替换，重新生成所有ID

```python
merge_strategy='replace'
```

**适用场景**:
- ⚠️ 全新开始，不需要保留历史
- ⚠️ 数据库也会重建
- ⚠️ **慎用**：会破坏所有外键关联

**示例**:
```
现有数据:
  fdc_id=123: id=abc-123, created=2024-01-01

输入数据:
  fdc_id=123: Chicken Breast

结果:
  fdc_id=123: id=NEW-UUID, created=2024-01-02  ← 全新ID
```

### 策略3: `append`

**行为**: 只添加新记录，不更新已存在的

```python
merge_strategy='append'
```

**适用场景**:
- ✅ 只想添加新食材
- ✅ 已存在的记录不能修改
- ✅ 增量导入场景

**示例**:
```
现有数据:
  fdc_id=123: Chicken Breast, Raw, category=5

输入数据:
  fdc_id=123: Chicken Breast, Cooked, category=5  # 描述变了
  fdc_id=456: Turkey Breast, Raw                  # 新食材

结果:
  fdc_id=123: Chicken Breast, Raw, category=5  ← 保持不变
  fdc_id=456: Turkey Breast, Raw               ← 只添加新的
```

## 自定义保留字段

默认保留 `['id', 'created_at']`，可以自定义：

```python
# 示例1: 额外保留 source 和 owner_uid
df = table_ingredients_generation_with_merge_options(
    input_file_path='data/food.csv',
    output_file_path='data/food_new.csv',
    merge_strategy='update',
    preserve_fields=['id', 'created_at', 'source', 'owner_uid']
)

# 示例2: 只保留 id（created_at 会更新）
df = table_ingredients_generation_with_merge_options(
    input_file_path='data/food.csv',
    output_file_path='data/food_new.csv',
    merge_strategy='update',
    preserve_fields=['id']  # created_at 会被更新
)
```

## 实际应用场景

### 场景1: 日常数据更新

```python
# 每天运行一次，更新食材信息
df = table_ingredients_generation(
    'data/food.csv',
    'data/food_new.csv'
)
```

**结果**:
- 已存在食材 → 更新描述、分类等信息，保留ID
- 新增食材 → 生成新ID并添加
- 所有记录的 `updated_at` 都会更新

### 场景2: 首次导入

```python
# 第一次运行，没有现有数据
df = table_ingredients_generation(
    'data/food.csv',
    'data/food_new.csv'
)
```

**结果**:
- 所有食材都是新记录
- 自动生成UUID和时间戳

### 场景3: 只添加新食材

```python
# 不想修改已存在的食材
df = table_ingredients_generation_with_merge_options(
    'data/food.csv',
    'data/food_new.csv',
    merge_strategy='append'
)
```

**结果**:
- 只有新的 fdc_id 会被添加
- 已存在的记录完全不变

### 场景4: 强制重建

```python
# 重新开始，生成全新的ID
df = table_ingredients_generation_with_merge_options(
    'data/food.csv',
    'data/food_new.csv',
    merge_strategy='replace'
)
```

**结果**:
- 所有记录都是新的
- 所有ID都重新生成
- ⚠️ **注意**: 数据库也需要清空重建

## 日志输出

运行时会输出详细的日志信息：

```
INFO - 生成食材短名称和分类...
INFO - ✓ 找到现有数据文件，包含 1250 条记录
INFO - 执行增量更新...
INFO -   - 更新已存在记录: 1240 条
INFO -   - 新增记录: 15 条
INFO - ✓ 食材表已生成: data/food_new.csv
INFO -   - 总记录数: 1255
```

## 数据完整性检查

### 检查ID稳定性

```python
import pandas as pd

# 第一次运行
df1 = table_ingredients_generation('data/food.csv', 'data/food_new.csv')

# 第二次运行
df2 = table_ingredients_generation('data/food.csv', 'data/food_new.csv')

# 验证ID是否一致
merged = pd.merge(
    df1[['fdc_id', 'id']], 
    df2[['fdc_id', 'id']], 
    on='fdc_id', 
    suffixes=('_v1', '_v2')
)

# 检查ID是否保持不变
id_changed = merged[merged['id_v1'] != merged['id_v2']]

if len(id_changed) == 0:
    print("✓ 所有ID保持稳定")
else:
    print(f"✗ 发现 {len(id_changed)} 个ID发生变化")
```

### 检查创建时间

```python
# 验证创建时间是否保留
old_df = pd.read_csv('data/food_new.csv')

# 运行更新
new_df = table_ingredients_generation('data/food.csv', 'data/food_new.csv')

# 合并比较
merged = pd.merge(
    old_df[['fdc_id', 'created_at']], 
    new_df[['fdc_id', 'created_at']], 
    on='fdc_id',
    suffixes=('_old', '_new')
)

# 检查创建时间是否保留
time_changed = merged[merged['created_at_old'] != merged['created_at_new']]

if len(time_changed) == 0:
    print("✓ 所有创建时间保持不变")
else:
    print(f"✗ 发现 {len(time_changed)} 个创建时间发生变化")
```

## 迁移步骤

### 从旧代码迁移

1. **备份现有数据**
   ```bash
   cp data/food_new.csv data/food_new_backup.csv
   ```

2. **替换函数**
   ```python
   # 原代码
   from dateset_preparing import table_ingredients_generation
   
   # 新代码
   from ingredients_generator_incremental import table_ingredients_generation
   ```

3. **测试运行**
   ```python
   # 第一次运行（会使用现有数据）
   df = table_ingredients_generation(
       'data/food.csv',
       'data/food_new_test.csv'  # 先输出到测试文件
   )
   ```

4. **验证结果**
   ```python
   import pandas as pd
   
   old = pd.read_csv('data/food_new.csv')
   new = pd.read_csv('data/food_new_test.csv')
   
   # 检查ID是否保留
   merged = pd.merge(old[['fdc_id', 'id']], new[['fdc_id', 'id']], on='fdc_id')
   print(f"ID保持率: {(merged['id_x'] == merged['id_y']).mean() * 100:.1f}%")
   ```

5. **正式使用**
   ```bash
   # 确认无误后，替换原文件
   mv data/food_new_test.csv data/food_new.csv
   ```

## 常见问题

### Q1: 如果我想重新生成所有ID怎么办？

```python
# 方法1: 删除现有文件
import os
os.remove('data/food_new.csv')
df = table_ingredients_generation('data/food.csv', 'data/food_new.csv')

# 方法2: 使用 replace 策略
df = table_ingredients_generation_with_merge_options(
    'data/food.csv',
    'data/food_new.csv',
    merge_strategy='replace'
)
```

### Q2: 如何只更新部分字段？

使用 `preserve_fields` 指定要保留的字段：

```python
# 只更新 description 和 short_name，其他都保留
df = table_ingredients_generation_with_merge_options(
    'data/food.csv',
    'data/food_new.csv',
    preserve_fields=['id', 'created_at', 'source', 'owner_uid', 
                     'food_category_id', 'food_group', 'is_active']
)
```

### Q3: updated_at 什么时候会更新？

**所有策略下，所有记录的 `updated_at` 都会更新为当前时间。**

如果你不想更新 `updated_at`，可以在 `preserve_fields` 中添加它：

```python
preserve_fields=['id', 'created_at', 'updated_at']
```

### Q4: 性能影响如何？

- 增加的开销：读取现有CSV文件
- 数据量 < 10万条：几乎无感知（<1秒）
- 数据量 > 100万条：可能需要2-3秒

**优化建议**: 如果数据量很大，考虑使用数据库而不是CSV。

## 总结

| 特性 | 原代码 | 新代码 |
|------|--------|--------|
| ID稳定性 | ❌ 每次重新生成 | ✅ 自动保留 |
| 创建时间 | ❌ 每次更新 | ✅ 自动保留 |
| 更新时间 | ✅ 支持 | ✅ 自动更新 |
| 增量更新 | ❌ 不支持 | ✅ 自动检测 |
| 合并策略 | ❌ 单一策略 | ✅ 三种策略 |
| 自定义保留字段 | ❌ 不支持 | ✅ 完全可定制 |
| 向后兼容 | - | ✅ 完全兼容 |

**推荐使用场景**: 所有需要保持数据库关联的场景都应该使用新版本！