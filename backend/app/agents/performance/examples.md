# Example Performance Agent Review Scenarios

## Scenario 1: Positive Finding - N+1 Database Query inside Loop

**Context:**
- PR Title: Fetch user profile details
- Code Diff:
```python
def get_user_profiles(user_ids: list[str]):
    profiles = []
    for uid in user_ids:
        # N+1 query vulnerability
        user = db.query(UserModel).filter_by(id=uid).first()
        profiles.append(user.to_dict())
    return profiles
```
- Performance Docs: `docs/performance_guidelines.md` states "Avoid querying database in loops; use bulk fetches with IN clause."

**Expected Finding JSON:**
```json
{
  "summary": "The PR introduces an N+1 database query pattern in `get_user_profiles`, executing a DB lookup per user ID.",
  "findings": [
    {
      "title": "N+1 Database Query in Profile Lookup",
      "category": "N+1 Query",
      "severity": "High",
      "confidence": 0.96,
      "summary": "Loop executes an individual database query for every user ID in the input list.",
      "reason": "Instead of executing 1 query, the function executes N+1 database roundtrips, causing linear latency inflation as user count grows.",
      "impact": "High network roundtrip overhead and potential connection pool exhaustion during batch requests.",
      "recommendation": "Use `db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()` to fetch all users in a single query.",
      "code_evidence": "services/user_service.py line 12: `user = db.query(UserModel).filter_by(id=uid).first()`",
      "docs_evidence": "docs/performance_guidelines.md: 'Avoid querying database in loops; use bulk fetches with IN clause.'",
      "file_path": "services/user_service.py",
      "line_number": 12,
      "suggested_fix": "users = db.query(UserModel).filter(UserModel.id.in_(user_ids)).all()\nreturn [u.to_dict() for u in users]"
    }
  ]
}
```

---

## Scenario 2: Negative Example - Bounded Loop over Constant List (NO FINDING)

**Context:**
- PR Title: Add supported region validation
- Code Diff:
```python
SUPPORTED_REGIONS = ["us-east-1", "us-west-2", "eu-west-1"]

def validate_region(region: str) -> bool:
    # Bounded iteration over fixed 3-element constant list
    for valid_reg in SUPPORTED_REGIONS:
        if valid_reg == region:
            return True
    return False
```

**Expected Response JSON:**
```json
{
  "summary": "Code changes reviewed. No performance or scalability bottlenecks detected. Bounded iteration over small fixed constant array is O(1) in practice.",
  "findings": []
}
```
