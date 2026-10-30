#!/bin/sh
set -eu
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 MODEL_ID /absolute/path/to/results" >&2
  exit 2
fi
agentre_dataset_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
agentre_model_id=$1
agentre_results_dir=$2
case "$agentre_results_dir" in
  /*) ;;
  *) echo "Use an absolute path for the results directory." >&2; exit 2 ;;
esac
case "$agentre_results_dir/" in
  "$agentre_dataset_dir/"*) echo "Keep results outside this dataset directory." >&2; exit 2 ;;
esac
case "$agentre_model_id" in
  anthropic/*) ;;
  */*) echo "This folder supports the anthropic provider." >&2; exit 2 ;;
  *) agentre_model_id="anthropic/$agentre_model_id" ;;
esac
: "${ANTHROPIC_API_KEY:?Set ANTHROPIC_API_KEY through your normal secret configuration}"
exec "${AGENTRE_HARBOR_BIN:-harbor}" run \
  -p "$agentre_dataset_dir/tasks" --jobs-dir "$agentre_results_dir" \
  --env docker -a claude-code -m "$agentre_model_id" \
  --agent-kwarg permission_mode=dontAsk --agent-kwarg version=2.1.112
