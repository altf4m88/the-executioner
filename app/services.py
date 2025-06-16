import os
import json
import time
from typing import List
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


def evaluate_answers_with_ai(payload: schemas.EvaluationPayload) -> List[schemas.AIEvaluationResponse]:
    """
    Sends a question and its answers to the Google Gemini API for evaluation,
    following the specified client, model, and streaming request pattern.
    
    Args:
        payload: A Pydantic schema object containing the question, preferred answer,
                 and a list of answers to evaluate.
                 
    Returns:
        A list of Pydantic schema objects with the AI's evaluation for each answer.
    """
    try:
        # 1. Initialize the client. It will automatically use the API key
        #    from the environment variables loaded by configure_ai_client().
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

        # 4. Construct the `contents` list for the API call.
        contents = [
            # types.Content(role="user", parts=[types.Part.from_text(text=few_shot_user_text)]),
            # types.Content(role="model", parts=[types.Part.from_text(text=few_shot_model_text)]),
            # The final user message contains the actual data to be evaluated.
            types.Content(role="user", parts=[types.Part.from_text(text=payload.model_dump_json(indent=2))]),
        ]

        # 5. Define the generation configuration.
        generate_content_config = types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="text/plain",
            system_instruction=[types.Part.from_text(text=system_instruction_text)],
        )

        logging.info(f"Sending request to Gemini API for {len(payload.answers)} answers.")
        start_time = time.time()

        # 6. Make the streaming API call.
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=contents,
            config=generate_content_config
        )

        end_time = time.time()
        duration = end_time - start_time
        logging.info(f"Gemini API inference finished in {duration:.2f} seconds.")

        if response.usage_metadata:
            logging.info(
                f"Token usage: {response.usage_metadata.prompt_token_count} prompt tokens, "
                f"{response.usage_metadata.candidates_token_count} candidates tokens, "
                f"{response.usage_metadata.total_token_count} total tokens."
            )
    
        # 7. Clean and parse the aggregated response.
        if response.text:
            cleaned_text = response.text.strip().replace("```json", "").replace("```", "").strip()
            evaluations_data = json.loads(cleaned_text)
            ai_responses = [schemas.AIEvaluationResponse(**item) for item in evaluations_data]
            
            # Package everything into the result object
            return schemas.ServiceEvaluationResult(
                evaluations=ai_responses,
                duration=duration,
                prompt_tokens=response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
                candidates_tokens=response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
                total_tokens=response.usage_metadata.total_token_count if response.usage_metadata else 0,
            )
        else:
            print("AI response was empty.")
            return []

    except Exception as e:
        print(f"An error occurred during AI evaluation: {e}")
        # Return an empty list or raise a custom exception if the API call fails.
        return []
