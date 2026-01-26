#!/usr/bin/env python3
"""
数据库连接重试启动脚本
在启动主应用前，确保所有数据库服务已就绪
"""
import time
import sys
import os
from pymongo import MongoClient
from neo4j import GraphDatabase
import redis


def wait_for_neo4j(uri, user, password, max_retries=30, delay=2):
    """等待 Neo4j 就绪"""
    print(f"等待 Neo4j 连接就绪: {uri}")
    for i in range(max_retries):
        try:
            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                session.run("RETURN 1")
            driver.close()
            print("✓ Neo4j 连接成功")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"  尝试 {i+1}/{max_retries}: Neo4j 未就绪，{delay}秒后重试...")
                time.sleep(delay)
            else:
                print(f"✗ Neo4j 连接失败: {e}")
                return False
    return False


def wait_for_mongodb(uri, max_retries=30, delay=2):
    """等待 MongoDB 就绪"""
    print(f"等待 MongoDB 连接就绪")
    for i in range(max_retries):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=2000)
            client.admin.command('ping')
            client.close()
            print("✓ MongoDB 连接成功")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"  尝试 {i+1}/{max_retries}: MongoDB 未就绪，{delay}秒后重试...")
                time.sleep(delay)
            else:
                print(f"✗ MongoDB 连接失败: {e}")
                return False
    return False


def wait_for_redis(host, port, max_retries=30, delay=2):
    """等待 Redis 就绪"""
    print(f"等待 Redis 连接就绪: {host}:{port}")
    for i in range(max_retries):
        try:
            r = redis.Redis(host=host, port=port, socket_connect_timeout=2)
            r.ping()
            r.close()
            print("✓ Redis 连接成功")
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f"  尝试 {i+1}/{max_retries}: Redis 未就绪，{delay}秒后重试...")
                time.sleep(delay)
            else:
                print(f"✗ Redis 连接失败: {e}")
                return False
    return False


def main():
    """主函数：等待所有数据库就绪"""
    print("=" * 60)
    print("智链机器人 - 数据库连接检查")
    print("=" * 60)
    
    # 从环境变量读取配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password123")
    
    mongodb_uri = os.getenv("MONGODB_URI", "mongodb://admin:password123@mongodb:27017")
    
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    
    # 等待所有数据库
    all_ready = True
    
    if not wait_for_neo4j(neo4j_uri, neo4j_user, neo4j_password):
        all_ready = False
    
    if not wait_for_mongodb(mongodb_uri):
        all_ready = False
    
    if not wait_for_redis(redis_host, redis_port):
        all_ready = False
    
    print("=" * 60)
    if all_ready:
        print("✓ 所有数据库连接就绪，启动应用...")
        print("=" * 60)
        return 0
    else:
        print("✗ 部分数据库连接失败，请检查配置")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
