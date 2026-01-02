# Production Ready RAG Project

## Overview
This project implements a scalable and modular Retrieval-Augmented Generation (RAG) pipeline.

## Project Structure
- `src/rag_engine/`: Contains the core logic for the RAG process.
  - `ingestion.py`: Document loading and text splitting.
  - `embedding.py`: Text to vector conversion.
  - `retrieval.py`: vector store interaction and similarity search.
  - `generation.py`: Context construction and LLM prompting.
- `config/`: centralized configuration.
- `data/`: Data storage layers (raw, processed, vectors).
- `logs/`: Application logs.
