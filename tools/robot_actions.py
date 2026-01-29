from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

async def control_head(params: FunctionCallParams):
    """Controls the robot's head movements."""
    
    action = params.arguments.get("action")
    
    logger.info(f"🤖 Robot Action Triggered: {action}")
    
    # TODO: Helper: Insert actual robot SDK code here
    # Example:
    # if action == "shake":
    #     await robot.head.shake()
    # elif action == "nod":
    #     await robot.head.nod()
    
    # Feedback to the LLM (optional, but good for conversation flow)
    # You can return a result string that the LLM will see.
    # For now we just complete the callback.
    await params.result_callback(f"Successfully performed head action: {action}")

NAME = "control_head"
DESCRIPTION = "Control the physical movement of the robot's head, such as shaking or nodding."

SCHEMA = FunctionSchema(
    name=NAME,
    description=DESCRIPTION,
    properties={
        "action": {
            "type": "string",
            "enum": ["shake", "nod"],
            "description": "The movement action to perform.",
        },
    },
    required=["action"],
)

HANDLERS = {
    NAME: control_head
}
