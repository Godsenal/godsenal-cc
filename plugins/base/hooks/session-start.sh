#!/bin/sh
# Silent under AGENT_HEADLESS=1: the caller names each skill itself.
if [ "${GBASE_SESSION_HOOK:-}" = off ] || [ "${AGENT_HEADLESS:-}" = 1 ]; then
  exit 0
fi
cat "$(dirname "$0")/session-start.md"
