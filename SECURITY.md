# Security Policy

## Supported Versions

Goodboy is currently an alpha developer tool. Security fixes target the main branch and the latest published release, when releases exist.

## Reporting A Vulnerability

Please report vulnerabilities privately through GitHub security advisories if enabled for the repository, or contact the maintainer directly through the repository owner profile.

Do not include raw API keys, private source images, generated provider payloads, or personal pet project artifacts in public issues.

## Secrets And Local Data

Goodboy reads provider credentials from environment variables such as `OPENAI_API_KEY` and `GEMINI_API_KEY`. The project is designed not to write raw keys into manifests, logs, docs, or generated packages.

Local Goodboy project folders can contain private source images, generated character art, approvals, provider metadata, and install packages. The repository ignores `projects/**` by default; keep private projects outside commits unless they are deliberate synthetic fixtures.

