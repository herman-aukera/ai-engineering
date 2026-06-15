# Diagnóstico arquitectónico del sistema RAG actual

**Branch de trabajo:** `gg-session-09/pre-work`
**Commit base observado:** `e8a2ba0 Add Session 08 to Task 09 readiness bridge`
**Transcripción trazada:** `examples/transcripts/02_ambiguous.txt`
**Fecha de captura:** 2026-06-15
**Estado:** diagnóstico arquitectónico basado en ejecución real del sistema actual.

## Resumen ejecutivo

El sistema actual ya implementa una base sólida de recuperación semántica: puede ingerir presupuestos históricos normalizados, crear chunks estructurales, generar embeddings con `text-embedding-3-small`, persistirlos en PostgreSQL con pgvector y recuperar los chunks más cercanos mediante `POST /search`.

Sin embargo, todavía no es un sistema RAG end-to-end para generar estimaciones desde una transcripción. El flujo implementado termina en retrieval. No hay análisis de intención, extracción de requisitos, reformulación de consulta, selección de evidencias, fase de augmentation ni generación de presupuesto final.

---

## 1. Diagrama de la arquitectura actual

```text
ARQUITECTURA ACTUAL

[Frontend / Cliente]
  Browser / Demo / Script
  examples/transcripts/02_ambiguous.txt
        |
        v
[Business backend FastAPI]
  GET  /health
  POST /embeddings/ingest
  POST /search
  POST /embeddings/compare
  GET  /search/metrics
        |
        v
[AI service actual]
  ingest / embeddings:
    JSONStructuralChunker
      -> OpenAIEmbedder text-embedding-3-small
      -> PersistentEmbeddingIngestionService
      -> DocumentRepository
      -> PostgreSQL + pgvector
         tables: documents, chunks

  search:
    transcript or query
      -> OpenAIEmbedder text-embedding-3-small
      -> SearchService
      -> pgvector cosine distance
      -> top-k chunks

  compare:
    deterministic keyword fake embedder
    learning endpoint only

IMPLEMENTED FLOW ENDS HERE:
  top-k chunks are returned.
  There is no augmentation stage.
  There is no generated estimate.
  There is no RAG quality gate.
```

### Observación

La arquitectura actual tiene las piezas de persistencia y búsqueda semántica, pero el flujo de RAG está incompleto. Actualmente la consulta devuelve chunks históricos; no transforma una transcripción ambigua en una propuesta de estimación.

---

## 2. Trace anotado de una transcripción

Transcripción usada: `examples/transcripts/02_ambiguous.txt`.

### 2.1 Precondición de branch y base técnica

La rama de trabajo fue verificada como:

```text
Current branch:
gg-session-09/pre-work

HEAD:
e8a2ba0 Add Session 08 to Task 09 readiness bridge

Relevant remote tips:
origin/gg-session-09/pre-work -> e8a2ba0
origin/gg-session-08-live-inspired-hardening -> e8a2ba0
origin/gg-session-08-pgvector-search -> 8efd5ea

Lineage check:
YES: live-inspired hardening is ancestor of current HEAD
YES: strict pgvector branch is also ancestor of current HEAD
```

**Observación:** La rama de Task 09 parte de la versión mejorada de Session 08 inspirada en la sesión en vivo. La rama estricta de pgvector también está en la historia, pero la base inmediata es `gg-session-08-live-inspired-hardening`.

### 2.2 Migración y estado de base de datos

Comando ejecutado para migrar:

```bash
cd /workspaces/ai-engineering

docker compose run --rm ai_service uv run alembic current || true
docker compose run --rm ai_service uv run alembic upgrade head
docker compose run --rm ai_service uv run alembic current
```

Resultado relevante:

```text
Running upgrade  -> 0001_session08_pgvector, Create pgvector document and chunk storage for Session 08.
Running upgrade 0001_session08_pgvector -> 0002_session08_hnsw_vector_index, Add HNSW cosine vector index for Session 08 extra-mile search.
0002_session08_hnsw_vector_index (head)
```

