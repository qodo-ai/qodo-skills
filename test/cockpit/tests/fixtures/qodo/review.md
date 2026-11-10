<h3>Code Review by Qodo</h3>

<code>🐞 Bugs (1)</code>  <code>📘 Rule violations (1)</code>  <code>🔗 Cross-repo conflicts (0)</code>  <code>📜 Skill insights (1)</code>  <code>🧠 Memories (0)</code>

<!-- qodo-summary-omitted-findings -->
> ⚠️ _2 lower-priority findings omitted to fit the comment size limit; re-run the review or view the findings in the Qodo portal._

<img src="https://www.qodo.ai/wp-content/uploads/2025/11/light-grey-line.svg" height="10%" alt="Grey Divider">

<br/>

<img src="https://img.shields.io/badge/High-634FD1?style=flat-square" height="20px" alt="Action required">

<details>
<summary>  1.  Refunds skip the ledger lock <code>📘 Rule violation</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
><b><i>issue_refund</i></b> writes the ledger row before taking the account lock, so two refunds can
>race and both succeed.
></pre>
></details>

> <details open>
><summary>Code</summary>
><br/>
>
><code>[src/payments/refunds.py[R40-44]](https://github.com/acme/shop/pull/12/files#diff-abcR40-R44)</code>
>
>```diff
>+    ledger.write(row)
>```
></details>

> <details>
><summary>Evidence</summary>
><br/>
>
><pre>
>The lock is acquired on line 46, after the write on line 41.
></pre>
>
> <code>Rule 101: [Take the account lock before any ledger write](https://app.qodo.ai/rules/101?state=active)</code>
></details>

> <details>
><summary>Agent prompt</summary>
><br/>
>
>```
>## Issue description
>The ledger write happens outside the lock.
>## Fix Focus Areas
>- src/payments/refunds.py[40-44]
>## Recommended Fix
>Move `ledger.write` inside the `with account.lock()` block.
>```
> <code>ⓘ Copy this prompt and use it to remediate the issue with your preferred AI generation tools</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/11111111-1111-4111-8111-111111111111?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/11111111-1111-4111-8111-111111111111)

<hr/>
</details>

<img src="https://img.shields.io/badge/Medium-634FD1?style=flat-square" height="20px" alt="Remediation recommended">

<details>
<summary>  2.  Cache key ignores currency <code>🐞 Bug</code> <code>⭐ New</code></summary>

<br/>

> <details open>
><summary>Description</summary>
><br/>
>
><pre>
>The price cache key omits the currency code.
></pre>
></details>

> <details open>
><summary>Code</summary>
><br/>
>
><code>[src/cache/prices.py[17]](https://github.com/acme/shop/pull/12/files#diff-defR17-R17)</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/22222222-2222-4222-8222-222222222222?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/22222222-2222-4222-8222-222222222222)

<hr/>
</details>

<img src="https://img.shields.io/badge/Low-634FD1?style=flat-square" height="20px" alt="Informational">

<details>
<summary>  3.  Test repeats fixture values <code>📜 Skill insight</code></summary>

> <details open>
><summary>Code</summary>
><br/>
>
><code>[tests/test_refunds.py[R5-9]](https://github.com/acme/shop/pull/12/files#diff-123R5-R9)</code>
></details>

[Dismiss ↗](https://app.qodo.ai/findings/33333333-3333-4333-8333-333333333333?action=dismiss&origin=git) | [View ↗](https://app.qodo.ai/findings/33333333-3333-4333-8333-333333333333)
</details>

<h3>Resolved findings</h3>

<details>
<summary>  1.  <s>Refund amount uses floats</s> <code>✓ Resolved</code></summary>
</details>

<details>
<summary>  2.  <s>Old endpoint still registered</s> <code>⊘ Outdated</code></summary>
</details>
