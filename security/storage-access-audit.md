# Contract Storage Access Audit

The audit policy lives in `security/storage-access-policy.json` and is checked
by `scripts/audit_storage_access.py`.

Run it locally with:

```bash
python3 scripts/audit_storage_access.py
```

The check inventories typed Soroban storage keys, verifies that documented
sensitive keys exist, flags policy entries for removed keys, and requires every
admin-sensitive storage write to be marked as multisig-admin governed.

Admin multisig is enforced operationally by deploying each contract with an
admin `Address` that is a Stellar account configured with the required signer
weights and thresholds. Contract code still calls `Address::require_auth()`;
the audit makes the multisig requirement explicit so deployments and reviews do
not silently downgrade to a single signer.
