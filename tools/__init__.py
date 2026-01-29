from tools import vision_tools, robot_actions, shopping

# List of tool modules to register
_TOOL_MODULES = [
    vision_tools,
    robot_actions,
    shopping,
]

def register_tools(llm_service):
    """
    Registers all tools from the configured modules to the provided LLM service.
    Returns a list of FunctionSchema objects to be used in the ToolsSchema.
    """
    schemas = []
    for module in _TOOL_MODULES:
        # Register handlers
        if hasattr(module, "HANDLERS"):
            for name, handler in module.HANDLERS.items():
                llm_service.register_function(name, handler)
        
        # Collect schemas
        if hasattr(module, "SCHEMA"):
            schemas.append(module.SCHEMA)
            
    return schemas
