"""初始化本体模型库 - 最小化版本"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import ontology_db


def init_ontology_minimal():
    """初始化本体模型库的最小数据集"""
    
    print("=" * 60)
    print("初始化本体模型库 - 最小化数据集")
    print("=" * 60)
    
    if not ontology_db:
        print("❌ 本体数据库未配置")
        return
    
    if not ontology_db.is_connected():
        ontology_db.connect()
    
    # 1. 插入五大核心类
    core_classes = [
        ("OC000000000001", "产业概念类", "IndustryConcept", "描述产业网链的抽象结构与分类属性", None, "core"),
        ("OC000000000002", "产业主体类", "IndustrySubject", "参与产业网链活动的异质性角色", None, "core"),
        ("OC000000000003", "产业对象类", "IndustryObject", "支撑产业网链运行的各类资源与规则", None, "core"),
        ("OC000000000004", "产业事件类", "IndustryEvent", "记录产业主体与对象的动态交互过程", None, "core"),
        ("OC000000000005", "产业文档类", "IndustryDocument", "记录产业实体与事件的凭证性文档", None, "core"),
    ]
    
    # 2. 插入四大支撑类
    support_classes = [
        ("OC000000000006", "标识要素", "IdentifierElement", "用于唯一识别产业实体的编码、名称、称谓等标识信息", None, "core"),
        ("OC000000000007", "类型要素", "TypeElement", "产业实体对应的分类术语", None, "core"),
        ("OC000000000008", "时间要素", "TimeElement", "刻画产业网链相关实体的时间属性", None, "core"),
        ("OC000000000009", "空间要素", "SpaceElement", "定位产业网链相关实体的地理或物理位置", None, "core"),
    ]
    
    # 3. 插入领域子类
    domain_classes = [
        ("OC000000000010", "企业", "Company", "企业主体", "OC000000000002", "domain"),
        ("OC000000000011", "产品", "Product", "产品对象", "OC000000000003", "domain"),
        ("OC000000000012", "技术", "Technology", "技术对象", "OC000000000003", "domain"),
        ("OC000000000013", "合作事件", "CooperationEvent", "合作事件", "OC000000000004", "domain"),
        ("OC000000000014", "资讯文档", "NewsDocument", "资讯文档", "OC000000000005", "domain"),
    ]
    
    all_classes = core_classes + support_classes + domain_classes
    
    with ontology_db.Session() as session:
        # 检查是否已有数据
        from sqlalchemy import text
        result = session.execute(text("SELECT COUNT(*) as count FROM inc_class")).fetchone()
        existing_count = result.count if result else 0
        
        if existing_count > 0:
            print(f"- 本体类已存在 {existing_count} 条记录，跳过初始化")
        else:
            print(f"开始插入 {len(all_classes)} 个本体类...")
            for class_data in all_classes:
                class_id, name, name_en, desc, parent_id, layer = class_data
                session.execute(
                    text("""
                        INSERT INTO inc_class (class_id, class_name, class_name_en, description, parent_class_id, 
                                              category, class_level, status)
                        VALUES (:id, :name, :name_en, :desc, :parent_id, 'concept', :layer, 'active')
                    """),
                    {
                        "id": class_id,
                        "name": name,
                        "name_en": name_en,
                        "desc": desc,
                        "parent_id": parent_id,
                        "layer": layer
                    }
                )
            session.commit()
            print(f"✓ 成功插入 {len(all_classes)} 个本体类")
        
        # 4. 插入基础属性
        basic_properties = [
            ("PROP000000000001", "名称", "name", "OC000000000002", "string", False, True),
            ("PROP000000000002", "描述", "description", "OC000000000002", "text", False, False),
            ("PROP000000000003", "成立时间", "establishment_date", "OC000000000010", "date", False, False),
            ("PROP000000000004", "注册资本", "registered_capital", "OC000000000010", "float", False, False),
            ("PROP000000000005", "产品名称", "product_name", "OC000000000011", "string", False, True),
            ("PROP000000000006", "技术名称", "tech_name", "OC000000000012", "string", False, True),
        ]
        
        result = session.execute(text("SELECT COUNT(*) as count FROM inc_property")).fetchone()
        existing_props = result.count if result else 0
        
        if existing_props > 0:
            print(f"- 本体属性已存在 {existing_props} 条记录，跳过初始化")
        else:
            print(f"开始插入 {len(basic_properties)} 个本体属性...")
            for prop_data in basic_properties:
                prop_id, name, name_en, domain_class, range_type, is_multi, is_required = prop_data
                session.execute(
                    text("""
                        INSERT INTO inc_property (property_id, property_name, property_name_en, class_id, 
                                                 data_type, is_required, property_group)
                        VALUES (:id, :name, :name_en, :domain, :range_type, :is_required, 'scene')
                    """),
                    {
                        "id": prop_id,
                        "name": name,
                        "name_en": name_en,
                        "domain": domain_class,
                        "range_type": range_type,
                        "is_required": is_required
                    }
                )
            session.commit()
            print(f"✓ 成功插入 {len(basic_properties)} 个本体属性")
        
        # 5. 插入基础关系
        basic_relations = [
            ("REL000000000001", "合作", "cooperates_with", "OC000000000010", "OC000000000010", "many_to_many"),
            ("REL000000000002", "生产", "produces", "OC000000000010", "OC000000000011", "one_to_many"),
            ("REL000000000003", "使用技术", "uses_technology", "OC000000000010", "OC000000000012", "many_to_many"),
            ("REL000000000004", "参与事件", "participates_in", "OC000000000002", "OC000000000004", "many_to_many"),
        ]
        
        result = session.execute(text("SELECT COUNT(*) as count FROM inc_relation")).fetchone()
        existing_rels = result.count if result else 0
        
        if existing_rels > 0:
            print(f"- 本体关系已存在 {existing_rels} 条记录，跳过初始化")
        else:
            print(f"开始插入 {len(basic_relations)} 个本体关系...")
            for rel_data in basic_relations:
                rel_id, name, name_en, source_class, target_class, cardinality = rel_data
                session.execute(
                    text("""
                        INSERT INTO inc_relation (relation_id, relation_name, relation_name_en, 
                                                 source_class_id, target_class_id, 
                                                 cardinality, relation_group)
                        VALUES (:id, :name, :name_en, :source, :target, :cardinality, 'base_main')
                    """),
                    {
                        "id": rel_id,
                        "name": name,
                        "name_en": name_en,
                        "source": source_class,
                        "target": target_class,
                        "cardinality": cardinality
                    }
                )
            session.commit()
            print(f"✓ 成功插入 {len(basic_relations)} 个本体关系")
    
    print("\n" + "=" * 60)
    print("本体模型库初始化完成！")
    print("=" * 60)
    
    # 打印统计
    with ontology_db.Session() as session:
        stats = ontology_db.get_statistics()
        print("\n当前统计：")
        print(f"- 本体类: {stats.get('total_classes', 0)}")
        print(f"- 本体属性: {stats.get('total_properties', 0)}")
        print(f"- 本体关系: {stats.get('total_relations', 0)}")


if __name__ == "__main__":
    init_ontology_minimal()
