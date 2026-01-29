# Tools System

This directory contains the modular tool system for the ReachyMini Chat bot.

## How to add a new tool

1. **Create a new file** in this directory (e.g., `tools/weather.py`).
2. **Define the Tool Logic**:
   - Implement the async function that handles the tool logic.
   - Define the FunctionSchema for the LLM.
3. **Export the following**:
   - `HANDLERS`: A dictionary mapping function names to their handler functions.
   - `SCHEMA`: The FunctionSchema object.
4. **Register the module**:
   - Open `tools/__init__.py`.
   - Import your new module.
   - Add it to the `_TOOL_MODULES` list.

## Example

```python
# tools/example.py
from pipecat.adapters.schemas.function_schema import FunctionSchema

async def my_tool_handler(params):
    # Implementation
    pass

SCHEMA = FunctionSchema(
    name="my_tool",
    description="Does something cool",
    properties={...}
)

HANDLERS = {
    "my_tool": my_tool_handler
}
```
