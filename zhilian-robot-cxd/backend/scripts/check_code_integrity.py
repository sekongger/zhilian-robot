"""
静态代码完整性检查 - 不需要实际导入模块
"""
import os
import ast
import re
from pathlib import Path
from typing import List, Dict, Set


class CodeIntegrityChecker:
    """代码完整性检查器"""
    
    def __init__(self, backend_path: str):
        self.backend_path = Path(backend_path)
        self.results = {
            'passed': [],
            'warnings': [],
            'errors': []
        }
    
    def check_file_exists(self, filepath: str, description: str):
        """检查文件是否存在"""
        full_path = self.backend_path / filepath
        if full_path.exists():
            self.results['passed'].append(f"✅ {description}: {filepath}")
            return True
        else:
            self.results['errors'].append(f"❌ {description}缺失: {filepath}")
            return False
    
    def check_class_methods(self, filepath: str, class_name: str, required_methods: List[str]):
        """检查类是否包含必要的方法"""
        full_path = self.backend_path / filepath
        
        if not full_path.exists():
            self.results['errors'].append(f"❌ 文件不存在: {filepath}")
            return False
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            # 查找类定义
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    # 获取所有方法名
                    methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    
                    # 检查每个必需方法
                    missing = []
                    for method in required_methods:
                        if method in methods:
                            self.results['passed'].append(f"  ✓ {class_name}.{method}")
                        else:
                            missing.append(method)
                    
                    if missing:
                        self.results['errors'].append(f"❌ {class_name} 缺少方法: {', '.join(missing)}")
                        return False
                    
                    self.results['passed'].append(f"✅ {class_name} 所有方法完整 ({len(required_methods)}个)")
                    return True
            
            self.results['errors'].append(f"❌ 未找到类: {class_name} in {filepath}")
            return False
            
        except Exception as e:
            self.results['errors'].append(f"❌ 解析失败 {filepath}: {e}")
            return False
    
    def check_function_exists(self, filepath: str, function_name: str):
        """检查函数是否存在"""
        full_path = self.backend_path / filepath
        
        if not full_path.exists():
            return False
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    self.results['passed'].append(f"✅ 函数存在: {function_name}")
                    return True
            
            self.results['errors'].append(f"❌ 函数缺失: {function_name}")
            return False
            
        except Exception as e:
            self.results['errors'].append(f"❌ 检查失败: {e}")
            return False
    
    def check_api_routes(self, filepath: str, expected_routes: Dict[str, List[str]]):
        """检查API路由定义"""
        full_path = self.backend_path / filepath
        
        if not full_path.exists():
            self.results['errors'].append(f"❌ API文件不存在: {filepath}")
            return False
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for method, routes in expected_routes.items():
                for route in routes:
                    # 简单的正则匹配
                    pattern = rf'@router\.{method.lower()}\(["\'].*{re.escape(route)}.*["\']\)'
                    if re.search(pattern, content):
                        self.results['passed'].append(f"  ✓ {method} {route}")
                    else:
                        self.results['warnings'].append(f"⚠️  路由可能缺失: {method} {route}")
            
            return True
            
        except Exception as e:
            self.results['errors'].append(f"❌ 检查路由失败: {e}")
            return False
    
    def print_results(self):
        """打印检查结果"""
        print("\n" + "="*70)
        print("📊 代码完整性检查结果")
        print("="*70)
        
        if self.results['passed']:
            print(f"\n✅ 通过项 ({len(self.results['passed'])}):")
            for item in self.results['passed'][:20]:  # 只显示前20项
                print(f"  {item}")
            if len(self.results['passed']) > 20:
                print(f"  ... 还有 {len(self.results['passed']) - 20} 项通过")
        
        if self.results['warnings']:
            print(f"\n⚠️  警告项 ({len(self.results['warnings'])}):")
            for item in self.results['warnings']:
                print(f"  {item}")
        
        if self.results['errors']:
            print(f"\n❌ 错误项 ({len(self.results['errors'])}):")
            for item in self.results['errors']:
                print(f"  {item}")
        
        # 总结
        total_passed = len(self.results['passed'])
        total_warnings = len(self.results['warnings'])
        total_errors = len(self.results['errors'])
        total = total_passed + total_warnings + total_errors
        
        print(f"\n{'='*70}")
        print(f"总计: {total_passed} 通过 / {total_warnings} 警告 / {total_errors} 错误")
        
        if total_errors == 0:
            print("\n🎉 代码结构完整，无严重错误！")
            return True
        else:
            print(f"\n⚠️  发现 {total_errors} 个错误需要修复")
            return False


