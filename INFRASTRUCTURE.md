# Infrastructure

For the human owner. Agents don't need this file.

Verify each GitHub feature against current documentation before relying on it; GitHub changes these often. Items marked **verify** are ones I'm least sure behave as described.

## 1. Repositories

| Repo | Visibility | What |
|---|---|---|
| `app-template` | Public | Template for new apps: the example app. Maintained by the maintainer; no workspace |
| `static-ai-apps.github.io` | Public | The library, published at the site root |
| `.static-ai-apps.github.io` | Public | The curator's workspace: a fork of the library |
| `my-app` / `.my-app` | Public | One pair per app, created by CI |
| `org-ci` | Public | CI: workflows, checks, config. Maintained by the maintainer. Public so Actions minutes are free |
| `alerts` | **Private** | Issues only: where alerts land. Watch it |
| `.github` | Public | Org-wide `SECURITY.md` and profile |

### Governance lives outside the org

This repository lives in your personal account as `static-ai-apps-governance`, not in the org. Locally it's always cloned into `<root>/governance`. Only you change it, with whatever help you choose; no agent and no App can reach it, because every agent identity is scoped to the org. The core reads governance only from your clone, `<root>/governance`, and gives every agent its rules and a read-only copy.

`governance` stays in the org's `reserved_names`, and in the core's own reserved list: links to `static-ai-apps/governance` keep redirecting to its home, and no app can take the name.

## 2. GitHub Apps

Three Apps, created in the org's settings. Use Apps rather than machine accounts: scoped permissions, short-lived tokens, and identities that are easy to tell apart.

| App | Repository permissions | Installed on | Private key held by |
|---|---|---|---|
| `static-ai-apps-ic` | Contents: write; Pull requests: write | All repos | The core |
| `static-ai-apps-curator` | Contents: write; Pull requests: write | All repos | The core |
| `static-ai-apps-ci` | Administration, Contents, Pull requests, Pages, Issues: write | All repos | `org-ci` secrets |

The core narrows each session's tokens to one app and the permissions it needs there ([core/README.md](core/README.md)). The installation permissions are only the ceiling.

None of the Apps gets Workflows permission, so nothing they push can contain a workflow file.

Put the bot logins in `org-ci/config/config.json` under `identities`. They're the App's slug plus `[bot]`.

## 3. `org-ci` settings

- **Variables:** `CI_APP_ID`
- **Secrets:** `CI_APP_PRIVATE_KEY`; optionally `ALERT_WEBHOOK_URL` (anything that accepts `{"text": …}`, such as Slack or ntfy) and `SAFE_BROWSING_API_KEY`
- **Branch protection on `main`:** only you push; but allow `github-actions[bot]` to push `HEARTBEAT`, or the monthly heartbeat fails and scheduled workflows stop after 60 days of inactivity
- Give the core a credential that can dispatch workflows here (`actions: write` on `org-ci` only)

## 4. Rulesets (org level)

Defense in depth: even a token with contents write shouldn't be able to change a published repo.

- **Published repos** (every repo not starting with `.`, except `app-template`, `org-ci`, `alerts`, `.github`): restrict creations, updates and deletions on all branches; bypass for `static-ai-apps-ci` only.
- **`app-template`:** restrict updates on all branches; bypass for org owners. This keeps App tokens out; it doesn't affect the maintainer, whose token acts as you.
- Workspaces need no rules: the IC owns them outright.

Rulesets on public repos are available on the free plan (**verify**).

## 5. Org settings

- **Interaction limits:** "collaborators only" org-wide. Not essential, since CI closes pull requests from anyone but the agents, but it cuts noise. Limits expire after at most six months; renew them.
- **Private vulnerability reporting:** on for all repos. CI enables it for new apps.
- **`SECURITY.md`** in `.github`: how to report a harmful app privately.
- **Actions:** allowed org-wide. CI disables Actions on each workspace individually.

## 6. One-time setup

1. Create `governance` in your own account, and the org's repos from section 1. Push `app-template`, the library, and `org-ci`.
2. Create the three Apps and install them on all repos.
3. Add `org-ci`'s variables and secrets.
4. Enable Pages on the library: deploy from `main`, root.
5. Fork the library as `.static-ai-apps.github.io` in the same org. **Verify** that GitHub lets you fork within the org under a different name; `create-app` depends on it for every app. If it doesn't, the fallback is to create workspaces as ordinary repos and have CI copy files across instead of using pull requests between forks.
6. On the library workspace: Issues off, Actions off, Pages off.
7. Run `self-test` once to check the detectors on GitHub's runners, then `bake` once.
8. Dispatch `create-app` by hand for a first test app, and check both repos came out right.

