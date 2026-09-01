# Security

Report security issues privately to security@qodo.ai. Do not open a public issue containing
credentials, customer data, or an exploitable vulnerability.

This package contains instructions and metadata only. It must not contain credentials,
service tokens, copied authentication state, direct Qodo API clients, or executable
post-install hooks. Authentication belongs to the local `qodo` runtime and begins with
`qodo login`.

Marketplace manifests intentionally declare no MCP server. A future MCP addition requires a
separate threat model, authentication design, and marketplace review; it must not be slipped
into a skill release.