Verificación de tablas y extensión:

```bash
cd /workspaces/ai-engineering

docker compose exec postgres psql -U estimator -d estimator -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';"
docker compose exec postgres psql -U estimator -d estimator -c "\dt"
docker compose exec postgres psql -U estimator -d estimator -c "SELECT COUNT(*) AS documents_count FROM documents;"
docker compose exec postgres psql -U estimator -d estimator -c "SELECT COUNT(*) AS chunks_count FROM chunks;"
```

Resultado relevante antes de la ingesta:

```text
vector extension: vector 0.8.2
tables: alembic_version, chunks, documents
documents_count before ingest: 0
chunks_count before ingest: 0
```

**Observación:** La infraestructura de pgvector estaba correctamente creada después de migrar, pero la base de datos empezó vacía. Sin ingesta, `/search` devuelve `results: []`, aunque el endpoint funcione.

### 2.3 Ingesta del corpus histórico de ejemplo

Comando ejecutado:

```bash
cd /workspaces/ai-engineering/estimador-cag

uv run python query_examples.py --base-url http://localhost:8000 --ingest-example-corpus | tee /tmp/session09-query-examples-output.txt
```

Respuesta de ingesta:

```json
{
  "document_id": 1,
  "chunks_created": 4,
  "embedding_dimension": 1536,
  "ingestion_time_ms": 771,
  "_client_elapsed_ms": 778
}
```

Verificación posterior:

```text
documents_count: 1
chunks_count: 4
```

**Observación:** El sistema queda preparado para retrieval con un único presupuesto histórico y cuatro chunks. Esto es suficiente para ejecutar el trace, pero es una base extremadamente pequeña para inferir estimaciones reales.

### 2.4 Vectorización de la transcripción completa

Comando ejecutado para vectorizar la transcripción completa sin cambiar código de producción:

```bash
cd /workspaces/ai-engineering/estimador-cag

uv run python - <<'PY' | tee /tmp/session09-embedding-vector-evidence.txt
import math
from pathlib import Path

from app.embedding_pipeline.embedder import OpenAIEmbedder

transcript = Path("../examples/transcripts/02_ambiguous.txt").read_text(encoding="utf-8")

embedder = OpenAIEmbedder()
vector = embedder.embed_one(transcript)

norm = math.sqrt(sum(float(x) * float(x) for x in vector))

print("embedding_dimension:", len(vector))
print("first_component:", vector[0])
print("last_component:", vector[-1])
print("l2_norm:", norm)
PY
```

Salida capturada:

```text
2026-06-15 16:18:18 [info     ] embedding_batch_completed      chunk_count=1 latency_ms=3391 model=text-embedding-3-small token_count=890
embedding_dimension: 1536
first_component: 0.00624847412109375
last_component: 0.0190277099609375
l2_norm: 1.0003498345455109
```

**Observación:** El sistema puede convertir toda la transcripción en un único vector de 1536 dimensiones. Ese vector representa la transcripción completa como un solo punto semántico, no una estructura de requisitos, componentes, prioridades, incertidumbres o restricciones de negocio.

### 2.5 Búsqueda semántica top-5 con la transcripción completa

Comando ejecutado:

```bash
cd /workspaces/ai-engineering

python - <<'PY' | tee /tmp/session09-search-trace.json
import json
from pathlib import Path
import urllib.error
import urllib.request

transcript = Path("examples/transcripts/02_ambiguous.txt").read_text(encoding="utf-8")

payload = {
    "query": transcript,
    "k": 5,
}

req = urllib.request.Request(
    "http://localhost:8000/search",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8")
        parsed = json.loads(body)
        print(json.dumps(parsed, indent=2, ensure_ascii=False))
except urllib.error.HTTPError as exc:
    print("HTTP_ERROR", exc.code)
    print(exc.read().decode("utf-8"))
except Exception as exc:
    print(type(exc).__name__)
    print(str(exc))
PY
```

