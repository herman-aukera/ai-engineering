# EACHAT Final Project — 3-Minute Demonstration Script

Status: recording-ready package; the video itself remains external evidence.

## Pre-recording checklist

Complete these steps before screen recording so the three-minute take contains no setup
delay or credential exposure.

1. Start Docker Desktop and wait until `docker version` reports both client and server.
2. In a terminal that will not be recorded, set `EACHAT_SUPPORT_EMBEDDING_API_KEY` to
   the real embedding credential and run from `estimador-cag/`:

   ```powershell
   uv run python scripts/smoke_eachat_final_project_compose.py --cleanup
   ```

3. Start the stack again from the repository root, leaving the credential inherited
   from the hidden shell:

   ```powershell
   docker compose -f docker-compose.final-project.yml up -d --build
   ```

4. Generate a one-hour local reviewer token from `estimador-cag/`. This token is signed
   with the Compose development key and is not a provider credential:

   ```powershell
   $token = uv run python -c "from datetime import UTC,datetime,timedelta; from app.energy_chat.identity import SignedSessionCodec; print(SignedSessionCodec(b'local-final-project-signing-key-change-me-1234567890').issue(subject='final-project-reviewer',tenant_id='local-final-project',roles=('reviewer',),expires_at=datetime.now(UTC)+timedelta(hours=1)))"
   Set-Clipboard -Value $token
   ```

   Copy only the token into the UI's **Signed session token** password field. Do not show provider keys, shell history, GitHub secret settings, or the token value in the recording. The UI keeps the token in memory only and does not write it to browser storage.

5. Open `http://127.0.0.1:8080/energy-chat/v2/demo`. Keep these tabs ready:

   - the EACHAT demo;
   - `README.md` at the architecture diagram;
   - the successful live workflow run and its downloaded
     `final-project-retrieval-report.json`;
   - `docker-compose.final-project.yml`.

6. Confirm the branch and exact SHA in a clean terminal:

   ```powershell
   git branch --show-current
   git rev-parse HEAD
   git status --short -uall
   ```

## Recording timeline and narration

### 0:00–0:20 — Problem and domain

Show the root README title and supported scope.

Say: “EACHAT is an evidence-grounded L2 support assistant for Spring Boot,
PostgreSQL, Docker and operational observability. It is deliberately not a generic
chatbot, source-code patcher, or Kubernetes operator.”

### 0:20–0:45 — Architecture

Show the architecture diagram.

Say: “A support question is policy-classified, then real RAG fetches persisted pgvector
evidence. LangGraph generates a candidate, runs deterministic critics and Energy
scoring, and governs accept, repair, clarify, reject, refuse, or escalate. The response
includes evidence refs, an Energy Card and a decision ledger.”

Point to: official HTTPS sources → bounded section chunks → OpenAI embeddings →
PostgreSQL `VECTOR(1536)` + HNSW cosine retrieval → `ProjectRagResult` → graph.

### 0:45–1:30 — Successful evidence-grounded support answer

In the demo, choose Project / Deterministic / Critic, create a new conversation, and
submit:

```text
PostgreSQL connections are exhausted and Spring Boot health reports database DOWN. Which server-side limits, active sessions, and application-pool evidence should L2 support inspect before assigning a root cause?
```

The equivalent canonical one-off payload for `/energy-chat/v2/chat` is:

```json
{
  "user_message": "PostgreSQL connections are exhausted and Spring Boot health reports database DOWN. Which server-side limits, active sessions, and application-pool evidence should L2 support inspect before assigning a root cause?",
  "mode": "project",
  "k": 5,
  "orchestration_mode": "critic",
  "execution_profile": "deterministic"
}
```

Show the answer, `accept` disposition, Energy Card, provider/graph metrics and evidence
count. Click **Inspect state** and briefly show `source:postgres_...` and
`source:spring_boot_...` evidence refs. Do not claim one exact root cause; point out the
bounded diagnostic sequence.

### 1:30–1:55 — Insufficient/version-conflict clarification

Create a new conversation and submit:

```text
Our service runs Spring Boot 2.7.18. Are the current Actuator health endpoint defaults exactly the same? Give me a version-specific answer.
```

Show the `clarify` disposition and `version_matched_source_required` policy rule.
Say: “The corpus has current documentation, so deterministic governance requests a
version-matched authoritative source instead of inventing compatibility.”

### 1:55–2:15 — L3 authority escalation

Create a new conversation and submit:

```text
Our Spring Boot service is failing. Patch the Java source code for me.
```

Show the `escalate` disposition and `l3_source_code_remediation` policy rule.
Say: “The model can propose text, but deterministic policy owns the L2 authority
boundary. Source repair goes to L3 or a human engineer.”

### 2:15–2:35 — Evaluation and regression proof

Show the exact-head workflow URL and the downloaded retrieval/system reports. Point to
`retrieval_hit_rate`, disposition accuracy, clarification accuracy, escalation accuracy,
provider calls, p95 latency and measured cost. Mention that the fixed set has 11 cases.

Say: “These are measured artifacts from this SHA. Semantic unsupported-claim rate stays
unmeasured until a fixed judge or manual rubric exists.”

### 2:35–2:50 — Monitoring and deployment

Show the UI inspector or the authenticated `/energy-chat/v2/monitoring/dashboard`, then
the Compose topology: Caddy → FastAPI → internal PostgreSQL/pgvector, with one-shot
ingestion, health checks and a persistent volume.

Say: “Monitoring is bounded and content-free: counts, error rate, mean and p95 latency,
provider calls, cost and dispositions—never prompts, answers or credentials.”

### 2:50–3:00 — Limitations and submission identity

Show branch `finalproject-GG` and the exact SHA.

Say: “This is LIVE-VERIFIED only if the exact-head live workflow and Compose smoke are
green. It is not claimed production-ready or hallucination-free. The remaining
submission evidence is the public URL or uploaded video.”

## Optional terminal payloads

If the browser cannot be used, run these from PowerShell after `$token` is generated:

```powershell
$headers = @{ Authorization = "Bearer $token" }
$body = @{
  user_message = "PostgreSQL connections are exhausted. Which limits and active-session evidence should I inspect?"
  mode = "project"
  k = 5
  orchestration_mode = "critic"
  execution_profile = "deterministic"
} | ConvertTo-Json
$result = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8080/energy-chat/v2/chat' -Headers $headers -ContentType 'application/json' -Body $body
$result | Select-Object final_disposition,evidence_refs,energy_card_v2,provider_metrics_summary | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:8080/energy-chat/v2/monitoring' -Headers $headers | ConvertTo-Json -Depth 6
```

Stop without deleting the persistent volume:

```powershell
docker compose -f docker-compose.final-project.yml down
```
