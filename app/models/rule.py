from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CriteriaType(str, Enum):
    TEXT = "text"
    LOGO = "logo"
    OBJECT = "object"
    COMBINATION = "combination"


class LogicalOperator(str, Enum):
    AND = "AND"
    OR = "OR"


class CriterionEvaluation(BaseModel):
    criterion_name: str
    criteria_type: CriteriaType
    met: bool
    available: bool
    confidence: Optional[float] = None
    details: str


class RuleEvaluationResult(BaseModel):
    rule_id: str
    rule_name: str
    approved: bool
    evaluated_criteria: List[CriterionEvaluation] = Field(default_factory=list)
    criteria_met: List[str] = Field(default_factory=list)
    criteria_not_met: List[str] = Field(default_factory=list)
    criteria_unavailable: List[str] = Field(default_factory=list)
    justification: str


class OverallEvaluationResult(BaseModel):
    approved: bool
    evaluations: List[RuleEvaluationResult] = Field(default_factory=list)
    justification: str


class RuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    criteria_type: CriteriaType
    specific_config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    logical_operator: LogicalOperator = LogicalOperator.OR
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    criteria_type: Optional[CriteriaType] = None
    specific_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    logical_operator: Optional[LogicalOperator] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class Rule(RuleBase):
    id: str
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
