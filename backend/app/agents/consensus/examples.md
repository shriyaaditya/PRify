# Example Consensus Review Scenarios

## Scenario 1: Merging Two Genuine Duplicate Findings

**Context & Inputs:**
- **ArchitectureAgent**: Finding on `services/user_service.py:15` titled "Database Query inside Service Loop" (Category: `architecture:layering`, Severity: `Medium`, Confidence: `0.85`, Evidence: `for id in ids: db.query(User).get(id)`).
- **PerformanceAgent**: Finding on `services/user_service.py:15` titled "N+1 Database Query in User Loop" (Category: `performance:n+1-query`, Severity: `High`, Confidence: `0.92`, Evidence: `for id in ids: db.query(User).get(id)`).

**Expected Consensus Output:**
- Merge into 1 finding with `source_agents`: `["ArchitectureAgent", "PerformanceAgent"]`.
- Consolidated Title: "N+1 Database Query inside User Loop"
- Normalized Severity: `High`

---

## Scenario 2: Two Findings on Same Line Representing Distinct Concerns (KEPT SEPARATE)

**Context & Inputs:**
- **SecurityAgent**: Finding on `routes/exec_route.py:30` titled "Unsanitized Input Passed to Command Execution" (Category: `security:command-injection`, Severity: `Critical`, Confidence: `0.95`, Evidence: `subprocess.run(user_cmd)`).
- **PerformanceAgent**: Finding on `routes/exec_route.py:30` titled "Blocking Subprocess Call in Async Route" (Category: `performance:blocking-async`, Severity: `Medium`, Confidence: `0.80`, Evidence: `subprocess.run(user_cmd)`).

**Expected Consensus Output:**
- Keep both findings separate!
- Finding 1: `security:command-injection`, `source_agents`: `["SecurityAgent"]`.
- Finding 2: `performance:blocking-async`, `source_agents`: `["PerformanceAgent"]`.

---

## Scenario 3: High-Confidence Specialist Finding with Weak Evidence (SUPPRESSED)

**Context & Inputs:**
- **TestingAgent**: Finding on `utils/logger.py:10` titled "Missing Unit Test for Logger Initialization" (Category: `testing:missing-unit-tests`, Severity: `High`, Confidence: `0.98`, Evidence: `logger = logging.getLogger(__name__)`).
- **Code Context**: Standard module-level logger instantiation with no business logic or custom configuration.

**Expected Consensus Output:**
- Suppress the finding! Modifying standard module logger declaration does not warrant unit test coverage.
- Final findings count: 0 (or finding omitted).

---

## Scenario 4: Multiple Agents Supporting Same Underlying Concern (CORROBORATION)

**Context & Inputs:**
- **ArchitectureAgent**: Flags missing interface layer for `PaymentClient` in `services/checkout.py:45`.
- **TestingAgent**: Flags inability to mock `PaymentClient` in unit tests due to hardcoded instantiation in `services/checkout.py:45`.

**Expected Consensus Output:**
- Consolidated into 1 finding: "Hardcoded PaymentClient Coupling Prevents Testability and Abstraction".
- `source_agents`: `["ArchitectureAgent", "TestingAgent"]`.
- Rationale integrates architectural coupling and testing impact.

---

## Scenario 5: Conflicting Specialist Recommendations (EVIDENCE-BASED RESOLUTION)

**Context & Inputs:**
- **SecurityAgent**: Recommends adding `try/except Exception` around external API call on `clients/api.py:20` to hide internal stack trace.
- **TestingAgent**: Recommends throwing typed `APIConnectionError` with root cause so caller error path tests can assert specific failure modes.

**Expected Consensus Output:**
- Resolves conflict in favor of structured typed exception (`APIConnectionError`), as concrete evidence shows caller functions catch custom domain exceptions while raw try/except Exception swallows critical details.
- Recommendation: "Wrap external call in try/except and re-raise domain-specific APIConnectionError."
