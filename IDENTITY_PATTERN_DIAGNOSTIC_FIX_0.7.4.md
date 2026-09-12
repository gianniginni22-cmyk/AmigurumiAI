# Amigurumi AI — Identity / Pattern Diagnostic Fix v0.7.4 candidate

## Why this candidate exists

The distributed Windows build was observed to identify BENCH-001 (Mr Bean Teddy Bear) as a kangaroo/wallaby. The source core benchmark itself remains green because CORE-008 validates the deterministic compiler with structured benchmark inputs, not live visual recognition.

A separate UI observation showed the Pattern panel at the initial `—` placeholder. The current source renderer already replaces an empty pattern with an explicit diagnostic message, and the deterministic compiler produces non-empty patterns in 36/36 source tests. Therefore the installed screenshot cannot by itself prove a compiler regression; this candidate adds a `generation_trace` to `/api/generate` so the next real run exposes the exact pipeline stage and pattern character/part counts.

## Changes

1. Stronger identity-first Design Model prompt:
   - explicitly rejects silhouette/pose-only classification;
   - requires adversarial comparison with at least one plausible alternative;
   - requires at least two specific identity evidence items;
   - records plausible identity alternatives.
2. `identity_evidence` and `identity_alternatives` are now part of the strict Design Model schema.
3. Identity Gate is more conservative: confidence >= 0.75, at least two distinctive features, and at least two identity evidence items. Image-only input is allowed when the model provides those checks; text contradictions still block the gate.
4. `/api/generate` exposes `generation_trace` with app version, endpoint, Design Model part count, Shape Graph node count, compiled pattern-part count, pattern character count and assembly character count.
5. Added regression coverage for the new identity contract.

## Verification

- 37/37 pytest PASS
- py_compile PASS

## Not yet verified

The identity correction is a prompt/schema improvement and still requires one real BENCH-001 API run. It must not be called fixed until the live app recognizes the Teddy Bear and the generation trace confirms a non-zero pattern.