Resumen de la respuesta:

```text
query_length: 2853
k: 5
search_time_ms: 181
results_count: 4
embedding_dimension: 1536
first_component: 0.00624847412109375
last_component: 0.0190277099609375
l2_norm: 1.0003498345455109
```

Respuesta cruda completa de `/search`:

```json
{
  "query": "Reunión exploratoria — sin título claro todavía\nCliente: Rubén Castaño (gerente, Casa Castaño — tienda de productos gourmet)\nConsultor: equipo de estimación\nFecha: primera toma de contacto\n\n[00:00:08] Consultor: Buenas, Rubén. Cuéntame, ¿qué os ronda por la cabeza?\n\n[00:00:15] Rubén: Pues mira, es que llevamos dándole vueltas un tiempo y no sé muy bien por dónde\nempezar, por eso os hemos llamado. Tenemos la tienda física de toda la vida, la de mi padre, llevamos\ncon ella desde el noventa y dos. Conservas, vinos, aceite, esas cosas. Y claro, vemos que el mundo va\npor otro lado y que hay que dar el salto, pero no tenemos ni idea de tecnología, ¿eh?, te lo digo ya.\n\n[00:01:02] Consultor: Sin problema, para eso estamos. ¿Qué te gustaría conseguir?\n\n[00:01:09] Rubén: A ver, lo ideal sería vender por internet, eso seguro. Que la gente entre, vea los\nproductos y compre, ¿no? Pero también... mira, mi sobrina, que de esto sabe más que yo, me dice que\nlo importante hoy es fidelizar. Que un cliente que repite vale más que diez que vienen una vez. Y yo\npienso, pues igual algo de puntos, o un club, no sé, que la gente acumule y luego canjee. Eso me\ngustaría. Aunque tampoco quiero liarlo mucho al principio, ¿eh?\n\n[00:02:05] Consultor: Vale. ¿Y cómo te imaginas el día a día gestionándolo?\n\n[00:02:12] Rubén: Pues eso es lo otro. Yo necesito ver qué se vende. Un panel, algo donde yo entre\npor la mañana con el café y vea los pedidos del día, lo que más se mueve, el stock... que ahora lo\nllevo en un cuaderno, te lo juro. Mi mujer me dice que parezco del siglo pasado. Algo visual, con sus\ngráficas, para tomar decisiones. Eso lo veo clarísimo, lo del panel de control.\n\n[00:03:01] Rubén: Ah, y oye, una cosa importante: que la gente pueda pagar con tarjeta, claro. Eso es\nfundamental, que el pago sea fácil y seguro, que no se me vayan en el último paso. He oído que mucha\ngente llena el carrito y luego no paga, y eso no puede ser.\n\n[00:03:40] Consultor: Totalmente. ¿Tenéis volumen previsto, mercados, algo de eso?\n\n[00:03:47] Rubén: Uf, pues no sabría decirte. España de momento, supongo. Aunque un primo en Francia\nme dice que allí los productos españoles se venden solos, así que quién sabe, igual más adelante.\nPero no me hagas mucho caso con eso. Y mira, también pensaba... no sé si es mucho pedir, pero estaría\nbien mandar un correo cuando alguien compra, para que sepa que va su pedido. Detalles, ¿sabes? Que el\ncliente se sienta atendido como en la tienda de siempre.\n\n[00:04:35] Rubén: En fin, que tampoco quiero marearos. Que sé que esto es un mundo. Lo que necesito\nes que me digáis vosotros, que sois los que sabéis, qué se puede hacer y más o menos cuánto cuesta.\nYo de presupuestos de software ni idea, ¿eh? Decidme un número y vemos.\n\n[00:05:02] Consultor: Tranquilo, Rubén, lo recogemos y te volvemos con una propuesta. Gracias.",
  "k": 5,
  "search_time_ms": 181,
  "filters_applied": {},
  "results": [
    {
      "chunk_id": 4,
      "document_id": 1,
      "chunk_type": "budget_component",
      "content": "[Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.]\n[Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]\n\nComponent: Operations dashboard\nDescription: Internal dashboard for operations teams to monitor audit events, integration status, and financial workflow health.\nTech stack: typescript, react\nComplexity: medium\nEstimated hours: 80\nDependencies: INT-001",
      "distance": 0.6812073805009786,
      "metadata": {
        "year": 2024,
        "chunk_id": "BUD-SESSION08-EXAMPLE::UI-001",
        "budget_id": "BUD-SESSION08-EXAMPLE",
        "complexity": "medium",
        "tech_stack": [
          "typescript",
          "react"
        ],
        "client_name": "FintechCorp",
        "token_count": 106,
        "component_id": "UI-001",
        "client_sector": "finance",
        "client_country": "ES",
        "estimated_hours": 80,
        "main_technology": "python"
      }
    },
    {
      "chunk_id": 2,
      "document_id": 1,
      "chunk_type": "budget_component",
      "content": "[Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.]\n[Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]\n\nComponent: External payment provider integration\nDescription: Integration with external banking and payment systems, including webhook handling, retry logic, and audit logging.\nTech stack: python, fastapi, postgresql\nComplexity: medium\nEstimated hours: 120\nDependencies: AUTH-001",
      "distance": 0.701399437355401,
      "metadata": {
        "year": 2024,
        "chunk_id": "BUD-SESSION08-EXAMPLE::INT-001",
        "budget_id": "BUD-SESSION08-EXAMPLE",
        "complexity": "medium",
        "tech_stack": [
          "python",
          "fastapi",
          "postgresql"
        ],
        "client_name": "FintechCorp",
        "token_count": 112,
        "component_id": "INT-001",
        "client_sector": "finance",
        "client_country": "ES",
        "estimated_hours": 120,
        "main_technology": "python"
      }
    },
    {
      "chunk_id": 1,
      "document_id": 1,
      "chunk_type": "budget_component",
      "content": "[Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.]\n[Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]\n\nComponent: JWT authentication API\nDescription: REST API development with JWT authentication, token refresh, role-based authorization, and financial-sector security controls.\nTech stack: python, fastapi, postgresql, redis\nComplexity: high\nEstimated hours: 140\nDependencies: none",
      "distance": 0.7205973391351352,
      "metadata": {
        "year": 2024,
        "chunk_id": "BUD-SESSION08-EXAMPLE::AUTH-001",
        "budget_id": "BUD-SESSION08-EXAMPLE",
        "complexity": "high",
        "tech_stack": [
          "python",
          "fastapi",
          "postgresql",
          "redis"
        ],
        "client_name": "FintechCorp",
        "token_count": 112,
        "component_id": "AUTH-001",
        "client_sector": "finance",
        "client_country": "ES",
        "estimated_hours": 140,
        "main_technology": "python"
      }
    },
    {
      "chunk_id": 3,
      "document_id": 1,
      "chunk_type": "budget_component",
      "content": "[Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.]\n[Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]\n\nComponent: Kubernetes migration\nDescription: Migration from monolith to microservices architecture using Kubernetes, containerized services, health checks, and deployment automation.\nTech stack: docker, kubernetes, python\nComplexity: high\nEstimated hours: 180\nDependencies: AUTH-001, INT-001",
      "distance": 0.7213019645316079,
      "metadata": {
        "year": 2024,
        "chunk_id": "BUD-SESSION08-EXAMPLE::MIG-001",
        "budget_id": "BUD-SESSION08-EXAMPLE",
        "complexity": "high",
        "tech_stack": [
          "docker",
          "kubernetes",
          "python"
        ],
        "client_name": "FintechCorp",
        "token_count": 116,
        "component_id": "MIG-001",
        "client_sector": "finance",
        "client_country": "ES",
        "estimated_hours": 180,
        "main_technology": "python"
      }
    }
  ]
}
```

