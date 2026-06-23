"""Validation and dry-run execution helpers for operator pipelines."""

from __future__ import annotations

from typing import Dict, Iterable, Type

from pydantic import BaseModel

from app.knowledge_extraction_operators import get_operator
from app.knowledge_extraction_operators.dto import (
    EntityResolutionInputDTO,
    EntityResolutionResultDTO,
    EventBatchDTO,
    EventResolutionInputDTO,
    EventResolutionResultDTO,
    GraphBuildInputDTO,
    GraphBuildResultDTO,
    GraphImportInputDTO,
    ChunkEntityBundleDTO,
    ChunkListDTO,
    ConceptSeedListDTO,
    DocumentDTO,
    DocumentSourceDTO,
    EntitySeedListDTO,
    EventSeedListDTO,
    NormalizedBatchDTO,
    GraphImportOutputDTO,
    PipelineExecutionPreviewIssueDTO,
    PipelineExecutionPreviewRequestDTO,
    PipelineExecutionPreviewResultDTO,
    PipelineExecutionPreviewStepDTO,
    PipelineValidationIssueDTO,
    RelationSeedListDTO,
)


SOURCE_ENTRY_TYPES = {
    "PdfSourceDTO",
    "WebPageSourceDTO",
    "DocxSourceDTO",
    "MarkdownSourceDTO",
    "RssFeedDTO",
    "StructuredTableRowDTO",
    "SourceRecordListDTO",
}


def can_resolve_input(expected_type: str, available_types: Iterable[str]) -> bool:
    available = set(available_types)
    if expected_type in available:
        return True
    if expected_type == "EventBatchDTO" and "NormalizedBatchDTO" in available:
        return True
    if expected_type == "EntityResolutionInputDTO" and "NormalizedBatchDTO" in available:
        return True
    if expected_type == "EventResolutionInputDTO" and "EntityResolutionResultDTO" in available and (
        "NormalizedBatchDTO" in available or "EventBatchDTO" in available
    ):
        return True
    if expected_type == "GraphBuildInputDTO" and {
        "NormalizedBatchDTO",
        "EntityResolutionResultDTO",
        "EventResolutionResultDTO",
    }.issubset(available):
        return True
    if expected_type == "GraphImportInputDTO" and "GraphBuildResultDTO" in available:
        return True
    if expected_type == "ChunkDTO" and "ChunkListDTO" in available:
        return True
    if expected_type == "ChunkEntityBundleDTO" and {"ChunkListDTO", "EntitySeedListDTO"}.issubset(available):
        return True
    return False


def validate_operator_sequence(operators: list[str], catalog: Dict[str, Dict[str, object]]) -> list[PipelineValidationIssueDTO]:
    issues: list[PipelineValidationIssueDTO] = []
    available_types: set[str] = set()

    for index, operator_name in enumerate(operators):
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

        input_type = str(operator["input_type"])
        output_type = str(operator["output_type"])

        if index == 0:
            if input_type not in SOURCE_ENTRY_TYPES:
                issues.append(
                    PipelineValidationIssueDTO(
                        code="INVALID_START_OPERATOR",
                        severity="error",
                        message=f"首个算子 `{operator_name}` 需要 `{input_type}`，不能直接作为 pipeline 起点。",
                        index=index,
                        operator=operator_name,
                        expected_type="source-entry",
                        actual_type=input_type,
                    )
                )
                continue
        elif not can_resolve_input(input_type, available_types):
            issues.append(
                PipelineValidationIssueDTO(
                    code="TYPE_MISMATCH",
                    severity="error",
                    message=f"当前上下文无法为 `{operator_name}` 提供 `{input_type}` 输入。",
                    index=index,
                    operator=operator_name,
                    expected_type=input_type,
                    actual_type=", ".join(sorted(available_types)) if available_types else "empty",
                )
            )
            continue

        available_types.add(output_type)

    return issues


