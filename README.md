# Smart Resume Screener

A full-stack application designed to parse, screen, and analyze resumes using natural language processing (NLP), vector searches, and LLM APIs.

## Architecture

*Placeholder: A detailed system architecture diagram and description will be added here later.*

## Project Structure

- `src/` - FastAPI backend application code
  - `routers/` - API endpoints and routing logic
  - `services/` - Business logic and processing helper modules
  - `models/` - SQLAlchemy models defining the DB schema
  - `schemas/` - Pydantic validation schemas
- `frontend/` - React Vite TypeScript frontend application code
- `docker-compose.yml` - Docker compose configuration for Postgres and local backend development
- `Dockerfile` - Backend containerization file
- `pyproject.toml` - Project dependency management configuration

## Getting Started

### Backend & Database (Docker)

1. Copy the environment variables:
   ```bash
   cp .env.example .env
   ```
2. Start the local developer environment with Docker Compose:
   ```bash
   docker compose up --build
   ```
3. The API will be available at http://localhost:8000. Interactive documentation (Swagger) can be accessed at http://localhost:8000/docs.

### Frontend (React + Vite)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Spin up the dev server:
   ```bash
   npm run dev
   ```
