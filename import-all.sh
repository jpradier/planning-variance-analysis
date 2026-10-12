#!/usr/bin/env bash
# import-all.sh — import the full Planning Analytics workspace into watsonx Orchestrate
#
# Run from anywhere inside the repo:
#   bash import-all.sh
#
# What is imported (in dependency order):
#   1. Connection   — PlanningAnalyticsConnection (server_url substituted from .env)
#   2. Credentials  — username=apikey / password=$PLANNING_KEY  (draft + live)
#   3. Toolkit      — ibm-pa-tools MCP (url=$PLANNING_MCP_URL)
#   4. Python tool  — export_table_to_excel
#   5. Python tool  — generate_c1_revenue_variance_pptx
#   6. Flow tool    — variance_pptx_flow
#   7. Agent        — pa_agent
#
# Prerequisites:
#   - .env file at the project root with PLANNING_URL, PLANNING_KEY,
#     PLANNING_MCP_URL
#   - orchestrate CLI installed and authenticated to the target environment
#   - project .venv at <repo-root>/.venv (created by: python -m venv .venv &&
#     .venv/bin/pip install ibm-watsonx-orchestrate-adk)
set -euo pipefail

ROOT="$(cd "$(git rev-parse --show-toplevel 2>/dev/null || echo "$(dirname "$0")")" && pwd)"

# ---------------------------------------------------------------------------
# Activate the project venv so the correct `orchestrate` + Python are used
# ---------------------------------------------------------------------------
VENV="${ROOT}/.venv"
if [[ ! -f "${VENV}/bin/activate" ]]; then
  echo "ERROR: project venv not found at ${VENV}" >&2
  echo "       Create it with: python -m venv .venv && .venv/bin/pip install ibm-watsonx-orchestrate-adk" >&2
  exit 1
fi
# shellcheck source=/dev/null
source "${VENV}/bin/activate"

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
ENV_FILE="${ROOT}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: .env file not found at ${ENV_FILE}" >&2
  exit 1
fi
# Export only KEY=VALUE lines (skip comments and blank lines)
set -o allexport
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +o allexport

# Validate required variables
for var in PLANNING_URL PLANNING_KEY PLANNING_MCP_URL; do
  if [[ -z "${!var:-}" ]]; then
    echo "ERROR: ${var} is not set in .env" >&2
    exit 1
  fi
done

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
step() { echo ""; echo "==> $*"; }

# ---------------------------------------------------------------------------
# 1. Connection — substitute <PLANNING_URL> placeholder and import
# ---------------------------------------------------------------------------
step "[1/7] Importing PlanningAnalyticsConnection..."
CONN_SRC="${ROOT}/toolkits/ibm-pa-tools/connections/PlanningAnalyticsConnection.yaml"
CONN_TMP="$(mktemp /tmp/PlanningAnalyticsConnection.XXXXXX.yaml)"
trap 'rm -f "${CONN_TMP}"' EXIT

sed "s|<PLANNING_URL>|${PLANNING_URL}|g" "${CONN_SRC}" > "${CONN_TMP}"
orchestrate connections import -f "${CONN_TMP}"

# ---------------------------------------------------------------------------
# 2. Credentials — apikey / $PLANNING_KEY for draft and live
# ---------------------------------------------------------------------------
step "[2/7] Setting credentials for PlanningAnalyticsConnection (draft + live)..."
for env in draft live; do
  orchestrate connections set-credentials \
    -a PlanningAnalyticsConnection \
    --env "${env}" \
    -u "apikey" \
    -p "${PLANNING_KEY}"
done

# ---------------------------------------------------------------------------
# 3. MCP Toolkit — ibm-pa-tools (URL from .env, per environment)
#    draft  → PLANNING_MCP_URL
#    live   → PLANNING_MCP_URL
#    The toolkit itself is environment-agnostic; we register the URL for the
#    active environment via `orchestrate toolkits add --url`.
# ---------------------------------------------------------------------------
step "[3/7] Importing ibm-pa-tools MCP toolkit..."
if orchestrate toolkits list 2>/dev/null | grep -q "ibm-pa-tools"; then
  echo "    Toolkit 'ibm-pa-tools' already exists — skipping."
else
  orchestrate toolkits add \
    --kind mcp \
    --name ibm-pa-tools \
    --description "IBM Planning Analytics MCP server — explore cubes, run MDX, manage sandboxes and processes." \
    --url "${PLANNING_MCP_URL}" \
    --transport streamable_http \
    --tools "*" \
    --app-id PlanningAnalyticsConnection
fi

# ---------------------------------------------------------------------------
# 4. Python tool — export_table_to_excel
# ---------------------------------------------------------------------------
step "[4/7] Importing export_table_to_excel tool..."
pip install --quiet -r "${ROOT}/tools/export_table_to_excel/requirements.txt"
orchestrate tools import -k python \
  -f "${ROOT}/tools/export_table_to_excel/export_table_to_excel.py" \
  -r "${ROOT}/tools/export_table_to_excel/requirements.txt" \
  -p "${ROOT}/tools/export_table_to_excel"

# ---------------------------------------------------------------------------
# 5. Python tool — generate_c1_revenue_variance_pptx
# ---------------------------------------------------------------------------
step "[5/7] Importing generate_c1_revenue_variance_pptx tool..."
pip install --quiet -r "${ROOT}/tools/generate_c1_revenue_variance_pptx/requirements.txt"
orchestrate tools import -k python \
  -f "${ROOT}/tools/generate_c1_revenue_variance_pptx/generate_c1_revenue_variance_pptx.py" \
  -r "${ROOT}/tools/generate_c1_revenue_variance_pptx/requirements.txt" \
  -p "${ROOT}/tools/generate_c1_revenue_variance_pptx"

# ---------------------------------------------------------------------------
# 6. Flow tool — variance_pptx_flow
# ---------------------------------------------------------------------------
step "[6/7] Importing variance_pptx_flow flow tool..."
orchestrate tools import -k flow \
  -f "${ROOT}/tools/variance_pptx_flow/variance_pptx_flow.py"

# ---------------------------------------------------------------------------
# 7. Agent — pa_agent
# ---------------------------------------------------------------------------
step "[7/7] Importing pa_agent..."
orchestrate agents import -f "${ROOT}/agents/pa_agent.yaml"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "Import complete. Verify with:"
echo "  orchestrate connections list"
echo "  orchestrate toolkits list   | grep ibm-pa-tools"
echo "  orchestrate tools list      | grep -E 'export_table|variance'"
echo "  orchestrate agents list     | grep pa_agent"
echo "=========================================="
