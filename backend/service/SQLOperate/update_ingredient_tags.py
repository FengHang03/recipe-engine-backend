import pandas as pd
from sqlalchemy import create_engine, text
import os

# ==========================================
# 1. 配置 (根据你的环境修改)
# ==========================================
DB_URL = "postgresql+psycopg2://postgres:Tuantuan_123@127.0.0.1:15432/tuanty_recipe"
CSV_PATH = "./data/food_tag_new.csv" # 你的生成脚本输出路径

def update_tags_table():
    if not os.path.exists(CSV_PATH):
        print(f"❌ 找不到文件: {CSV_PATH}")
        return

    engine = create_engine(DB_URL)
    
    print("1. 读取并清洗 CSV 数据...")
    df = pd.read_csv(CSV_PATH)

    df = df.where(pd.notnull(df), None)
    # -------------------------------------------------------
    # 🧹 数据清洗关键步骤
    # 之前的生成脚本可能包含 'description', 'fdc_id' 等辅助列
    # 但 ingredient_tags 表可能只需要以下几列：
    # ingredient_id, tag_type, tag, source
    # -------------------------------------------------------
    
    # 确保只选取数据库表里有的列
    # 假设你的数据库表结构是: id, ingredient_id, tag_type, tag, source, created_at
    target_cols = ['ingredient_id', 'tag_type', 'tag', 'source']
    
    # 过滤掉不需要的辅助列 (如 chk_... 或 description)
    df_to_upload = df[target_cols].copy()
    
    # 确保没有重复行
    df_to_upload.drop_duplicates(inplace=True)

    print(f"   准备更新 {len(df_to_upload)} 条标签数据...")

    # 定义表名
    TARGET_TABLE = "ingredient_tags"
    TEMP_TABLE = "temp_import_tags"

    try:
        with engine.begin() as conn:
            # ---------------------------------------------------
            # A. 上传到临时表
            # ---------------------------------------------------
            print("2. 创建临时表...")
            df_to_upload.to_sql(TEMP_TABLE, conn, if_exists='replace', index=False)
            
            # ---------------------------------------------------
            # B. 删除旧数据 (关键!)
            # 逻辑：只要临时表里出现了这个 ingredient_id，就先把主表里该食材
            #       的所有旧标签删光，防止出现"僵尸标签"。
            # ---------------------------------------------------
            print("3. 清理旧标签 (Delete Old Tags)...")
            sql_delete = text(f"""
                DELETE FROM {TARGET_TABLE}
                WHERE ingredient_id IN (
                    SELECT DISTINCT ingredient_id::uuid FROM {TEMP_TABLE}
                );
            """)
            conn.execute(sql_delete)
            
            # ---------------------------------------------------
            # C. 插入新数据
            # ---------------------------------------------------
            print("4. 插入新标签 (Insert New Tags)...")
            # 假设主表有自增 ID 和 created_at，这里只插入业务列
            sql_insert = text(f"""
                INSERT INTO {TARGET_TABLE} (ingredient_id, tag_type, tag, source)
                SELECT 
                    t.ingredient_id::uuid, 
                    t.tag_type::ingredient_tag_type, 
                    t.tag, 
                    t.source
                FROM {TEMP_TABLE} t
                INNER JOIN ingredients i ON t.ingredient_id::uuid = i.id;
            """)
            result = conn.execute(sql_insert)
            print(f"   ✓ 成功插入了 {result.rowcount} 条标签 (已自动过滤无效ID)")
            
            # ---------------------------------------------------
            # D. 清理
            # ---------------------------------------------------
            conn.execute(text(f"DROP TABLE {TEMP_TABLE}"))
            
        print("✅ 标签表更新成功！")
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")

if __name__ == "__main__":
    update_tags_table()