def _merge_streamed_output(output_type: str, outputs: list[BaseModel]) -> BaseModel:
    if output_type == "EntitySeedListDTO":
        entities = []
        for output in outputs:
            entities.extend(output.entities)
        return EntitySeedListDTO(entities=entities)
    if output_type == "RelationSeedListDTO":
        relations = []
        for output in outputs:
            relations.extend(output.relations)
        return RelationSeedListDTO(relations=relations)
    if output_type == "EventSeedListDTO":
        events = []
        for output in outputs:
            events.extend(output.events)
        return EventSeedListDTO(events=events)
    if output_type == "ConceptSeedListDTO":
        concepts = []
        for output in outputs:
            concepts.extend(output.concepts)
        return ConceptSeedListDTO(concepts=concepts)
    raise ValueError(f"Unsupported streamed output type: {output_type}")


def _resolve_runtime_input(expected_type: str, context: Dict[str, BaseModel]):
    direct = context.get(expected_type)
    if direct is not None:
        return direct, None

    if expected_type == "EventBatchDTO" and "NormalizedBatchDTO" in context:
        batch = context["NormalizedBatchDTO"]
        return EventBatchDTO(events=batch.events), None

    if expected_type == "EntityResolutionInputDTO" and "NormalizedBatchDTO" in context:
        batch = context["NormalizedBatchDTO"]
        event_batch = context.get("EventBatchDTO")
        return (
            EntityResolutionInputDTO(
                entities=batch.entities,
                events=event_batch.events if event_batch is not None else batch.events,
                extra_region_names=[],
            ),
            None,
        )

    if expected_type == "EventResolutionInputDTO" and "EntityResolutionResultDTO" in context:
        batch = context.get("NormalizedBatchDTO")
        event_batch = context.get("EventBatchDTO")
        events = []
        if event_batch is not None:
            events = event_batch.events
        elif batch is not None:
            events = batch.events
        return (
            EventResolutionInputDTO(
                events=events,
                entity_resolution=context["EntityResolutionResultDTO"],
            ),
            None,
        )

    if expected_type == "GraphBuildInputDTO" and {
        "NormalizedBatchDTO",
        "EntityResolutionResultDTO",
        "EventResolutionResultDTO",
    }.issubset(context):
        return (
            GraphBuildInputDTO(
                normalized_batch=context["NormalizedBatchDTO"],
                entity_resolution=context["EntityResolutionResultDTO"],
                event_resolution=context["EventResolutionResultDTO"],
            ),
            None,
        )

    if expected_type == "GraphImportInputDTO" and "GraphBuildResultDTO" in context:
        return GraphImportInputDTO(batch=context["GraphBuildResultDTO"].batch, dry_run=True), None

    if expected_type == "ChunkDTO" and "ChunkListDTO" in context:
        chunk_list = context["ChunkListDTO"]

        def execute_stream(operator):
            outputs = [operator.run(chunk) for chunk in chunk_list.chunks]
            return _merge_streamed_output(operator.spec.output_type, outputs)

        return None, execute_stream

    if expected_type == "ChunkEntityBundleDTO" and "ChunkListDTO" in context and "EntitySeedListDTO" in context:
        chunk_list = context["ChunkListDTO"]
        entities = context["EntitySeedListDTO"].entities

        def execute_stream(operator):
            outputs = [
                operator.run(ChunkEntityBundleDTO(chunk=chunk, entities=entities))
                for chunk in chunk_list.chunks
            ]
            return _merge_streamed_output(operator.spec.output_type, outputs)

        return None, execute_stream

    return None, None


