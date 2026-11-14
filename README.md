# Palm Mind RAG Backend

A modular FastAPI backend for document-based question answering and interview booking.

## Features

- Upload `.pdf` and `.txt` documents.
- Split text using fixed-size or recursive-paragraph chunking.
- Generate Google Gemini embeddings and store document chunks in Qdrant.
- Answer questions using retrieved document excerpts and Google Gemini.
- Keep recent chat history and booking drafts in Redis.
- Gather interview details over multiple chat messages and save confirmed bookings in SQLite.

## Technology

- Python 3.10+
- FastAPI and Uvicorn
- SQLite and SQLAlchemy
- Qdrant
- Redis
- Google Gemini API

## Prerequisites

Install these before starting:

- Python 3.12 recommended
- Git
- Docker Desktop, running
- A Google Gemini API key

Postman is optional. You can also try the endpoints using FastAPI's interactive docs at `http://127.0.0.1:8000/docs`.

## Get the project

Clone the repository and enter its folder:

```bash
git clone https://github.com/NayakYadav1/RAG-backend.git
cd RAG-backend
```

## Set up Python

These commands are for Git Bash:

```bash
py -3.12 -m venv venv
source venv/Scripts/activate
python --version
```

The terminal prompt should show `(venv)`. Use this environment whenever you install dependencies, run the API, or run tests.

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Configure environment variables

Create your local environment file:

```bash
cp .env.example .env
```

Open `.env` and set your own Gemini API key:

```dotenv
GEMINI_API_KEY=your_private_api_key
```

Do not share or commit `.env`. Never put a real API key in the README or `.env.example`.

The project specification sets `gemini-2.5-flash` as the default chat model. If that model is unavailable to your account, set `GEMINI_CHAT_MODEL` in your local `.env` to a model available to your Gemini API key. This project was tested with `gemini-3.5-flash`.

The other settings have local defaults:

```dotenv
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=company_documents
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./rag_backend.db
CHAT_HISTORY_TTL_SECONDS=86400
```

## Start Qdrant and Redis

From the repository folder:

```bash
docker compose up -d
docker compose ps
```

Qdrant is available at `http://localhost:6333`; Redis is available at `localhost:6379`.

To stop the containers later:

```bash
docker compose down
```

Docker volumes preserve their data between restarts.

## Initialize the database

Create the SQLite tables:

```bash
python -m app.db.init_db
```

The SQLite database file is created locally and should not be committed.

## Run the API

Start the development server:

```bash
python -m uvicorn app.main:app --reload
```

Keep this terminal open while using the API.

- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Document upload: `POST /api/v1/documents/upload`
- Chat and interview booking: `POST /api/v1/chat`

## Upload a document

In Postman, create a `POST` request to:

```text
http://127.0.0.1:8000/api/v1/documents/upload
```

Choose **Body → form-data** and add:

| Key | Type | Value |
|---|---|---|
| `file` | File | Choose a `.pdf` or `.txt` file |
| `chunking_strategy` | Text | `fixed_size` or `recursive_paragraph` |

A successful response includes the document ID, filename, chunking strategy, chunk count, and upload time. Uploading calls Gemini for embeddings and stores vectors in Qdrant.

## Ask a question

Send a `POST` request to:

```text
http://127.0.0.1:8000/api/v1/chat
```

Choose **Body → raw → JSON** and send:

```json
{
  "message": "What does the uploaded document say?"
}
```

The response contains an `answer` and a `session_id`. Keep the session ID to continue the conversation:

```json
{
  "session_id": "PASTE_SESSION_ID_HERE",
  "message": "Can you summarize that briefly?"
}
```

Answers are based on retrieved document excerpts. If the uploaded documents do not contain the answer, the assistant should say so.

## Book an interview

Interview booking uses the same chat endpoint and session ID.

1. Ask to book an interview:

   ```json
   {
     "message": "I want to book an interview"
   }
   ```

2. Copy the returned `session_id`.
3. Send the requested details in follow-up messages, always reusing that session ID. The assistant may ask for your name, email, date, and time.
4. Review the complete booking summary.
5. Send an explicit confirmation, such as `Yes, confirm`.
6. The booking is saved to SQLite only after confirmation.

Use an unambiguous date such as `2026-12-01` and 24-hour time such as `14:30`. The current database model stores a date and local time without a timezone.

## Run tests

With the virtual environment active:

```bash
python -m unittest discover -s tests -v
```

## Project layout

```text
app/
  api/routes/  FastAPI endpoints
  core/        Application configuration
  db/          SQLAlchemy database setup
  models/      SQLAlchemy database models
  schemas/     Pydantic request and response schemas
  services/    Document processing, embeddings, vector search, RAG, and booking
tests/         Automated tests
docker-compose.yml
requirements.txt
```

## Troubleshooting

- **`ModuleNotFoundError` for a project package:** Check that the terminal prompt shows `(venv)`. Activate it with `source venv/Scripts/activate`, then install dependencies with `python -m pip install -r requirements.txt`.
- **Gemini authentication or model error:** Check your local `.env`, confirm the key is valid, and choose a chat model available to your API account. Never paste the key into an issue or chat.
- **Qdrant or Redis connection error:** Confirm Docker Desktop is running and check `docker compose ps`.
- **Slow chat response:** A normal RAG request calls Gemini for a query embedding and then for answer generation. Network latency and model response time can make requests take several seconds or longer.
- **Scanned PDF has no extracted text:** This project extracts embedded PDF text; it does not currently perform OCR.