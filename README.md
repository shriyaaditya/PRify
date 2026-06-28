# PRify: AI Multi-Agent GitHub Code Review System

## Overview
An AI-powered multi-agent GitHub Pull Request review system built using LangGraph. It listens to GitHub PR webhooks, retrieves context using RAG, executes specialized review agents (security, performance, architecture, testing), aggregates responses through a consensus agent, and publishes comments back to GitHub.

## Architecture
- **Frontend**: Next.js (App Router), TypeScript, Tailwind CSS, shadcn/ui.
- **Backend**: FastAPI, Python 3.12, LangGraph, SQLAlchemy.
- **Vector DB**: Qdrant.
- **Database**: PostgreSQL.

## Folder Structure
- `/frontend`: Next.js web application.
- `/backend`: FastAPI backend and AI agents.
- `/docker`: Docker compose and related configurations.
- `/docs`: Documentation.
- `/scripts`: Utility scripts.

## Getting Started

### Installation
1. Clone the repository.
2. Copy `.env.example` to `.env` and fill in the values.

### Running Locally
You can run the application locally or via Docker.

#### Docker Instructions
Run the entire stack:
```sh
docker-compose up -d
```

#### Environment Variables
See `.env.example` for required variables.