def run_integrity_check():
    """运行完整性检查"""
    print("\n" + "🔍 " + "="*66 + " 🔍")
    print("🔍  智链机器人代码完整性检查（静态分析）")
    print("🔍 " + "="*66 + " 🔍")
    
    backend_path = os.path.dirname(__file__)
    checker = CodeIntegrityChecker(backend_path)
    
    # 1. 检查核心文件存在性
    print("\n[1] 检查核心文件...")
    checker.check_file_exists("app/database/mongodb.py", "MongoDB管理模块")
    checker.check_file_exists("app/database/neo4j_db.py", "Neo4j管理模块")
    checker.check_file_exists("app/services/canonicalization_service.py", "规范化服务")
    checker.check_file_exists("app/analytics/momentum.py", "动量引擎")
    checker.check_file_exists("app/nlp/llm.py", "LLM处理器")
    checker.check_file_exists("app/models/schemas.py", "数据模型")
    
    # 2. 检查MongoDB管理类方法
    print("\n[2] 检查MongoDB管理器...")
    checker.check_class_methods(
        "app/database/mongodb.py",
        "SourceManager",
        ["register_source", "get_source_by_domain", "get_credibility"]
    )
    checker.check_class_methods(
        "app/database/mongodb.py",
        "CanonicalEntityManager",
        ["create_or_update_entity", "add_synonym", "update_momentum", "find_by_name", "increment_reference_count"]
    )
    checker.check_class_methods(
        "app/database/mongodb.py",
        "DocumentInstanceManager",
        ["save_document_instance", "get_recent_documents", "clean_expired_cache"]
    )
    
    # 3. 检查Neo4j方法
    print("\n[3] 检查Neo4j扩展方法...")
    checker.check_class_methods(
        "app/database/neo4j_db.py",
        "Neo4jConnection",
        ["create_canonical_entity", "update_entity_momentum", "create_temporal_relation", 
         "get_entity_with_momentum", "get_top_momentum_entities", "get_entity_relations_with_time"]
    )
    
    # 4. 检查LLM新增方法
    print("\n[4] 检查LLM处理器...")
    checker.check_class_methods(
        "app/nlp/llm.py",
        "LLMProcessor",
        ["extract_temporal_info", "extract_sentiment", "analyze_with_temporal_and_sentiment"]
    )
    
    # 5. 检查动量引擎
    print("\n[5] 检查动量引擎...")
    checker.check_class_methods(
        "app/analytics/momentum.py",
        "MomentumEngine",
        ["calculate_momentum", "get_momentum_trend", "update_all_momentum", 
         "get_top_momentum_entities", "detect_momentum_spike"]
    )
    
    # 6. 检查规范化服务
    print("\n[6] 检查规范化服务...")
    checker.check_class_methods(
        "app/services/canonicalization_service.py",
        "CanonicalizationService",
        ["canonicalize_entity", "save_canonical_graph", "merge_duplicate_entities"]
    )
    
    # 7. 检查API路由
    print("\n[7] 检查时间分析API路由...")
    checker.check_api_routes(
        "app/api/graph_routes.py",
        {
            "get": [
                "/entities/{entity_id}/timeline",
                "/entities/{entity_id}/momentum",
                "/momentum/top"
            ],
            "post": [
                "/momentum/update"
            ]
        }
    )
    
    # 8. 检查前端组件
    print("\n[8] 检查前端组件...")
    frontend_timeline = Path(backend_path).parent / "frontend" / "src" / "components" / "TimelineView.jsx"
    if frontend_timeline.exists():
        checker.results['passed'].append("✅ 前端TimelineView组件已创建")
    else:
        checker.results['warnings'].append("⚠️  前端TimelineView组件未找到")
    
    # 打印结果
    success = checker.print_results()
    
    # 额外提示
    print("\n" + "="*70)
    print("💡 下一步建议:")
    print("="*70)
    print("1. 确保所有Python依赖已安装: pip install -r requirements.txt")
    print("2. 配置环境变量: backend/.env (DEEPSEEK_API_KEY等)")
    print("3. 启动数据库服务: MongoDB, Neo4j, Redis")
    print("4. 运行后端服务: cd backend && uvicorn main:app --reload")
    print("5. 运行前端服务: cd frontend && npm run dev")
    print("6. 访问 http://localhost:8000/docs 查看API文档")
    
    return success


if __name__ == "__main__":
    import sys
    success = run_integrity_check()
    sys.exit(0 if success else 1)
