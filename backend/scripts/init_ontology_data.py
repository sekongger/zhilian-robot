"""初始化本体模型库数据 - 使用原始SQL"""

import sys
import os
import pymysql

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings


def init_ontology_data():
    """初始化本体模型库的最小数据集"""
    
    print("=" * 60)
    print("初始化本体模型库数据")
    print("=" * 60)
    
    try:
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_ONTOLOGY_SCHEMA_DATABASE,
            charset='utf8mb4'
        )
        print(f"✓ 连接到数据库: {settings.MYSQL_ONTOLOGY_SCHEMA_DATABASE}")
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return False
    
    try:
        with connection.cursor() as cursor:
            # 检查是否已有数据
            cursor.execute("SELECT COUNT(*) FROM inc_class")
            existing_count = cursor.fetchone()[0]
            
            if existing_count > 0:
                print(f"- 本体类已存在 {existing_count} 条记录，跳过初始化")
                return True
            
            print("开始插入本体数据...")
            
            # 1. 插入五大核心类
            core_classes = [
                ("OC000000000001", "产业概念类", "IndustryConcept", "描述产业网链的抽象结构与分类属性", None, "core", "concept"),
                ("OC000000000002", "产业主体类", "IndustrySubject", "参与产业网链活动的异质性角色", None, "core", "actor"),
                ("OC000000000003", "产业对象类", "IndustryObject", "支撑产业网链运行的各类资源与规则", None, "core", "object"),
                ("OC000000000004", "产业事件类", "IndustryEvent", "记录产业主体与对象的动态交互过程", None, "core", "event"),
                ("OC000000000005", "产业文档类", "IndustryDocument", "记录产业实体与事件的凭证性文档", None, "core", "document"),
            ]
            
            # 2. 插入四大支撑类
            support_classes = [
                ("OC000000000006", "标识要素", "IdentifierElement", "用于唯一识别产业实体的编码、名称、称谓等标识信息", None, "support", "identifier"),
                ("OC000000000007", "类型要素", "TypeElement", "产业实体对应的分类术语", None, "support", "type"),
                ("OC000000000008", "时间要素", "TimeElement", "刻画产业网链相关实体的时间属性", None, "support", "time"),
                ("OC000000000009", "空间要素", "SpaceElement", "定位产业网链相关实体的地理或物理位置", None, "support", "space"),
            ]
            
            # 3. 插入领域子类
            domain_classes = [
                ("OC000000000010", "企业", "Company", "企业主体", "OC000000000002", "core", "actor"),
                ("OC000000000011", "产品", "Product", "产品对象", "OC000000000003", "core", "object"),
                ("OC000000000012", "技术", "Technology", "技术对象", "OC000000000003", "core", "object"),
                ("OC000000000013", "合作事件", "CooperationEvent", "合作事件", "OC000000000004", "core", "event"),
                ("OC000000000014", "资讯文档", "NewsDocument", "资讯文档", "OC000000000005", "core", "document"),
            ]
            
            all_classes = core_classes + support_classes + domain_classes
            
            for class_data in all_classes:
                class_id, name, name_en, desc, parent_id, level, category = class_data
                cursor.execute("""
                    INSERT INTO inc_class (class_id, class_name, class_name_en, description, 
                                          parent_class_id, class_level, category)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (class_id, name, name_en, desc, parent_id, level, category))
            
            connection.commit()
            print(f"✓ 成功插入 {len(all_classes)} 个本体类")
            
            # 4. 插入基础属性
            basic_properties = [
                ("PROP000000000001", "名称", "name", "OC000000000002", "string", 1, "scene"),
                ("PROP000000000002", "描述", "description", "OC000000000002", "text", 0, "scene"),
                ("PROP000000000003", "成立时间", "establishment_date", "OC000000000010", "date", 0, "scene"),
                ("PROP000000000004", "注册资本", "registered_capital", "OC000000000010", "float", 0, "scene"),
                ("PROP000000000005", "产品名称", "product_name", "OC000000000011", "string", 1, "scene"),
                ("PROP000000000006", "技术名称", "tech_name", "OC000000000012", "string", 1, "scene"),
            ]
            
            for prop_data in basic_properties:
                prop_id, name, name_en, class_id, data_type, is_required, prop_group = prop_data
                cursor.execute("""
                    INSERT INTO inc_property (property_id, property_name, property_name_en, 
                                             class_id, data_type, is_required, property_group)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (prop_id, name, name_en, class_id, data_type, is_required, prop_group))
            
            connection.commit()
            print(f"✓ 成功插入 {len(basic_properties)} 个本体属性")
            
            # 5. 插入基础关系
            basic_relations = [
                ("REL000000000001", "合作", "cooperates_with", "OC000000000010", "OC000000000010", "n:n", "base_main"),
                ("REL000000000002", "生产", "produces", "OC000000000010", "OC000000000011", "1:n", "base_main"),
                ("REL000000000003", "使用技术", "uses_technology", "OC000000000010", "OC000000000012", "n:n", "base_main"),
                ("REL000000000004", "参与事件", "participates_in", "OC000000000002", "OC000000000004", "n:n", "base_main"),
            ]
            
            for rel_data in basic_relations:
                rel_id, name, name_en, source_class, target_class, cardinality, rel_group = rel_data
                cursor.execute("""
                    INSERT INTO inc_relation (relation_id, relation_name, relation_name_en, 
                                             source_class_id, target_class_id, cardinality, relation_group)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (rel_id, name, name_en, source_class, target_class, cardinality, rel_group))
            
            connection.commit()
            print(f"✓ 成功插入 {len(basic_relations)} 个本体关系")
            
            print("\n" + "=" * 60)
            print("本体模型库数据初始化完成！")
            print("=" * 60)
            
            # 打印统计
            cursor.execute("SELECT COUNT(*) FROM inc_class")
            class_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM inc_property")
            prop_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM inc_relation")
            rel_count = cursor.fetchone()[0]
            
            print("\n当前统计：")
            print(f"- 本体类: {class_count}")
            print(f"- 本体属性: {prop_count}")
            print(f"- 本体关系: {rel_count}")
            
            return True
            
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        connection.close()


if __name__ == "__main__":
    success = init_ontology_data()
    sys.exit(0 if success else 1)
