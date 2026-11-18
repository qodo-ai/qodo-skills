#!/usr/bin/env bash
# Post ONE Slack message per protected environment in the current workflow run
# that has been waiting on a human reviewer for longer than the threshold.
#
# Runs as a sidecar job next to the gated job(s). It polls only so it can exit
# as soon as nothing is left to remind about: a sidecar that slept for the full
# threshold would keep the run (and its workflow concurrency group) open after
# a quick approval, delaying the next deploy.
#
# Each watched environment gets its own clock, started when that gate first
# shows up as pending, so gates that open at different times (for example a
# matrix job queued behind another run) are each timed fairly.
#
# Only gates with required reviewers count. None of the watched environments
# combine reviewers with a wait timer or a custom protection rule, so a pending
# reviewer gate means a person has not clicked yet.
#
# The sidecar exits when no watched gate is pending (or every pending one was
# already reminded) and no gate can still open: either no job in the run is
# still queued, or every watched environment has already been seen.
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
#   POLL_INTERVAL_SECONDS - default 30.
#   MAX_API_FAILURES      - consecutive GitHub API failures before giving up. Default 10.
set -euo pipefail

: "${GH_TOKEN:?}" "${REPO:?}" "${RUN_ID:?}" "${RUN_URL:?}" "${ENVIRONMENTS:?}" "${SUBJECT:?}"
REMIND_AFTER_SECONDS="${REMIND_AFTER_SECONDS:-900}"
POLL_INTERVAL_SECONDS="${POLL_INTERVAL_SECONDS:-30}"
MAX_API_FAILURES="${MAX_API_FAILURES:-10}"

if [ -z "${WEBHOOK:-}" ]; then
  echo "::warning::Slack webhook not set - skipping the pending-approval reminder"
  exit 0
fi

# The watched, reviewer-gated pending deployments as a JSON array.
pending_gates() {
  gh api "repos/${REPO}/actions/runs/${RUN_ID}/pending_deployments" |
    jq -c --arg envs "$ENVIRONMENTS" '
      ($envs | split(" ") | map(select(. != ""))) as $watched
      | [ .[] | select((.reviewers | length) > 0)
              | select(.environment.name as $n | $watched | index($n)) ]'
}

# How many jobs in the run's latest attempt are queued and may still reach a
# watched gate. `waiting` is excluded: that is a job already sitting at a gate,
# which pending_gates reports directly.
unstarted_jobs() {
  gh api "repos/${REPO}/actions/runs/${RUN_ID}/jobs?per_page=100" |
    jq '[.jobs[] | select(.status == "queued" or .status == "pending" or .status == "requested")] | length'
}

notify() {
  local gates="$1" due="$2" minutes envs approvers payload
  minutes=$(( REMIND_AFTER_SECONDS / 60 ))
  envs="$(jq -r 'join(", ")' <<<"$due")"
  approvers="$(jq -r --argjson due "$due" '[.[] | select(.environment.name as $n | $due | index($n)) | .reviewers[].reviewer | (.login // .slug // .name)] | unique | join(", ")' <<<"$gates")"
  payload="${RUNNER_TEMP:-/tmp}/pending-approval.json"
  jq -n --arg s "$SUBJECT" --arg m "$minutes" --arg e "$envs" --arg a "$approvers" --arg u "$RUN_URL" '{
    text: "⏳ \($s) has been waiting \($m)+ min for approval (\($e)) · approvers: \($a) · <\($u)|review deployment>"
  }' > "$payload"
  curl -sS --fail-with-body --max-time 30 \
    -X POST -H 'Content-type: application/json' \
    --data @"$payload" "$WEBHOOK"
  echo
  echo "Reminder sent for: ${envs}"
}

# {env: {first: <SECONDS when first seen pending>, notified: bool}}
state='{}'
failures=0
while :; do
  # Jobs first: a job that moves from queued to waiting between the two reads
  # is then counted as unstarted or seen as a pending gate, never neither.
  if unstarted="$(unstarted_jobs)" && gates="$(pending_gates)"; then
    failures=0
    now=$SECONDS
    for env in $(jq -r '.[].environment.name' <<<"$gates"); do
      if [ "$(jq --arg e "$env" 'has($e)' <<<"$state")" = false ]; then
        echo "Gate pending: ${env}"
        state="$(jq --arg e "$env" --argjson t "$now" '.[$e] = {first: $t, notified: false}' <<<"$state")"
      fi
    done
    due="$(jq -c --argjson gates "$gates" --argjson now "$now" --argjson after "$REMIND_AFTER_SECONDS" '
      ([ $gates[].environment.name ] | unique) as $pending
      | [ to_entries[] | select(.key as $k | $pending | index($k))
          | select(.value.notified | not) | select($now - .value.first >= $after) | .key ]' <<<"$state")"
    if [ "$(jq length <<<"$due")" -gt 0 ]; then
      notify "$gates" "$due"
      state="$(jq --argjson due "$due" 'reduce $due[] as $e (.; .[$e].notified = true)' <<<"$state")"
    fi
    awaiting="$(jq --argjson gates "$gates" '
      [ $gates[].environment.name as $n | select((.[$n].notified // false) | not) ] | length' <<<"$state")"
    # Once every watched gate has been seen, a queued job (for example one
    # waiting on another concurrency group after approval) cannot open a new one.
    unseen="$(jq --arg envs "$ENVIRONMENTS" '
      ($envs | split(" ") | map(select(. != ""))) as $watched
      | [ $watched[] as $e | select(has($e) | not) ] | length' <<<"$state")"
    if [ "$awaiting" -eq 0 ] && { [ "$unstarted" -eq 0 ] || [ "$unseen" -eq 0 ]; }; then
      echo "No gate left to remind about - done."
      exit 0
    fi
  else
    failures=$(( failures + 1 ))
    echo "::warning::could not read the run's deployments or jobs (${failures}/${MAX_API_FAILURES})"
    if [ "$failures" -ge "$MAX_API_FAILURES" ]; then
      echo "::warning::GitHub API unavailable - giving up on the pending-approval reminder"
      exit 0
    fi
  fi
  sleep "$POLL_INTERVAL_SECONDS"
done
