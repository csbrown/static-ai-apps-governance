"""Tests for the core, against a fake `docker`, a mocked GitHub and local git repos. No network.

Usage: python3 governance/core/tests/test_core.py     (exits non-zero on failure)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORE = HERE.parent / "core.py"
TMP = Path(tempfile.mkdtemp(prefix="core-test-"))
(TMP / "bin").mkdir()
shutil.copy(HERE / "fake-docker", TMP / "bin" / "docker")
os.chmod(TMP / "bin" / "docker", 0o755)
os.environ.update(STATIC_AI_APPS_HOME=str(TMP / "root"), STATIC_AI_APPS_NO_UPDATE="1",
                  FAKE_LOG=str(TMP / "docker.log"), PATH=f"{TMP / 'bin'}:{os.environ['PATH']}")
sys.path.insert(0, str(HERE.parent))
import core as C  # noqa: E402

failures = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        failures.append(what)


def docker_runs():
    if not Path(os.environ["FAKE_LOG"]).exists():
        return []
    return [json.loads(line) for line in open(os.environ["FAKE_LOG"]) if json.loads(line)[0] == "run"]


def arg(cmd, flag):
    return cmd[cmd.index(flag) + 1]


def mounts(cmd):
    return [cmd[i + 1] for i, a in enumerate(cmd) if a == "-v"]


# ---------- configuration, as setup writes it, then filled in ----------

C.CONF_DIR.mkdir(parents=True)
cfg = dict(C.DEFAULT_CONFIG)
cfg["apps"] = {"ic": {**cfg["apps"]["ic"], "id": 1}, "curator": {**cfg["apps"]["curator"], "id": 2}}
(C.CONF_DIR / "config.json").write_text(json.dumps(cfg))
for f in ["ic.pem", "curator.pem", "claude-token", "github-token"]:
    (C.CONF_DIR / f).write_text("x\n")
check(not any(str(TMP) in v for v in json.dumps(cfg).split('"')), "config holds no absolute paths")

# ---------- a whole cycle ----------

existing = {"test-timer", ".test-timer", "static-ai-apps.github.io", ".static-ai-apps.github.io"}
calls = []


def fake_github(method, path, token=None, body=None, ok404=False):
    calls.append((method, path, body))
    if method == "GET" and path.startswith("/repos/static-ai-apps/") and path.count("/") == 3:
        name = path.split("/")[3]
        return {"name": name} if name in existing else None
    if path.endswith("/pulls?state=open&per_page=100"):
        repo = path.split("/")[3]
        return [{"number": 7, "user": {"login": "static-ai-apps-ic[bot]"},
                 "head": {"repo": {"full_name": f"static-ai-apps/.{repo}"}}}]
    if "create-app.yml/dispatches" in path:
        existing.update({body["inputs"]["name"], "." + body["inputs"]["name"]})
    return None


C.github = fake_github
C.mint = lambda cfg, role, repos, perms: f"tok-{role}-{'+'.join(repos)}"
C.prepare_clone = lambda org, repo, tok, dest: dest.mkdir(parents=True)
C.wait_for_app = lambda cfg, name, token, seconds=300: C.is_app(cfg, name, token)


class Args:
    force = False


C.cmd_cycle(Args())
recs = C.ledger_records()
print(C.ledger_text(recs))
check([r["role"] for r in recs] == ["curator", "ic", "ic", "ic"], "curator first, then three IC sessions")
check([r["repo"] for r in recs[1:]] == ["kitchen-timer", "test-timer", "test-timer"], "queue order and skips")
check(sum(r["cost"] for r in recs[1:]) <= cfg["pool"], "IC spending stays within the pool")
runs = docker_runs()
check(all("bypassPermissions" in r and "--max-budget-usd" in r and "--max-turns" in r for r in runs),
      "every session has a budget cap, a turn cap and the unattended permission mode")
check(all(arg(r, "--append-system-prompt-file") == C.RULES_IN_CONTAINER for r in runs),
      "every session gets the rules in its system prompt")
check(all("Agent" in arg(r, "--disallowedTools").split(",") for r in runs), "every session has sub-agents switched off")
check(all(f"{C.GOV}:/governance:ro" in mounts(r) for r in runs), "every session gets governance, read-only")
check(all(m.endswith(":ro") for r in runs for m in mounts(r) if "/governance" in m or C.RULES_IN_CONTAINER in m),
      "the rules and governance are mounted read-only")
check(all("{{" not in arg(r, "-p") for r in runs), "preambles fully filled")
rules = {d.name.split("-")[2]: (d / "rules.md").read_text() for d in C.SESSIONS.iterdir()}
def has(text, name):
    return f"<!-- /governance/{name} -->" in text


check(has(rules["ic"], "IC.md") and not has(rules["ic"], "CURATOR.md"), "an IC gets IC.md, not CURATOR.md")
check(has(rules["curator"], "CURATOR.md") and not has(rules["curator"], "IC.md"), "the curator gets CURATOR.md, not IC.md")
check(all(has(t, "GOVERNANCE.md") and has(t, "SPEC.md") for t in rules.values()),
      "every role gets GOVERNANCE.md and SPEC.md")
check(not list(C.DATA_DIR.rglob("session.env")), "no token files left on disk")
dispatched = [c[1].split("/")[-2] for c in calls if c[1].endswith("/dispatches")]
check(dispatched.count("create-app.yml") == 1 and dispatched.count("pipeline.yml") == 3, "CI dispatched")

home = next(C.SESSIONS.glob("*-ic-kitchen-timer-*")) / "home"


def cred(url):
    out = subprocess.run(["git", "-c", "credential.interactive=false", "credential", "fill"],
                         input=f"url={url}\n\n", capture_output=True, text=True,
                         env={**os.environ, "HOME": str(home), "WS_TOKEN": "secret-ws", "GIT_TERMINAL_PROMPT": "0"})
    return "password=secret-ws" in out.stdout


check(cred("https://github.com/static-ai-apps/.kitchen-timer.git"), "the workspace token reaches the workspace")
check(not cred("https://github.com/static-ai-apps/kitchen-timer.git"), "...and not the published repo")
check(not cred("https://github.com/static-ai-apps/.test-timer.git"), "...and not another app's workspace")
try:
    C.cmd_cycle(Args())
    check(False, "a second cycle the same day is refused")
except SystemExit:
    check(True, "a second cycle the same day is refused")

# ---------- one-off sessions respect the daily pool ----------

C.cfg_pool_before = cfg["pool"]


class SessionArgs:
    repo, budget, advice, advice_file = "test-timer", 3, "x", None


n_before = len(docker_runs())
try:
    C.cmd_session(SessionArgs())
except SystemExit:
    pass
granted = C.ledger_records()[-1]["granted"] if len(docker_runs()) > n_before else 0
check(granted <= max(0, cfg["pool"] - sum(r["cost"] for r in recs[1:])) + 1e-9,
      "a one-off session can't exceed what's left of today's pool")

# ---------- the maintainer's container ----------

(C.MAINT_DIR).mkdir(parents=True, exist_ok=True)
(C.MAINT_DIR / "env").write_text("GH_TOKEN=x\n")
(C.ROOT / "repos").mkdir(exist_ok=True)
subprocess.run([sys.executable, str(CORE), "maintainer"], check=True)
m = docker_runs()[-1]
vols = mounts(m)
check(f"{C.REPOS}:/repos" in vols and f"{C.GOV}:/governance:ro" in vols, "the maintainer sees repos/ and read-only governance")
check(not any(str(C.CONF_DIR) in v or "ledger" in v or str(C.SESSIONS) in v for v in vols),
      "...and not the core's keys, the ledger or session logs")
check(arg(m, "--append-system-prompt-file") == C.RULES_IN_CONTAINER and "-p" not in m,
      "the maintainer is interactive, with its rules in its system prompt")
check("Agent" in arg(m, "--disallowedTools").split(","), "the maintainer has sub-agents switched off too")
check(has((C.DATA_DIR / "maintainer-rules.md").read_text(), "MAINTAINER.md"), "the maintainer's rules include MAINTAINER.md")

# ---------- the core's own integrity: a real git clone of governance ----------

remote = TMP / "remote-governance.git"
subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
work = TMP / "seed"
shutil.copytree(C.GOV, work, ignore=shutil.ignore_patterns(".git", "__pycache__"))
G = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
subprocess.run(G + ["-C", str(work), "add", "-A"], check=True)
subprocess.run(G + ["-C", str(work), "commit", "-qm", "v1"], check=True)
subprocess.run(["git", "-C", str(work), "push", "-q", str(remote), "main"], check=True)

project = TMP / "project"
project.mkdir()
subprocess.run(["git", "clone", "-q", str(remote), str(project / "governance")], check=True)
env = {k: v for k, v in os.environ.items() if k not in ("STATIC_AI_APPS_HOME", "STATIC_AI_APPS_NO_UPDATE")}

# Run from the maintainer's working copy: refused.
(project / "repos").mkdir()
subprocess.run(["git", "clone", "-q", str(remote), str(project / "repos" / "governance")], check=True)
r = subprocess.run([sys.executable, str(project / "repos" / "governance" / "core" / "core.py"), "ledger"],
                   capture_output=True, text=True, env=env)
check(r.returncode != 0 and "working copy" in r.stderr, "the core refuses to run from the maintainer's working copy")

# A new commit on GitHub reaches the trusted clone before the core acts.
(work / "README.md").write_text((work / "README.md").read_text() + "\nUpdated.\n")
subprocess.run(G + ["-C", str(work), "commit", "-qam", "v2"], check=True)
subprocess.run(["git", "-C", str(work), "push", "-q", str(remote), "main"], check=True)
r = subprocess.run([sys.executable, str(project / "governance" / "core" / "core.py"), "build"],
                   capture_output=True, text=True, env=env)
head = subprocess.run(["git", "-C", str(project / "governance"), "log", "-1", "--format=%s"],
                      capture_output=True, text=True).stdout.strip()
check(head == "v2" and "Governance updated" in r.stderr, "the core updates itself from GitHub before acting")

# Setup creates the layout and clones what's missing, governance included, from the trusted clone's origin.
r = subprocess.run([sys.executable, str(project / "governance" / "core" / "core.py"), "setup"],
                   capture_output=True, text=True, env={**env, "GIT_CONFIG_GLOBAL": str(TMP / "gitconfig")})
check((project / ".config" / "core" / "config.json").exists() and (project / "data").is_dir()
      and oct((project / ".config").stat().st_mode)[-3:] == "700", "setup creates the layout, private where it should be")
check("have   repos/governance" in r.stdout, "setup recognises the maintainer's governance copy")

shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if failures else 0)
