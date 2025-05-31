import json
import sys
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell, new_output
import re  # For regex to identify tables
from html import unescape  # For unescaping HTML entities
from fastmcp import FastMCP, Context
from typing import Optional  # Import Optional for type hinting

# Constants for output formatting
MAX_TEXT_OUTPUT_LENGTH = 500
MAX_TABLE_ROWS = 5
TRUNCATION_MARKER = "[TRUNCATED]"
HINT_FULL_OUTPUT = "Use `get_full_output` for full content."

mcp = FastMCP(name="JupyterMCPTool")


def _read_notebook(filepath) -> tuple[Optional[nbformat.NotebookNode], Optional[str]]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return nbformat.read(f, as_version=4), None
    except FileNotFoundError:
        return None, f"Notebook file not found at {filepath}"
    except Exception as e:
        return None, f"Error reading notebook: {e}"


def _write_notebook(notebook, filepath):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            nbformat.write(notebook, f)
        return True, None
    except Exception as e:
        return False, f"Error writing notebook: {e}"


def _format_text_output(text_content, cell_idx, output_idx):
    if len(text_content) > MAX_TEXT_OUTPUT_LENGTH:
        return f"Text: {text_content[:MAX_TEXT_OUTPUT_LENGTH]}... {TRUNCATION_MARKER} {HINT_FULL_OUTPUT} (cell {cell_idx} [1-based], output {output_idx} [1-based])"
    return f"Text: {text_content}"


def _format_image_output(cell_idx, output_idx):
    return f"Image (PNG) - IMG_ID{cell_idx:03d}{output_idx:03d} {HINT_FULL_OUTPUT} (cell {cell_idx} [1-based], output {output_idx} [1-based])"


def _format_table_output(html_content, cell_idx, output_idx):
    # Attempt to parse HTML table and get first N rows
    # This is a simplified regex-based approach as we don't have BeautifulSoup
    table_rows = []
    header_match = re.search(
        r'<thead.*?>(.*?)</thead>', html_content, re.DOTALL | re.IGNORECASE)
    if header_match:
        header_content = header_match.group(1)
        # Extract header cells (th)
        th_matches = re.findall(
            r'<th.*?>(.*?)</th>', header_content, re.DOTALL | re.IGNORECASE)
        if th_matches:
            table_rows.append(
                "| " + " | ".join([unescape(re.sub(r'<.*?>', '', h)).strip() for h in th_matches]) + " |")
            table_rows.append("|" + "---|"*len(th_matches))

    body_match = re.search(r'<tbody.*?>(.*?)</tbody>',
                           html_content, re.DOTALL | re.IGNORECASE)
    tr_matches = []  # Initialize tr_matches
    if body_match:
        body_content = body_match.group(1)
        # Extract table rows (tr)
        tr_matches = re.findall(
            r'<tr.*?>(.*?)</tr>', body_content, re.DOTALL | re.IGNORECASE)
        for i, tr in enumerate(tr_matches):
            if i >= MAX_TABLE_ROWS:
                break
            # Extract table data cells (td)
            td_matches = re.findall(
                r'<td.*?>(.*?)</td>', tr, re.DOTALL | re.IGNORECASE)
            if td_matches:
                table_rows.append(
                    "| " + " | ".join([unescape(re.sub(r'<.*?>', '', d)).strip() for d in td_matches]) + " |")

    if table_rows:
        summary = "\n".join(table_rows)
        if len(tr_matches) > MAX_TABLE_ROWS:
            summary += f"\n... {TRUNCATION_MARKER}"
        return f"Table (HTML): \n```markdown\n{summary}\n```\n{HINT_FULL_OUTPUT} (cell {cell_idx} [1-based], output {output_idx} [1-based])"

    # Fallback if no table found or parsing failed
    return f"HTML content (truncated): {html_content[:MAX_TEXT_OUTPUT_LENGTH]}... {TRUNCATION_MARKER} {HINT_FULL_OUTPUT} (cell {cell_idx} [1-based], output {output_idx} [1-based])"


