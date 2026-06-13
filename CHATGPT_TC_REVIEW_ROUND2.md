# Trader Acelerator — T&C: Round 2 review request

**Context for ChatGPT:** You previously reviewed our Terms & Conditions for a small
digital educational platform (trading education, not financial advice; operated by
two founders; not yet incorporated; payments currently manual). You flagged a list of
issues. We agreed to apply **only items #1–4** now (internal inconsistencies + missing
standard boilerplate), and to defer the rest (#5–9) until we have a real lawyer and/or
scale to more jurisdictions and an automated payment processor.

Below are the **4 changes we actually applied**, quoted verbatim. For each, please
respond in this exact format:

> **Verdict:** APPROVED / NEEDS CHANGE
> **Residual risk (if any):**
> **Suggested replacement text (only if NEEDS CHANGE):**

Goal: shield the operator (me) as much as legally reasonable for a pre-incorporation,
pre-lawyer digital education product. Be strict — if any of these 4 still has a hole,
say so. If you think any of the deferred items (#5–9) is actually a *must-fix-now* and
we were wrong to defer it, flag it separately at the end. **Do not rewrite the whole
document** — only react to these 4 and to anything you consider genuinely
launch-blocking.

---

## FIX #1 — Legal entity / counterparty disclosure (was: implied a company that doesn't exist)

**Your original concern:** The document referred to "Trader Acelerator" as
"Company" without any legal form (LLC/Corp) or physical address, leaving the
counterparty undefined — a real "who am I contracting with?" risk.

**What we added (new paragraph at the end of Section 1, "Acceptance of Terms"):**

> Trader Acelerator is, as of the date of these Terms, an unincorporated business
> operated by its founders. References in these Terms to "Trader Acelerator,"
> "Company," "we," "us," or "our" refer to that operating business and the
> individuals operating it. We will update this section to reflect any future
> change in legal/corporate structure.

**Question:** Does this adequately disclose the counterparty for a pre-incorporation
business, or do we still need a named individual and/or physical/registered address
to be enforceable and to avoid a consumer-protection "hidden seller identity" problem?

---

## FIX #2 — Internal inconsistency: arbitration clause pointed to a postal "contact address" that didn't exist

**Your original concern:** Section 14 (Dispute Resolution) told users to "send written
notice to our contact address" for the arbitration opt-out and to "contact us at the
address listed in Section 17," but Section 17 (Contact) only provided an **email**, not
a postal address — an internal inconsistency.

**What we changed — Section 14, "Informal Resolution First":**

> Before initiating any formal proceeding, you agree to contact us at the email
> address listed in Section 17 and give us a reasonable opportunity of at least
> thirty (30) days to resolve the dispute informally.

**What we changed — Section 14, "Opt-Out":**

> You may opt out of this arbitration agreement by sending written notice to the
> email address listed in Section 17 within thirty (30) days of first accepting
> these Terms. If you opt out, you and Trader Acelerator each agree to submit to
> the exclusive jurisdiction of the courts specified in Section 15.

(Section 17 — now Section 18 after Fix #4 — still provides
`support@traderacelerator.com` as the contact.)

**Question:** Is allowing the arbitration opt-out and informal-resolution notice to be
delivered **by email only** (no postal address) enforceable and consumer-fair under the
AAA Consumer Arbitration Rules / typical US consumer law? Or does a binding arbitration
+ class-action-waiver clause require a physical opt-out address to survive scrutiny?

---

## FIX #3 — Cancellation friction (FTC "Click to Cancel")

**Your original concern:** If subscribing is one click but cancelling requires going
through human support, that violates the FTC 2024 "Click to Cancel" rule.

**What we verified (no text change needed):** Cancellation is already self-service in
the product — there is a `POST /account/cancel-plan` endpoint wired to a button in
account Settings (sets `cancel_at_period_end = True`; access continues until period end).
The Terms already describe it accurately in Section 10:

> You may cancel your subscription at any time through your account settings or by
> contacting support. Cancellation will take effect at the end of the current billing
> period, and you will retain access to the Service until that date. Voluntary
> cancellation does not entitle you to any refund for amounts already paid.

**Question:** Given that self-service cancellation genuinely exists in the UI (not just
in the text), does this clause satisfy the FTC Click-to-Cancel rule, or is additional
language required (e.g., explicit statement that cancellation requires no contact with
support and no retention/"save" flow)?

---

## FIX #4 — Missing standard boilerplate (added new Section 17, "General Provisions")

**Your original concern:** The document was missing standard protective clauses:
severability, entire agreement, survival, assignment, force majeure, and a guarantee
that changes aren't applied retroactively to already-paid periods.

**What we added — new Section 17, "General Provisions"** (Contact was renumbered to 18):

> **Entire Agreement:** These Terms, together with our Privacy Policy and any other
> policies referenced herein, constitute the entire agreement between you and Trader
> Acelerator regarding the Service and supersede any prior or contemporaneous
> agreements, communications, or proposals, whether oral or written.
>
> **Severability:** If any provision of these Terms is found by a court or arbitrator
> of competent jurisdiction to be invalid, illegal, or unenforceable, that provision
> shall be limited or eliminated to the minimum extent necessary, and the remaining
> provisions shall remain in full force and effect.
>
> **No Waiver:** Our failure to enforce any right or provision of these Terms shall not
> be deemed a waiver of such right or provision.
>
> **Assignment:** You may not assign or transfer these Terms, or any rights or
> obligations under them, without our prior written consent. We may assign or transfer
> these Terms, in whole or in part, without restriction, including in connection with a
> merger, acquisition, reorganization, or sale of assets.
>
> **Force Majeure:** We will not be liable for any failure or delay in performance
> resulting from causes beyond our reasonable control, including acts of God, natural
> disasters, war, terrorism, riots, labor disputes, internet or telecommunications
> failures, or actions of governmental authorities or third-party service or
> infrastructure providers.
>
> **No Retroactive Changes to Paid Periods:** Any changes we make to these Terms, to
> subscription prices, or to the features included in a plan will not retroactively
> reduce the access or features you are entitled to for a billing period you have
> already paid for in full; such changes take effect, at the earliest, at the start of
> your next billing cycle as described in Section 5.
>
> **Survival:** Sections of these Terms that by their nature should survive termination
> of your account or these Terms — including, but not limited to, Intellectual Property
> & Content License, Disclaimers, Limitation of Liability, Indemnification, Dispute
> Resolution, Governing Law, and this General Provisions section — shall survive any
> such termination.

**Question:** Are these 7 clauses complete and correctly worded? Is anything standard
still missing (e.g., notices, third-party beneficiaries, headings/interpretation,
export controls, U.S.-government-end-user, electronic communications consent)? Flag only
what you consider genuinely important for this stage.

---

## Deferred items (for your reference — we are NOT changing these now)

We agreed to defer the following until we have a lawyer / scale. Tell us only if you
think any is actually launch-blocking and we're wrong to defer:

5. AAA arbitration fee allocation not specified.
6. Heavy use of "sole discretion" / unilateral terms.
7. "Not financial advice" disclaimer doesn't immunize if product/marketing behaves like advice (product-operations issue, not text).
8. Rewards/gamification: enforcement matters, not just text (we verified spin/daily are free, no purchase required).
9. "No refunds" is aggressive (but standard for instant-delivery digital content; EU buyers would later need an explicit waiver-of-withdrawal checkbox at checkout).

**End of request.**