def summarize_output(output: BaseModel) -> dict:
    if isinstance(output, DocumentSourceDTO):
        return {"source_id": output.source_id, "source_type": output.source_type}
    if isinstance(output, DocumentDTO):
        return {"document_id": output.document_id, "content_length": len(output.content)}
    if isinstance(output, NormalizedBatchDTO):
        return {
            "entity_count": len(output.entities),
            "relation_count": len(output.relations),
            "document_count": len(output.documents),
            "chunk_count": len(output.chunks),
            "event_count": len(output.events),
            "concept_count": len(output.concept_seeds),
        }
    if isinstance(output, EventBatchDTO):
        return {"event_count": len(output.events)}
    if isinstance(output, ChunkListDTO):
        return {"chunk_count": len(output.chunks)}
    if isinstance(output, EntitySeedListDTO):
        return {"entity_count": len(output.entities), "sample_entities": [item.name for item in output.entities[:5]]}
    if isinstance(output, RelationSeedListDTO):
        return {"relation_count": len(output.relations), "sample_predicates": [item.predicate for item in output.relations[:5]]}
    if isinstance(output, EventSeedListDTO):
        return {"event_count": len(output.events), "sample_events": [item.event_type for item in output.events[:5]]}
    if isinstance(output, ConceptSeedListDTO):
        return {"concept_count": len(output.concepts), "sample_concepts": [item.name for item in output.concepts[:5]]}
    if isinstance(output, EntityResolutionResultDTO):
        return {"entity_count": len(output.entities), "conflict_count": len(output.conflicts)}
    if isinstance(output, EventResolutionResultDTO):
        return {"event_count": len(output.events)}
    if isinstance(output, GraphBuildResultDTO):
        return {
            "concept_node_count": len(output.concept_nodes),
            "entity_node_count": len(output.entity_nodes),
            "event_node_count": len(output.event_nodes),
            "document_node_count": len(output.document_nodes),
            "chunk_node_count": len(output.chunk_nodes),
            "edge_count": len(output.edges),
        }
    if isinstance(output, GraphImportOutputDTO):
        return {"status": output.status, "node_count": output.node_count, "edge_count": output.edge_count}
    return {"model_type": output.__class__.__name__}


def execute_preview(
    request: PipelineExecutionPreviewRequestDTO,
    catalog: Dict[str, Dict[str, object]],
    dto_types: Dict[str, Type[BaseModel]],
) -> PipelineExecutionPreviewResultDTO:
    input_model = dto_types.get(request.input_type)
    if input_model is None:
        return PipelineExecutionPreviewResultDTO(
            valid=False,
            issues=[
                PipelineExecutionPreviewIssueDTO(
                    code="UNKNOWN_INPUT_TYPE",
                    severity="error",
                    message=f"未知输入类型 `{request.input_type}`。",
                )
            ],
        )

    context: Dict[str, BaseModel] = {
        request.input_type: input_model.model_validate(request.input_payload),
    }
    steps: list[PipelineExecutionPreviewStepDTO] = []
    issues: list[PipelineExecutionPreviewIssueDTO] = []
    final_output: BaseModel | None = None
    final_output_type: str | None = None

    for index, operator_name in enumerate(request.operators):
        if operator_name not in catalog:
            issues.append(
                PipelineExecutionPreviewIssueDTO(
                    code="UNKNOWN_OPERATOR",
                    severity="error",
                    message=f"算子 `{operator_name}` 未注册。",
                    operator=operator_name,
                    index=index,
                )
            )
            break

        try:
            operator = get_operator(operator_name)
        except KeyError:
            issues.append(
                PipelineExecutionPreviewIssueDTO(
                    code="UNIMPLEMENTED_OPERATOR",
                    severity="error",
                    message=f"算子 `{operator_name}` 当前仅存在目录定义，尚未接入可执行实现。",
                    operator=operator_name,
                    index=index,
                )
            )
            break
        direct_input, stream_runner = _resolve_runtime_input(operator.spec.input_type, context)
        if direct_input is None and stream_runner is None:
            issues.append(
                PipelineExecutionPreviewIssueDTO(
                    code="UNRESOLVED_INPUT",
                    severity="error",
                    message=f"无法为 `{operator_name}` 解析输入 `{operator.spec.input_type}`。",
                    operator=operator_name,
                    index=index,
                )
            )
            break

        output = stream_runner(operator) if stream_runner else operator.run(direct_input)
        context[operator.spec.output_type] = output
        final_output = output
        final_output_type = operator.spec.output_type
        steps.append(
            PipelineExecutionPreviewStepDTO(
                operator=operator.spec.name,
                input_type=operator.spec.input_type,
                output_type=operator.spec.output_type,
                summary=summarize_output(output),
            )
        )

    return PipelineExecutionPreviewResultDTO(
        valid=not any(item.severity == "error" for item in issues),
        issues=issues,
        steps=steps,
        final_output_type=final_output_type,
        final_output_summary=summarize_output(final_output) if final_output is not None else {},
    )
