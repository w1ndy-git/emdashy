# What changed and why

The reworded copy in `README.md` was produced by running the source one-pager
(`ORIGINAL.md`) through the `no-ai-slop` writing rules. This log records the
specific edits and the rule each one serves.

## Rule 1: No em dashes

The source uses the em dash as its main connector. Count in the original: 14.
Count in the rewrite: 0.

- "By the time it becomes a physical event — it was telegraphed" became two sentences: "By the time it turns physical, the warning was already there. It just arrived in pieces..."
- "Create your account in minutes — add SiftSuite Attack or Krypt" became "Account setup takes a few minutes. Add SiftSuite Attack for domain coverage or Krypt for individual coverage."
- Every section heading and list line dropped its em dash for a colon, a comma, or a period.

## Rule 4 and Rule 5: No intensifiers, no hollow statements

- "Enterprise-grade threat intelligence fusion at SMB price" (a slogan with no detail) became "enterprise threat intelligence fusion, priced for teams that don't staff a SOC," which names who the price is for.
- "always starts digitally" softened to "almost always starts online," which is defensible rather than absolute.

## Rule 7: No structural slop

The source "WHY SIFTSUITE" block is four cells built from one template
(LABEL, headline, one supporting line). That reads as machine output. The
rewrite replaces the four identical cells with three prose paragraphs of
different length and shape under "What SiftSuite runs on": one on the platform,
one that lists the actual feeds and what each is for, one on the output format.

## Rule 16: No dramatic headings

Headings now name their section instead of teasing it.

| Original heading | Reworded heading |
|---|---|
| THE PROBLEM | Attacks show up online weeks before they turn physical |
| LIVE SIGNAL CHAIN — ONE PRINCIPAL, SIX WEEKS | One principal, six weeks: a real signal chain |
| WHY SIFTSUITE | What SiftSuite runs on |
| THERE IS A WINDOW | The window between digital and physical |

## Naming over abstraction

- "TOXIC COMBINATION DETECTED" (product jargon) was replaced with a plain description of what the combination means: "one person who has been compromised, impersonated, tracked, and listed for sale inside six weeks."
- The signal chain became a table with a Week column, so the six-week timeline is legible at a glance instead of stated in the heading and lost in the list.
- The feed names (Snusbase, Malpedia, MalwareBazaar, Feodo, SSLBL, Ahmia) were paired with what each one covers, rather than listed as a bare string.

## What was kept

The concrete, checkable material carries the pitch, so it stayed: the Brian
Thompson reference, the "$5 wrench attack," the OpenCTI platform claim, the
five-signal chain with its severities, every price, and the two add-ons. The
rewrite removes the slop around these facts; it does not invent new ones.