**Observación:** La petición solicitó `k = 5`, pero devolvió 4 resultados porque el corpus solo contiene 4 chunks. Todos los chunks provienen del mismo presupuesto histórico fintech, aunque la transcripción pertenece a una tienda gourmet.

### 2.6 Lectura de los chunks devueltos

| Rank | chunk_id | document_id | historical budget | component | sector | hours | distance | tech stack |
| ---: | ---: | ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | 4 | 1 | BUD-SESSION08-EXAMPLE | UI-001 | finance | 80 | 0.681207 | ['typescript', 'react'] |
| 2 | 2 | 1 | BUD-SESSION08-EXAMPLE | INT-001 | finance | 120 | 0.701399 | ['python', 'fastapi', 'postgresql'] |
| 3 | 1 | 1 | BUD-SESSION08-EXAMPLE | AUTH-001 | finance | 140 | 0.720597 | ['python', 'fastapi', 'postgresql', 'redis'] |
| 4 | 3 | 1 | BUD-SESSION08-EXAMPLE | MIG-001 | finance | 180 | 0.721302 | ['docker', 'kubernetes', 'python'] |

### Chunk 1: UI-001

- **Historical budget:** `BUD-SESSION08-EXAMPLE`.
- **Sector:** `finance`.
- **Distance:** `0.6812073805009786`.
- **Estimated hours in historical component:** `80`.
- **Observation:** El chunk es estructurado y útil como antecedente histórico, pero pertenece a un proyecto fintech. La transcripción analizada habla de una tienda gourmet que necesita ecommerce, fidelización, dashboard, pago con tarjeta y correos de pedido. La coincidencia es parcial por conceptos genéricos como dashboard, pagos o integración, no por dominio ni por arquitectura de negocio.
- **Content preview:** [Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.] [Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]  Component: Operations dashboard Description: Internal dashboard for operations teams to monitor audit events, integration status, and financial workflow health.

