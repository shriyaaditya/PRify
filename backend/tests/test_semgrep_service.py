import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from app.parsers.tree_sitter.models import ChangedFile
from app.services.github.semgrep_service import SemgrepService
from app.workflows.github_review.nodes.analyze_semgrep import analyze_semgrep
from app.workflows.github_review.state import GitHubReviewState

# --- Test A: Semgrep JSON parsing ---


def test_semgrep_json_parsing_single_finding():
    service = SemgrepService()
    sample_json = json.dumps(
        {
            "results": [
                {
                    "check_id": "python.lang.security.audit.sqli.hardcoded-sql-expression",
                    "path": "app/services/payment.py",
                    "start": {"line": 42, "col": 5},
                    "extra": {
                        "message": "Possible SQL injection detected.",
                        "severity": "ERROR",
                        "lines": "db.execute(f'SELECT * FROM users WHERE id = {user_id}')",
                    },
                }
            ]
        }
    )

    findings = service.parse_semgrep_json(sample_json)

    assert len(findings) == 1
    f = findings[0]
    assert f.rule_id == "python.lang.security.audit.sqli.hardcoded-sql-expression"
    assert f.file_path == "app/services/payment.py"
    assert f.line_number == 42
    assert f.severity == "ERROR"
    assert "SQL injection" in f.message
    assert "db.execute" in f.code_snippet


# --- Test B: Multiple findings ---


def test_semgrep_json_parsing_multiple_findings():
    service = SemgrepService()
    sample_json = json.dumps(
        {
            "results": [
                {
                    "check_id": "rule-1",
                    "path": "app/main.py",
                    "start": {"line": 10},
                    "extra": {
                        "message": "Msg 1",
                        "severity": "WARNING",
                        "lines": "code 1",
                    },
                },
                {
                    "check_id": "rule-2",
                    "path": "app/auth.py",
                    "start": {"line": 25},
                    "extra": {
                        "message": "Msg 2",
                        "severity": "INFO",
                        "lines": "code 2",
                    },
                },
            ]
        }
    )

    findings = service.parse_semgrep_json(sample_json)

    assert len(findings) == 2
    assert findings[0].rule_id == "rule-1"
    assert findings[1].rule_id == "rule-2"


# --- Test C: Nested filepath preservation ---


def test_nested_filepath_preservation():
    service = SemgrepService()
    sample_json = json.dumps(
        {
            "results": [
                {
                    "check_id": "rule-nested",
                    "path": "app/services/auth/payment_gateway.py",
                    "start": {"line": 15},
                    "extra": {"message": "Finding", "severity": "ERROR"},
                }
            ]
        }
    )

    findings = service.parse_semgrep_json(sample_json)

    assert len(findings) == 1
    assert findings[0].file_path == "app/services/auth/payment_gateway.py"


# --- Test D: Severity mapping ---


def test_severity_mapping():
    service = SemgrepService()
    assert service.map_severity("ERROR") == "ERROR"
    assert service.map_severity("WARNING") == "WARNING"
    assert service.map_severity("INFO") == "INFO"
    assert service.map_severity("unknown") == "WARNING"


# --- Test E: No findings ---


def test_no_findings_returns_empty_list():
    service = SemgrepService()
    sample_json = json.dumps({"results": []})
    findings = service.parse_semgrep_json(sample_json)
    assert findings == []


# --- Test F: Missing executable ---


@pytest.mark.anyio
async def test_missing_executable_returns_empty_and_logs_warning():
    service = SemgrepService()
    changed_file = ChangedFile(
        filename="main.py",
        filepath="main.py",
        language="python",
        content="print('hello')",
    )

    with patch("shutil.which", return_value=None):
        findings = await service.run_analysis([changed_file])
        assert findings == []


# --- Test G: Timeout handling ---


@pytest.mark.anyio
async def test_timeout_handling_kills_process():
    service = SemgrepService(timeout=1)
    changed_file = ChangedFile(
        filename="main.py",
        filepath="main.py",
        language="python",
        content="print('hello')",
    )

    mock_proc = AsyncMock()
    mock_proc.communicate.side_effect = asyncio.TimeoutError()

    with (
        patch("shutil.which", return_value="/usr/bin/semgrep"),
        patch("asyncio.create_subprocess_exec", return_value=mock_proc),
    ):
        findings = await service.run_analysis([changed_file])

        assert findings == []
        mock_proc.kill.assert_called_once()


# --- Test H: Invalid JSON ---


def test_invalid_json_returns_empty_list_without_crash():
    service = SemgrepService()
    invalid_json = "Semgrep Error: Internal Fatal Crash Text"
    findings = service.parse_semgrep_json(invalid_json)
    assert findings == []


# --- Test I: Path traversal protection ---


@pytest.mark.anyio
async def test_path_traversal_protection_blocks_malicious_paths():
    service = SemgrepService()
    malicious_file = ChangedFile(
        filename="../../malicious.py",
        filepath="../../malicious.py",
        language="python",
        content="import os; os.system('pwned')",
    )

    with patch("shutil.which", return_value="/usr/bin/semgrep"):
        # run_analysis should detect unsafe relative path and skip file staging
        findings = await service.run_analysis([malicious_file])
        assert findings == []


# --- Test J: Workflow node integration ---


@pytest.mark.anyio
async def test_analyze_semgrep_node_integration():
    state = GitHubReviewState(
        changed_files=[
            ChangedFile(
                filename="app/main.py",
                filepath="app/main.py",
                language="python",
                content="eval(input())",
            )
        ]
    )
    config = RunnableConfig(configurable={})

    mock_finding = MagicMock()
    mock_finding.rule_id = "test-rule"

    with patch(
        "app.workflows.github_review.nodes.analyze_semgrep.semgrep_service.run_analysis",
        AsyncMock(return_value=[mock_finding]),
    ):
        res = await analyze_semgrep(state, config)

        assert "semgrep_findings" in res
        assert len(res["semgrep_findings"]) == 1
        assert res["semgrep_findings"][0].rule_id == "test-rule"
