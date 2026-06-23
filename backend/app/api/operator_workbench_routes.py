"""Knowledge computing workbench routes for catalog and visual pipeline templates."""

from __future__ import annotations

from typing import Dict, List, Type

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.knowledge_extraction_operators import (
    CanonicalKnowledgeBundleDTO,
    ChunkDTO,
    ChunkEntityBundleDTO,
    ChunkListDTO,
    ConceptSeedListDTO,
    DocxSourceDTO,
    DocumentDTO,
    DocumentSourceDTO,
    EntityResolutionInputDTO,
    EntityResolutionResultDTO,
    EntitySeedListDTO,
    EventBatchDTO,
    EventResolutionInputDTO,
    EventResolutionResultDTO,
    EventSeedListDTO,
    GraphBuildInputDTO,
    GraphBuildResultDTO,
    GraphSeedDTO,
    GraphImportInputDTO,
    GraphImportOutputDTO,
    MarkdownSourceDTO,
    NormalizedBatchDTO,
    OutlineDTO,
    PdfSourceDTO,
    PipelineEdgeDTO,
    PipelineExecutionPreviewRequestDTO,
    PipelineExecutionPreviewResultDTO,
    PipelineNodeDTO,
    PipelineValidationRequestDTO,
    PipelineValidationResultDTO,
    PipelineValidationSummaryDTO,
    PipelineValidationIssueDTO,
    PublishPipelineRequestDTO,
    PublishedPipelineDTO,
    RelationSeedListDTO,
    RssFeedDTO,
    SourceRecordListDTO,
    StructuredRowDTO,
    StructuredTableRowDTO,
    TableSeedListDTO,
    WebPageSourceDTO,
    get_operator_catalog,
)
from app.knowledge_extraction_operators.catalog_specs import (
    LAYER_DEFINITIONS,
    PIPELINE_TEMPLATES,
    PLANNED_OPERATOR_SPECS,
    classify_operator,
)
from app.knowledge_extraction_operators.runtime import execute_preview, validate_operator_sequence
from app.knowledge_extraction_operators.published_pipeline_repository import PublishedPipelineRepository

router = APIRouter(prefix="/operator-workbench", tags=["Knowledge Computing Workbench"])
published_pipeline_repo = PublishedPipelineRepository()


DTO_TYPES: Dict[str, Type[BaseModel]] = {
    "PdfSourceDTO": PdfSourceDTO,
    "WebPageSourceDTO": WebPageSourceDTO,
    "DocxSourceDTO": DocxSourceDTO,
    "MarkdownSourceDTO": MarkdownSourceDTO,
    "RssFeedDTO": RssFeedDTO,
    "DocumentSourceDTO": DocumentSourceDTO,
    "DocumentDTO": DocumentDTO,
    "ChunkDTO": ChunkDTO,
    "ChunkListDTO": ChunkListDTO,
    "OutlineDTO": OutlineDTO,
    "TableSeedListDTO": TableSeedListDTO,
    "StructuredTableRowDTO": StructuredTableRowDTO,
    "StructuredRowDTO": StructuredRowDTO,
    "EntitySeedListDTO": EntitySeedListDTO,
    "RelationSeedListDTO": RelationSeedListDTO,
    "EventSeedListDTO": EventSeedListDTO,
    "ConceptSeedListDTO": ConceptSeedListDTO,
    "ChunkEntityBundleDTO": ChunkEntityBundleDTO,
    "GraphSeedDTO": GraphSeedDTO,
    "CanonicalKnowledgeBundleDTO": CanonicalKnowledgeBundleDTO,
    "SourceRecordListDTO": SourceRecordListDTO,
    "NormalizedBatchDTO": NormalizedBatchDTO,
    "EventBatchDTO": EventBatchDTO,
    "EntityResolutionInputDTO": EntityResolutionInputDTO,
    "EntityResolutionResultDTO": EntityResolutionResultDTO,
    "EventResolutionInputDTO": EventResolutionInputDTO,
    "EventResolutionResultDTO": EventResolutionResultDTO,
    "GraphBuildInputDTO": GraphBuildInputDTO,
    "GraphBuildResultDTO": GraphBuildResultDTO,
    "GraphImportInputDTO": GraphImportInputDTO,
    "GraphImportOutputDTO": GraphImportOutputDTO,
    "PipelineExecutionPreviewRequestDTO": PipelineExecutionPreviewRequestDTO,
    "PipelineExecutionPreviewResultDTO": PipelineExecutionPreviewResultDTO,
    "PipelineValidationRequestDTO": PipelineValidationRequestDTO,
    "PipelineValidationResultDTO": PipelineValidationResultDTO,
}


def _catalog_by_name() -> Dict[str, Dict[str, object]]:
    return {item["name"]: item for item in _serialize_operators()}


