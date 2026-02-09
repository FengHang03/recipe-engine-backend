import pandas as pd
from sqlalchemy import create_engine, text
import os

# ==========================================
# 配置数据库连接 (请根据你的环境修改)
# ==========================================
# 这里使用 TCP 连接 (配合 Cloud SQL Proxy)
DB_USER = 'postgres'
DB_PASS = 'Tuantuan_123'
DB_HOST = '127.0.0.1'
DB_PORT = '15432'  # 你的 Proxy 端口
DB_NAME = 'tuanty_recipe'

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def upsert_ingredients():
    # 1. 读取 CSV
    csv_path = "./data/new_food_data.csv"  # 你的 CSV 文件路径
    if not os.path.exists(csv_path):
        print(f"❌ 找不到文件: {csv_path}")
        return

    print("1. 读取 CSV 数据...")
    df = pd.read_csv(csv_path)
    
    # 确保 fdc_id 是整数 (或字符串，取决于你数据库里的类型，通常 fdc_id 是 int)
    # df['fdc_id'] = df['fdc_id'].astype(int) 
    
    print(f"   准备更新 {len(df)} 条数据")

    # 2. 连接数据库
    engine = create_engine(DB_URL)
    
    # 定义表名
    MAIN_TABLE = "ingredients"      # 你的主表名字
    TEMP_TABLE = "temp_subgroup_update" # 临时表名字

    try:
        with engine.begin() as conn:
            print("2. 创建临时表并上传数据...")
            # 将 DataFrame 存入数据库临时表
            df = df.where(pd.notnull(df), None)
            df.to_sql(TEMP_TABLE, conn, if_exists='replace', index=False)
            
            print("3. 执行 SQL 批量更新...")
            # 核心 SQL: 使用 FROM 子句进行关联更新
            sql_update = text(f"""
                UPDATE {MAIN_TABLE} AS t
                SET 
                    ingredient_group = s.food_group,
                    food_subgroup = s.food_subgroup,
                    updated_at = NOW()  -- 如果你有这个字段，建议顺便更新时间
                FROM {TEMP_TABLE} AS s
                WHERE t.fdc_id = s.fdc_id; -- 关键：通过 fdc_id 匹配
            """)
            
            result = conn.execute(sql_update)
            print(f"   ✓ 成功更新了 {result.rowcount} 行数据")

            # 第二步：INSERT (插入新数据)
            # print("4. 执行 INSERT (插入新记录)...")

            # sql_insert = text(f"""
            #     INSERT INTO {MAIN_TABLE} (
            #         id, 
            #         source,
            #         owner_uid,
            #         fdc_id, 
            #         description,       -- 注意：这里有 description
            #         short_name,
            #         food_category_id,
            #         food_category_label, 
            #         ingredient_group,        -- 修正：原代码是 ingredient_group，请确认你的数据库列名
            #         is_active,
            #         max_pct_kcal,
            #         max_g_per_kg_bw,
            #         created_at, 
            #         updated_at, 
            #         food_subgroup      -- 1. 修复：这里去掉了逗号
            #     )
            #     SELECT 
            #         s.id,              -- 2. 修复：原代码写成了 s,id (逗号变成点)
            #         s.source,
            #         s.owner_uid,       -- 3. 检查：临时表列名通常保持一致
            #         s.fdc_id, 
            #         s.description,     -- 4. 修复：补上了缺失的 description 列！
            #         s.short_name,
            #         s.food_category_id,
            #         s.food_category_label, 
            #         s.ingredient_group,      
            #         s.is_active,
            #         s.max_pct_kcal,
            #         s.max_g_per_kg_bw,
            #         s.created_at,
            #         s.updated_at,
            #         s.food_subgroup    -- 5. 修复：这里也去掉了逗号
            #     FROM {TEMP_TABLE} s
            #     WHERE NOT EXISTS (
            #         SELECT 1 FROM {MAIN_TABLE} t WHERE t.fdc_id = s.fdc_id
            #     );
            # """)

            # res_ins = conn.execute(sql_insert)
            # print(f"   ✓ 新增了 {res_ins.rowcount} 条新数据")

            print("5. 清理临时表...")
            conn.execute(text(f"DROP TABLE {TEMP_TABLE}"))
            
        print("\n✅ 所有操作完成！")
        
    except Exception as e:
        print(f"\n❌ 更新失败: {e}")