@mcp.tool()
def get_formatted_content(filepath: str):
    """
    Retrieves the formatted content of a Jupyter notebook.
    """
    notebook, error = _read_notebook(filepath)
    if error:
        return {"formatted_content": "", "filepath": filepath, "error": error}

    formatted_content = []
    if notebook:  # Ensure notebook is not None before proceeding
        for i, cell in enumerate(notebook.cells):
            formatted_content.append(
                f"[[Cell {i + 1} - {cell.cell_type.capitalize()}]]\n")
            formatted_content.append("```\n")
            formatted_content.append(cell.source.strip())
            formatted_content.append("\n```\n")

            if cell.cell_type == 'code' and cell.outputs:
                formatted_content.append(f"[[Cell {i + 1} - Output]]\n")
                for j, output in enumerate(cell.outputs):
                    output_summary = ""
                    if output.output_type == "stream":
                        output_summary = _format_text_output(
                            output.text, i + 1, j + 1)
                    elif output.output_type == "display_data" or output.output_type == "execute_result":
                        if 'image/png' in output.data:
                            output_summary = _format_image_output(i + 1, j + 1)
                        elif 'text/html' in output.data and ('<table' in output.data['text/html'] or '<TABLE' in output.data['text/html']):
                            output_summary = _format_table_output(
                                output.data['text/html'], i + 1, j + 1)
                        elif 'text/plain' in output.data:
                            output_summary = _format_text_output(
                                output.data['text/plain'], i + 1, j + 1)
                        else:
                            output_summary = f"Other data type: {', '.join(output.data.keys())} {HINT_FULL_OUTPUT} (cell {i + 1}, output {j + 1})"
                    elif output.output_type == "error":
                        output_summary = f"Error: {output.ename}: {output.evalue} {HINT_FULL_OUTPUT} (cell {i + 1}, output {j + 1})"
                    formatted_content.append(f"- {output_summary}\n")
            formatted_content.append("\n")
    return {"formatted_content": "".join(formatted_content), "filepath": filepath, "error": error}


@mcp.tool()
def get_full_output(filepath: str, cell_index: int, output_index: int, type_hint: Optional[str] = None):
    """
    Retrieves the full content of a specific output from a Jupyter notebook cell.
    """
    notebook, error = _read_notebook(filepath)
    if error:
        return {"full_output_data": None, "mime_type": None, "error": error}

    if notebook is None:
        return {"full_output_data": None, "mime_type": None, "error": error}

    # Adjust for 1-based indexing
    adjusted_cell_index = cell_index - 1
    adjusted_output_index = output_index - 1

    if not (0 <= adjusted_cell_index < len(notebook.cells)):
        return {"full_output_data": None, "mime_type": None, "error": f"Cell index {cell_index} out of bounds. Please use a 1-based index."}

    cell = notebook.cells[adjusted_cell_index]
    if cell.cell_type != 'code' or not cell.outputs:
        return {"full_output_data": None, "mime_type": None, "error": f"Cell {cell_index} is not a code cell or has no outputs."}

    if not (0 <= adjusted_output_index < len(cell.outputs)):
        return {"full_output_data": None, "mime_type": None, "error": f"Output index {output_index} out of bounds for cell {cell_index}. Please use a 1-based index."}

    output = cell.outputs[adjusted_output_index]
    full_output_data = None
    mime_type = None

    if output.output_type == "stream":
        full_output_data = output.text
        mime_type = f"text/{output.name}"
    elif output.output_type in ["display_data", "execute_result"]:
        if type_hint == "image" and 'image/png' in output.data:
            full_output_data = output.data['image/png']
            mime_type = "image/png"
        elif type_hint == "text" and 'text/plain' in output.data:
            full_output_data = output.data['text/plain']
            mime_type = "text/plain"
        elif type_hint == "table" and 'text/html' in output.data:  # Assuming tables are often rendered as HTML
            full_output_data = output.data['text/html']
            mime_type = "text/html"
        elif 'text/plain' in output.data:  # Fallback to text/plain if no specific type hint or type hint doesn't match
            full_output_data = output.data['text/plain']
            mime_type = "text/plain"
        elif 'image/png' in output.data:  # Fallback to image/png
            full_output_data = output.data['image/png']
            mime_type = "image/png"
        else:
            full_output_data = json.dumps(output.data)
            mime_type = "application/json"
    elif output.output_type == "error":
        full_output_data = {
            "ename": output.ename, "evalue": output.evalue, "traceback": output.traceback}
        mime_type = "application/json"  # Or a custom error mime type

    return {"full_output_data": full_output_data, "mime_type": mime_type, "error": None}


@mcp.tool()
def edit_cell(filepath: str, cell_index: int, new_source_content: str):
    """
    Edits the source content of a specific cell in a Jupyter notebook.
    Note: For code cells, existing outputs will be cleared upon editing, as they are considered stale.
    """
    notebook, error = _read_notebook(filepath)
    if error:
        return {"success": False, "filepath": filepath, "error": error}

    if notebook is None:
        return {"success": False, "filepath": filepath, "error": error}

    # Adjust for 1-based indexing
    adjusted_cell_index = cell_index - 1

    if not (0 <= adjusted_cell_index < len(notebook.cells)):
        return {"success": False, "filepath": filepath, "error": f"Cell index {cell_index} out of bounds. Please use a 1-based index."}

    notebook.cells[adjusted_cell_index].source = new_source_content
    if notebook.cells[adjusted_cell_index].cell_type == 'code':
        # Clear outputs on edit
        notebook.cells[adjusted_cell_index].outputs = []

    success, error = _write_notebook(notebook, filepath)
    return {"success": success, "filepath": filepath, "error": error}


