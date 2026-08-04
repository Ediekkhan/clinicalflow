# Deterministic Clinical Knowledge Graph

## Architecture decision

Neo4j is an optional, auxiliary clinical-ontology service. PostgreSQL remains the system of record for tenants, patients, tickets, providers, slots, and appointments. This avoids split ownership of transactional data and lets the application continue safely when Neo4j is unavailable.

The graph contains global, non-patient clinical knowledge only:

- `(:Symptom)-[:INDICATES {weight}]->(:Condition)`
- `(:Condition)-[:ROUTES_TO]->(:Specialty)`
- `(:Condition)-[:HAS_SEVERITY]->(:Urgency)`

No phone number, intake narrative, patient identifier, tenant identifier, ticket, appointment, or other PHI is written to Neo4j.

## Runtime flow

1. The backend extracts supported symptom IDs from the intake text locally.
2. When Neo4j is enabled and healthy, the read-only service runs the parameterized weighted traversal in `backend/app/services/knowledge_graph.py`.
3. The chosen condition, urgency, specialty, and symptom IDs are persisted on the PostgreSQL ticket.
4. If Neo4j is disabled, unreachable, returns no match, or raises an error, the same service returns a conservative deterministic fallback route.
5. Red-flag symptoms such as chest pain, breathing difficulty, and severe bleeding always fall back to `CRITICAL` / Emergency Medicine.

## Local setup

Run the statements in `backend/neo4j/schema.cypher` against a Neo4j database, then configure:

```dotenv
NEO4J_ENABLED=true
NEO4J_URI=neo4j://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=replace-me
NEO4J_DATABASE=neo4j
```

Keep `NEO4J_ENABLED=false` for the pitch deployment unless a managed Neo4j instance has been provisioned and seeded. The fallback is intentional production behavior, not a demo stub.

## Safety and operations

- The application session uses Neo4j read access only.
- Query inputs are parameterized symptom IDs, never raw text.
- A failed graph call marks the integration unavailable for the process lifetime and immediately falls back.
- Expand the ontology by reviewing and versioning the Cypher seed data; do not allow clinical graph edits through public API routes.
- Clinical mappings are decision support and require clinical governance before real-world deployment.