## 7. The core and the maintainer

Everything for running agents lives in one project folder on your machine, which can be moved or copied as a unit:

```
<root>/governance/   your clone of this repository: you run the core from here
<root>/repos/        one clone per org repo, named as on GitHub, and nothing else: all the maintainer sees
<root>/.config/      secrets: the core's keys and tokens, the maintainer's token and Claude login
<root>/data/         the ledger, session logs, assembled rules
```

To create it: `git clone` this repository into `<root>/governance`, then run `python3 governance/core/core.py setup`. It makes the rest, clones the repos, and lists the secrets still to add. `.config/` holds the App keys, so treat any copy of the folder as secret, or copy it without `.config/` and recreate that on the other side.

**The core** ([core/](core/)) is the only thing that starts agents, and the only code here that runs on your machine. It holds the App keys and the Claude token, gives every agent its rules in its system prompt, mints narrow tokens per session, runs each session in a fresh container from the agent image (`core/image/`), caps spending, runs the daily cycle, keeps the ledger, and dispatches CI after sessions. Before acting, it fast-forwards `<root>/governance` from GitHub, so it always runs what you've pushed and nothing else. It refuses to run from anything in `repos/`, which the maintainer can edit.

**The maintainer** runs in its own long-lived container, started with `python3 governance/core/core.py maintainer`. It sees `repos/` at `/repos` and your governance clone, read-only, at `/governance`; its rules are in its system prompt. Its GitHub access is a fine-grained token you create for it, kept in `.config/maintainer/env` as `GH_TOKEN=…`:

- **Resource owner:** static-ai-apps. **Repositories:** all repositories. Governance is in your account, so a token for the org can't reach it. **Expiry:** 30 days.
- **Repository permissions, read and write:** Actions, Contents, Pull requests, Workflows.

Its instructions confine it to `org-ci` and `app-template`; the token isn't narrowed to match, because GitHub can't tell its actions from yours anyway. Governance it only reads.

**Changing governance, the core included,** is yours: commit and push from `<root>/governance` (or any clone of it). Don't leave edits there unpushed, or the core's update stops fast-forwarding. The core picks up what you push on its next run.

Fine-grained tokens for an org must be allowed in the org's settings (Personal access tokens). The maintainer signs in to Claude inside its container the first time; the login is kept in `.config/maintainer/home/`.

The daily cycle can run on a schedule or when you start it by hand each evening; it's the same either way. Before relying on unattended runs, check that they fit your Claude plan's terms of use.

**Calibrating the budget.** Your plan's allowance isn't stated in dollars, so learn the exchange rate: run the first few sessions by hand and note each session's estimated cost against how much of your usage meter it consumed. Then set the pool to leave comfortable headroom for your own use. A starting guess to adjust: curator allowance $2, IC sessions capped at $3, a pool of about $10 a day. Also confirm on the first run that sessions report an estimated cost and stop at their cap when you're signed in with a subscription.

## 8. Alerts

Alerts arrive as issues in the private `alerts` repo, and optionally on your webhook. Three sources:

| Source | Example |
|---|---|
| CI detectors on every pull request | An app opens WebSockets on load; a new external host |
| Agents' `## Needs human` notes, scanned daily | An IC reports that another app looks like a miner |
| Safe Browsing, checked daily (needs an API key) | Google flags the site |

Plus the public, through private vulnerability reports, which GitHub delivers to you directly.

Agent notes are quoted, not followed: they're reports, possibly from a compromised agent.

## 9. Kill switch

1. Stop running the core, and stop any session that's running (`docker ps --filter name=saa-`, then `docker stop`). No new sessions; existing tokens expire within an hour.
2. Run `governance/core/kill-switch.sh stop`. Actions stop org-wide, so nothing merges.
3. If it's urgent, suspend the IC and curator Apps in the org's installation settings. Their tokens stop working at once.

Published sites stay up. To take one app down: `gh api -X DELETE repos/static-ai-apps/<app>/pages`.

To resume, reverse the order: `kill-switch.sh resume`, unsuspend the Apps, run the core again.

## 10. Open items

Planned changes to governance and the core are in [ROADMAP.md](ROADMAP.md). CI work is in the maintainer's notes in `org-ci`.
