---
title: Goodboy Versus Hatch Pet Benchmark Protocol
date: 2026-07-16
type: protocol
status: current
---

# Goodboy Versus Hatch Pet Benchmark Protocol

Goodboy must not claim superior source likeness merely because it has more identity machinery. The claim requires a frozen, blinded comparison against the Hatch Pet baseline.

## Primary Question

For a specific source identity, which output looks more like that identity?

Secondary questions:

- cross-state identity consistency;
- visual appeal;
- animation clarity.

Technical validity and unacceptable failures are veto gates, not aesthetic votes.

## Unit Of Analysis

The unit is the source identity, not an individual frame.

Each identity produces one blinded trial containing a Goodboy output and a Hatch output generated under a documented provider/budget policy. Multiple reviewers rate the trial. Reviewer votes are collapsed to one identity-level outcome before aggregate statistics are calculated.

This prevents identities with more frames or more observations from dominating the result.

## Freeze The Protocol

```bash
goodboy benchmark init <benchmark-dir> \
  --benchmark-id goodboy-v2 \
  --seed <private-randomization-seed> \
  --release-min-identities 30 \
  --min-raters 3
```

Initialization writes:

- a frozen protocol plus a private policy-lock hash;
- a private seed and answer key;
- a 65% decisive likeness win-rate threshold;
- a 50% null threshold;
- 95% confidence;
- zero permitted v2-validity deficit;
- zero permitted excess unacceptable-failure rate;
- minimum appeal and clarity tie-adjusted rates of 45%.

Every later prepare, rating, and analysis command verifies the policy lock. Do
not edit thresholds after looking at ratings. Start a new benchmark instead.

## Comparison Manifest

```json
{
  "identities": [
    {
      "identity_id": "pet-001",
      "source_set_id": "sources-001",
      "goodboy_output": "/private/path/goodboy.png",
      "hatch_output": "/private/path/hatch.png",
      "goodboy_package": "/private/path/goodboy-package",
      "hatch_package": "/private/path/hatch-package",
      "cohort": {
        "species": "dog",
        "coat": "asymmetric"
      },
      "provider_budget": {
        "provider": "same-provider",
        "attempts_per_method": 2
      }
    }
  ]
}
```

Prepare randomized trials:

```bash
goodboy benchmark prepare <benchmark-dir> \
  --comparisons /absolute/path/comparisons.json
```

Goodboy deterministically randomizes the method into A or B, copies blinded outputs, and writes the method/path/hash mapping only to `private/answer-key.json`.

Each package directory must contain the actual `pet.json` and
`spritesheet.webp` for that method. Goodboy independently validates the v2
metadata and exact `1536x2288` atlas, then records hashes in the private answer
key. Legacy `goodboy_v2_valid` and `hatch_v2_valid` booleans can be ingested for
compatibility, but they are explicitly marked unverified and can never satisfy
the technical-evidence release gate.

The review packet does not include source pixels. Reviewers must receive the approved source reference set through a separate controlled channel.

## Reviewer Submission

```json
{
  "reviewer_id": "reviewer-01",
  "ratings": [
    {
      "trial_id": "trial-0001",
      "likeness": "A",
      "identity_consistency": "A",
      "visual_appeal": "tie",
      "animation_clarity": "B",
      "unacceptable": [],
      "notes": "A preserves the side marking; B has smoother motion."
    }
  ]
}
```

Each choice must be `A`, `B`, or `tie`. `unacceptable` may contain `A`, `B`, both, or neither.

Every submission must cover every trial exactly once, and a reviewer ID may submit only once:

```bash
goodboy benchmark rate <benchmark-dir> \
  --ratings /absolute/path/reviewer-01.json
```

Use at least three independent reviewers per identity. Reviewers must not inspect filenames, metadata, provider receipts, prompts, or the answer key.

## Analysis

```bash
goodboy benchmark analyze <benchmark-dir>
```

For each question:

1. decode A/B only after ratings are stored;
2. take a strict method majority per identity;
3. record a tie when neither method has a strict majority;
4. calculate decisive Goodboy win rate;
5. calculate tie-adjusted rate where a tie is 0.5;
6. report a Wilson 95% interval over decisive identity outcomes;
7. report a 10,000-sample identity-cluster bootstrap interval.

## Claim Gates

Every gate must pass:

- all trials have the minimum number of reviewers;
- at least the predeclared number of identities is analyzed;
- decisive likeness win rate is at least 65%;
- the Wilson lower bound is above 50%;
- both methods have independently validated, hash-recorded v2 packages;
- Goodboy v2 validity is not below Hatch validity;
- Goodboy's unacceptable-rating rate is not above Hatch's;
- visual appeal tie-adjusted rate is at least 45%;
- animation clarity tie-adjusted rate is at least 45%.

If any gate fails, the result is:

> WITHHELD: the predeclared evidence does not permit a better source-likeness claim.

The generated report may be shared without source material or the private answer key. Failure clusters should still be inspected qualitatively before product decisions.

## Required Cohort Review

At minimum, inspect outcomes by:

- species or subject type;
- light, dark, patterned, and low-contrast coats/materials;
- symmetric versus asymmetric markings;
- long versus short fur;
- accessories;
- sparse versus multi-view references;
- provider/model snapshot;
- migration versus new build.

The current analyzer preserves cohort labels in each identity outcome. Cohort inference remains a human analysis step; do not overinterpret small groups.

## Privacy

Benchmark directories are private by default. They may contain copyrighted or personal source identities, generated outputs, local paths, a private seed, and the answer key. Do not commit them to the public Goodboy repository.
