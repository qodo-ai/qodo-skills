<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

1\. Refunds skip the ledger lock <code>📘 Rule violation</code> <code>⛨ Security</code>

<pre>
<b><i>issue_refund</i></b> writes the ledger row before taking the account lock.
</pre>

<details>
<summary><strong>Agent Prompt</strong></summary>

```
## Issue description
The ledger write happens outside the lock.
## Fix Focus Areas
- src/payments/refunds.py[40-44]
## Recommended Fix
Move `ledger.write` inside the lock.
```
</details>

[Dismiss ↗](https://app.qodo.ai/findings/11111111-1111-4111-8111-111111111111?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/11111111-1111-4111-8111-111111111111)
