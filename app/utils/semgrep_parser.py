from typing import Any


def parse_semgrep_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for result in payload.get("results", []):
        severity = (result.get("extra", {}).get("severity") or "UNKNOWN").upper()
        if severity not in {"HIGH", "CRITICAL"}:
            continue
        findings.append(
            {
                "file_path": result.get("path", ""),
                "rule_id": result.get("check_id", "unknown"),
                "severity": severity,
                "code_snippet": result.get("extra", {}).get("lines", ""),
            }
        )
    return findings
