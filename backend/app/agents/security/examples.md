# Example Security Agent Review Scenarios

## Scenario 1: Validated SQL Injection with Semgrep Support

**Context:**
- PR Title: Add search endpoint
- Semgrep Finding: `generic.security.audit.sqli-raw-query` at `app/routes/search.py:18`
- Code Diff: `results = db.query(f"SELECT * FROM products WHERE title LIKE '%{user_query}%'")`
- Security Docs: `docs/security_policy.md` specifies "All search queries must use parameter bindings."

**Expected Finding JSON:**
```json
{
  "summary": "The PR introduces a SQL Injection vulnerability in the search route due to unescaped string interpolation.",
  "findings": [
    {
      "title": "SQL Injection via String Formatting",
      "category": "SQL Injection",
      "severity": "High",
      "confidence": 0.98,
      "summary": "User input `user_query` is interpolated directly into an SQL statement.",
      "reason": "An attacker can craft malicious SQL input in `user_query` to manipulate the database query structure.",
      "impact": "Potential unauthorized reading, modification, or deletion of sensitive database records.",
      "recommendation": "Use parameterized queries with placeholder bindings.",
      "code_evidence": "app/routes/search.py line 18: `db.query(f\"SELECT * FROM products WHERE title LIKE '%{user_query}%'\")`",
      "docs_evidence": "docs/security_policy.md: 'All search queries must use parameter bindings.'",
      "semgrep_evidence": "Validated Semgrep finding `generic.security.audit.sqli-raw-query` at app/routes/search.py:18",
      "file_path": "app/routes/search.py",
      "line_number": 18,
      "suggested_fix": "db.query('SELECT * FROM products WHERE title LIKE %s', (f'%{user_query}%',))"
    }
  ]
}
```
