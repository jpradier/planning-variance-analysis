#!/usr/bin/env bash
# import-all.sh — import the variance PPTX flow into watsonx Orchestrate
#
# Run from the project root:
#   bash tools/variance_pptx_flow/import-all.sh
#
# This script imports:
#   1. The PPTX renderer Python tool (generate_c1_revenue_variance_pptx)
#   2. The agentic flow (variance_pptx_flow) that gathers PA data + renders
#   3. The PA agent (pa_agent)
#
# Prerequisites:
#   - orchestrate CLI authenticated to the target environment
#   - ibm-pa-tools MCP toolkit already registered in the platform
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")/../..")"

echo "==> [1/3] Importing PPTX renderer tool..."
orchestrate tools import -k python \
  -f tools/generate_c1_revenue_variance_pptx/generate_c1_revenue_variance_pptx.py \
  -r tools/generate_c1_revenue_variance_pptx/requirements.txt \
  -p tools/generate_c1_revenue_variance_pptx

echo ""
echo "==> [2/3] Importing variance PPTX flow..."
orchestrate tools import -k flow \
  -f tools/variance_pptx_flow/variance_pptx_flow.py

echo ""
echo "==> [3/3] Importing PA agent..."
orchestrate agents import -f agents/pa_agent.yaml

echo ""
echo "Done."
echo "  Verify tools: orchestrate tools list | grep -E 'variance'"
echo "  Verify agent: orchestrate agents list | grep pa_agent"
