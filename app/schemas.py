import uuid
from pydantic import BaseModel, Field
from typing import List, Optional

# Pydantic schemas for data validation and serialization.
# These help ensure the data moving in and out of the API has the correct shape.

class AnswerBase(BaseModel):
    task_answer_id: uuid.UUID = Field(..., alias='task_answer_id')
    answer: str

class AnswerForEval(AnswerBase):
    """Schema for a single answer sent to the AI for evaluation."""
    class Config:
        orm_mode = True
        allow_population_by_field_name = True

class EvaluationPayload(BaseModel):
    """Schema for the complete payload sent to the AI for one question."""
    question: str
    preferred_answer: Optional[str] = None
    answers: List[AnswerForEval]

class AIEvaluationResponse(BaseModel):
    """Schema for a single answer evaluation returned by the AI."""
    task_answer_id: uuid.UUID
    correct: bool

class EvaluationResult(BaseModel):
    """Schema for the overall result of an evaluation process."""
    question_id: uuid.UUID
    question_text: str
    answers_evaluated: int
    evaluations: List[AIEvaluationResponse]

class BulkEvaluationSummary(BaseModel):
    """Schema for the summary response after evaluating all questions."""
    message: str
    questions_processed: int
    total_answers_evaluated: int
    details: List[EvaluationResult]

class ServiceEvaluationResult(BaseModel):
    """
    Schema for the structured result returned from the AI service,
    including evaluations and metadata.
    """
    evaluations: List[AIEvaluationResponse]
    duration: float
    prompt_tokens: int
    candidates_tokens: int
    total_tokens: int

class RequestLogBase(BaseModel):
    request_time: float
    question_count: int
    prompt_token_count: int
    candidates_token_count: int
    total_token_count: int
    question_id: uuid.UUID

class RequestLogCreate(RequestLogBase):
    """Schema for creating a new request log entry."""
    pass

class RequestLog(RequestLogBase):
    """Schema for reading a request log entry, includes the ID."""
    id: uuid.UUID

    class Config:
        orm_mode = True