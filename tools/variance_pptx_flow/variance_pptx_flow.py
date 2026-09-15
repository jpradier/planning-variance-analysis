"""
variance_pptx_flow.py
=====================
Agentic Flow — fetches C1_Revenue data from IBM Planning Analytics via 5
separate MDX calls (as proper flow nodes), assembles the slide payload in a
Script node, enriches it with LLM-computed variance metrics and narrative
insights (gpt-oss-120b), then renders the PPTX via
generate_c1_revenue_variance_pptx.

Each ibm-pa-tools MCP call is a dedicated tool node referenced by its
registered name string.  No PA credentials are required in any Python tool —
the MCP toolkit handles authentication transparently.

The final render node references generate_c1_revenue_variance_pptx by its
registered name string (not as a Python callable) — this is the pattern that
causes the flow engine to surface the bytes output as a download link.

Import command
--------------
    orchestrate tools import -k flow -f tools/variance_pptx_flow/variance_pptx_flow.py
"""

from pydantic import BaseModel, Field

from ibm_watsonx_orchestrate.flow_builder.flows import END, START, Flow, PromptNode, flow

# ── Constants ─────────────────────────────────────────────────────────────────
_SERVER = "Region03N"
_CUBE   = "C1_Revenue"

# ── Flow-level schemas ────────────────────────────────────────────────────────


class VariancePptxFlowInput(BaseModel):
    """Parameters for the C1_Revenue variance PPTX flow."""
    server:   str = Field(default=_SERVER,                    description="TM1 server name")
    year_a:   str = Field(default="Y1",                       description="A_Year member for base period (e.g. 'Y1')")
    year_b:   str = Field(default="Y2",                       description="A_Year member for comparison period (e.g. 'Y2')")
    label_a:  str = Field(default="2024 Actual",              description="Human label for year A")
    label_b:  str = Field(default="2025 Actual",              description="Human label for year B")
    filename: str = Field(default="C1_Revenue_Variance.pptx", description="Output filename")


# ── Per-MDX-call schemas ──────────────────────────────────────────────────────


class MdxCallInput(BaseModel):
    """Input for a single execute_mdx_and_get_view call."""
    server:      str = Field(description="TM1 server name")
    cube:        str = Field(description="Cube name")
    mdx:         str = Field(description="MDX query string")


class MdxCallInputWide(BaseModel):
    """Input for execute_mdx_and_get_view that returns more than 8 columns."""
    server:      str = Field(description="TM1 server name")
    cube:        str = Field(description="Cube name")
    mdx:         str = Field(description="MDX query string")
    max_columns: int = Field(description="Maximum number of columns to return", default=12)


# ── Script node output ────────────────────────────────────────────────────────


class AssembleOutput(BaseModel):
    """Output of the assemble_payload script node."""
    slide_data_json: str = Field(description="JSON payload for the PPTX renderer")
    filename:        str = Field(description="Output filename passed through from flow input")


class LLMEnrichInput(BaseModel):
    """Input for the LLM enrichment prompt node."""
    slide_data_json: str = Field(description="Raw slide data JSON assembled from MDX results")
    label_a:         str = Field(description="Human label for year A (e.g. '2024 Actual')")
    label_b:         str = Field(description="Human label for year B (e.g. '2025 Actual')")


class LLMEnrichOutput(BaseModel):
    """Output of the LLM enrichment prompt node: enriched JSON + filename pass-through."""
    slide_data_json: str = Field(description="Enriched JSON payload with computed variance and LLM findings")
    filename:        str = Field(description="Output filename passed through from flow input")


# ── MDX strings ───────────────────────────────────────────────────────────────

_KPI_MDX = (
    "SELECT {"
    "[A_Year].[A_Year].[Y1],[A_Year].[A_Year].[Y2],"
    "[A_Year].[A_Year].[Y2-Y1 $],[A_Year].[A_Year].[Y2-Y1 %]"
    "} ON COLUMNS,"
    "{[C1_Revenue Measure].[C1_Revenue Measure].[Gross Revenue]} ON ROWS "
    "FROM [C1_Revenue] "
    "WHERE ([A_Organization].[A_Organization].[Total Company],"
    "[C1_Channel].[C1_Channel].[Channel Total],"
    "[C1_Product].[C1_Product].[Product Total],"
    "[A_Month].[A_Month].[Year],"
    "[A_Version].[A_Version].[Actual])"
)

