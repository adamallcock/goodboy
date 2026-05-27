# Goodboy Manifest Map

Load this reference when a Goodboy project has validation errors or unclear state.

- `goodboy.json`: project identity and output contract.
- `sources/source-images.json`: immutable source image copies, hashes, dimensions, roles, thumbnails.
- `sources/source-card.json`: editable semantic source description.
- `candidates/baseline-candidates.json`: planned or generated baseline directions.
- `candidates/baseline-*/candidate.json`: individual candidate metadata.
- `character/selected-candidate.json`: selected candidate record.
- `character/character-card.json`: reusable semantic identity contract.
- `feedback/events.json`: human, system, or vision-critic feedback events.
- `branches/*/branch.json`: explicit fork reason and parent/target metadata.
- `style/emotion-style-sheet.json`: state behavior, avoid rules, thresholds.
- `runs/<run-id>/generation-jobs.json`: provider jobs for row generation.
- `runs/<run-id>/provider-invocations/*.json`: provider handoff or execution records.
- `runs/<run-id>/qa/install-policy.json`: hard failures, warnings, and override reason.
- `runs/<run-id>/run-summary.json`: final output paths and run status.