### Chunk 2: INT-001

- **Historical budget:** `BUD-SESSION08-EXAMPLE`.
- **Sector:** `finance`.
- **Distance:** `0.701399437355401`.
- **Estimated hours in historical component:** `120`.
- **Observation:** El chunk es estructurado y útil como antecedente histórico, pero pertenece a un proyecto fintech. La transcripción analizada habla de una tienda gourmet que necesita ecommerce, fidelización, dashboard, pago con tarjeta y correos de pedido. La coincidencia es parcial por conceptos genéricos como dashboard, pagos o integración, no por dominio ni por arquitectura de negocio.
- **Content preview:** [Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.] [Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]  Component: External payment provider integration Description: Integration with external banking and payment systems, including webhook handling, retry logic, and

### Chunk 3: AUTH-001

- **Historical budget:** `BUD-SESSION08-EXAMPLE`.
- **Sector:** `finance`.
- **Distance:** `0.7205973391351352`.
- **Estimated hours in historical component:** `140`.
- **Observation:** El chunk es estructurado y útil como antecedente histórico, pero pertenece a un proyecto fintech. La transcripción analizada habla de una tienda gourmet que necesita ecommerce, fidelización, dashboard, pago con tarjeta y correos de pedido. La coincidencia es parcial por conceptos genéricos como dashboard, pagos o integración, no por dominio ni por arquitectura de negocio.
- **Content preview:** [Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.] [Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]  Component: JWT authentication API Description: REST API development with JWT authentication, token refresh, role-based authorization, and financial-sector securi

### Chunk 4: MIG-001