_QUARTERLY_MDX = (
    "SELECT {"
    "[A_Month].[A_Month].[Q1],[A_Month].[A_Month].[Q2],"
    "[A_Month].[A_Month].[Q3],[A_Month].[A_Month].[Q4]"
    "} ON COLUMNS,"
    "{[A_Year].[A_Year].[Y1],[A_Year].[A_Year].[Y2]} ON ROWS "
    "FROM [C1_Revenue] "
    "WHERE ([A_Organization].[A_Organization].[Total Company],"
    "[C1_Channel].[C1_Channel].[Channel Total],"
    "[C1_Product].[C1_Product].[Product Total],"
    "[A_Version].[A_Version].[Actual])"
)

_MONTHLY_MDX = (
    "SELECT {"
    "[A_Month].[A_Month].[Jan],[A_Month].[A_Month].[Feb],"
    "[A_Month].[A_Month].[Mar],[A_Month].[A_Month].[Apr],"
    "[A_Month].[A_Month].[May],[A_Month].[A_Month].[Jun],"
    "[A_Month].[A_Month].[Jul],[A_Month].[A_Month].[Aug],"
    "[A_Month].[A_Month].[Sep],[A_Month].[A_Month].[Oct],"
    "[A_Month].[A_Month].[Nov],[A_Month].[A_Month].[Dec]"
    "} ON COLUMNS,"
    "{[A_Year].[A_Year].[Y1],[A_Year].[A_Year].[Y2]} ON ROWS "
    "FROM [C1_Revenue] "
    "WHERE ([A_Organization].[A_Organization].[Total Company],"
    "[C1_Channel].[C1_Channel].[Channel Total],"
    "[C1_Product].[C1_Product].[Product Total],"
    "[A_Version].[A_Version].[Actual])"
)

_PRODUCT_MDX = (
    "SELECT {"
    "[C1_Product].[C1_Product].[20000],"
    "[C1_Product].[C1_Product].[30000],"
    "[C1_Product].[C1_Product].[40000]"
    "} ON COLUMNS,"
    "{[A_Year].[A_Year].[Y1],[A_Year].[A_Year].[Y2]} ON ROWS "
    "FROM [C1_Revenue] "
    "WHERE ([A_Organization].[A_Organization].[Total Company],"
    "[C1_Channel].[C1_Channel].[Channel Total],"
    "[A_Month].[A_Month].[Year],[A_Version].[A_Version].[Actual])"
)

_CHANNEL_MDX = (
    "SELECT {"
    "[C1_Channel].[C1_Channel].[10],"
    "[C1_Channel].[C1_Channel].[20],"
    "[C1_Channel].[C1_Channel].[30]"
    "} ON COLUMNS,"
    "{[A_Year].[A_Year].[Y1],[A_Year].[A_Year].[Y2]} ON ROWS "
    "FROM [C1_Revenue] "
    "WHERE ([A_Organization].[A_Organization].[Total Company],"
    "[C1_Product].[C1_Product].[Product Total],"
    "[A_Month].[A_Month].[Year],[A_Version].[A_Version].[Actual])"
)


# ── Agentic Flow ──────────────────────────────────────────────────────────────


