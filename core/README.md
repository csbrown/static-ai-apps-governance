# The core

The only thing that starts agents. The human owner runs it on the host; no agent can change it, because it lives in the governance repository, where only the owner pushes.

It guarantees five things, and nothing else needs to be trusted for them:

1. **Every agent starts with the rules in its system prompt:** `GOVERNANCE.md`, `SPEC.md` and its role's file, assembled from governance at the start of each session. System-prompt text stays in view for the whole session, unlike the first message, which long sessions summarize away. The whole repository is mounted read-only at `/governance`.
2. **Only the core starts agents.** The curator asks for IC sessions through its requests file; it never launches them. Claude Code's sub-agent tool is switched off in every session, the maintainer's included. Starting an agent from the shell is forbidden by the rules ([GOVERNANCE.md](../GOVERNANCE.md) §8), but can't yet be prevented, because the Claude token is in the container ([roadmap](../ROADMAP.md), item 1).
3. **Each session gets only narrow, short-lived credentials.** The core holds the App keys and the Claude token, and mints per-session GitHub tokens limited to one app.
4. **Spending is capped,** per session (Claude Code's own budget and turn caps, plus a time limit) and per day (the pool, tracked in a ledger only the core writes).
5. **Every agent runs in a container** that sees only what it needs: never your home directory, the core's keys, or the Docker socket.

Everything else, such as CI, the checks, the template and tooling, lives in the org and is the maintainer's to change.

## The project folder

```
<root>/governance/   a clone of this repository: the core runs from here, and it's mounted read-only into agents
<root>/repos/        one clone per project repo, named as on GitHub: all the maintainer sees
<root>/.config/      core/ (App keys, tokens, config) and maintainer/ (its token and Claude login)
<root>/data/         the ledger, session folders, and assembled rules
```

`<root>/governance` is yours. The maintainer has its own working copy in `repos/governance` for drafting proposals. The core refuses to run from that copy, because the maintainer can edit it.

Before most commands, the core fast-forwards `<root>/governance` from GitHub and restarts itself if anything changed. Only you can push there, so sessions always get current governance and the core never runs code you didn't push.

## Setting up

```sh
mkdir static-ai-apps && cd static-ai-apps
git clone https://github.com/static-ai-apps/governance.git governance
pip install pyjwt cryptography
python3 governance/core/core.py setup     # creates the rest; rerun any time to see what's missing
python3 governance/core/core.py build     # the agent image; rerun to update Claude Code
```

`setup` lists what to put in `.config/`:

| File | What |
|---|---|
| `core/config.json` | The IC and curator App ids, budgets, limits. Paths in it are relative to its folder |
| `core/ic.pem`, `core/curator.pem` | The two Apps' private keys |
| `core/claude-token` | A Claude token for sessions: run `claude setup-token` and save what it prints |
| `core/github-token` | A fine-grained token for the org with Actions: write on `org-ci`, to start CI after sessions |
| `maintainer/env` | One line, `GH_TOKEN=…`: the maintainer's token ([INFRASTRUCTURE.md](../INFRASTRUCTURE.md) §7) |

Then `chmod 600` them.

## Running

```sh
C=governance/core/core.py
python3 $C maintainer                                   # the maintainer, interactive; --shell for bash
python3 $C session ic test-timer --budget 2 --advice "…" # one IC session, outside the cycle
python3 $C cycle                                        # the daily cycle
python3 $C ledger --days 7                              # what sessions spent and shipped
```

Run `cycle` once a day, by hand or from cron. It refuses to run twice in a day unless you pass `--force`. A one-off `session` counts against the same daily pool.

Session folders are kept under `data/sessions/` for 14 days, each with its clone, its rules, the Claude transcript in `home/.claude/` and `result.json`. They're the audit trail.

## What a session gets

A fresh container from the agent image, as a non-root user, with memory, CPU and process limits:

| Inside | What |
|---|---|
| `/work/<repo>` | A clone of the workspace, with `origin` (the workspace) and `upstream` (the published repo) |
| `/governance` | This repository, read-only |
| `/etc/static-ai-apps/rules.md` | The role's rules, read-only, passed with `--append-system-prompt-file` |
| `/home/node` | An empty home, apart from a `.gitconfig` that gives the workspace token to the workspace URL only |
| `WS_TOKEN` | The role's App, limited to `.<repo>`, contents write. Used by git |
| `GH_TOKEN` | The role's App, limited to `<repo>` and `.<repo>`, pull requests write and contents read. Used by `gh` |
| `CLAUDE_CODE_OAUTH_TOKEN` | The Claude token |

It runs `claude -p <preamble>` with the session's budget as `--max-budget-usd`, `--max-turns`, the sub-agent tool switched off (`--disallowedTools Agent`), and the unattended permission mode. The preamble ([`preambles/`](preambles/)) gives the session's facts and how-to; the rules come through the system prompt. Tokens expire after an hour and sessions stop at 55 minutes.

The maintainer's container is long-lived and interactive: `repos/` at `/repos`, governance read-only at `/governance`, its rules in its system prompt, and its own token and Claude login from `.config/maintainer/`.

## The daily cycle

1. **The curator's session,** capped at the curator allowance, with today's pool and yesterday's ledger in its preamble.
2. **Its requests,** from `/work/requests.json`, checked: `create` (a name and a pitch, dispatched to CI's `create-app`) and `launch` (an existing app, a budget within the per-session maximum, advice). At most 20 are read.
3. **The queue,** one session at a time in the curator's order. Each session's actual spend comes off the pool; a request bigger than what's left is skipped; the cycle stops when the pool is nearly spent or the usage limit is hit. What didn't run expires.
4. **After each session:** a ledger record, and CI is asked to check any pull request right away.

Advice sits between two copies of a random marker made for each session, with the marker removed from the advice, so advice can't fake the end of its block.

## Configuration

| Setting | Default |
|---|---|
| `curator_allowance` | 2 |
| `pool` | 10 |
| `max_session` | 3 |
| `max_turns` | 200 |
| `time_limit_minutes` | 55 |
| `model` | Claude Code's default |
| `container` | 4 GB memory, 2 CPUs, 1024 processes |
| `keep_sessions_days` | 14 |

Budgets are credits: estimated US dollars of usage ([GOVERNANCE.md](../GOVERNANCE.md) §11).

## Stopping

Stopping the core stops all agent activity. To stop a running session: `docker ps --filter name=saa-`, then `docker stop <name>`. For the whole org, see [`kill-switch.sh`](kill-switch.sh) and [INFRASTRUCTURE.md](../INFRASTRUCTURE.md) §9.

## What the core can't promise

- **The Claude token is in every container,** because a subscription login can't be scoped. A hijacked agent could copy it, spend your allowance elsewhere, or start a second Claude process with no budget cap, so a session's hard limits are really its time limit and your plan's usage limits. Watch your usage meter. Keeping the token out of containers is item 1 on the [roadmap](../ROADMAP.md).
- **Reading the rules isn't obeying them.** After the start of a session, the guarantees come from capabilities: token scopes, CI, caps and isolation.
- **Nested containers are off.** Docker-in-Docker, or the Docker socket, would give an agent control of your machine. If one ever needs nested containers, use Sysbox or a VM.

## Testing

`python3 governance/core/tests/test_core.py` runs a whole cycle against a fake `docker` and a mocked GitHub, and checks the maintainer's container, setup, self-update, and the refusal to run from the maintainer's copy.
