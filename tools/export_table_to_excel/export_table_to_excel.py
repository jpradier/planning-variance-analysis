"""
Tool: export_table_to_excel

Accepts a list of rows (as a JSON string) and an optional sheet name, builds an
Excel workbook in memory, and returns the raw bytes so the watsonx Orchestrate
UI renders a download link for the user.

Usage example (LLM → tool call):
    export_table_to_excel(
        columns='["Risk ID", "Name", "Status", "Owner"]',
        rows='[["R-001","Cyber risk","Open","Alice"],["R-002","Compliance","Closed","Bob"]]',
        sheet_name="Risk Report"
    )
"""

import io
import json

from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool


@tool(
    name="export_table_to_excel",
    description=(
        "Generate a downloadable Excel (.xlsx) file from tabular data that is "
        "already in the conversation context. "
        "Pass the column headers as a JSON array of strings and the data rows "
        "as a JSON array of arrays. "
        "Returns the file as bytes so the user receives a download link."
    ),
    permission=ToolPermission.READ_ONLY,
)
def export_table_to_excel(
    columns: str,
    rows: str,
    sheet_name: str = "Sheet1",
    filename: str = "export.xlsx",
) -> bytes:
    """Generate an Excel workbook from tabular data and return it as bytes.

    Args:
        columns (str): JSON array of column header strings.
            Example: '["Risk ID", "Name", "Status", "Owner"]'
        rows (str): JSON array of arrays, each inner array being one data row.
            Example: '[["R-001","Cyber risk","Open","Alice"],["R-002","Compliance","Closed","Bob"]]'
        sheet_name (str): Name of the worksheet tab. Defaults to "Sheet1".
        filename (str): Suggested filename for the download. Defaults to "export.xlsx".
            Must end with .xlsx.

    Returns:
        bytes: Binary content of the .xlsx workbook, delivered as a download link.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    # Parse inputs
    col_headers: list = json.loads(columns)
    data_rows: list = json.loads(rows)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name

    # --- Header row styling ---
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(fill_type="solid", fgColor="1F4E79")  # IBM dark-blue
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for col_idx, header in enumerate(col_headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # --- Data rows ---
    for row_idx, row_data in enumerate(data_rows, start=2):
        for col_idx, value in enumerate(row_data, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    # --- Auto-fit column widths (best-effort) ---
    for col_cells in ws.columns:
        max_length = max(
            (len(str(cell.value)) if cell.value is not None else 0) for cell in col_cells
        )
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_length + 4, 60)

    # --- Serialize to bytes ---
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