def import_new_ingredient_nutrients(csv_path: str, db_url: str):
    """
    读取 CSV 并将新增的营养素数据导入 ingredient_nutrients 表。
    使用 ON CONFLICT DO NOTHING 策略，自动跳过已存在的记录。
    """
    
    print(f"🔄 开始读取 CSV: {csv_path}")
    
    # 1. 读取 CSV
    try:
        df = pd.read_csv(csv_path)
    except FileNotFoundError:
        print("❌ 错误: 找不到 CSV 文件")
        return

    # 2. 数据清洗与列名映射
    # 数据库列名: ingredient_id, nutrient_id, amount_per_100g, data_source, created_at
    # CSV 列名:   ingredient_id, nutrient_id, amount,          data_source, created_at, fdc_id
    
    # 重命名 amount -> amount_per_100g
    if 'amount' in df.columns:
        df = df.rename(columns={'amount': 'amount_per_100g'})
    
    # 确保必需的列存在
    required_cols = ['ingredient_id', 'nutrient_id', 'amount_per_100g']
    if not all(col in df.columns for col in required_cols):
        print(f"❌ 错误: CSV 缺少必要的列。需要: {required_cols}")
        return

    # 填充 data_source 默认值
    if 'data_source' not in df.columns:
        df['data_source'] = 'usda'
    df['data_source'] = df['data_source'].fillna('usda')

    # 剔除数据库中不存在的列 (如 fdc_id)
    # 我们构建一个只包含目标列的 DataFrame
    target_columns = ['ingredient_id', 'nutrient_id', 'amount_per_100g', 'data_source']
    
    # 如果 CSV 里有 created_at 就用，没有就让数据库用默认值 (now())
    if 'created_at' in df.columns:
        target_columns.append('created_at')
        # 确保时间格式正确，pandas 自动转换通常很稳健
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
    
    # 过滤数据
    df_to_insert = df[target_columns].copy()
    df_to_insert = df_to_insert.dropna(subset=['ingredient_id', 'nutrient_id', 'amount_per_100g'])

    if df_to_insert.empty:
        print("⚠️ 没有有效数据需要导入。")
        return

    print(f"📊 准备处理 {len(df_to_insert)} 条记录...")

    # 3. 批量插入 (使用 ON CONFLICT DO NOTHING)
    engine = create_engine(db_url)

    print("🔍 正在校验 ingredient_id 是否有效...")
    
    try:
        with engine.connect() as conn:
            # 查询数据库中所有现存的 ID
            valid_ids_df = pd.read_sql("SELECT id FROM ingredients", conn)
            # 转为 set 集合，通过字符串比对 (确保格式一致)
            valid_ids = set(valid_ids_df['id'].astype(str))
            
            # 确保 CSV 里的 ID 也是字符串格式
            df_to_insert['ingredient_id'] = df_to_insert['ingredient_id'].astype(str)
            
            # 过滤：只保留在 valid_ids 里的行
            initial_count = len(df_to_insert)
            df_valid = df_to_insert[df_to_insert['ingredient_id'].isin(valid_ids)].copy()
            
            dropped_count = initial_count - len(df_valid)
            
            if dropped_count > 0:
                print(f"⚠️ 警告: 发现 {dropped_count} 条数据的 ingredient_id 在 ingredients 表中找不到。")
                print(f"   (这些孤儿数据将被跳过，只导入剩下的 {len(df_valid)} 条)")
            else:
                print("✅ 所有 ingredient_id 均有效。")

    except Exception as e:
        print(f"❌ 读取 ingredients 表失败: {e}")
        return

    if df_valid.empty:
        print("⚠️ 没有有效数据需要导入。")
        return

    print(f"📊 准备导入 {len(df_valid)} 条有效记录...")

    # 3. 批量插入
    cols_str = ", ".join(target_columns)
    params_str = ", ".join([f":{col}" for col in target_columns])

    sql = text(f"""
        INSERT INTO ingredient_nutrients ({cols_str})
        VALUES ({params_str})
        ON CONFLICT (ingredient_id, nutrient_id) 
        DO NOTHING;
    """)

    try:
        with engine.begin() as conn:
            data_dict = df_valid.to_dict(orient='records')
            conn.execute(sql, data_dict)
            print(f"✅ 导入成功！")
            
    except Exception as e:
        print(f"❌ 数据库操作失败: {e}")

if __name__ == "__main__":
    # upsert_ingredients()
    CSV_PATH = "./data/food_nutrient_new.csv" 
    
    if os.path.exists(CSV_PATH):
        import_new_ingredient_nutrients(CSV_PATH, DB_URL)
    else:
        print(f"请检查 CSV_PATH: {CSV_PATH}")