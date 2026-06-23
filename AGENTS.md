# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## First Read

Before changing graph, pipeline, MCP, or frontend behavior, read `docs/ARCHITECTURE.md` first. It captures the current implementation boundary: common-sense graph and Graphiti news graph are separated, connected through anchors, and browser-friendly news graph views are produced through `NewsProjection` rather than by merging dynamic news back into the stable common graph.

## Project Overview

智链机器人 (Zhilian Robot) is an AI-powered industrial chain knowledge graph construction platform. It uses DeepSeek LLM for intelligent data collection, NLP analysis (entity recognition + relationship extraction), and interactive D3.js force-directed graph visualization.

## Architecture

**Microservices architecture with Docker Compose orchestration (9 containers):**

- **Frontend**: React 18 + Vite + Ant Design (dark theme) + D3.js, served via Nginx on port 80
- **Backend**: FastAPI + Python 3.9, port 8000
- **Task Processing**: Celery worker + Celery Beat (scheduler) + Flower (monitoring on port 5555)
- **Data Storage**:
  - Neo4j (port 7474/7687) - Knowledge graph storage
  - MongoDB (port 27017) - Articles and RSS data
  - MySQL (port 3307) - Task configuration
  - Redis (port 6379) - Celery broker + cache
  - MinIO (port 9000/9100) - Object storage

All services communicate via Docker bridge network `zhilian-network`.

## Development Commands

### Docker Operations

```bash
docker-compose up -d                    # Start all 9 containers
docker-compose down                     # Stop all services
docker-compose logs -f <service>        # View logs (backend, frontend, celery-worker)
docker-compose restart <service>        # Restart specific service
docker-compose build --no-cache <service>  # Rebuild container
docker exec -it zhilian-backend bash    # Enter backend container
```

### Frontend Development

```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Development server
npm run build        # Production build
npm run lint         # ESLint check
```

### Backend Development

```bash
cd backend
pip install -r requirements.txt    # Install dependencies
```

## Key Directories

|            Path            |                          Purpose                           |
|----------------------------|------------------------------------------------------------|
| `backend/app/api/`         | FastAPI route handlers                                     |
| `backend/app/nlp/`         | DeepSeek LLM integration for NER and relation extraction   |
| `backend/app/analytics/`   | Momentum calculation and anomaly detection                 |
| `backend/app/crawler/`     | RSS feeds and news crawlers (Scrapy-based)                 |
| `backend/app/tasks/`       | Celery async tasks                                         |
| `backend/app/services/`    | Business logic (Neo4j graph service, entity normalization) |
| `backend/app/database/`    | Database connections (Neo4j/MongoDB/Redis)                 |
| `frontend/src/pages/`      | React page components                                      |
| `frontend/src/components/` | Reusable UI components including D3ForceGraph              |
| `frontend/src/services/`   | API client services                                        |

## Service Access

|    Service    |          URL          |     Credentials     |
|---------------|-----------------------|---------------------|
| Frontend      | http://localhost      | -                   |
| Backend API   | http://localhost:8000 | -                   |
| Neo4j Browser | http://localhost:7474 | neo4j / password123 |
| Flower        | http://localhost:5555 | -                   |
| MinIO Console | http://localhost:9100 | See .env            |

## Environment Configuration

Environment variables are in `.env` (use `.env.example` as template). Key variables:
- `OPENAI_API_KEY` - DeepSeek API key (in `backend/.env`)
- Neo4j, MongoDB, MySQL, Redis connection settings
- MinIO credentials

## Scheduled Tasks (Celery Beat)

- **Daily 02:00** - Full news crawling
- **Every 6 hours** - RSS incremental updates
- **Weekly Monday 03:00** - Clean 30-day old data
