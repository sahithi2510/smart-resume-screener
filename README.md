````markdown
# Smart Resume Screener

An AI-powered resume screening and candidate matching system that analyzes resumes against job descriptions, performs semantic candidate retrieval, and generates explainable candidate scores.

---

## 🚀 Overview

Smart Resume Screener automates the initial stages of the recruitment process by combining:

- Resume document parsing
- Structured resume information extraction
- Sentence Transformer embeddings
- PostgreSQL with pgvector
- Semantic similarity-based candidate retrieval
- Gemini-powered job description analysis
- Rubric-based AI candidate scoring
- React-based recruiter dashboard

The system follows a **two-stage candidate matching architecture**.

```text
                    Job Description
                           │
                           ▼
                 ┌──────────────────┐
                 │   JD Extraction  │
                 │      Gemini      │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Job Embedding    │
                 │ Sentence         │
                 │ Transformers     │
                 └────────┬─────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ PostgreSQL         │
                │ + pgvector         │
                │ Semantic Search    │
                └─────────┬──────────┘
                          │
                     Top-N Candidates
                          │
                          ▼
                 ┌──────────────────┐
                 │ Gemini LLM       │
                 │ Candidate Scoring│
                 └────────┬─────────┘
                          │
                          ▼
                   Ranked Candidates
````

---

## ✨ Features

### Resume Processing

* Upload PDF/DOCX resumes
* Extract resume text
* Parse structured candidate information
* Generate semantic embeddings
* Store resume information and embeddings in PostgreSQL

### Semantic Candidate Matching

The system converts resumes and job descriptions into vector representations using Sentence Transformers.

These embeddings are stored in PostgreSQL using the `pgvector` extension.

Candidate retrieval uses **cosine similarity** to identify the most relevant resumes.

### Two-Stage Candidate Screening

#### Stage 1 — Semantic Pre-filtering

The job description is converted into an embedding and compared with stored resume embeddings.

Only the most relevant candidates are selected for detailed evaluation.

#### Stage 2 — AI Scoring

The selected candidates are evaluated by Gemini using a structured scoring rubric.

This reduces unnecessary LLM calls and makes the system more scalable.

### Explainable Candidate Scoring

Each candidate receives:

* Overall match score
* Skills match score
* Experience relevance score
* Education fit score
* Domain keyword overlap score
* Matched skills
* Missing required skills
* AI-generated justification
* Confidence score
* High-variance flag
* Individual scoring run results

---

# 🛠️ Tech Stack

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* Recharts

## Backend

* Python
* FastAPI
* Uvicorn
* Pydantic
* SQLAlchemy
* Alembic

## Database

* PostgreSQL
* pgvector

## AI / NLP

* Google Gemini API
* Sentence Transformers
* Vector embeddings
* Cosine similarity search

## Development

* Docker
* Docker Compose
* Git
* GitHub

---

# 📁 Project Structure

```text
smart-resume-screener/
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.tsx
│   │
│   ├── public/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── tsconfig.json
│
├── src/
│   ├── models/
│   │   └── resume.py
│   │
│   ├── routers/
│   │   ├── resume.py
│   │   └── match.py
│   │
│   ├── schemas/
│   │   ├── job.py
│   │   └── scoring.py
│   │
│   ├── services/
│   │   ├── parser.py
│   │   ├── extractor.py
│   │   ├── embeddings.py
│   │   └── scorer.py
│   │
│   ├── config.py
│   ├── database.py
│   └── main.py
│
├── alembic/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── .env.example
├── .gitignore
└── README.md
```

---

# 🔌 API Endpoints

## Health Check

```http
GET /
```

Returns the backend status and API version.

---

## Resume Upload

```http
POST /resumes/upload
```

Uploads and processes a resume.

Processing pipeline:

```text
Resume
  ↓
Document Parser
  ↓
Structured Information Extraction
  ↓
Embedding Generation
  ↓
PostgreSQL + pgvector
```

Example successful response:

```json
{
  "id": 1,
  "source_filename": "resume.pdf",
  "message": "Resume uploaded and processed successfully"
}
```

---

## Candidate Pre-filtering

```http
POST /match/prefilter
```

Retrieves the top-N candidates using vector similarity.

Example request:

```json
{
  "required_skills": [
    "Java",
    "Python",
    "Data Structures and Algorithms",
    "SQL",
    "REST APIs"
  ],
  "preferred_skills": [
    "Spring Boot",
    "PostgreSQL",
    "React",
    "Docker"
  ],
  "min_years_experience": 0,
  "education_requirement": "Bachelor's"
}
```

---

## Candidate Scoring

```http
POST /match/score
```

Runs the complete candidate matching pipeline.

```text
Raw Job Description
        ↓
LLM Job Description Extraction
        ↓
Job Embedding
        ↓
pgvector Pre-filtering
        ↓
Top-N Candidates
        ↓
LLM Rubric-based Scoring
        ↓
