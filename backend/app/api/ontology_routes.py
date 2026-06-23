"""
本体模型管理 API 路由
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.database.mysql_ontology_db import ontology_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ontology", tags=["本体模型管理"])


class InstanceRegisterRequest(BaseModel):
    """实例注册请求"""
    class_id: str = Field(..., description="归属类ID")
    canonical_name: str = Field(..., description="规范名称")
    neo4j_node_id: Optional[int] = Field(None, description="Neo4j节点ID")
    mongodb_doc_id: Optional[str] = Field(None, description="MongoDB文档ID")


class InstanceUpdateRequest(BaseModel):
    """实例更新请求"""
    neo4j_node_id: Optional[int] = Field(None, description="Neo4j节点ID")
    mongodb_doc_id: Optional[str] = Field(None, description="MongoDB文档ID")


@router.get("/meta")
async def get_ontology_meta():
    """获取本体模型信息"""
    try:
        meta = ontology_db.get_ontology_meta()
        if not meta:
            return {"meta": None, "message": "本体模型信息未初始化"}
        return {"meta": meta}
    except Exception as e:
        logger.error(f"获取本体模型信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取本体模型信息失败: {str(e)}")


@router.get("/classes")
async def get_classes(
    category: Optional[str] = Query(None, description="类别过滤: actor/object/event/concept/document/identifier/type/time/space"),
    level: Optional[str] = Query(None, description="层级过滤: core/support")
):
    """获取类定义列表"""
    try:
        classes = ontology_db.get_classes(category, level)
        return {"classes": classes, "total": len(classes)}
    except Exception as e:
        logger.error(f"获取类定义失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取类定义失败: {str(e)}")


@router.get("/classes/tree")
async def get_class_tree():
    """获取类层级树"""
    try:
        tree = ontology_db.get_class_tree()
        return {"tree": tree}
    except Exception as e:
        logger.error(f"获取类层级树失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取类层级树失败: {str(e)}")


@router.get("/classes/{class_id}")
async def get_class_by_id(class_id: str):
    """根据ID获取类定义"""
    try:
        cls = ontology_db.get_class_by_id(class_id)
        if not cls:
            raise HTTPException(status_code=404, detail=f"类 {class_id} 不存在")
        return {"class": cls}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取类定义失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取类定义失败: {str(e)}")


@router.get("/properties")
async def get_properties(
    class_id: Optional[str] = Query(None, description="归属类ID过滤")
):
    """获取属性定义列表"""
    try:
        properties = ontology_db.get_properties(class_id)
        return {"properties": properties, "total": len(properties)}
    except Exception as e:
        logger.error(f"获取属性定义失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取属性定义失败: {str(e)}")


@router.get("/relations")
async def get_relations(
    group: Optional[str] = Query(None, description="关系分组过滤: base_main/actor_object/classify")
):
    """获取关系定义列表"""
    try:
        relations = ontology_db.get_relations(group)
        return {"relations": relations, "total": len(relations)}
    except Exception as e:
        logger.error(f"获取关系定义失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取关系定义失败: {str(e)}")


@router.get("/axioms")
async def get_axioms(
    axiom_type: Optional[str] = Query(None, description="公理类型过滤: basic/decision/evolution"),
    enabled_only: bool = Query(True, description="仅返回启用的公理")
):
    """获取公理列表"""
    try:
        axioms = ontology_db.get_axioms(axiom_type, enabled_only)
        return {"axioms": axioms, "total": len(axioms)}
    except Exception as e:
        logger.error(f"获取公理列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取公理列表失败: {str(e)}")


@router.get("/concepts")
async def get_concepts(
    concept_type: Optional[str] = Query(None, description="概念类型过滤: industry_network/industry_chain/industry_node/value_link")
):
    """获取产业概念列表"""
    try:
        concepts = ontology_db.get_concepts(concept_type)
        return {"concepts": concepts, "total": len(concepts)}
    except Exception as e:
        logger.error(f"获取产业概念失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取产业概念失败: {str(e)}")


@router.get("/instances")
async def get_instances(
    class_id: Optional[str] = Query(None, description="归属类ID过滤"),
    status: str = Query("active", description="状态过滤: active/inactive/merged"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取实例列表"""
    try:
        instances = ontology_db.get_instances(class_id, status, limit, offset)
        total = ontology_db.count_instances(class_id, status)
        return {"instances": instances, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"获取实例列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取实例列表失败: {str(e)}")


@router.get("/instances/{instance_id}")
async def get_instance_by_id(instance_id: str):
    """根据ID获取实例"""
    try:
        instance = ontology_db.get_instance_by_id(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"实例 {instance_id} 不存在")
        return {"instance": instance}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取实例失败: {str(e)}")


@router.post("/instances")
async def register_instance(request: InstanceRegisterRequest):
    """注册新实例"""
    try:
        cls = ontology_db.get_class_by_id(request.class_id)
        if not cls:
            raise HTTPException(status_code=400, detail=f"类 {request.class_id} 不存在")
        
        instance_id = ontology_db.register_instance(
            class_id=request.class_id,
            canonical_name=request.canonical_name,
            neo4j_node_id=request.neo4j_node_id,
            mongodb_doc_id=request.mongodb_doc_id
        )
        return {"instance_id": instance_id, "message": "实例注册成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"注册实例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"注册实例失败: {str(e)}")


@router.put("/instances/{instance_id}")
async def update_instance(instance_id: str, request: InstanceUpdateRequest):
    """更新实例信息"""
    try:
        instance = ontology_db.get_instance_by_id(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"实例 {instance_id} 不存在")
        
        if request.neo4j_node_id is not None:
            ontology_db.update_instance_neo4j_id(instance_id, request.neo4j_node_id)
        
        return {"message": "实例更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新实例失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新实例失败: {str(e)}")


@router.get("/statistics")
async def get_statistics():
    """获取本体统计信息"""
    try:
        stats = ontology_db.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
