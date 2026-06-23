"""创建本体数据库和表结构"""

import sys
import os
import pymysql

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings


def create_ontology_database():
    """创建本体数据库和表结构"""
    
    print("=" * 60)
    print("创建本体数据库")
    print("=" * 60)
    
    # 连接到MySQL服务器（不指定数据库）
    try:
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            charset='utf8mb4'
        )
        print(f"✓ 成功连接到MySQL服务器: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}")
    except Exception as e:
        print(f"✗ 连接MySQL失败: {e}")
        return False
    
    try:
        with connection.cursor() as cursor:
            # 读取SQL脚本
            sql_file = os.path.join(os.path.dirname(__file__), 'init_ontology_tables.sql')
            with open(sql_file, 'r', encoding='utf-8') as f:
                sql_script = f.read()
            
            # 分割SQL语句（按分号分割，但要处理注释）
            statements = []
            current_statement = []
            
            for line in sql_script.split('\n'):
                # 跳过注释行
                line = line.strip()
                if line.startswith('--') or not line:
                    continue
                
                current_statement.append(line)
                
                # 如果行以分号结尾，表示一个完整的语句
                if line.endswith(';'):
                    statement = ' '.join(current_statement)
                    if statement.strip():
                        statements.append(statement)
                    current_statement = []
            
            # 执行每个SQL语句
            for i, statement in enumerate(statements, 1):
                try:
                    # 跳过USE语句，因为我们会在每个语句前切换数据库
                    if statement.strip().upper().startswith('USE '):
                        continue
                    
                    # 如果是CREATE DATABASE语句，直接执行
                    if 'CREATE DATABASE' in statement.upper():
                        cursor.execute(statement)
                        print(f"✓ [{i}/{len(statements)}] 创建数据库")
                    else:
                        # 其他语句需要先切换到目标数据库
                        cursor.execute(f"USE {settings.MYSQL_ONTOLOGY_SCHEMA_DATABASE}")
                        cursor.execute(statement)
                        
                        # 提取表名用于显示
                        if 'CREATE TABLE' in statement.upper():
                            table_name = statement.split('CREATE TABLE')[1].split('(')[0].strip().split()[0]
                            if 'IF NOT EXISTS' in statement.upper():
                                table_name = table_name.replace('IF', '').replace('NOT', '').replace('EXISTS', '').strip()
                            print(f"✓ [{i}/{len(statements)}] 创建表: {table_name}")
                        else:
                            print(f"✓ [{i}/{len(statements)}] 执行SQL语句")
                    
                    connection.commit()
                    
                except Exception as e:
                    # 如果表已存在，忽略错误
                    if 'already exists' in str(e).lower() or '1050' in str(e):
                        print(f"- [{i}/{len(statements)}] 表已存在，跳过")
                    else:
                        print(f"✗ [{i}/{len(statements)}] 执行失败: {e}")
                        print(f"   SQL: {statement[:100]}...")
        
        print("\n" + "=" * 60)
        print("数据库和表结构创建完成！")
        print("=" * 60)
        
        # 验证数据库和表
        with connection.cursor() as cursor:
            cursor.execute(f"USE {settings.MYSQL_ONTOLOGY_SCHEMA_DATABASE}")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"\n创建的表数量: {len(tables)}")
            for table in tables:
                print(f"  - {table[0]}")
        
        return True
        
    except Exception as e:
        print(f"✗ 创建数据库失败: {e}")
        return False
    finally:
        connection.close()


if __name__ == "__main__":
    success = create_ontology_database()
    sys.exit(0 if success else 1)