def _validate_pipeline(request: PipelineValidationRequestDTO) -> PipelineValidationResultDTO:
    catalog = _catalog_by_name()
    issues: List[PipelineValidationIssueDTO] = []
    normalized: List[str] = []

    if not request.operators:
        issues.append(
            PipelineValidationIssueDTO(
                code="EMPTY_PIPELINE",
                severity="warning",
                message="当前 pipeline 为空，请先拖入算子。",
            )
        )
        return PipelineValidationResultDTO(
            valid=True,
            issues=issues,
            normalized_operators=[],
            summary=PipelineValidationSummaryDTO(error_count=0, warning_count=1),
        )

    for index, operator_name in enumerate(request.operators):
        operator = catalog.get(operator_name)
        if operator is None:
            issues.append(
                PipelineValidationIssueDTO(
                    code="UNKNOWN_OPERATOR",
                    severity="error",
                    message=f"算子 `{operator_name}` 未注册，无法参与编排校验。",
                    index=index,
                    operator=operator_name,
                )
            )
            continue

        normalized.append(operator_name)

        if operator.get("status") != "implemented":
            issues.append(
                PipelineValidationIssueDTO(
                    code="PLANNED_OPERATOR",
                    severity="warning",
                    message=f"算子 `{operator_name}` 仍处于规划中，目前只能参与设计，不可直接执行。",
                    index=index,
                    operator=operator_name,
                )
            )

    issues.extend(validate_operator_sequence(request.operators, catalog))

    if normalized:
        last_operator = catalog.get(normalized[-1])
        if last_operator and last_operator["name"] != "graph_import":
            issues.append(
                PipelineValidationIssueDTO(
                    code="PIPELINE_NOT_TERMINATED",
                    severity="warning",
                    message=f"当前 pipeline 以 `{last_operator['name']}` 结束，尚未连接最终落图算子 `graph_import`。",
                    index=len(normalized) - 1,
                    operator=last_operator["name"],
                )
            )

    error_count = sum(1 for item in issues if item.severity == "error")
    warning_count = sum(1 for item in issues if item.severity == "warning")
    return PipelineValidationResultDTO(
        valid=error_count == 0,
        issues=issues,
        normalized_operators=normalized,
        summary=PipelineValidationSummaryDTO(error_count=error_count, warning_count=warning_count),
    )


def _model_schema(type_name: str) -> Dict[str, object]:
    model = DTO_TYPES.get(type_name)
    if model is None:
        return {}
    schema = model.model_json_schema()
    return schema if isinstance(schema, dict) else {}


def _serialize_operators() -> List[Dict[str, object]]:
    merged_specs = {
        spec.name: spec
        for spec in [*PLANNED_OPERATOR_SPECS, *get_operator_catalog()]
    }
    operators = []
    for _, spec in sorted(merged_specs.items()):
        item = spec.model_dump()
        knowledge_category, operator_class = classify_operator(spec)
        item["knowledge_category"] = knowledge_category
        item["operator_class"] = operator_class
        item["input_schema"] = _model_schema(spec.input_type)
        item["output_schema"] = _model_schema(spec.output_type)
        operators.append(item)
    return operators


def _serialize_overview() -> Dict[str, object]:
    published_pipeline_repo.ensure_builtin_pipelines(PIPELINE_TEMPLATES)
    published_rows = []
    for item in published_pipeline_repo.list_pipelines():
        published_rows.append(item.model_dump() if hasattr(item, "model_dump") else item)
    return {
        "operators": _serialize_operators(),
        "dto_schemas": {name: _model_schema(name) for name in DTO_TYPES},
        "pipelines": PIPELINE_TEMPLATES,
        "published_pipelines": published_rows,
        "layers": LAYER_DEFINITIONS,
    }


@router.get("/catalog")
def get_operator_catalog_view():
    overview = _serialize_overview()
    return {
        "operators": overview["operators"],
        "dto_schemas": overview["dto_schemas"],
    }


@router.get("/pipelines")
def get_operator_pipeline_templates():
    return {
        "pipelines": PIPELINE_TEMPLATES,
    }


@router.get("/published", response_model=List[PublishedPipelineDTO])
def get_published_pipelines():
    published_pipeline_repo.ensure_builtin_pipelines(PIPELINE_TEMPLATES)
    rows = []
    for item in published_pipeline_repo.list_pipelines():
        rows.append(item if isinstance(item, PublishedPipelineDTO) else PublishedPipelineDTO.model_validate(item))
    return rows


@router.get("/overview")
def get_operator_workbench_overview():
    return _serialize_overview()


@router.post("/validate", response_model=PipelineValidationResultDTO)
def validate_operator_pipeline(request: PipelineValidationRequestDTO):
    return _validate_pipeline(request)


@router.post("/execute-preview", response_model=PipelineExecutionPreviewResultDTO)
def execute_operator_pipeline_preview(request: PipelineExecutionPreviewRequestDTO):
    return execute_preview(request, _catalog_by_name(), DTO_TYPES)


@router.post("/publish", response_model=PublishedPipelineDTO)
def publish_operator_pipeline(request: PublishPipelineRequestDTO):
    operator_names = [node.operator for node in request.nodes]
    validation = _validate_pipeline(PipelineValidationRequestDTO(operators=operator_names))
    blocking_issue_codes = {
        "PLANNED_OPERATOR",
        "PIPELINE_NOT_TERMINATED",
    }
    blocking_issues = [
        issue for issue in validation.issues if issue.severity == "error" or issue.code in blocking_issue_codes
    ]
    if not request.nodes:
        raise HTTPException(status_code=400, detail="当前 pipeline 为空，无法发布。")
    if blocking_issues:
        reason = "；".join(issue.message for issue in blocking_issues[:3])
        raise HTTPException(status_code=400, detail=f"当前 pipeline 未通过发布校验：{reason}")
    published_pipeline_repo.ensure_builtin_pipelines(PIPELINE_TEMPLATES)
    return published_pipeline_repo.publish_pipeline(request)