@mcp.tool()
def add_cell(filepath: str, cell_index: int, cell_type: str, source_content: str):
    """
    Adds a new cell (code or markdown) to a Jupyter notebook at a specified index.
    """
    notebook, error = _read_notebook(filepath)
    if error:
        return {"success": False, "filepath": filepath, "new_cell_actual_index": -1, "error": error}

    if notebook is None:
        return {"success": False, "filepath": filepath, "new_cell_actual_index": -1, "error": error}

    # Adjust for 1-based indexing for insertion point
    adjusted_cell_index = cell_index - 1

    if not (0 <= adjusted_cell_index <= len(notebook.cells)):
        return {"success": False, "filepath": filepath, "new_cell_actual_index": -1, "error": f"Cell index {cell_index} out of bounds for adding. Please use a 1-based index."}

    if cell_type == "code":
        new_cell = new_code_cell(source_content)
    elif cell_type == "markdown":
        new_cell = new_markdown_cell(source_content)
    else:
        return {"success": False, "filepath": filepath, "new_cell_actual_index": -1, "error": f"Invalid cell type: {cell_type}. Must be 'code' or 'markdown'."}

    notebook.cells.insert(adjusted_cell_index, new_cell)

    success, error = _write_notebook(notebook, filepath)
    return {"success": success, "filepath": filepath, "new_cell_actual_index": cell_index if success else -1, "error": error}


@mcp.tool()
def delete_cell(filepath: str, cell_index: int):
    """
    Deletes a cell from a Jupyter notebook at a specified index.
    """
    notebook, error = _read_notebook(filepath)
    if error:
        return {"success": False, "filepath": filepath, "error": error}

    if notebook is None:
        return {"success": False, "filepath": filepath, "error": error}

    # Adjust for 1-based indexing
    adjusted_cell_index = cell_index - 1

    if not (0 <= adjusted_cell_index < len(notebook.cells)):
        return {"success": False, "filepath": filepath, "error": f"Cell index {cell_index} out of bounds. Please use a 1-based index."}

    del notebook.cells[adjusted_cell_index]

    success, error = _write_notebook(notebook, filepath)
    return {"success": success, "filepath": filepath, "error": error}


@mcp.tool()
def merge_cells(filepath: str, cell_index1: int, cell_index2: int):
    """
    Merges two consecutive cells in a Jupyter notebook.
    The content of cell_index2 will be appended to cell_index1, and cell_index2 will be deleted.
    """
    notebook, error = _read_notebook(filepath)
    if error:
        return {"success": False, "filepath": filepath, "error": error}

    if notebook is None:
        return {"success": False, "filepath": filepath, "error": error}

    # Adjust for 1-based indexing
    adj_idx1 = cell_index1 - 1
    adj_idx2 = cell_index2 - 1

    # Input Validation
    if not (0 <= adj_idx1 < len(notebook.cells)) or not (0 <= adj_idx2 < len(notebook.cells)):
        return {"success": False, "filepath": filepath, "error": f"One or both cell indices ({cell_index1}, {cell_index2}) are out of bounds."}

    if adj_idx2 != adj_idx1 + 1:
        return {"success": False, "filepath": filepath, "error": f"Cells are not consecutive. Cell {cell_index2} is not immediately after cell {cell_index1}."}

    cell1 = notebook.cells[adj_idx1]
    cell2 = notebook.cells[adj_idx2]

    # Merging Logic
    merged_source = cell1.source + "\n" + cell2.source

    # Determine merged cell type
    if cell1.cell_type == 'code' and cell2.cell_type == 'code':
        merged_cell_type = 'code'
    else:
        # If any cell is markdown, or if types are mixed, result is markdown
        merged_cell_type = 'markdown'

    # Create new merged cell
    if merged_cell_type == 'code':
        merged_cell = new_code_cell(merged_source)
        # Clear outputs if it's a code cell
        merged_cell.outputs = []
    else:
        merged_cell = new_markdown_cell(merged_source)

    # Replace the first cell with the merged cell
    notebook.cells[adj_idx1] = merged_cell

    # Delete the second cell
    # adj_idx2 is now the index of the second cell after the first cell was replaced
    del notebook.cells[adj_idx2]

    success, error = _write_notebook(notebook, filepath)
    return {"success": success, "filepath": filepath, "error": error}


if __name__ == "__main__":
    mcp.run()
