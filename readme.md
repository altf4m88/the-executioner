# AI Answer Evaluator API

An API to evaluate student answers using Google's Generative AI. This project uses a FastAPI backend to process evaluation requests, interacts with a database to store questions and answers, and leverages the Google Gemini API to check if the provided answers are correct.

## Features

  - **Bulk Evaluation**: Trigger an evaluation for all answers in the database.
  - **Subject-Specific Evaluation**: Trigger an evaluation for all answers related to a specific subject.
  - **Background Processing**: Evaluations run as background tasks to prevent blocking the API.
  - **AI-Powered**: Uses Google's Gemini API to determine the correctness of answers.
  - **Database Logging**: Logs request metadata, including token usage and duration, for each evaluation.

## Project Structure

```
.
├── app
│   ├── __init__.py
│   ├── crud.py          # Database Create, Read, Update, Delete operations
│   ├── database.py      # Database engine and session setup
│   ├── main.py          # FastAPI application and endpoints
│   ├── models.py        # SQLAlchemy database models
│   ├── schemas.py       # Pydantic data validation schemas
│   └── services.py      # Logic for interacting with the Google Gemini AI
├── .gitignore
├── readme.md
└── requirements.txt
```

## Prerequisites

  - Python 3.8+
  - pip
  - A running PostgreSQL database instance

## Setup

1.  **Clone the repository**

    ```bash
    git clone <your-repository-url>
    cd <your-repository-name>
    ```

2.  **Create and activate a virtual environment**

      * **macOS/Linux:**

        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

      * **Windows:**

        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```

3.  **Install dependencies**

    Install all the required Python packages from the `requirements.txt` file.

    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables**

    Create a file named `.env` in the root directory of the project. This file will store your secret keys and database connection string. The `.gitignore` file is already configured to ignore this file.

    Your `.env` file should contain the following:

    ```env
    # Your connection string for the PostgreSQL database
    DATABASE_URL="postgresql://user:password@host:port/dbname"

    # Your API key for the Google Gemini API
    GEMINI_API_KEY="your-gemini-api-key"
    ```

      - `DATABASE_URL`: The application uses this to connect to your database.
      - `GEMINI_API_KEY`: The application needs this to send requests to the Gemini API for answer evaluation.

## Running the Application

Once the setup is complete, you can run the FastAPI application using `uvicorn`. The `--reload` flag will automatically restart the server whenever you make changes to the code.

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Endpoints

The interactive API documentation (powered by Swagger UI) will be available at `http://127.0.0.1:8000/docs`.

### Trigger Evaluations

  - #### `POST /evaluate/all-answers`

    Triggers a background task to evaluate all answers for all questions currently in the database.

      - **Response `202 Accepted`**:
        ```json
        {
          "message": "Evaluation process started in the background. The `status` field in the `task_answers` table will be updated upon completion."
        }
        ```

  - #### `POST /evaluate/subject/{subject_id}`

    Triggers a background task to evaluate all answers for questions belonging to a specific subject.

      - **Path Parameter**:
          - `subject_id` (UUID): The unique identifier for the subject.
      - **Response `202 Accepted`**:
        ```json
        {
          "message": "Evaluation process for subject {subject_id} started in the background. The `status` field in the `task_answers` table will be updated upon completion."
        }
        ```

### View Evaluation Results

  - #### `GET /answers/all`

    Retrieves the current evaluation status of all answers that have been processed by the AI.

      - **Response `200 OK`**:
        ```json
        [
          {
            "task_answer_id": "uuid-of-the-answer",
            "correct": true
          },
          {
            "task_answer_id": "another-uuid-of-an-answer",
            "correct": false
          }
        ]
        ```
