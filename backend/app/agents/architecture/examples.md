# Example Architecture Agent Scenarios

## Scenario 1: Controller bypassing the Service Layer

**Context:**
- PR Title: Add fast path for user lookup.
- Changed Files: `app/api/user.py` introduces `db.execute("SELECT * FROM users WHERE id = %s", id)`.
- Retrieved Docs: `docs/architecture.md` states "All database interactions must be abstracted behind the Repository pattern. Controllers must call the Service layer."

**Expected Finding JSON:**
```json
{
  "summary": "The PR introduces a direct database query in the API controller, bypassing the established service and repository layers.",
  "findings": [
    {
      "title": "Service Layer Bypass",
      "severity": "High",
      "confidence": 0.98,
      "reason": "The user API controller is executing raw SQL directly, which violates the layered architecture.",
      "impact": "Tight coupling between the API layer and the database, making the code harder to test and maintain.",
      "recommendation": "Move the database query to `UserRepository` and invoke it via `UserService`.",
      "code_evidence": "app/api/user.py: db.execute('SELECT * FROM users...')",
      "docs_evidence": "docs/architecture.md: 'All database interactions must be abstracted behind the Repository pattern.'",
      "file_path": "app/api/user.py",
      "line_number": 25,
      "suggested_fix": "user = user_service.get_user_by_id(db, user_id)"
    }
  ]
}
```
