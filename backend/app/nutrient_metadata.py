import csv
import logging
from enum import unique, IntEnum

from app.shared.contracts.enums import NutrientID

# --------------------------
# 1. 先定义 NutrientID 枚举（保持和原有代码一致）
# --------------------------
from app.shared.contracts.enums import NutrientID

# --------------------------
# 2. 配置日志（方便调试）
# --------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --------------------------
# 3. 核心函数：从 CSV 生成 NUTRIENT_METADATA
# --------------------------
def generate_nutrient_metadata(csv_path: str = "D:/Programs/Pet-Recipe-251204/data/nutrient.csv") -> dict[NutrientID, dict]:
    """
    从 nutrient.csv 读取营养素信息，匹配 NutrientID 枚举，生成 NUTRIENT_METADATA 字典
    
    Args:
        csv_path: nutrient.csv 文件路径（默认当前目录）
    
    CSV 列要求（可根据实际调整列名）：
        - id: USDA 营养素ID（整数，对应 NutrientID 的值）
        - name: 营养素名称（如 Energy、Protein）
        - unit_name: 单位（如 kcal、g、mg、IU）
    
    Returns:
        符合格式的 NUTRIENT_METADATA 字典
    """
    # 初始化结果字典
    nutrient_metadata = {}
    
    # 映射 NutrientID 值到枚举成员（方便快速查找）
    nutrient_id_map = {member.value: member for member in NutrientID}
    
    try:
        with open(csv_path, mode="r", encoding="utf-8") as csv_file:
            # 读取 CSV（使用 DictReader 按列名解析）
            csv_reader = csv.DictReader(csv_file)
            
            # 验证必要列是否存在
            required_columns = {"id", "name", "unit_name"}
            if not required_columns.issubset(csv_reader.fieldnames):
                raise ValueError(
                    f"CSV 缺少必要列！需要：{required_columns}，实际：{csv_reader.fieldnames}"
                )
            
            # 遍历每一行数据
            for row_num, row in enumerate(csv_reader, start=2):  # 行号从2开始（跳过表头）
                # 提取并清洗数据
                raw_id = row["id"].strip()
                raw_name = row["name"].strip()
                raw_unit = row["unit_name"].strip()
                
                # 跳过空行或ID为空的行
                if not raw_id:
                    logger.warning(f"第 {row_num} 行：ID 为空，跳过")
                    continue
                
                # 转换ID为整数（处理异常）
                try:
                    nutrient_id_value = int(raw_id)
                except ValueError:
                    logger.warning(f"第 {row_num} 行：ID '{raw_id}' 不是有效整数，跳过")
                    continue
                
                # 匹配 NutrientID 枚举
                if nutrient_id_value not in nutrient_id_map:
                    logger.info(f"第 {row_num} 行：ID {nutrient_id_value} 不在 NutrientID 枚举中，跳过")
                    continue
                
                # 提取枚举成员
                nutrient_enum = nutrient_id_map[nutrient_id_value]
                
                # 验证名称和单位非空
                if not raw_name:
                    logger.warning(f"第 {row_num} 行：ID {nutrient_id_value} 名称为空，跳过")
                    continue
                if not raw_unit:
                    logger.warning(f"第 {row_num} 行：ID {nutrient_id_value} 单位为空，跳过")
                    continue
                
                # 添加到结果字典
                nutrient_metadata[nutrient_enum] = {
                    "name": raw_name,
                    "unit_name": raw_unit
                }
                logger.debug(f"成功匹配：{nutrient_enum.name} ({nutrient_id_value}) -> {raw_name} ({raw_unit})")
        
        logger.info(f"生成完成！共匹配到 {len(nutrient_metadata)} 个营养素")
        return nutrient_metadata

    except FileNotFoundError:
        logger.error(f"文件不存在：{csv_path}")
        raise
    except Exception as e:
        logger.error(f"读取CSV失败：{str(e)}")
        raise

# --------------------------
# 4. 生成并输出 NUTRIENT_METADATA
# --------------------------
if __name__ == "__main__":
    # 生成 metadata（替换为你的 nutrient.csv 实际路径）
    NUTRIENT_METADATA = generate_nutrient_metadata(csv_path="D:/Programs/Pet-Recipe-251204/data/nutrient.csv")
    
    # 打印生成的结果（可选：也可以写入到Python文件中）
    print("\n===== 生成的 NUTRIENT_METADATA =====")
    print("NUTRIENT_METADATA = {")
    for enum_member, meta in NUTRIENT_METADATA.items():
        print(f"    NutrientID.{enum_member.name}: {{'name': '{meta['name']}', 'unit_name': '{meta['unit_name']}'}},")
    print("}")
    
    # 可选：将结果写入到指定的Python文件（如 nutrient_constants.py）
    with open("nutrient_constants.py", mode="w", encoding="utf-8") as f:
        f.write("from enum import unique, IntEnum\n\n")
        # 写入 NutrientID 枚举定义
        f.write(repr(NutrientID))
        f.write("\n\n")
        # 写入 NUTRIENT_METADATA
        f.write("NUTRIENT_METADATA = {\n")
        for enum_member, meta in NUTRIENT_METADATA.items():
            f.write(f"    NutrientID.{enum_member.name}: {{'name': '{meta['name']}', 'unit_name': '{meta['unit_name']}'}},\n")
        f.write("}\n")
    logger.info("已将结果写入 nutrient_constants.py 文件")