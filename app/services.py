import os
import json
import time
from typing import List, Optional
from google import genai
from google.genai import types
from . import schemas
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def configure_ai_client():
    """
    Loads the Gemini API key from environment variables.
    The genai library will automatically use this when a client is created.
    """
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is not set in the environment variables.")

# Call configuration at module level to ensure API key is loaded.
try:
    configure_ai_client()
except ValueError as e:
    logging.error(e)


def evaluate_answers_with_ai(payload: schemas.EvaluationPayload) -> Optional[schemas.ServiceEvaluationResult]:
    """
    Sends a question and its answers to the Google Gemini API for evaluation in chunks,
    following the specified client, model, and streaming request pattern.
    
    Args:
        payload: A Pydantic schema object containing the question, preferred answer,
                 and a list of answers to evaluate.
                 
    Returns:
        A Pydantic schema object with the AI's evaluation for each answer, or None on failure.
    """
    try:
        # 1. Initialize the client.
        client = genai.Client()

        # 2. Define the system instruction for the AI model.
        system_instruction_text = """
            You are a highly intelligent AI model. Your task is to evaluate if the given answer to a question is correct or not. Return the result in JSON format as described below.
            Input Payload:
            {
            "question": "The original question that needs to be evaluated",
            "preferred_answer": "A preferred answer given by the user as reference"
            "answers": [
                {
                "task_answer_id": "unique identifier for this answer",
                "answer": "the text of the provided answer"
                },
                {
                "task_answer_id": "another unique identifier",
                "answer": "another provided answer"
                }
            ]
            }

            Desired Output:
            For each provided answer, determine if it correctly addresses the question. Return the result in the following JSON format:
            [
            {
                "task_answer_id": "unique identifier for this answer",
                "correct": true
            },
            ]

            Instructions:
            Analyse the provided question and each corresponding answer.
            For each answer, decide if it correctly answers the question.
            Respond with a JSON array of objects, where each object contains:
            task_answer_id: The identifier for the answer being evaluated.
            correct: A boolean indicating whether the answer is correct (true) or incorrect (false).
            """

        # 3. Define the few-shot learning example.
        few_shot_user_text = """{
                "question": "Keterampilan apa yang sangat penting yang harus dipelajari seseorang agar bisa sukses di dunia saat ini?",
                "preferred_answer": "Adaptasi, komunikasi, koneksi",
                "answers": [
                    {
                    "task_answer_id": "550e8400-e29b-41d4-a716-446655440000",
                    "answer": "Kemampuan beradaptasi dengan cepat terhadap perubahan teknologi sangat penting di dunia saat ini. Dunia kerja terus berkembang dengan cepat, dan individu yang mampu belajar teknologi baru akan tetap relevan."
                    },
                    {
                    "task_answer_id": "550e8400-e29b-41d4-a716-446655440002",
                    "answer": "Memiliki hewan peliharaan seperti kucing adalah keterampilan utama untuk sukses di dunia saat ini. Hewan peliharaan bisa menjadi teman yang baik, tapi bukan faktor utama untuk kesuksesan."
                    }
                ]
            }
        """
        few_shot_model_text = """```json
            [
            {
                "task_answer_id": "550e8400-e29b-41d4-a716-446655440000",
                "correct": true
            },
            {
                "task_answer_id": "550e8400-e29b-41d4-a716-446655440001",
                "correct": true
            },
            {
                "task_answer_id": "550e8400-e29b-41d4-a716-446655440002",
                "correct": false
            }
            ]
        ```"""

        # --- Logic for chunking and processing ---
        all_answers = payload.answers
        chunk_size = 10
        aggregated_evaluations: List[schemas.AIEvaluationResponse] = []
        total_duration = 0.0
        total_prompt_tokens = 0
        total_candidates_tokens = 0
        total_tokens = 0

        logging.info(f"Received {len(all_answers)} answers. Processing in chunks of {chunk_size}.")

        for i in range(0, len(all_answers), chunk_size):
            chunk_of_answers = all_answers[i:i + chunk_size]
            chunk_number = (i // chunk_size) + 1
            logging.info(f"Processing chunk {chunk_number} with {len(chunk_of_answers)} answers.")

            # Create a new payload for the current chunk
            chunk_payload = schemas.EvaluationPayload(
                question=payload.question,
                preferred_answer=payload.preferred_answer,
                answers=chunk_of_answers
            )

            contents = [
                # types.Content(role="user", parts=[types.Part.from_text(text=few_shot_user_text)]),
                # types.Content(role="model", parts=[types.Part.from_text(text=few_shot_model_text)]),
                types.Content(role="user", parts=[types.Part.from_text(text=chunk_payload.model_dump_json(indent=2))]),
            ]

            generate_content_config = types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="text/plain",
                system_instruction=[types.Part.from_text(text=system_instruction_text)],
            )

            start_time = time.time()
            
            # Make the API call for the chunk
            response = client.models.generate_content(
                model="gemini-2.0-flash-lite",
                contents=contents,
                config=generate_content_config
            )

            end_time = time.time()
            duration = end_time - start_time
            total_duration += duration
            logging.info(f"Gemini API inference for chunk {chunk_number} finished in {duration:.2f} seconds.")

            # Aggregate token usage
            if response.usage_metadata:
                prompt_tokens = response.usage_metadata.prompt_token_count
                candidates_tokens = response.usage_metadata.candidates_token_count
                total_prompt_tokens += prompt_tokens
                total_candidates_tokens += candidates_tokens
                total_tokens += response.usage_metadata.total_token_count
                logging.info(
                    f"Token usage for chunk {chunk_number}: {prompt_tokens} prompt, "
                    f"{candidates_tokens} candidates, {response.usage_metadata.total_token_count} total."
                )
            
            # Clean, parse, and aggregate the response
            if response.text:
                cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
                try:
                    evaluations_data = json.loads(cleaned_text)
                    ai_responses = [schemas.AIEvaluationResponse(**item) for item in evaluations_data]
                    aggregated_evaluations.extend(ai_responses)
                except json.JSONDecodeError:
                    logging.error(f"Failed to decode JSON from AI response for chunk {chunk_number}: {cleaned_text}")
            else:
                logging.warning(f"AI response was empty for chunk {chunk_number}.")

        if aggregated_evaluations:
            # Return a single result object with aggregated data
            return schemas.ServiceEvaluationResult(
                evaluations=aggregated_evaluations,
                duration=total_duration,
                prompt_tokens=total_prompt_tokens,
                candidates_tokens=total_candidates_tokens,
                total_tokens=total_tokens,
            )
        else:
            logging.warning("No evaluations were produced after processing all chunks.")
            return None

    except Exception as e:
        logging.error(f"An error occurred during AI evaluation: {e}", exc_info=True)
        return None