@flow(
    name="variance_pptx_flow",
    display_name="C1 Revenue Variance PPTX",
    description=(
        "End-to-end flow: runs 5 MDX queries against C1_Revenue on Region03N "
        "as separate flow nodes, assembles the slide data in a script node, "
        "and renders a variance analysis PowerPoint deck. "
        "PA credentials are handled by the ibm-pa-tools MCP toolkit."
    ),
    input_schema=VariancePptxFlowInput,
    suppress_agent_summarization=False,
)
def build_variance_pptx_flow(aflow: Flow) -> Flow:
    """
    9-node flow:
      1. mdx_kpi          — KPI totals via ibm-pa-tools:execute_mdx_and_get_view
      2. mdx_quarterly    — Quarterly best period
      3. mdx_monthly      — Monthly trend Jan–Dec (max_columns=12 to fetch all 12 months)
      4. mdx_product      — C1_Product breakdown
      5. mdx_channel      — C1_Channel breakdown
      6. assemble_payload — Script: parse results → slide_data_json
      7. llm_enrich       — Prompt (gpt-oss-120b): recompute var_abs/var_pct + generate findings
      8. enrich_fixup     — Script: validate LLM JSON, attach filename
      9. render_pptx      — generate_c1_revenue_variance_pptx tool (by name string)
    """

    # ── Nodes 1-5: MDX calls ──────────────────────────────────────────────────
    mdx_kpi_node = aflow.tool(
        "ibm-pa-tools:execute_mdx_and_get_view",
        name="mdx_kpi",
        display_name="Fetch KPI totals",
        input_schema=MdxCallInput,
    )
    mdx_kpi_node.map_input(input_variable="server", expression="flow.input.server")
    mdx_kpi_node.map_input(input_variable="cube",   expression=f'"{_CUBE}"')
    mdx_kpi_node.map_input(input_variable="mdx",    expression=f'"{_KPI_MDX}"')

    mdx_quarterly_node = aflow.tool(
        "ibm-pa-tools:execute_mdx_and_get_view",
        name="mdx_quarterly",
        display_name="Fetch quarterly best period",
        input_schema=MdxCallInput,
    )
    mdx_quarterly_node.map_input(input_variable="server", expression="flow.input.server")
    mdx_quarterly_node.map_input(input_variable="cube",   expression=f'"{_CUBE}"')
    mdx_quarterly_node.map_input(input_variable="mdx",    expression=f'"{_QUARTERLY_MDX}"')

    mdx_monthly_node = aflow.tool(
        "ibm-pa-tools:execute_mdx_and_get_view",
        name="mdx_monthly",
        display_name="Fetch monthly trend",
        input_schema=MdxCallInputWide,
    )
    mdx_monthly_node.map_input(input_variable="server",      expression="flow.input.server")
    mdx_monthly_node.map_input(input_variable="cube",        expression=f'"{_CUBE}"')
    mdx_monthly_node.map_input(input_variable="mdx",        expression=f'"{_MONTHLY_MDX}"')
    mdx_monthly_node.map_input(input_variable="max_columns", expression="12")

    mdx_product_node = aflow.tool(
        "ibm-pa-tools:execute_mdx_and_get_view",
        name="mdx_product",
        display_name="Fetch C1_Product breakdown",
        input_schema=MdxCallInput,
    )
    mdx_product_node.map_input(input_variable="server", expression="flow.input.server")
    mdx_product_node.map_input(input_variable="cube",   expression=f'"{_CUBE}"')
    mdx_product_node.map_input(input_variable="mdx",    expression=f'"{_PRODUCT_MDX}"')

    mdx_channel_node = aflow.tool(
        "ibm-pa-tools:execute_mdx_and_get_view",
        name="mdx_channel",
        display_name="Fetch C1_Channel breakdown",
        input_schema=MdxCallInput,
    )
    mdx_channel_node.map_input(input_variable="server", expression="flow.input.server")
    mdx_channel_node.map_input(input_variable="cube",   expression=f'"{_CUBE}"')
    mdx_channel_node.map_input(input_variable="mdx",    expression=f'"{_CHANNEL_MDX}"')

    # ── Node 6: Assemble payload ──────────────────────────────────────────────
    assemble_node = aflow.script(
        name="assemble_payload",
        display_name="Assemble slide data",
        output_schema=AssembleOutput,
        script=r"""
def _j(v):
    if v is None: return "null"
    if v is True: return "true"
    if v is False: return "false"
    if isinstance(v, str): return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, list): return "[" + ",".join(_j(i) for i in v) + "]"
    if isinstance(v, dict): return "{" + ",".join('"' + k + '":' + _j(val) for k, val in v.items()) + "}"
    return '"' + str(v) + '"'

def _parse(md):
    rows = []
    for line in (md or "").strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        if all(c in "-| " for c in line):
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows

def _v(rows, r, c):
    try:
        return float(str(rows[r][c]).replace(",", "").replace(" ", "") or "0")
    except:
        return 0.0

def _m(v):  return f"${v/1e6:.1f}M"
def _pct(n): return f"{'+'if n>0 else ''}{n:.1f}%"

label_a = flow.input.label_a
label_b = flow.input.label_b
point_a = label_a.split()[0]
point_b = label_b.split()[0]

kpi_rows = _parse(flow.mdx_kpi.output.data)
dr = kpi_rows[1] if len(kpi_rows) > 1 else (kpi_rows[0] if kpi_rows else [""]*5)
total_a = _v([dr], 0, 1)
total_b = _v([dr], 0, 2)
# Compute variance arithmetically from the two raw totals.
# TM1 computed members [Y2-Y1 $] and [Y2-Y1 %] are unreliable in MDX context.
var_abs = total_b - total_a
var_pct = ((total_b - total_a) / total_a * 100) if total_a else 0.0

q_rows = _parse(flow.mdx_quarterly.output.data)
q_a = [_v(q_rows, 1, i) for i in range(1, 5)]
q_b = [_v(q_rows, 2, i) for i in range(1, 5)]
best_idx    = q_b.index(max(q_b)) if q_b else 0
best_period = ["Q1","Q2","Q3","Q4"][best_idx]
best_val_b  = q_b[best_idx] if q_b else 0.0
best_pct    = ((best_val_b - q_a[best_idx]) / q_a[best_idx] * 100) if q_a and q_a[best_idx] else 0.0

months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
m_rows = _parse(flow.mdx_monthly.output.data)
vals_a = [_v(m_rows, 1, i)/1e6 for i in range(1, 13)]
vals_b = [_v(m_rows, 2, i)/1e6 for i in range(1, 13)]
max_b  = vals_b.index(max(vals_b)) if vals_b else 0
min_b  = vals_b.index(min(vals_b)) if vals_b else 0
avg_b  = sum(vals_b)/len(vals_b) if vals_b else 0
avg_a  = sum(vals_a)/len(vals_a) if vals_a else 0
trend  = "upward" if vals_b and vals_b[-1] > vals_b[0] else "downward"
insights = [
    {"tag":"PEAK MONTH",  "title":f"{months[max_b]}: ${vals_b[max_b]:.1f}M", "body":"Highest revenue month."},
    {"tag":"LOW POINT",   "title":f"{months[min_b]}: ${vals_b[min_b]:.1f}M", "body":"Lowest revenue month."},
    {"tag":"TREND",       "title":f"Overall {trend} trajectory",              "body":f"Avg ${avg_b:.1f}M vs ${avg_a:.1f}M prior."},
]

prod_names = ["Phones","PCs","Tablets"]
pr_rows = _parse(flow.mdx_product.output.data)
p_a = [_v(pr_rows, 1, i) for i in range(1, 4)]
p_b = [_v(pr_rows, 2, i) for i in range(1, 4)]
prod_stats = []
for i, nm in enumerate(prod_names):
    pct = ((p_b[i]-p_a[i])/p_a[i]*100) if p_a[i] else 0.0
    prod_stats.append({"name":nm,"val_a":_m(p_a[i]),"val_b":_m(p_b[i]),"var":_pct(pct),"positive":pct>=0})

chan_names = ["Direct","Internet","Indirect"]
ch_rows = _parse(flow.mdx_channel.output.data)
c_a = [_v(ch_rows, 1, i) for i in range(1, 4)]
c_b = [_v(ch_rows, 2, i) for i in range(1, 4)]
chan_stats = []
for i, nm in enumerate(chan_names):
    pct = ((c_b[i]-c_a[i])/c_a[i]*100) if c_a[i] else 0.0
    chan_stats.append({"name":nm,"val_a":_m(c_a[i]),"val_b":_m(c_b[i]),"var":_pct(pct),"positive":pct>=0})

payload = {
    "meta": {
        "title": f"C1_Revenue Variance: {point_a} vs {point_b}",
        "server": flow.input.server, "cube": "C1_Revenue",
        "variance_dimension": "A_Year",
        "point_a": point_a, "point_b": point_b,
        "label_a": label_a, "label_b": label_b,
        "measure": "Gross Revenue",
        "subtitle": "Total Company · All Channels · All Products · Actual",
    },
    "kpi": {
        "total_a": total_a, "total_b": total_b,
        "var_abs": var_abs, "var_pct": var_pct,
        "best_period": best_period,
        "best_period_val_b": best_val_b, "best_period_pct": best_pct,
    },
    "trend": {
        "dim_name": "A_Month", "labels": months,
        "values_a": vals_a, "values_b": vals_b,
        "label_a": label_a, "label_b": label_b,
        "y_label": "Gross Revenue ($M)", "insights": insights,
    },
    "breakdowns": [
        {"dim_key":"c1_product","dim_name":"C1_Product",
         "title":"Revenue by C1_Product",
         "subtitle":f"Gross Revenue · {point_a} vs {point_b} · Actual",
         "labels":prod_names,
         "values_a":[v/1e6 for v in p_a],"values_b":[v/1e6 for v in p_b],
         "stats":prod_stats,"label_a":point_a,"label_b":point_b,
         "y_label":"Gross Revenue ($M)","bar_dir":"col"},
        {"dim_key":"c1_channel","dim_name":"C1_Channel",
         "title":"Revenue by C1_Channel",
         "subtitle":f"Gross Revenue · {point_a} vs {point_b} · Actual",
         "labels":chan_names,
         "values_a":[v/1e6 for v in c_a],"values_b":[v/1e6 for v in c_b],
         "stats":chan_stats,"label_a":point_a,"label_b":point_b,
         "y_label":"Gross Revenue ($M)","bar_dir":"bar"},
    ],
}
self.output.slide_data_json = _j(payload)
self.output.filename = flow.input.filename
""",
    )

    # ── Node 7: LLM enrichment ────────────────────────────────────────────────
    # Uses gpt-oss-120b to:
    #   1. Recompute var_abs and var_pct from total_a / total_b (avoids
    #      relying on TM1 computed members that may return 0 or non-numeric).
    #   2. Generate 5 narrative findings and 4 recommendations for slide 6.
    #
    # The user_prompt references {slide_data_json}, {label_a}, {label_b} which
    # the prompt node resolves from the input_schema fields at runtime.
    llm_enrich_node = aflow.prompt(
        name="llm_enrich",
        display_name="LLM: compute variance & generate insights",
        description=(
            "Uses an LLM to recompute year-over-year variance from the raw totals "
            "and generate rich narrative findings and recommendations for slide 6."
        ),
        llm="groq/openai/gpt-oss-120b",
        llm_parameters={"temperature": 0, "max_new_tokens": 2000},
        input_schema=LLMEnrichInput,
        output_schema=LLMEnrichOutput,
        system_prompt=(
            "You are a financial analyst assistant. "
            "You receive a JSON payload from an IBM Planning Analytics C1_Revenue variance analysis. "
            "Your job is to: "
            "(1) Recompute kpi.var_abs and kpi.var_pct from kpi.total_a and kpi.total_b "
            "    using: var_abs = total_b - total_a, var_pct = (total_b - total_a) / total_a * 100. "
            "    Replace whatever values are currently in the JSON for those fields. "
            "(2) Replace the 'insights' list in the 'trend' object with 3 concise data-driven "
            "    insight cards based on the monthly trend values_a and values_b arrays. "
            "    Each card must have 'tag' (ALL CAPS, max 12 chars), 'title' (< 60 chars), "
            "    and 'body' (< 120 chars with specific numbers). "
            "(3) Add a 'findings' list with exactly 5 entries to the payload. "
            "    Each finding must have 'tag' (ALL CAPS, max 12 chars), 'title' (< 60 chars), "
            "    'body' (< 120 chars with specific numbers and percentages from the data), "
            "    and 'color' (one of: '28A745' for positive/growth, 'DC3545' for negative/decline, "
            "    '1E90FF' for informational, 'FF8C00' for standout). "
            "    Base findings on: overall YoY growth, best product, weakest product, "
            "    best channel, and a seasonal/monthly pattern from the trend data. "
            "(4) Add a 'recommendations' list with exactly 4 short actionable strings "
            "    (< 90 chars each) based on the findings. "
            "Return ONLY the complete, valid JSON payload with these fields updated — "
            "no markdown fences, no explanation, no extra text. "
            "Also set 'filename' in your output to exactly: "
        ),
        user_prompt=[
            "label_a={label_a}, label_b={label_b}. Here is the slide data JSON:\n{slide_data_json}",
        ],
    )
    llm_enrich_node.map_input(input_variable="slide_data_json", expression="flow.assemble_payload.output.slide_data_json")
    llm_enrich_node.map_input(input_variable="label_a",         expression="flow.input.label_a")
    llm_enrich_node.map_input(input_variable="label_b",         expression="flow.input.label_b")

    # Post-LLM script: inject filename (LLM cannot reliably pass it through)
    # and ensure the enriched JSON is valid before handing to the renderer.
    enrich_fixup_node = aflow.script(
        name="enrich_fixup",
        display_name="Fixup: attach filename to enriched payload",
        output_schema=LLMEnrichOutput,
        script=r"""
raw = flow.llm_enrich.output.slide_data_json or ""

# Strip markdown fences if the LLM accidentally wrapped the JSON
raw = raw.strip()
if raw.startswith("```"):
    lines = raw.splitlines()
    raw = "\n".join(l for l in lines if not l.startswith("```")).strip()

# Fallback: if the result doesn't look like a JSON object, use the
# raw assemble output so the render still works.
if raw.startswith("{") and raw.endswith("}"):
    enriched = raw
else:
    enriched = flow.assemble_payload.output.slide_data_json

self.output.slide_data_json = enriched
self.output.filename        = flow.input.filename
""",
    )

    # ── Node 9: Render PPTX ───────────────────────────────────────────────────
    # LLMEnrichOutput field names match the tool's parameter names exactly.
    render_node = aflow.tool(
        tool="generate_c1_revenue_variance_pptx",
        name="render_pptx",
        display_name="Render PPTX",
        input_schema=LLMEnrichOutput,
    )

    # ── Wire the sequence ─────────────────────────────────────────────────────
    aflow.sequence(
        START,
        mdx_kpi_node,
        mdx_quarterly_node,
        mdx_monthly_node,
        mdx_product_node,
        mdx_channel_node,
        assemble_node,
        llm_enrich_node,
        enrich_fixup_node,
        render_node,
        END,
    )

    return aflow
