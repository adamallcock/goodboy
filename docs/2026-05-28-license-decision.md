---
title: License Decision
date: 2026-05-28
type: decision-record
status: accepted
---

# License Decision

## Decision

Goodboy uses the MIT License for the first public alpha release.

MIT is the best fit right now because Goodboy is intended to be easy to inspect, fork, wrap, and use inside local agent workflows without forcing downstream projects into a heavier compliance model.

## Options Considered

### MIT

Pros:

- Short, familiar, and easy for individuals and companies to understand.
- Allows commercial and private use with minimal friction.
- Good fit for developer tooling, examples, skills, plugins, and small CLIs.
- Keeps contribution and adoption overhead low for an alpha project.

Cons:

- Does not include an explicit patent grant.
- Does not require downstream source disclosure.
- Provides less contributor/legal structure than heavier licenses.

### Apache-2.0

Pros:

- Includes an explicit patent grant.
- Common for serious infrastructure and company-backed open-source projects.
- Provides more detailed contribution and notice terms than MIT.

Cons:

- Longer and slightly more intimidating for casual users.
- More paperwork-like for a small alpha tool.

### BSD-3-Clause

Pros:

- Permissive and business-friendly.
- Adds a non-endorsement clause.
- Familiar in infrastructure ecosystems.

Cons:

- Less common than MIT for small JavaScript/Python tooling.
- No explicit patent grant.

### GPL-3.0 Or AGPL-3.0

Pros:

- Ensures modifications remain open when redistributed, and AGPL extends that expectation to network use.
- Useful when protecting a commons matters more than adoption friction.

Cons:

- Too restrictive for Goodboy’s current goals.
- Can discourage companies or agent-tool authors from trying, embedding, or wrapping the project.
- Adds licensing questions that distract from the alpha pipeline and UI work.

## Asset Policy

The bundled Review Room demo assets are treated as part of the repository and covered by the MIT License unless a future asset-specific notice says otherwise.

Public demo assets are intentionally generic and optimized for size. They are included to make the UI explorable without private source photos, provider credentials, or generated-image folders.

## Revisit Trigger

Revisit the license if Goodboy grows into a hosted service, accepts broad external contributions, includes third-party assets with different terms, or needs an explicit patent grant for enterprise adoption.
