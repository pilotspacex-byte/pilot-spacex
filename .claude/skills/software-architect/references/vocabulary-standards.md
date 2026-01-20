# Vocabulary Standards Reference

Load this reference when precision in architectural communication is required.

---

## Precise Terminology Mapping

Replace vague language with precise architectural terms.

| Instead of | Use |
|------------|-----|
| "talks to" | "invokes", "publishes to", "queries", "subscribes to" |
| "stores data" | "persists", "caches", "journals", "materializes" |
| "handles errors" | "propagates", "recovers", "compensates", "dead-letters" |
| "scales" | "scales horizontally/vertically", "partitions", "shards", "replicates" |
| "fast" | "P95 latency <Xms", "throughput X req/s", "sub-millisecond" |
| "reliable" | "99.9% available", "MTTR <5min", "zero data loss" |
| "secure" | "encrypted at rest/transit", "RBAC-protected", "audit-logged" |
| "connects" | "integrates via REST/gRPC/Kafka", "synchronizes with" |

---

## Architecture Pattern Vocabulary

### Structural Patterns

| Pattern | When to Use | Key Characteristic |
|---------|-------------|-------------------|
| **Microservices** | Independent scaling, team autonomy | Decoupled deployment |
| **Modular Monolith** | Simpler ops, shared data | Single deployment, logical boundaries |
| **Service Mesh** | Cross-cutting concerns at scale | Sidecar proxy pattern |
| **Sidecar** | Per-service auxiliary functions | Co-located container |
| **Ambassador** | External service abstraction | Proxy to external APIs |
| **Strangler Fig** | Legacy migration | Incremental replacement |
| **Backend for Frontend** | Multiple client types | Client-specific aggregation |

### Behavioral Patterns

| Pattern | When to Use | Key Characteristic |
|---------|-------------|-------------------|
| **CQRS** | Read/write asymmetry | Separate read/write models |
| **Event Sourcing** | Full audit trail needed | Events as source of truth |
| **Saga** | Distributed transactions | Compensating transactions |
| **Choreography** | Loosely coupled services | Event-driven coordination |
| **Orchestration** | Complex workflows | Central coordinator |
| **Pub/Sub** | Fan-out messaging | Decoupled producers/consumers |
| **Request-Reply** | Synchronous needs | Direct response expected |

### Data Patterns

| Pattern | When to Use | Key Characteristic |
|---------|-------------|-------------------|
| **Repository** | Data access abstraction | Collection-like interface |
| **Unit of Work** | Transaction management | Track changes, batch commit |
| **Event Store** | Event sourcing persistence | Append-only event log |
| **Materialized View** | Query optimization | Pre-computed read model |
| **CDC (Change Data Capture)** | Data synchronization | Stream database changes |
| **Outbox** | Reliable event publishing | Transactional event capture |

### Resilience Patterns

| Pattern | When to Use | Key Characteristic |
|---------|-------------|-------------------|
| **Circuit Breaker** | Prevent cascade failures | Fail fast when downstream failing |
| **Bulkhead** | Isolation | Resource partitioning |
| **Retry with Backoff** | Transient failures | Exponential delay |
| **Timeout** | Prevent hanging | Bounded wait time |
| **Fallback** | Graceful degradation | Default behavior on failure |
| **Dead Letter Queue** | Unprocessable messages | Quarantine for analysis |
| **Idempotency** | Safe retries | Same result on repeat |

### Domain Patterns (DDD)

| Pattern | When to Use | Key Characteristic |
|---------|-------------|-------------------|
| **Bounded Context** | Domain boundaries | Explicit model scope |
| **Aggregate** | Consistency boundary | Transactional unit |
| **Entity** | Identity-based object | Mutable, tracked by ID |
| **Value Object** | Immutable data | Equality by value |
| **Domain Event** | State transitions | Past-tense naming |
| **Anti-Corruption Layer** | Legacy integration | Translation boundary |
| **Domain Service** | Cross-aggregate logic | Stateless operations |

---

## Quality Attributes Taxonomy (ISO 25010)

When discussing non-functional requirements, use this structure with specific metrics.

| Category | Attributes | Metrics | Example Targets |
|----------|------------|---------|-----------------|
| **Performance** | Latency, Throughput, Utilization | P50/P95/P99, req/s, CPU%, Memory% | P95 <100ms, 10k req/s |
| **Reliability** | Availability, Fault Tolerance, Recoverability | Uptime %, MTBF, MTTR, RPO, RTO | 99.9%, MTTR <5min |
| **Security** | Confidentiality, Integrity, AuthN, AuthZ | CVE count, Patch time, Audit % | Zero critical CVE, 24h patch |
| **Scalability** | Elasticity, Load Handling, Capacity | Max concurrent, Scale time, Cost | 100k concurrent, <2min scale |
| **Maintainability** | Modularity, Testability, Analyzability | Complexity, Coverage %, Change fail | <10 complexity, >95% coverage |
| **Operability** | Deployability, Observability, Configurability | Deploy frequency, MTTD, Drift | Daily deploy, <1min MTTD |

---

## Uncertainty Expression Guide

Match confidence level to expression style.

| Confidence | Expression Pattern | Example |
|------------|-------------------|---------|
| **High** (established patterns) | Direct statement, no qualifier | "Use repository pattern for data access." |
| **Medium** (context-dependent) | Conditional recommendation | "For read-heavy loads, CQRS is appropriate. For simple CRUD, standard repository suffices." |
| **Low** (novel/complex) | Investigation statement | "This requires investigation. Key factors: [X, Y, Z]. Initial lean: A because [reason]." |
| **Unknown** | Information request | "Insufficient information to recommend. Need: [specific questions]." |

---

## Response Depth Calibration

Match response depth to user signal.

| User Signal | Response Depth |
|-------------|----------------|
| "Quick thoughts on..." | 2-3 bullet points, no diagrams |
| "How should we..." | Design proposal with key decisions |
| "Evaluate options for..." | Full comparison with weighted scoring |
| "Review this architecture..." | Comprehensive analysis with findings matrix |
| `--ultrathink` or `--deep` | Maximum depth: all considerations, edge cases, alternatives |
| `--quick` | Concise, key points only |
