"""Base contracts for knowledge extraction operators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar, List

from pydantic import BaseModel, Field


class OperatorSpec(BaseModel):
    """Agent-facing operator metadata."""

    name: str
    stage: str
    layer: str = "fusion"
    knowledge_category: str = ""
    operator_class: str = "general"
    description: str
    input_type: str
    output_type: str
    implementation_ref: str
    status: str = "implemented"
    agent_callable: bool = True
    deterministic: bool = True
    side_effect: bool = False
    requires_llm: bool = False
    requires_schema: bool = False
    applicable_sources: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    decoupling_reason: str = ""


class KnowledgeOperatorABC(ABC):
    """Minimal operator interface for extraction-oriented pipelines."""

    SPEC: ClassVar[OperatorSpec]

    @property
    def spec(self) -> OperatorSpec:
        return self.SPEC.model_copy(deep=True)

    @abstractmethod
    def run(self, input_data):
        """Run the operator on a strongly typed input payload."""
