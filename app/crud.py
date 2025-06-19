from sqlalchemy.orm import Session, joinedload
from . import models, schemas
import uuid
from typing import List

def get_all_questions_with_answers(db: Session) -> List[models.Question]:
    """
    Retrieves all questions from the database, and preloads (joins)
    their related task answers to avoid multiple queries later (N+1 problem).
    """
    return db.query(models.Question).options(joinedload(models.Question.task_answers)).all()

def update_task_answer_status(db: Session, task_answer_id: uuid.UUID, is_correct: bool):
    """
    Finds a task answer by its ID and updates its status field.
    """
    db_answer = db.query(models.TaskAnswer).filter(models.TaskAnswer.id == task_answer_id).first()
    if db_answer:
        db_answer.status = is_correct
        db.commit()
        db.refresh(db_answer)
    return db_answer

def create_request_log(db: Session, log: schemas.RequestLogCreate) -> models.RequestLog:
    """
    Creates a new request log entry in the database.
    """
    db_log = models.RequestLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_questions_with_answers_by_subject(db: Session, subject_id: uuid.UUID) -> List[models.Question]:
    """
    Retrieves all questions for a specific subject, preloading their related task answers.
    """
    return db.query(models.Question).options(joinedload(models.Question.task_answers)).filter(models.Question.subject_id == subject_id).all()