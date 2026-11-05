# Instructions

This repository is the governance layer for the static-ai-apps organization: the rules every agent and process works under. Everyone reads it; only the human owner pushes to it. It lives in the owner's account, outside the org, so no agent identity can reach it. Every agent gets its rules from here in its system prompt, and a read-only copy at `/governance`.

## Read in this order

**Every agent:**

1. [GOVERNANCE.md](GOVERNANCE.md): mission, repository pairs, roles, objectives, permissions, trust, harm
2. [SPEC.md](SPEC.md): the technical rules CI enforces

**Then your role:**

- Individual contributor, working on one app: [IC.md](IC.md), then [ADVICE.md](ADVICE.md)
- Curator, working on the library: [CURATOR.md](CURATOR.md), then skim [ADVICE.md](ADVICE.md) so your advice speaks the same language as the ICs' instructions
- Maintainer, working on the org's infrastructure with the owner: [MAINTAINER.md](MAINTAINER.md)

**The human owner:**

- [INFRASTRUCTURE.md](INFRASTRUCTURE.md): repos, Apps, settings, setup, alerts, kill switch.
- [ROADMAP.md](ROADMAP.md): planned changes to governance and the core.
- [core/](core/): the core, the only thing that starts agents, and how to run it. CI is in [static-ai-apps/org-ci](https://github.com/static-ai-apps/org-ci).

## Version

Governance v0.9 (draft). See the changelog at the end of GOVERNANCE.md.
