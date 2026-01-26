"""
数据接入API路由 - 文件上传和数据导入接口
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingestion", tags=["数据接入"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    source_name: str = Form(default="file_upload"),
    process_immediately: bool = Form(default=True),
    background_tasks: BackgroundTasks = None
):
    """
    上传文件并接入到系统
    
    支持的文件格式:
    - PDF (.pdf)
    - Excel (.xlsx, .xls)
    - CSV (.csv)
    - Word (.docx, .doc)
    - 文本文件 (.txt)
    
    Args:
        file: 上传的文件
        source_name: 数据源名称
        process_immediately: 是否立即处理(提取文本并保存)
        
    Returns:
        接入结果
    """
    try:
        # 读取文件内容
        content = await file.read()
        filename = file.filename
        
        # 检查文件大小 (最大100MB)
        max_size = 100 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {len(content)} bytes (最大 {max_size})"
            )
        
        # 检查文件类型
        allowed_extensions = {'.pdf', '.xlsx', '.xls', '.csv', '.docx', '.doc', '.txt', '.json', '.xml'}
        import os
        ext = os.path.splitext(filename)[1].lower()
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {ext}. 支持的类型: {allowed_extensions}"
            )
        
        # 使用文件接入器处理
        from app.ingestion.file_ingestor import FileIngestor
        
        ingestor = FileIngestor(source_name=source_name)
        records = ingestor.ingest(content, filename=filename)
        
        if not records:
            raise HTTPException(status_code=400, detail="文件解析失败")
        
        record = records[0]
        
        # 验证记录
        if not ingestor.validate(record):
            raise HTTPException(status_code=400, detail="文件验证失败")
        
        result = {
            "success": True,
            "record_id": record.record_id,
            "filename": filename,
            "content_type": record.content_type,
            "file_size": len(content),
            "ingested_at": record.ingested_at.isoformat()
        }
        
        if process_immediately:
            try:
                # 提取文本
                extracted_text = ingestor.extract_text(record)
                record.extracted_text = extracted_text
                
                # 保存到存储
                minio_path = ingestor.save_to_storage(record)
                mongodb_id = ingestor.save_metadata(record)
                
                result.update({
                    "processed": True,
                    "minio_path": minio_path,
                    "mongodb_id": mongodb_id,
                    "extracted_text_length": len(extracted_text),
                    "extracted_text_preview": extracted_text[:500] if extracted_text else ""
                })
                
            except Exception as e:
                logger.error(f"处理文件失败: {e}")
                result.update({
                    "processed": False,
                    "processing_error": str(e)
                })
        else:
            result["processed"] = False
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/batch")
async def upload_batch_files(
    files: List[UploadFile] = File(...),
    source_name: str = Form(default="batch_upload")
):
    """
    批量上传文件
    
    Args:
        files: 文件列表
        source_name: 数据源名称
        
    Returns:
        批量处理结果
    """
    results = []
    success_count = 0
    failed_count = 0
    
    for file in files:
        try:
            content = await file.read()
            filename = file.filename
            
            from app.ingestion.file_ingestor import FileIngestor
            
            ingestor = FileIngestor(source_name=source_name)
            records = ingestor.ingest(content, filename=filename)
            
            if records:
                record = records[0]
                if ingestor.validate(record):
                    record.extracted_text = ingestor.extract_text(record)
                    ingestor.save_to_storage(record)
                    ingestor.save_metadata(record)
                    
                    results.append({
                        "filename": filename,
                        "success": True,
                        "record_id": record.record_id
                    })
                    success_count += 1
                    continue
            
            results.append({
                "filename": filename,
                "success": False,
                "error": "解析或验证失败"
            })
            failed_count += 1
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })
            failed_count += 1
    
    return {
        "total": len(files),
        "success": success_count,
        "failed": failed_count,
        "results": results
    }


@router.get("/records")
async def list_raw_data_records(
    source_type: Optional[str] = None,
    source_name: Optional[str] = None,
    is_processed: Optional[bool] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    列出原始数据记录
    
    Args:
        source_type: 按数据源类型筛选
        source_name: 按数据源名称筛选
        is_processed: 按处理状态筛选
        limit: 返回数量限制
        offset: 分页偏移
        
    Returns:
        记录列表
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        # 构建查询条件
        query = {}
        if source_type:
            query["source_type"] = source_type
        if source_name:
            query["source_name"] = source_name
        if is_processed is not None:
            query["is_processed"] = is_processed
        
        # 查询
        records = mongodb_conn.find_many(
            "raw_data",
            query=query,
            limit=limit,
            sort=[("ingested_at", -1)]
        )
        
        # 跳过offset
        records = records[offset:offset + limit]
        
        # 格式化结果
        result = []
        for record in records:
            record["_id"] = str(record.get("_id", ""))
            result.append(record)
        
        return {
            "total": len(result),
            "offset": offset,
            "limit": limit,
            "records": result
        }
        
    except Exception as e:
        logger.error(f"查询记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records/{record_id}")
async def get_raw_data_record(record_id: str):
    """
    获取单条原始数据记录
    
    Args:
        record_id: 记录ID
        
    Returns:
        记录详情
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        record = mongodb_conn.find_one("raw_data", {"record_id": record_id})
        
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        record["_id"] = str(record.get("_id", ""))
        
        return record
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records/{record_id}/download")
async def download_raw_data(record_id: str):
    """
    下载原始数据文件
    
    Args:
        record_id: 记录ID
        
    Returns:
        文件临时下载URL
    """
    try:
        from app.database.mongodb import mongodb_conn
        from app.database.minio_db import minio_conn
        
        # 获取记录
        record = mongodb_conn.find_one("raw_data", {"record_id": record_id})
        
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        minio_path = record.get("minio_path", "")
        if not minio_path:
            raise HTTPException(status_code=404, detail="原始文件不存在")
        
        # 解析bucket和object name
        parts = minio_path.split("/", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=500, detail="无效的存储路径")
        
        bucket_name, object_name = parts
        
        # 生成预签名URL
        from datetime import timedelta
        url = minio_conn.get_presigned_url(bucket_name, object_name, expires=timedelta(hours=1))
        
        return {
            "download_url": url,
            "expires_in": "1 hour",
            "filename": record.get("metadata", {}).get("filename", "unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成下载链接失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/records/{record_id}/process")
async def process_raw_data(record_id: str):
    """
    处理原始数据记录 (提取实体和关系)
    
    Args:
        record_id: 记录ID
        
    Returns:
        处理结果
    """
    try:
        from app.database.mongodb import mongodb_conn
        from app.nlp.llm import llm_processor
        from app.services.graph_service import graph_service
        
        # 获取记录
        record = mongodb_conn.find_one("raw_data", {"record_id": record_id})
        
        if not record:
            raise HTTPException(status_code=404, detail="记录不存在")
        
        extracted_text = record.get("extracted_text", "")
        if not extracted_text:
            raise HTTPException(status_code=400, detail="记录没有提取的文本内容")
        
        # 使用LLM处理
        result = llm_processor.analyze_industry_chain(extracted_text)
        entities = result.get("entities", {})
        relations = result.get("relations", [])
        
        # 保存到图谱
        save_result = graph_service.save_analyzed_data(entities, relations)
        
        # 更新记录状态
        mongodb_conn.update_one(
            "raw_data",
            {"record_id": record_id},
            {
                "$set": {
                    "is_processed": True,
                    "processed_at": datetime.now(),
                    "entities": entities,
                    "relations": relations
                }
            }
        )
        
        return {
            "success": True,
            "record_id": record_id,
            "entities_count": sum(len(v) for v in entities.values()),
            "relations_count": len(relations),
            "graph_save_result": save_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_ingestion_stats():
    """
    获取数据接入统计信息
    
    Returns:
        统计数据
    """
    try:
        from app.database.mongodb import mongodb_conn
        
        # 总记录数
        total_records = len(mongodb_conn.find_many("raw_data", query={}))
        
        # 按来源类型统计
        source_type_stats = mongodb_conn.aggregate("raw_data", [
            {"$group": {"_id": "$source_type", "count": {"$sum": 1}}}
        ])
        
        # 按来源名称统计
        source_name_stats = mongodb_conn.aggregate("raw_data", [
            {"$group": {"_id": "$source_name", "count": {"$sum": 1}}}
        ])
        
        # 处理状态统计
        processed_stats = mongodb_conn.aggregate("raw_data", [
            {"$group": {"_id": "$is_processed", "count": {"$sum": 1}}}
        ])
        
        return {
            "total_records": total_records,
            "by_source_type": {item["_id"]: item["count"] for item in source_type_stats if item["_id"]},
            "by_source_name": {item["_id"]: item["count"] for item in source_name_stats if item["_id"]},
            "by_processed": {str(item["_id"]): item["count"] for item in processed_stats}
        }
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
