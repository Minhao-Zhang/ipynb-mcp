# ipynb-mcp

This project implements an MCP (Model Context Protocol) server that provides tools for programmatic interaction with Jupyter notebooks (`.ipynb`) files. It allows external agents (like AI models or other systems) to read, edit, and manage Jupyter notebook cells and their outputs.

## How to Use This MCP Server

To run this MCP server, you need to have `uv` (a Python package manager) installed and configure your MCP client to connect to it.

1. **Prerequisites**:
    * Ensure you have Python 3.12 installed.
    * Install `uv` if you haven't already:

        ```bash
        pip install uv
        ```

2. **Setup Project Environment**:
    * Navigate to the project's root directory.
    * Create a virtual environment and install dependencies:

        ```bash
        uv venv --python 3.12
        uv pip install -r pyproject.toml
        ```

3. **Configure Your MCP Client**:
    * Add the following configuration to your MCP client's settings:

        ```json
        {
          "mcpServers": {
            "ipynb-mcp": {
              "command": "uv",
              "args": [
                "--directory",
                "ABSOLUTE_PATH_TO_REPO",
                "run",
                "main.py"
              ]
            }
          }
        }
        ```

        *Replace `ABSOLUTE_PATH_TO_REPO` with the actual absolute path to this project's directory.*

## What Tools Does This MCP Have?

This MCP server provides the following tools for managing Jupyter notebooks:

* `get_formatted_content`: Retrieves a summary of the notebook's content and outputs.
* `get_full_output`: Fetches the complete content of a specific cell output.
* `edit_cell`: Modifies the source code or markdown of a notebook cell.
* `add_cell`: Inserts a new code or markdown cell into the notebook.
* `delete_cell`: Removes a cell from the notebook.
* `merge_cells`: Merges two consecutive cells into one.

## How to Further Develop This Project

1. **Explore `main.py`**: The core logic for interacting with Jupyter notebooks and defining the MCP tools is in [`main.py`](main.py).
2. **Add New Tools**: You can extend the functionality by adding new `@mcp.tool()` decorated functions in `main.py` to perform other notebook operations (e.g., running cells, exporting to other formats).
3. **Improve Output Formatting**: The current output formatting for `get_formatted_content` is basic. You can enhance `_format_text_output`, `_format_image_output`, and `_format_table_output` functions for richer summaries.
4. **Error Handling**: Enhance error handling and user feedback for more robust operations.
5. **Dependencies**: Manage dependencies using `uv` and `pyproject.toml`.

## Comprehensive Detail Description of All Tools

**`get_formatted_content(filepath: str)`**

* **Description**: Retrieves a formatted, summarized view of the entire Jupyter notebook's content, including cell types, source code/markdown, and truncated outputs. This tool is useful for getting a quick overview of the notebook without loading all large outputs.
* **Parameters**:
  * `filepath` (`str`): The path to the Jupyter notebook file (e.g., `test/example.ipynb`).
* **Returns**: A dictionary containing:
  * `formatted_content` (`str`): A string representation of the notebook's cells and their summarized outputs.
  * `filepath` (`str`): The path of the notebook that was read.
  * `error` (`Optional[str]`): An error message if the operation failed, otherwise `None`.

**`get_full_output(filepath: str, cell_index: int, output_index: int, type_hint: Optional[str] = None)`**

* **Description**: Fetches the complete, untruncated content of a specific output from a Jupyter notebook cell. This is particularly useful for retrieving full text, image data, or large table outputs that are truncated in `get_formatted_content`.
* **Parameters**:
  * `filepath` (`str`): The path to the Jupyter notebook file.
  * `cell_index` (`int`): The 1-based index of the cell containing the desired output.
  * `output_index` (`int`): The 1-based index of the specific output within the cell.
  * `type_hint` (`Optional[str]`): An optional hint about the expected output type (`"text"`, `"image"`, `"table"`). This helps in retrieving the most relevant data format.
* **Returns**: A dictionary containing:
  * `full_output_data` (`Any`): The full content of the output (e.g., raw text, base64 encoded image data, HTML for tables).
  * `mime_type` (`Optional[str]`): The MIME type of the retrieved output (e.g., `text/plain`, `image/png`, `text/html`).
  * `error` (`Optional[str]`): An error message if the operation failed, otherwise `None`.

**`edit_cell(filepath: str, cell_index: int, new_source_content: str)`**

* **Description**: Modifies the source content of an existing cell in a Jupyter notebook. When a code cell is edited, its existing outputs are automatically cleared as they become stale.
* **Parameters**:
  * `filepath` (`str`): The path to the Jupyter notebook file.
  * `cell_index` (`int`): The 1-based index of the cell to edit.
  * `new_source_content` (`str`): The new source code or markdown content for the cell.
* **Returns**: A dictionary containing:
  * `success` (`bool`): `True` if the cell was successfully edited, `False` otherwise.
  * `filepath` (`str`): The path of the notebook that was modified.
  * `error` (`Optional[str]`): An error message if the operation failed, otherwise `None`.

**`add_cell(filepath: str, cell_index: int, cell_type: str, source_content: str)`**

* **Description**: Adds a new cell (either `code` or `markdown`) to the Jupyter notebook at a specified 1-based index.
* **Parameters**:
  * `filepath` (`str`): The path to the Jupyter notebook file.
  * `cell_index` (`int`): The 1-based index at which to insert the new cell. Cells at and after this index will be shifted down.
  * `cell_type` (`str`): The type of cell to add (`"code"` or `"markdown"`).
  * `source_content` (`str`): The initial source content for the new cell.
* **Returns**: A dictionary containing:
  * `success` (`bool`): `True` if the cell was successfully added, `False` otherwise.
  * `filepath` (`str`): The path of the notebook that was modified.
  * `new_cell_actual_index` (`int`): The 1-based index where the new cell was actually inserted, or `-1` if unsuccessful.
  * `error` (`Optional[str]`): An error message if the operation failed, otherwise `None`.

**`delete_cell(filepath: str, cell_index: int)`**

* **Description**: Deletes a cell from the Jupyter notebook at the specified 1-based index.
* **Parameters**:
  * `filepath` (`str`): The path to the Jupyter notebook file.
  * `cell_index` (`int`): The 1-based index of the cell to delete.
* **Returns**: A dictionary containing:
  * `success` (`bool`): `True` if the cell was successfully deleted, `False` otherwise.
  * `filepath` (`str`): The path of the notebook that was modified.
  * `error` (`Optional[str]`): An error message if the operation failed, otherwise `None`.

**`merge_cells(filepath: str, cell_index1: int, cell_index2: int)`**

* **Description**: Merges two consecutive cells in a Jupyter notebook. The content of the second cell (`cell_index2`) is appended to the first cell (`cell_index1`), and the second cell is then deleted. The merged cell's type will be 'code' if both original cells were 'code', otherwise it will be 'markdown'.
* **Parameters**:
  * `filepath` (`str`): The path to the Jupyter notebook file.
  * `cell_index1` (`int`): The 1-based index of the first cell.
  * `cell_index2` (`int`): The 1-based index of the second cell, which must be immediately consecutive to `cell_index1` (i.e., `cell_index2 = cell_index1 + 1`).
* **Returns**: A dictionary containing:
  * `success` (`bool`): `True` if the cells were successfully merged, `False` otherwise.
  * `filepath` (`str`): The path of the notebook that was modified.
  * `error` (`Optional[str]`): An error message if the operation failed, otherwise `None`.
