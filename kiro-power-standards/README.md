# Qodo Standards for Kiro

Generated skills contain the complete reviewed Qodo playbooks for this release.
Install or update Qodo Standards through the Kiro Powers marketplace.
The Qodo CLI remains a separate runtime and is never bundled here.

## Optional read-only permission

The stable `qodo read ...` gateway exposes only tools that the live Qodo catalog
explicitly marks non-mutating. To remove repeated safe-read prompts, choose **Always allow**
for the exact `qodo read *` pattern in Kiro, or review and merge
`qodo-read-only.permissions.yaml` into your user- or workspace-scoped Kiro permissions.
Keep every other Qodo command on ask. The Power never changes permission files itself.

- Privacy: https://www.qodo.ai/privacy-policy/
- Support: https://help.qodo.ai/hc/en-us/requests/new
- Terms: https://www.qodo.ai/terms/
