---
title: Third-Party Notices
date: 2026-07-16
type: reference
status: current
---

# Third-Party Notices

## Hatch Pet deterministic backend

Goodboy includes a pinned snapshot of deterministic image-processing scripts
from OpenAI's bundled Hatch Pet Codex skill.

- Location: `src/goodboy/vendor/hatch_pet/`
- Upstream snapshot date: 2026-07-16
- License: Apache License 2.0
- License copy: `src/goodboy/vendor/hatch_pet/LICENSE.txt`

The vendored files are currently unmodified except for their placement inside
the Goodboy package. Goodboy-owned wrappers, contracts, orchestration, identity
logic, and tests live outside the vendored directory.