- **Historical budget:** `BUD-SESSION08-EXAMPLE`.
- **Sector:** `finance`.
- **Distance:** `0.7213019645316079`.
- **Estimated hours in historical component:** `180`.
- **Observation:** El chunk es estructurado y útil como antecedente histórico, pero pertenece a un proyecto fintech. La transcripción analizada habla de una tienda gourmet que necesita ecommerce, fidelización, dashboard, pago con tarjeta y correos de pedido. La coincidencia es parcial por conceptos genéricos como dashboard, pagos o integración, no por dominio ni por arquitectura de negocio.
- **Content preview:** [Project: Fintech modernization project with REST APIs, JWT authentication, external integrations, Kubernetes migration, and an operations dashboard.] [Client sector: finance | Country: ES | Year: 2024 | Main technology: python | Total estimated hours: 520]  Component: Kubernetes migration Description: Migration from monolith to microservices architecture using Kubernetes, containerized services, health checks, and d


---

## 3. Diagnóstico: cinco fallos identificados

### Fallo 1 — La transcripción completa se usa como una única query semántica

- **Problema observado:** La transcripción tiene `2853` caracteres y se incrusta como un único vector. El sistema no extrae intención, requisitos funcionales, actores, restricciones, incertidumbres ni prioridades.
- **Causa probable:** La arquitectura actual todavía está centrada en `query -> embedding -> vector search`. No existe una capa previa de análisis de transcript ni de normalización hacia una consulta de recuperación orientada a estimación.
- **Propuesta de solución:** Añadir un módulo `TranscriptAnalyzer` que convierta la transcripción en una estructura intermedia: dominio, objetivo, features detectadas, señales de incertidumbre, restricciones, prioridades y preguntas abiertas.

### Fallo 2 — No hay detección de mismatch de dominio

- **Problema observado:** Una transcripción de ecommerce gourmet recupera chunks de un proyecto fintech. El primer resultado es `UI-001` del sector `finance`, con distancia `0.6812073805009786`.
- **Causa probable:** La búsqueda vectorial no aplica filtros de dominio, sector, tipo de proyecto ni umbrales de similitud. El sistema siempre devuelve los vecinos más cercanos disponibles, aunque sean débiles.
- **Propuesta de solución:** Añadir metadata retrieval y un `RetrievalPolicy`: sector, tipo de producto, país, tecnología, complejidad y umbral de distancia. Si no hay evidencia suficientemente cercana, el sistema debe devolver `insufficient_context` o solicitar más datos.

### Fallo 3 — El sistema recupera chunks, pero no construye contexto aumentado

- **Problema observado:** La respuesta de `/search` devuelve chunks crudos con distancia y metadata, pero no produce un contexto sintético para estimación.
- **Causa probable:** Falta una fase de `Augmentation`. No hay módulo que seleccione, ordene, agrupe o explique por qué cada chunk debe influir en una estimación.
- **Propuesta de solución:** Crear `AugmentationBuilder`, que reciba la transcripción estructurada y los chunks recuperados, descarte evidencia débil, agrupe componentes equivalentes y produzca un paquete de evidencia para generación.

### Fallo 4 — No existe generación de presupuesto desde la evidencia recuperada

- **Problema observado:** Después de `/search`, el flujo termina. No se genera propuesta, desglose de módulos, horas, coste, incertidumbres ni preguntas para el cliente.
- **Causa probable:** La arquitectura actual implementa el bloque Retrieval, pero no el bloque Generation del flujo RAG.
- **Propuesta de solución:** Añadir `EstimateGenerator`, con salida tipada: componentes, descripción, supuestos, horas mínimas/máximas, dependencias, riesgos, preguntas abiertas y justificación basada en evidencia.

### Fallo 5 — No hay quality gate ni evaluación de suficiencia

