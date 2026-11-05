# Roadmap

Planned changes to governance and the core: things decided to be worth doing, but not yet. Each says why, what it would involve, and what to check before relying on it. CI work that doesn't touch governance is tracked in the maintainer's notes in `org-ci` instead.

Only the owner changes this file, like the rest of this repository. The maintainer may propose items.

## 1. Keep the Claude token out of agent containers

**Why.** Today each IC and curator session has the Claude token in its container's environment ([core/README.md](core/README.md), "What the core can't promise"). An agent that goes looking can read it, copy it elsewhere, or start a second Claude process with no budget cap. Until this is fixed, a session's real limits are its 55-minute wall clock and the plan's own usage limits, not its budget.

**Where we're heading: the loop outside, the tools inside.** Run the agent loop, the part that talks to Anthropic and holds the token, on the owner's machine. Run everything Claude asks to do in the session's container, file access included. Nothing the model asks for executes on the owner's machine, and the container holds no Claude credential.

Two ways to build it:

- **A. Claude Code as the loop, on the host,** with its built-in local tools switched off, plus a small tool bridge (shell, read, write, edit) that runs each call inside the container. Keeps the subscription login. Preferred.
- **B. Our own loop against Anthropic's API.** The most transparent option, but it needs an API key, billed separately from the subscription.

What it would simplify: the token can't leak from a container; budget caps hold even against an agent that doesn't cooperate; the rule against starting other agents ([GOVERNANCE.md](GOVERNANCE.md) §8) becomes a capability; the image no longer needs Claude Code; the maintainer can work the same way.

Before relying on it:

- The exact settings that switch off every built-in local tool, web fetching included. Fetching would run on the host; it's harmless, but it should be a decision, not an accident.
- Subagents and skills don't bring local tools back.
- Nothing else in Claude Code runs on the host because of what the model asks for.
- File tools run inside the container, never against the mounted folder from the host side, where a planted link could reach the owner's files.
- The arrangement fits the plan's terms of use.

**Afterwards, remove the soft rule.** Once agents genuinely can't start other agents, the prose against it is no longer needed, so refactor it out rather than leave it beside the capability that replaced it. Rules that describe impossible actions are noise in every system prompt, and they blur which rules are enforced and which rest on an agent's cooperation. Specifically:

- [GOVERNANCE.md](GOVERNANCE.md) §8, "One agent per session": keep the fact (every session is a single agent, started only by the core) and drop the prohibition, the "rule, not a capability" caveat and the shut-down warning.
- The matching lines in [IC.md](IC.md) §8, [CURATOR.md](CURATOR.md) §2 and [MAINTAINER.md](MAINTAINER.md) rule 7. Keep the IC's advice on splitting large tasks across sessions, which is still useful.
- [core/README.md](core/README.md), guarantee 2, and "What the core can't promise".
- Then check the remaining rules the same way: anything else written as a prohibition that the new design makes impossible.

Keep the core's `--disallowedTools Agent`: it costs nothing and covers sub-agents whatever the loop looks like.

**A smaller step on the way, if wanted:** Claude Code's sandboxed Bash tool inside each container, with the token denied to every command the agent runs, strict mode on so commands can't leave the sandbox, and permission rules stopping the Read tool from reading the process's own environment. Check first that the sandbox starts inside an unprivileged container; it needs a weaker nesting mode there.

**An alternative to either:** give agent sessions an API key in its own Claude Console workspace with a spending limit, and keep the subscription for the owner and the maintainer. A leaked key could then cost no more than that limit.

**Status:** deferred, 2026-11-05. The current containers stay the boundary for now; short sessions and a watch on the usage meter cover the risk meanwhile.

## 2. Move governance to the owner's account

**Why.** Governance in the org means the maintainer's token has to be limited to selected repositories to keep it out. Outside the org, it can simply cover the whole org.

**How:** the checklist in [INFRASTRUCTURE.md](INFRASTRUCTURE.md) §1.

**Status:** after bootstrapping, once the first cycles have run cleanly.

## 3. Schedule the daily cycle

**Why.** Today the owner runs `core.py cycle` by hand. A schedule would make the system run without the owner present.

**Before relying on it:** check that unattended runs fit the plan's terms of use; have run enough cycles by hand to trust the budget calibration; consider item 1 done or its risk accepted.

**Status:** after the first week of manual cycles.

## 4. Budget policy

**Why.** The curator decides the whole pool ([GOVERNANCE.md](GOVERNANCE.md) §11.3). If its allocations show bias, two additions were discussed: a formula-based floor, so apps whose stars are growing get some sessions regardless of the curator; and a small lottery slice for exploration.

**Also:** calibrate credits against the plan's allowance after the first week ([INFRASTRUCTURE.md](INFRASTRUCTURE.md) §7).

**Status:** watch the ledger; revisit after a month.

## 5. Q computed by CI

**Why.** Until CI computes it, the curator estimates Q itself ([GOVERNANCE.md](GOVERNANCE.md) §6.4), and nothing independent checks the figure the curator is judged by.

**How:** a CI job, built by the maintainer, computing Q exactly as §6 defines it and publishing it where the curator and the owner can read it. Q's definition stays here.

**Status:** after the first apps have stars to count.

## 6. A watchdog

**Why.** Every agent now has a stake in something: stars, Q, or keeping CI working. A watchdog would have none: a read-only agent that looks for harm in recently merged apps and reports straight to the owner, not through files other agents can edit.

**How:** a new role, with its own rules here and its own session type in the core.

**Status:** after the system has been running for a while, if the existing detectors and alerts prove not to be enough.
