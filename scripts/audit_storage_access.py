#!/usr/bin/env python3
"""Audit Soroban contract storage access against an explicit policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ENUM_RE = re.compile(r"pub\s+enum\s+(?P<name>\w+)\s*\{(?P<body>.*?)\n\}", re.S)
VARIANT_RE = re.compile(r"^\s*(?P<name>[A-Z]\w*)", re.M)
FUNCTION_RE = re.compile(r"pub\s+fn\s+(?P<name>\w+)\s*\(")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rust_files(path: Path) -> list[Path]:
    return sorted(path.glob("**/*.rs"))


def read_contract_source(path: Path) -> str:
    return "\n".join(file.read_text(encoding="utf-8") for file in rust_files(path))


def enum_keys(source: str, enum_names: list[str]) -> set[str]:
    keys: set[str] = set()
    for match in ENUM_RE.finditer(source):
        enum_name = match.group("name")
        if enum_name not in enum_names:
            continue
        for variant in VARIANT_RE.finditer(match.group("body")):
            keys.add(f"{enum_name}::{variant.group('name')}")
    return keys


def literal_symbol_keys(source: str) -> set[str]:
    keys = set()
    for literal in re.findall(r"Symbol::new\([^,]+,\s*\"([^\"]+)\"\)", source):
        keys.add(f"Symbol::{literal}")
    return keys


def functions(source: str) -> set[str]:
    return {match.group("name") for match in FUNCTION_RE.finditer(source)}


def storage_write_key_mentions(source: str) -> set[str]:
    mentions: set[str] = set()
    for key in re.findall(r"&((?:DataKey|RegistryKey|StorageKey)::[A-Z]\w*)", source):
        mentions.add(key)
    for key in literal_symbol_keys(source):
        if re.search(rf"set\([^)]*{re.escape(key.split('::', 1)[1])}", source):
            mentions.add(key)
    return mentions


def audit_contract(repo: Path, name: str, config: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    path = repo / config["path"]
    source = read_contract_source(path)
    declared = enum_keys(source, config.get("key_enums", [])) | set(config.get("literal_keys", []))
    literal_keys = literal_symbol_keys(source) & set(config.get("literal_keys", []))
    declared |= literal_keys
    policy = config.get("sensitive_writes", {})
    public_functions = functions(source)
    write_mentions = storage_write_key_mentions(source)

    failures: list[str] = []
    if len(declared) != len(list(declared)):
        failures.append(f"{name}: duplicate storage key declaration detected")

    for key in write_mentions:
        if key in declared and key not in policy:
            failures.append(f"{name}: storage key {key} is written/read but missing policy")

    for key, entry in policy.items():
        if key not in declared:
            failures.append(f"{name}: policy references undeclared storage key {key}")
        auth_model = entry.get("auth_model")
        if not auth_model:
            failures.append(f"{name}: {key} missing auth_model")
        authorized = entry.get("authorized_functions", [])
        if not authorized:
            failures.append(f"{name}: {key} missing authorized_functions")
        for fn in authorized:
            if fn not in public_functions:
                failures.append(f"{name}: {key} policy references missing function {fn}")
        if "admin" in str(auth_model) and not entry.get("admin_multisig_required", False):
            failures.append(f"{name}: {key} admin auth is not marked multisig-required")

    report = {
        "contract": name,
        "declared_keys": sorted(declared),
        "policy_keys": sorted(policy.keys()),
        "storage_key_mentions": sorted(write_mentions),
        "public_functions": sorted(public_functions),
    }
    return failures, report


def markdown(reports: list[dict[str, Any]], failures: list[str]) -> str:
    lines = [
        "## Contract Storage Access Audit",
        "",
        "| Contract | Declared Keys | Policy Entries | Status |",
        "|---|---:|---:|---|",
    ]
    failed_contracts = {failure.split(":", 1)[0] for failure in failures}
    for report in reports:
        status = "fail" if report["contract"] in failed_contracts else "pass"
        lines.append(
            f"| `{report['contract']}` | {len(report['declared_keys'])} | "
            f"{len(report['policy_keys'])} | {status} |"
        )
    if failures:
        lines.extend(["", "### Findings", ""])
        lines.extend(f"- {failure}" for failure in failures)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--policy", type=Path, default=Path("security/storage-access-policy.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/security"))
    args = parser.parse_args()

    repo = args.repo.resolve()
    policy_path = args.policy if args.policy.is_absolute() else repo / args.policy
    out_dir = args.output_dir if args.output_dir.is_absolute() else repo / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    policy = read_json(policy_path)
    failures: list[str] = []
    reports: list[dict[str, Any]] = []
    for name, config in policy.get("contracts", {}).items():
        contract_failures, report = audit_contract(repo, name, config)
        failures.extend(contract_failures)
        reports.append(report)

    payload = {"reports": reports, "failures": failures}
    (out_dir / "storage-access-audit.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    md = markdown(reports, failures)
    (out_dir / "storage-access-audit.md").write_text(md, encoding="utf-8")
    print(md)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
