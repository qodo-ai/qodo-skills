<h3>PR Summary by Qodo</h3>

Make refunds idempotent

<code>✨ Enhancement</code> <code>🧪 Tests</code> <code>🕐 10-20 Minutes</code>

<details>
<summary>AI Description</summary>

><pre>
>• Add an idempotency key to refunds.
>• Test duplicate refund requests.
></pre>

</details>

<details>
<summary>Diagram</summary>

```mermaid
sequenceDiagram
    Client->>API: POST /refunds
    API->>Ledger: write
```

</details>

<details>
<summary>High-Level Assessment</summary>

>Reuse the existing idempotency table.

</details>
