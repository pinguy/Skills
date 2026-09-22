---
name: "minimum-sufficient-change"
description: "Minimise over-solving during implementation, repair, integration, automation, and local systems work. Use when an agent could add machinery, rewrite a subsystem, introduce dependencies, retrain a model, or otherwise solve more than the observed failure requires."
---

# Minimum sufficient change

Apply Maximum Parsimony and Minimum Description Length to engineering work.

## Core rule

**Use the smallest plausible intervention that fixes the observed failure, prove it through the real end-to-end path, escalate only when evidence falsifies the simpler approach, and stop when it works.**

Do not confuse sophistication with fitness. Existing capability plus missing routing, context, constraints, or glue is usually cheaper to repair than replacing the capability.

## Working loop

1. **State the actual failure.**
   - Describe the observed bad output or behaviour.
   - Separate it from guesses about the cause.
   - Name the user-visible acceptance check.

2. **Inspect the live path.**
   - Resolve the real files, services, configuration, versions, data flow, and entry point.
   - Find where the failure is introduced.
   - Reuse existing logs, examples, corrections, and known-good components.
   - Treat configured behaviour as unproven until exercised.

3. **Form the smallest plausible hypothesis.**
   - Ask what single missing connection, constraint, routing rule, context item, or local correction could explain the failure.
   - Prefer a narrow change with a short causal chain.
   - State what result would falsify the hypothesis.

4. **Choose the least machinery that can work.**
   Prefer, in order:
   - using the existing tool correctly;
   - supplying missing local context or parameters;
   - adding a small routing, validation, correction, or adapter layer;
   - changing configuration;
   - adding a bounded script or dependency;
   - replacing, retraining, or redesigning a subsystem.

   Skip directly to a larger intervention only when direct evidence rules out the cheaper levels.

5. **Preserve the working foundation.**
   - Back up or capture a rollback for material changes.
   - Keep user work and unrelated dirty state intact.
   - Avoid boot-critical, destructive, external, or difficult-to-reverse changes without the authority and recovery proof they require.
   - Make the change narrow enough that its effect is attributable.

6. **Test the real path end to end.**
   - Exercise the entry point the user actually uses, not only an isolated helper.
   - Compare before and after on the same representative case.
   - Check the intended outcome, important regressions, latency or resource overhead where relevant, and rollback viability.
   - Record commands, outputs, changed files, and concrete examples.

7. **Escalate only on evidence.**
   Escalation is justified when:
   - the simpler hypothesis was directly falsified;
   - repeated real cases show the narrow fix cannot cover the important failure class;
   - the workaround creates unacceptable fragility, latency, maintenance, or ambiguity;
   - the existing component lacks a required capability rather than merely lacking context or plumbing.

   When escalating, move one level at a time and retain the same acceptance test.

8. **Stop when sufficient.**
   - Stop once the acceptance check passes through the real path with acceptable overhead and no material regression.
   - Do not continue because a more elegant, general, fashionable, or intellectually interesting solution exists.
   - Record remaining imperfections honestly; do not turn them into compulsory scope.

## Anti-patterns

Reject these unless evidence specifically requires them:

- rewriting a subsystem before locating the fault;
- teaching or reimplementing capabilities the existing tool already has;
- adding an LLM where a deterministic rule is sufficient;
- building a framework for one bounded operation;
- retraining before trying vocabulary, context, routing, or correction layers;
- benchmarking synthetic cases while ignoring the user's real failures;
- polishing internal architecture after the user-visible path already meets the target;
- claiming improvement from configuration alone without an end-to-end canary;
- expanding scope because nearby problems are interesting.

## Scaling the method

For a trivial, reversible job, compress the loop to:

**observe → smallest fix → real-path check → stop**

For a material or fragile system, make the same loop more explicit with backups, baseline measurements, falsifiers, rollback, and receipts. Parsimony reduces unnecessary machinery; it never waives safety.

## Completion receipt

Report only what helps verify the result:

- observed failure and likely cause;
- smallest change made and why it was sufficient;
- before/after or equivalent canary;
- overhead and regressions checked;
- files or state changed;
- rollback location when material;
- what remains imperfect.

If the acceptance test fails, say so plainly and identify which evidence justifies the next escalation.