Ranked Candidates
```

Example request:

```json
{
  "job_description_text": "We are looking for a Software Engineer with strong Java, SQL, DSA and REST API skills...",
  "top_n": 5
}
```

---

# 📊 Scoring Rubric

Candidates are evaluated across four categories:

| Category               | Weight |
| ---------------------- | -----: |
| Skills Match           |    40% |
| Experience Relevance   |    30% |
| Education Fit          |    15% |
| Domain Keyword Overlap |    15% |

The final score is calculated on a **0–10 scale**.

### Formula

```text
Overall Score =
    (Skills Match × 0.40)
  + (Experience Relevance × 0.30)
  + (Education Fit × 0.15)
  + (Domain Keyword Overlap × 0.15)
```

---

# 🧠 AI Scoring and Variance Detection

The scoring service performs multiple scoring runs for a candidate.

If the scoring runs differ significantly, the candidate is flagged for human review.

```text
Candidate Resume
       │
       ├──────────────► Gemini Run 1
       │
       └──────────────► Gemini Run 2
                            │
                            ▼
                     Compare Scores
                            │
                 ┌──────────┴──────────┐
                 │                     │
          Difference ≤ 1.0       Difference > 1.0
                 │                     │
                 ▼                     ▼
             Normal             Human Review Flag
```

The `high_variance` field indicates whether the scoring runs disagreed by more than 1 point.

---

# ⚙️ Local Setup

## Prerequisites

* Python 3.12+
* Node.js
* npm
* Docker Desktop
* Git

## 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/smart-resume-screener.git
cd smart-resume-screener
```

## 2. Configure Environment Variables

Create `.env` from `.env.example`.

### Windows

```cmd
copy .env.example .env
```

Configure the required values:

```env
DATABASE_URL=your_database_url
GEMINI_API_KEY=your_gemini_api_key
```

**Never commit `.env` to GitHub.**

---

## 3. Start the Backend

From the project root:

```bash
docker compose up --build
```

Backend:

```text
http://localhost:8000
```

---

## 4. Open API Documentation

FastAPI Swagger UI:

```text
http://localhost:8000/docs
```

---

## 5. Start the Frontend

Open another terminal:

```cmd
cd frontend
npm install
npm run dev
```

Vite will provide the frontend URL, usually:

```text
http://localhost:5173
```

---

## 6. Production Build

```cmd
cd frontend
npm run build
```

---

# 🔄 Complete Application Flow

```text
                    Recruiter
                       │
                       ▼
                React Frontend
                       │
                       ▼
                 FastAPI API
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
       Resume Upload        Job Description
             │                   │
             ▼                   ▼
       Document Parser       Gemini Extraction
             │                   │
             ▼                   ▼
      Resume Extraction      Job Embedding
             │                   │
             ▼                   │
     Resume Embedding            │
             │                   │
             └─────────┬─────────┘
                       ▼
                PostgreSQL
                  + pgvector
                       │
                       ▼
              Semantic Search
                       │
                       ▼
                 Top-N Resumes
                       │
                       ▼
                 Gemini Scoring
                       │
                       ▼
              Ranked Candidates
                       │
                       ▼
                React Dashboard
```

---

# 🎯 Why Two-Stage Matching?

Sending every resume directly to an LLM can be expensive and slow.

Instead, the system first uses vector similarity to identify the most relevant candidates.

```text
1000 Resumes
     ↓
Vector Similarity Search
     ↓
Top 20 Candidates
     ↓
LLM Evaluation
     ↓
Ranked Results
```

This approach improves:

* Scalability
* Response efficiency
* LLM usage
* Cost control

---

# ⚠️ Current Limitations

* Gemini API availability depends on the configured API quota.
* AI scoring requires a valid Gemini API key.
* The frontend depends on the FastAPI backend being available.
* Candidate scoring is limited to the configured `top_n`.
* Resume parsing accuracy depends on document quality and format.
* The current version is intended as a functional prototype.

---

# 🚧 Future Improvements

* Recruiter authentication and authorization
* Resume management dashboard
* Job description management
* Batch resume upload
* Candidate filtering and sorting
* Advanced recruiter analytics
* Persistent scoring history
* Background processing for large resume batches
* Support for additional LLM providers
* Cloud deployment
* Automated email notifications
* Human-in-the-loop review workflow
* Improved resume parsing
* Advanced candidate ranking

---

# 📌 Project Status

**Functional Prototype**

### Implemented

* ✅ React frontend
* ✅ TypeScript
* ✅ Vite
* ✅ Tailwind CSS
* ✅ FastAPI backend
* ✅ Resume upload API
* ✅ Resume document parsing
* ✅ Structured resume extraction
* ✅ Sentence Transformer embeddings
* ✅ PostgreSQL integration
* ✅ pgvector integration
* ✅ Semantic candidate pre-filtering
* ✅ Gemini-based JD extraction
* ✅ Gemini-based candidate scoring
* ✅ Dual-run scoring
* ✅ High-variance detection
* ✅ FastAPI Swagger documentation
* ✅ Docker configuration
* ✅ Alembic database migrations

---

# 🛡️ Security

Sensitive credentials are stored using environment variables.

Do not commit:

```text
.env
API keys
Database passwords
Private credentials
```

Use `.env.example` as the configuration template.

---

# 👩‍💻 Author

**Sahithi Dhanakudharam**

B.Tech — Computer Science and Engineering

---

# 📄 License

This project is developed for educational and portfolio purposes.

```
```
