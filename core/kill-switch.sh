#!/usr/bin/env bash
# Halt or resume all automation in the org. Run by an org owner with the GitHub CLI (`gh auth login`).
#
#   core/kill-switch.sh stop      disable Actions for every repository in the org
#   core/kill-switch.sh resume   re-enable Actions for every repository
#
# Stop the core first (no cycle running; `docker stop` any session): that ends agent sessions and new tokens.
# Published sites stay up. To take one app down: gh api -X DELETE repos/static-ai-apps/<app>/pages
set -euo pipefail
ORG="${ORG:-static-ai-apps}"

case "${1:-}" in
  stop)
    gh api -X PUT "orgs/$ORG/actions/permissions" -f enabled_repositories=none >/dev/null
    echo "Actions disabled for every repository in $ORG. Nothing will merge or run."
    echo "If you haven't already: stop any running sessions, and suspend the IC and curator Apps in"
    echo "  https://github.com/organizations/$ORG/settings/installations"
    ;;
  resume)
    gh api -X PUT "orgs/$ORG/actions/permissions" -f enabled_repositories=all -f allowed_actions=all >/dev/null
    echo "Actions re-enabled. Workspaces stay disabled individually; check with:"
    echo "  gh workflow run housekeeping.yml -R $ORG/org-ci"
    echo "Then unsuspend the Apps and resume running the core."
    ;;
  *)
    echo "usage: $0 stop|resume" >&2
    exit 2
    ;;
esac
