"""RAG pipeline for Pilot Space.

Components:
- embeddings: Embedding generation using OpenAI text-embedding-3-large
- retriever: Similarity search using pgvector with HNSW index
- indexer: Background worker for embedding generation

Configuration:
- Embedding dimensions: 3072 (text-embedding-3-large)
- Chunk size: 512 tokens with 50 token overlap
- Similarity threshold: 0.7 for duplicate detection
"""
