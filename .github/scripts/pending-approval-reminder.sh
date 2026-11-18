#!/usr/bin/env bash
# Post ONE Slack message when a protected environment in the current workflow
# run has been waiting on a human reviewer for longer than the threshold.
#
# Runs as a sidecar job next to the gated job. It polls the run's pending
# deployments only so it can exit as soon as the gate is resolved: a sidecar
# that slept for the full threshold would keep the run (and its workflow
# concurrency group) open after a quick approval, delaying the next deploy.
#
# Only gates with required reviewers count. A wait timer or a branch policy is
# not something a person can click through, so it never triggers a reminder.
#
# Required env:
#   GH_TOKEN      - token with `actions: read` on this repository
#   REPO          - owner/name
#   RUN_ID        - the workflow run to watch
#   RUN_URL       - link included in the message
#   ENVIRONMENTS  - space-separated environment names to watch
#   SUBJECT       - what is waiting, e.g. "qodo-agent-runtime 1.2.3 production deploy"
#   WEBHOOK       - Slack incoming-webhook URL (empty -> warn and exit)
#
# Optional env:
#   REMIND_AFTER_SECONDS  - how long a gate may wait before the reminder. Default 900.
#   APPEAR_WINDOW_SECONDS - give up if no watched gate appears within this long
#                           (approved before the first poll, or the gate never
#                           ran). Default 600.
#   POLL_INTERVAL_SECONDS - default 30.
set -euo pipefail

: "${GH_TOKEN:?}" "${REPO:?}" "${RUN_ID:?}" "${RUN_URL:?}" "${ENVIRONMENTS:?}" "${SUBJECT:?}"
REMIND_AFTER_SECONDS="${REMIND_AFTER_SECONDS:-900}"
APPEAR_WINDOW_SECONDS="${APPEAR_WINDOW_SECONDS:-600}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-30}"

if [ -z "${WEBHOOK:-}" ]; then
  echo "::warning::Slack webhook not set - skipping the pending-approval reminder"
  exit 0
fi

# Prints the watched, reviewer-gated pending deployments as a JSON array.
# Fails (non-zero) on an API error so the caller can retry on the next poll.
pending_gates() {
  gh api "repos/${REPO}/actions/runs/${RUN_ID}/pending_deployments" |
    jq -c --arg envs "$ENVIRONMENTS" '
      ($envs | split(" ") | map(select(. != ""))) as $watched
      | [ .[] | select((.reviewers | length) > 0)
              | select(.environment.name as $n | $watched | index($n)) ]'
}

notify() {
  local gates="$1" minutes envs approvers
  minutes=$(( REMIND_AFTER_SECONDS / 60 ))
  envs="$(jq -r '[.[].environment.name] | unique | join(", ")' <<<"$gates")"
  approvers="$(jq -r '[.[].reviewers[].reviewer | (.login // .slug // .name)] | unique | join(", ")' <<<"$gates")"
  jq -n --arg s "$SUBJECT" --arg m "$minutes" --arg e "$envs" --arg a "$approvers" --arg u "$RUN_URL" '{
    text: "⏳ \($s) has been waiting \($m)+ min for approval (\($e)) · approvers: \($a) · <\($u)|review deployment>"
  }' > "${RUNNER_TEMP:-/tmp}/pending-approval.json"
  curl -sS --fail-with-body --max-time 30 \
    -X POST -H 'Content-type: application/json' \
    --data @"${RUNNER_TEMP:-/tmp}/pending-approval.json" "$WEBHOOK"
  echo
  echo "Reminder sent: ${envs} waiting on ${approvers}."
}

first_seen=''
while :; do
  if gates="$(pending_gates)"; then
    if [ "$(jq length <<<"$gates")" -gt 0 ]; then
      [ -n "$first_seen" ] || { first_seen=$SECONDS; echo "Gate pending: $(jq -r '[.[].environment.name] | join(", ")' <<<"$gates")"; }
      if (( SECONDS - first_seen >= REMIND_AFTER_SECONDS )); then
        notify "$gates"
        exit 0
      fi
    elif [ -n "$first_seen" ]; then
      echo "Gate resolved before the reminder threshold - nothing to send."
      exit 0
    elif (( SECONDS >= APPEAR_WINDOW_SECONDS )); then
      echo "No reviewer gate became pending - nothing to send."
      exit 0
    fi
  else
    echo "::warning::could not read pending deployments; retrying"
  fi
  sleep "$POLL_INTERVAL_SECONDS"
done
