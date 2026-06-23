"""Registry for executable knowledge extraction operators."""

from __future__ import annotations

from typing import Dict, List, Type

from app.knowledge_extraction_operators.base import KnowledgeOperatorABC, OperatorSpec


_OPERATOR_REGISTRY: Dict[str, Type[KnowledgeOperatorABC]] = {}


def register_operator(cls: Type[KnowledgeOperatorABC]) -> Type[KnowledgeOperatorABC]:
    spec = cls.SPEC
    if spec.name in _OPERATOR_REGISTRY:
        raise ValueError(f"Operator '{spec.name}' is already registered.")
    _OPERATOR_REGISTRY[spec.name] = cls
    return cls


def get_operator(name: str) -> KnowledgeOperatorABC:
    if name not in _OPERATOR_REGISTRY:
        raise KeyError(f"Unknown operator: {name}")
    return _OPERATOR_REGISTRY[name]()


def get_operator_catalog() -> List[OperatorSpec]:
    return [cls.SPEC.model_copy(deep=True) for _, cls in sorted(_OPERATOR_REGISTRY.items())]


def list_operator_names() -> List[str]:
    return sorted(_OPERATOR_REGISTRY)

