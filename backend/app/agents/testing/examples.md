# Example Testing Agent Review Scenarios

## Scenario 1: Positive Finding - New Validation Branch Without Test (MISSING TEST FINDING)

**Context:**
- PR Title: Add input validation for user discount codes
- Code Diff:
```python
def apply_discount(cart, discount_code):
    if not discount_code:
        return cart.total
    if len(discount_code) > 20:
        raise ValueError("Discount code exceeds max length")
    # ... apply code
```
- Existing Tests: `tests/test_cart.py` tests `apply_discount` with valid codes and empty codes, but has no test for discount codes exceeding 20 characters.

**Expected Finding JSON:**
```json
{
  "summary": "PR adds length validation logic to `apply_discount`, but no test cases verify that discount codes longer than 20 characters raise a `ValueError`.",
  "findings": [
    {
      "title": "Missing Unit Test for Discount Code Length Limit",
      "category": "Untested Error Path",
      "severity": "Medium",
      "confidence": 0.92,
      "summary": "New input validation rejecting discount codes longer than 20 characters lacks unit test coverage.",
      "reason": "The added `ValueError` exception path is unverified by existing or added unit tests.",
      "impact": "Refactoring or boundary changes in discount code validation could break without build failure.",
      "recommendation": "Add a test in `tests/test_cart.py` passing a 21-character string to `apply_discount` and asserting `ValueError` is raised.",
      "code_evidence": "app/cart.py line 5: `if len(discount_code) > 20: raise ValueError('Discount code exceeds max length')`",
      "test_evidence": "tests/test_cart.py: existing test cases only exercise valid discount codes and empty string",
      "docs_evidence": "docs/testing.md: All raised exceptions in business logic require dedicated unit tests.",
      "file_path": "app/cart.py",
      "line_number": 5,
      "suggested_test": "def test_apply_discount_code_too_long_raises_value_error()"
    }
  ]
}
```

---

## Scenario 2: Negative Finding - Internal Refactoring with Full Existing Test Coverage (NO FINDING)

**Context:**
- PR Title: Refactor list processing helper method internally
- Code Diff:
```python
def process_items(items):
    # Refactored list comprehension to use generator expression for internal memory optimization
    return list(transform_item(item) for item in items if item.is_active)
```
- Existing Tests: `tests/test_processor.py` contains thorough unit tests verifying active/inactive filtering and item transformation output.

**Expected Response JSON:**
```json
{
  "summary": "Reviewed internal refactoring of `process_items`. Existing unit tests in `tests/test_processor.py` exercise active item filtering and transformation behavior. No testing gaps identified.",
  "findings": []
}
```

---

## Scenario 3: Negative Finding - Production Code Change Without PR Test Diff, Covered by Existing Test Files (NO FINDING)

**Context:**
- PR Title: Update error message string in payment service
- Code Diff:
```python
def process_payment(amount):
    if amount <= 0:
        raise InvalidPaymentError("Payment amount must be greater than zero")
```
- PR Test Diff: None (0 test files modified in PR).
- Qdrant Vector DB Retrieved Context: `tests/test_payment.py` contains:
```python
def test_process_payment_negative_amount():
    with pytest.raises(InvalidPaymentError):
        process_payment(-10)
```

**Expected Response JSON:**
```json
{
  "summary": "PR updates error message string in `process_payment`. Existing test suite in `tests/test_payment.py` (retrieved from vector store) already asserts `InvalidPaymentError` on zero/negative amounts. No new test required.",
  "findings": []
}
```
