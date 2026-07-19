# Spec 0009 — Sandboxed Tool Adapter Design

## 1. Architectural position

The sandboxed tool adapter sits below the existing EACODE policy/authorization boundary and above the OS process layer:

```text
ExecutionPlan + consumed AuthorizationReceipt (when human-gated)
    + current repository revision
        → SandboxedToolAdapter (disabled by default)
            → independent pre-start verifier
            → environment constructor (name allowlist only)
            → path/symlink re-resolver
            → subprocess.Popen (args list, no shell)
            → stdout/stderr streamer with redaction + truncation
            → timeout + cancellation + process-tree cleanup
            → ExecutionEvidence builder (execution_performed=true)
        → existing EACODE evidence and decider path
```

The adapter is a subordinate evidence producer. It never decides whether a command is acceptable, whether evidence is sufficient, or whether a candidate should be accepted.

## 2. Proposed contracts

### SandboxedToolConfig

```python
class SandboxedToolConfig:
    enabled: bool = False  # Must be explicitly set to True
    repository_root: str
    current_revision: int
    trusted_actors: list[str]
    consumed_nonce_hashes: list[str]
    environment_allowlist: list[str]
    max_timeout_seconds: int = 120
    max_output_chars: int = 20_000
    denied_executables: list[str]
    denied_git_subcommands: list[str]
```

### RealToolResult (extends FakeToolResult concept)

```python
class RealToolResult:
    stdout: str
    stderr: str
    exit_code: int | None  # None if killed before exit
    duration_ms: int
    timed_out: bool
    cancelled: bool
    process_tree_cleaned: bool
    cleanup_error: str | None
    failure_class: str | None  # "timeout", "cancelled", "non_zero_exit", "cleanup_failure"
```

### SandboxedToolAdapter

```python
class SandboxedToolAdapter:
    config: SandboxedToolConfig

    def invoke(self, plan: ExecutionPlan) -> RealToolResult:
        """Execute a validated plan and return bounded, redacted evidence."""
        # 1. Verify enabled
        # 2. Independent pre-start verification
        # 3. Resolve executable against allowlist
        # 4. Resolve paths and check for traversal/symlink escape
        # 5. Build minimal environment
        # 6. Create and monitor process
        # 7. Stream, redact, truncate output
        # 8. Handle timeout, cancellation, cleanup
        # 9. Build and return RealToolResult
```

### Integration with review_execution

Extend `review_execution()` to accept an optional `SandboxedToolAdapter`. When the plan mode is not "dry_run" or "fake", use the sandboxed adapter instead of `FakeToolAdapter`. The sandboxed adapter internally verifies its own preconditions.

## 3. Pre-start verification design

```text
verify_enabled(config)
    → verify_plan_not_denied(plan)
    → if plan.requires_human_authorization:
        → verify_authorization_present(auth_receipt)
        → verify_authorization_consumed(auth_receipt)
        → verify_plan_hash_match(auth_receipt, plan)
        → verify_revision_match(auth_receipt, config)
        → verify_nonce_not_replayed(auth_receipt, config)
    → verify_executable_allowed(plan.executable, config)
    → verify_no_denied_git_subcommand(plan)
    → resolve_repository_root(config)
    → resolve_working_directory(plan, root)
    → verify_all_paths_within_root(plan, root)
    → verify_no_symlink_escape(root)
```

Each verification failure raises a specific `PermissionError` with a structured reason.

## 4. Process creation design

```python
def _create_process(plan, resolved_env):
    return subprocess.Popen(
        args=[plan.executable, *plan.arguments],
        cwd=plan.working_directory,
        env=resolved_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        shell=False,  # Hard invariant
        text=False,   # Read bytes, decode after redaction
    )
```

## 5. Environment construction

```python
def _build_environment(plan, config):
    env = {}
    for name in plan.environment_names:
        if name in config.environment_allowlist:
            value = os.environ.get(name, "")
            env[name] = value
    # Explicit PATH needed for executable resolution
    env["PATH"] = os.environ.get("PATH", "")
    # System root needed on Windows
    if sys.platform == "win32":
        env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "C:\\Windows")
    return env
```

No other parent environment variables are inherited.

## 6. Output streaming with redaction

```python
def _stream_output(process, plan):
    # Read stdout and stderr concurrently via threads or async
    # Apply _redact() from controlled_execution.py to each chunk
    # Apply _truncate() when total exceeds plan.max_output_chars
    # Track total bytes, redaction status, truncation status
    # Return bounded stdout, stderr, and metadata
```

