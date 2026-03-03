"""Memory engine application services.

T-030: MemorySearchService — hybrid vector + full-text search
T-031: MemorySaveService — sync persist + async embedding enqueue
T-033: ConstitutionIngestService — RFC 2119 rule ingest + versioning
T-034: ConstitutionVersionGate — block skill execution until indexed

DEPRECATED: The flat memory engine (MemorySearchService, MemorySaveService) is
superseded by the knowledge graph services (GraphSearchService, GraphWriteService).
Will be removed in v2.0. Use pilot_space.application.services.memory.graph_search_service
and pilot_space.application.services.memory.graph_write_service instead.
"""