- **Problema observado:** El sistema acepta como respuesta válida una lista de chunks con distancias relativamente altas entre `0.6812` y `0.7213`, sin advertir que la evidencia es débil o de dominio distinto.
- **Causa probable:** No hay `RAGQualityGate`, ni detector de baja confianza, ni clasificación de evidencia suficiente versus insuficiente.
- **Propuesta de solución:** Añadir una etapa de evaluación antes de generar: cobertura de requisitos, diversidad de evidencias, similitud mínima, compatibilidad de dominio y trazabilidad. Si falla, el sistema debe responder con reparación: pedir más datos, buscar otra fuente o marcar evidencia insuficiente.

---

## 4. Propuesta de evolución arquitectónica

```text
PROPUESTA DE EVOLUCIÓN ARQUITECTÓNICA

[Frontend / Cliente]
  Usuario
  Meeting transcript
  Estimate view + evidence card
        |
        v
[Business backend FastAPI]
  NEW POST /estimate-from-transcript
  POST /search
  POST /embeddings/ingest
  GET  /metrics
        |
        v
[AI service futuro RAG end-to-end]

  NEW TranscriptAnalyzer
    raw transcript
    -> structured requirements

  NEW QueryPlanner
    structured requirements
    -> multiple retrieval queries

  Existing SearchService
    retrieval queries
    -> pgvector cosine search

  NEW RetrievalPolicy
    chunks + distances + metadata
    -> accepted evidence or insufficient_evidence

  NEW AugmentationBuilder
    accepted chunks
    -> EvidenceBundle

  NEW EstimateGenerator
    EvidenceBundle
    -> typed estimate proposal

  NEW RAGQualityGate
    estimate + evidence
    -> accept, repair, reject, or clarify

  NEW Repair / Clarify loop
    weak evidence or missing requirements
    -> retry retrieval or ask the user

[PostgreSQL + pgvector]
  documents
  chunks
```

### Responsabilidad de los módulos nuevos

**TranscriptAnalyzer:** extrae requisitos desde la transcripción: ecommerce, fidelización, dashboard, pagos, correos y expansión futura. Recibe texto crudo y devuelve JSON estructurado. La primera pieza crítica es un schema Pydantic de `TranscriptRequirements`.

**QueryPlanner:** convierte requisitos estructurados en consultas de recuperación separadas. Por ejemplo, una query para ecommerce, otra para pagos, otra para dashboards y otra para fidelización. La primera pieza crítica es generar 3 a 6 queries trazables.

**RetrievalPolicy:** decide si un chunk recuperado es suficientemente relevante. Usa distancia, metadata, dominio y cobertura. La primera pieza crítica es definir umbrales y una respuesta `insufficient_evidence`.

**AugmentationBuilder:** construye el contexto aumentado que recibirá el generador. Agrupa chunks, elimina ruido y explica la relación con la transcripción. La primera pieza crítica es un paquete `EvidenceBundle`.

**EstimateGenerator:** produce una estimación tipada, no texto libre. Debe devolver módulos, horas, supuestos, riesgos, exclusiones y preguntas abiertas. La primera pieza crítica es un schema `GeneratedEstimate`.

**RAGQualityGate:** evalúa cobertura, grounding y confianza antes de devolver la estimación. Si hay evidencia débil o falta un requisito, repara o pide aclaración. La primera pieza crítica es un set de checks deterministas.

### Primera evolución recomendada

```text
TranscriptAnalyzer + schema de requisitos

Motivo:
Sin una representación estructurada de la transcripción, todo lo demás seguirá dependiendo de una query gigante y ambigua.
```

---

## Conclusión

El sistema actual es una base correcta de retrieval semántico persistente, pero todavía no es un RAG completo para estimaciones. La ejecución con `02_ambiguous.txt` demuestra que el sistema vectoriza la transcripción y devuelve chunks cercanos, pero no valida si esos chunks son suficientes, no detecta mismatch de dominio y no genera un presupuesto.

El siguiente paso arquitectónico debe ser separar la transcripción en requisitos estructurados antes de buscar, porque ese contrato será la base para retrieval más preciso, augmentation controlada, generación de estimación y evaluación de calidad.
