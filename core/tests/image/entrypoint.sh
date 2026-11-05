#!/bin/sh
# Container entry: let git push with GH_TOKEN, unless the launcher has set up git itself.
set -e
if [ -n "$GH_TOKEN" ] && [ -z "$SANDBOX_GIT_PRECONFIGURED" ]; then
  gh auth setup-git >/dev/null 2>&1 || true
fi
exec "$@"
