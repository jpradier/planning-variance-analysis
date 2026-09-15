#!/usr/bin/env bash
# import-all.sh — import generate_c1_revenue_variance_pptx into watsonx Orchestrate
set -euo pipefail
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo "==> Importing generate_c1_revenue_variance_pptx tool..."
orchestrate tools import -k python \
  -f "${SCRIPT_DIR}/generate_c1_revenue_variance_pptx.py" \
  -r "${SCRIPT_DIR}/requirements.txt" \
  -p "${SCRIPT_DIR}"

echo ""
echo "Done."
echo "  Verify: orchestrate tools list | grep variance_pptx"