Use `threading.Thread` for concurrent stdout/stderr reads to avoid deadlock. Each thread reads chunks, redacts, and appends to a bounded buffer protected by a lock.

## 7. Timeout and cancellation

### Timeout

```python
def _wait_with_timeout(process, timeout_seconds):
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return RealToolResult(
            exit_code=process.returncode,
            timed_out=False,
            ...
        )
    except subprocess.TimeoutExpired:
        _kill_process_tree(process.pid)
        partial_stdout, partial_stderr = _collect_partial_output(process)
        return RealToolResult(
            exit_code=None,
            timed_out=True,
            failure_class="timeout",
            ...
        )
```

### Cancellation

Use a `threading.Event` that external code can set. The adapter checks the event between chunk reads and initiates cleanup when set:

```python
class SandboxedToolAdapter:
    def __init__(self, config):
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def invoke(self, plan):
        # ... in streaming loop:
        if self._cancel_event.is_set():
            _kill_process_tree(process.pid)
            return _cancellation_result(process)
```

## 8. Process-tree cleanup

### Windows

Use `taskkill /F /T /PID <pid>` as primary mechanism. For stronger guarantees, use Windows Job Objects via `pywin32` or ctypes, but `taskkill` is the stdlib-first approach.

```python
def _kill_process_tree_windows(pid):
    subprocess.run(
        ["taskkill", "/F", "/T", "/PID", str(pid)],
        capture_output=True,
        timeout=10,
    )
```

### Unix

Use `os.killpg(pgid, signal.SIGKILL)` after setting the process group:

```python
def _kill_process_tree_unix(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
```

## 9. Evidence record

```python
def build_real_execution_evidence(
    plan: ExecutionPlan,
    result: RealToolResult,
    authorization_receipt: AuthorizationReceipt | None,
    config: SandboxedToolConfig,
) -> ExecutionEvidence:
    return ExecutionEvidence(
        schema_version="1.0.0",
        evidence_id=f"execution-{plan.plan_hash[:16]}",
        run_id=plan.plan_id,
        proposal_id=plan.proposal_id,
        plan_hash=plan.plan_hash,
        status="pass" if result.exit_code == 0 else "fail",
        summary=_build_summary(result),
        execution_mode=plan.execution_mode,
        execution_performed=True,  # Real execution
        adapter_invoked=True,
        exit_code=result.exit_code,
        stdout_excerpt=result.stdout,
        stderr_excerpt=result.stderr,
        output_truncated=result.stdout_truncated or result.stderr_truncated,
        redaction_status="redacted" if result.redacted else "not_required",
        artifact_hash=_hash_payload({...}),
        duration_ms=result.duration_ms,
        rollback_available=bool((plan.rollback_summary or "").strip()),
        trust_classification="trusted",
        policy_reasons=list(plan.reasons),
    )
```

## 10. CLI design

```text
python -m energy_core.sandboxed_tool_cli \
    --plan <path-to-ExecutionPlan.json> \
    --repository-root <path> \
    --run-id <id> \
    [--authorization-receipt <path-to-AuthorizationReceipt.json>] \
    [--live-tool] \
    [--format json|text]
```

Without `--live-tool`, the CLI refuses real execution and suggests using the controlled-execution CLI for dry-run/fake review.

## 11. Failure injection design

For deterministic testing, provide a `SandboxedToolAdapter` subclass that can inject failures:

```python
class FailureInjectingAdapter(SandboxedToolAdapter):
    def __init__(self, config, *, inject_timeout=False, inject_non_zero=False, ...):
        super().__init__(config)
        self._inject_timeout = inject_timeout
        ...

    def invoke(self, plan):
        if self._inject_timeout:
            return _timeout_result()
        # ...
```

## 12. Platform strategy

| Feature | Windows | Unix |
|---|---|---|
| Process creation | `subprocess.Popen` | `subprocess.Popen` |
| No shell | `shell=False` | `shell=False` |
| Process tree kill | `taskkill /F /T /PID` | `os.killpg(SIGKILL)` |
| Symlink detection | `Path.resolve()` | `Path.resolve()` |
| Path resolution | Backslash normalization | Forward slash |
| Env minimal | Include SYSTEMROOT | Include PATH only |

Platform-specific tests are marked with `@pytest.mark.skipif`.

## 13. Migration and rollback

- All new code is additive; no existing files are modified except a backward-compatible extension to `review_execution()`.
- `SandboxedToolAdapter.enabled` defaults to `False`.
- Existing `FakeToolAdapter` remains the CI default.
- Rollback: delete `sandboxed_tool.py`, `sandboxed_tool_cli.py`, and the test file; revert any `review_execution()` changes.
