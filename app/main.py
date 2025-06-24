from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import time
from . import crud, models, schemas, services
from .database import get_db

app = FastAPI(
    title="AI Answer Evaluator API",
    description="An API to evaluate student answers using Google's Generative AI.",
    version="1.0.0"
)

def run_evaluation_and_update_db(db: Session):
    """
    The core logic for the background task.
    1. Fetches all questions and their answers.
    2. Iterates through each question, sending its answers to the AI for evaluation.
    3. Updates the database with the AI's evaluation.
    """
    print("Starting background task: Evaluating all answers...")
    questions = crud.get_all_questions_with_answers(db)
    
    for question in questions:
        if not question.task_answers:
            print(f"Skipping question ID {question.id}: No answers to evaluate.")
            continue

        print(f"Processing question ID: {question.id}")

        # Prepare payload for the AI service
        answers_for_eval = [
            schemas.AnswerForEval(task_answer_id=ans.id, answer=ans.answer)
            for ans in question.task_answers
        ]
        
        payload = schemas.EvaluationPayload(
            question=question.question_text,
            preferred_answer=question.preferred_answer,
            answers=answers_for_eval
        )
        
        # Call the AI evaluation service
        service_result = services.evaluate_answers_with_ai(payload)
        
        # Check if the service call was successful
        if service_result:
            # 1. Update the status for each answer
            for eval_result in service_result.evaluations:
                crud.update_task_answer_status(
                    db=db,
                    task_answer_id=eval_result.task_answer_id,
                    is_correct=eval_result.correct
                )
            print(f"Successfully evaluated {len(service_result.evaluations)} answers for question ID {question.id}")

            # 2. Create the request log entry
            log_entry = schemas.RequestLogCreate(
                request_time=service_result.duration,
                question_count=len(question.task_answers),
                prompt_token_count=service_result.prompt_tokens,
                candidates_token_count=service_result.candidates_tokens,
                total_token_count=service_result.total_tokens,
                question_id=question.id
            )
            crud.create_request_log(db=db, log=log_entry)
            print(f"Successfully created request log for question ID {question.id}")

        else:
            print(f"Failed to get evaluations for question ID {question.id}")

        # rate limiting purpose
        print("turu dulu 2 detik")
        time.sleep(2)
    
    print("Background evaluation task finished.")


@app.post("/evaluate/all-answers", status_code=202)
def trigger_bulk_evaluation(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers a background task to evaluate all answers for all questions in the database.
    
    This endpoint immediately returns a 202 Accepted response while the
    evaluation runs in the background. This is ideal for long-running processes.
    """
    background_tasks.add_task(run_evaluation_and_update_db, db)
    return {
        "message": "Evaluation process started in the background. "
                   "The `status` field in the `task_answers` table will be updated upon completion."
    }

@app.get("/answers/all", response_model=List[schemas.AIEvaluationResponse])
def get_all_evaluated_answers(db: Session = Depends(get_db)):
    """
    A utility endpoint to view the current evaluation status of all answers.
    """
    answers = db.query(models.TaskAnswer).all()
    return [
        schemas.AIEvaluationResponse(task_answer_id=ans.id, correct=ans.status)
        for ans in answers if ans.status is not None
    ]

def run_evaluation_for_subject_and_update_db(subject_id: str, db: Session):
    """
    Evaluates all answers for all questions in a specific subject.
    """
    import uuid as uuidlib
    print(f"Starting evaluation for subject: {subject_id}")
    questions = crud.get_questions_with_answers_by_subject(db, uuidlib.UUID(subject_id))
    for question in questions:
        if not question.task_answers:
            print(f"Skipping question ID {question.id}: No answers to evaluate.")
            continue
        print(f"Processing question ID: {question.id}")
        answers_for_eval = [
            schemas.AnswerForEval(task_answer_id=ans.id, answer=ans.answer)
            for ans in question.task_answers
        ]
        payload = schemas.EvaluationPayload(
            question=question.question_text,
            preferred_answer=question.preferred_answer,
            answers=answers_for_eval
        )
        service_result = services.evaluate_answers_with_ai(payload)
        if service_result:
            for eval_result in service_result.evaluations:
                crud.update_task_answer_status(
                    db=db,
                    task_answer_id=eval_result.task_answer_id,
                    is_correct=eval_result.correct
                )
            print(f"Successfully evaluated {len(service_result.evaluations)} answers for question ID {question.id}")
            log_entry = schemas.RequestLogCreate(
                request_time=service_result.duration,
                question_count=len(question.task_answers),
                prompt_token_count=service_result.prompt_tokens,
                candidates_token_count=service_result.candidates_tokens,
                total_token_count=service_result.total_tokens,
                question_id=question.id
            )
            crud.create_request_log(db=db, log=log_entry)
            print(f"Successfully created request log for question ID {question.id}")
        else:
            print(f"Failed to get evaluations for question ID {question.id}")
        print("turu dulu 2 detik")
        time.sleep(2)
    print("Subject evaluation task finished.")

@app.post("/evaluate/subject/{subject_id}", status_code=202)
def trigger_subject_evaluation(subject_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Triggers a background task to evaluate all answers for all questions in a specific subject.
    """
    background_tasks.add_task(run_evaluation_for_subject_and_update_db, subject_id, db)
    return {
        "message": f"Evaluation process for subject {subject_id} started in the background. The `status` field in the `task_answers` table will be updated upon completion."
    }

