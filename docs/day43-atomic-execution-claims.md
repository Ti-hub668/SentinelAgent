# Day43: Durable Execution Claims

## Guarantee and ordering

The persistent broker path used by `POST /agent/runs/{run_id}/execute` keeps
Policy → Approval → typed contract validation → ExecutionIntent → durable claim
→ dry-run executor → atomic claim/receipt/Ledger persistence.
The endpoint and orchestrator already call the persistent broker and need no
interface changes. Current authorization and contract checks still precede replay.

`execution_claims.idempotency_key` has a database UNIQUE constraint. A committed
INSERT grants ownership; losing workers read the existing state. Both MySQL
InnoDB and file-backed SQLite are covered by the concurrency evaluator. No Python
lock participates in production claim acquisition.

| Existing state | Same fingerprint | Different fingerprint |
| --- | --- | --- |
| No row | INSERT; one winner executes | First committed binding wins |
| claimed | blocked (`in_progress` in message) | blocked/conflict |
| completed | Replay stored output, no executor | blocked/conflict |
| failed | CAS retry, at most 3 total attempts | blocked/conflict |
| released | CAS retry, same total attempt budget | blocked/conflict |

Retries require another broker invocation and pass authorization again. CAS
matches key, fingerprint, observed status, attempt and owner token, then increments
attempt and replaces the token. A stale owner cannot finalize a newer attempt.
`released` is reserved for an operator-reconciled safe release; there is no public
release endpoint, automatic lease expiration, or automatic takeover.

The owner token is internal and is not serialized into API results or the Ledger.
The claim contains the receipt, output and source event ID. The broker flushes the
existing Day42 event payload and conditionally finalizes the claim in one
transaction. A failed COMMIT cannot turn an uncertain successful executor outcome
into a retryable failure. Such slots remain claimed and require reconciliation.

## Schema and rollout

This repository uses SQLAlchemy `Base.metadata.create_all()`, not Alembic.
The change is additive: a new table, no changes to existing tables or history.

1. Stop/drain **all** Day42 API/workers before rollout. Mixed Day42/Day43 workers
   are unsafe because old workers do not acquire claims.
2. Back up the database using the usual deployment procedure.
3. From `D:\SentinelAgent\backend`, using a working Python environment, run:

   ```powershell
   python -m app.db.init_execution_claims
   ```

   Normal application startup also imports `ExecutionClaim` before `create_all`.
   The dedicated command creates only the new table and is safe to repeat.
   Existing investigation tables must already exist. Database user needs CREATE
   permission. Claim and Ledger tables must use transactional storage (InnoDB).
4. Restart only Day43 workers.

On first authorized access, pre-Day43 successful Ledger slots become completed
claims without invoking the executor. Existing fingerprint bindings remain
authoritative; missing/mismatched bindings fail closed. Legacy failures keep the
retry budget. There is no bulk rewrite of historical events.

`create_all` does not migrate an existing incompatible `execution_claims` table;
future schema changes need an explicit migration.

## Evaluation

Run from the backend directory:

```powershell
python -m app.evaluation.tool_registry_evaluator
python -m app.evaluation.tool_capability_evaluator
python -m app.evaluation.execution_idempotency_evaluator
python -m app.evaluation.tool_broker_evaluator
python -m app.evaluation.policy_fail_closed_evaluator
python -m app.evaluation.execution_claim_evaluator
python -m app.evaluation.execution_claim_evaluator --mysql
python -m app.evaluation.tool_broker_integration_evaluator
git diff --check
```

The default claim evaluator uses a temporary file-backed SQLite database with
foreign keys enabled, independent sessions/connections, two concurrent workers,
and synchronization that holds the winner inside the executor until the losing
worker returns. The MySQL option uses the configured application database,
creates the claim table if absent, and **retains synthetic runs/events/claims** for
audit. It invokes patched dry-run executors only. Some cases intentionally leave
claims in `claimed` to model crash recovery; these are synthetic tests, not stuck
real tools. The integration evaluator creates an ordinary investigation run.

Eight Day43 checks cover initial contention, concurrent retry, retry exhaustion,
atomic receipt rollback, stale owner/attempt fencing, historical replay import,
acquisition storage failure, and old claimed slots remaining blocked/conflicting.

## Limits

- This is durable atomic claim ownership, **not external exactly-once**. A process
  may die after a side effect but before receipt persistence. Do not clear such
  claims until the external outcome is reconciled.
- Generic executor exceptions are retryable only because all current registered
  tools are dry-run. Real adapters need explicit safe-to-retry vs uncertain
  outcomes and preferably downstream idempotency keys before being enabled.
- The existing no-DB broker entry points are retained for offline mock evaluators;
  they do not provide durable claims and must never serve real adapters/API work.
- Database errors fail closed by propagating to the caller; no fallback executor
  path exists. In-progress is represented as legacy `status="blocked"`, preserving
  existing API/UI compatibility, with an explicit `in_progress` message.
- Session transactions are owned by claim operations. Pending caller writes are
  rejected; the orchestrator currently passes a read-only snapshot session.
- Authorization uses the current loaded workflow snapshot. Simultaneous approval
  revocation after that snapshot is not serialized with execution by this change.
- No heartbeat, lease renewal, release UI, operator recovery workflow or automated
  retry scheduler is introduced.

## Environment note

During development the repository's `.venv\Scripts\python.exe` referenced a
missing Python 3.12 installation. Tests were run using the bundled Python 3.12
runtime with the repository's existing `.venv\Lib\site-packages` and backend
working directory; no dependency installation or environment-file changes were
needed. Repair that launcher before relying on the plain `python` commands above.
