from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.frames.frames import UserImageRequestFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import FunctionCallParams

async def fetch_user_image(params: FunctionCallParams):
    """Fetch the user image and push it to the LLM.

    When called, this function pushes a UserImageRequestFrame upstream to the
    transport. As a result, the transport will request the user image and push a
    UserImageRawFrame downstream which will be added to the context by the LLM
    assistant aggregator.
    """
    user_id = params.arguments.get("user_id")
    # If user_id is missing/None, we might still want to try capturing "the user"
    # But UserImageRequestFrame requires a user_id if we want to target a specific participant.
    # In local WebRTC, usually there's only one peer.
    
    question = params.arguments.get("question", "What do you see in this image?")
    video_source = params.arguments.get("video_source", "camera")
    logger.debug(f"Requesting image with user_id={user_id}, question={question}, source={video_source}")

    # Request a user image frame and indicate that it should be added to the
    # context. Also associate it to the function call.
    
    await params.llm.push_frame(
        UserImageRequestFrame(
            user_id=user_id,
            text=question,
            video_source=video_source,
            append_to_context=True,
            function_name=params.function_name,
            tool_call_id=params.tool_call_id,
        ),
        FrameDirection.UPSTREAM,
    )

    await params.result_callback(None)

NAME = "fetch_user_image"
DESCRIPTION = "Called when the user asks you to see them, look at them, or describe what you see in the camera feed."

SCHEMA = FunctionSchema(
    name=NAME,
    description=DESCRIPTION,
    properties={
        "user_id": {
            "type": "string",
            "description": "The ID of the user to grab the image from. You must use the user ID provided in the system prompt.",
        },
        "question": {
            "type": "string",
            "description": "The question that the user is asking about the image. Default to 'Describe what you see'.",
        },
        "video_source": {
            "type": "string",
            "enum": ["camera", "screenVideo"],
            "description": "The source of the image. Use 'camera' to see the user or 'screenVideo' to see their shared screen/browser tab.",
        },
    },
    required=["user_id"],
)

HANDLERS = {
    NAME: fetch_user_image
}
