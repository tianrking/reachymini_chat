import os

from dotenv import load_dotenv
from loguru import logger

from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.turn.smart_turn.local_smart_turn_v3 import LocalSmartTurnAnalyzerV3
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import LLMRunFrame, TTSSpeakFrame, UserImageRequestFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameDirection
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import (
    create_transport,
    get_transport_client_id,
    maybe_capture_participant_camera,
)
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.services.openai.base_llm import BaseOpenAILLMService
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.transports.base_transport import BaseTransport, TransportParams
from pipecat.transports.daily.transport import DailyParams
from pipecat.turns.user_stop import TurnAnalyzerUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

# Import debug helper
from debug_helper import ImageSaver, VisionRTVIProcessor

# Load custom UI
from fastapi.staticfiles import StaticFiles
import pipecat_ai_small_webrtc_prebuilt.frontend

custom_dist_path = os.path.join(os.path.dirname(__file__), "custom_ui")
if os.path.exists(custom_dist_path):
    pipecat_ai_small_webrtc_prebuilt.frontend.SmallWebRTCPrebuiltUI = StaticFiles(
        directory=custom_dist_path,
        html=True
    )
    logger.info(f"✅ Loaded custom UI from: {custom_dist_path}")

load_dotenv(override=True)



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
    # DEBUG: We can't easily intercept the *resulting* frame here in the function call 
    # because this function just *requests* it. The Transport handles the actual capture 
    # and pushes the UserImageRawFrame downstream.
    # To debug what is being seen, we rely on the fact that Pipecat transports generally 
    # work correct. However, if 'UserImageRawFrame' is what flows through the pipeline,
    # maybe we can add a simple FrameProcessor to sniffer/save it?
    
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


# We store functions so objects (e.g. SileroVADAnalyzer) don't get
# instantiated. The function will be called when the desired transport gets
# selected.
transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_in_enabled=True, # Enable video input
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
    ),
    "webrtc": lambda: TransportParams(
        audio_in_enabled=True,
        audio_out_enabled=True,
        video_in_enabled=True, # Enable video input
        vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
    ),
}


async def run_bot(transport: BaseTransport, runner_args: RunnerArguments):
    logger.info(f"Starting bot")

    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        model="nova-2",
        language="zh", # Enable Chinese support
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
    )

    # ZhipuAI GLM-4.6V Configuration
    llm = OpenAILLMService(
        # api_key=os.getenv("ZHIPU_API_KEY"),
        api_key="22adb9b231a64bafa046bd70bff407af.y5trCWhy4HMPrfPY",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        model="glm-4.6v",
        # Note: 'thinking' param removed for compatibility
    )
    
    llm.register_function("fetch_user_image", fetch_user_image)

    @llm.event_handler("on_function_calls_started")
    async def on_function_calls_started(service, function_calls):
        await tts.queue_frame(TTSSpeakFrame("Okay, let me take a look."))

    fetch_image_function = FunctionSchema(
        name="fetch_user_image",
        description="Called when the user asks you to see them, look at them, or describe what you see in the camera feed.",
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
    tools = ToolsSchema(standard_tools=[fetch_image_function])

    messages = [
        {
            "role": "system",
            "content": "You are a helpful LLM in a WebRTC call. You can see the user via their camera or their shared screen. If they ask 'what do you see', 'describe me', or 'look at my screen', call the fetch_user_image function with the appropriate video_source. Your output will be spoken aloud, so avoid special characters. Respond to what the user said in a creative and helpful way. You can speak Chinese.",
        },
    ]

    # Pre-append the user ID instruction placeholder (will be updated or we rely on the dynamic one if API supports multiple system msgs)
    # To be safe for Zhipu, let's keep it simple.

    context = LLMContext(messages, tools)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                stop=[TurnAnalyzerUserTurnStopStrategy(turn_analyzer=LocalSmartTurnAnalyzerV3())]
            ),
        ),
    )
    
    rtvi = VisionRTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),  # Transport user input
            rtvi, # Handle RTVI messages (text chat, etc.)
            stt,  # STT
            user_aggregator,  # User responses
            ImageSaver(save_path="debug_latest_capture.png"), # DEBUG: Save image to check what is seen
            llm,  # LLM
            tts,  # TTS
            transport.output(),  # Transport bot output
            assistant_aggregator,  # Assistant spoken responses
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=runner_args.pipeline_idle_timeout_secs,
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(f"Client connected")

        # Request camera access from the client
        await maybe_capture_participant_camera(transport, client)

        client_id = get_transport_client_id(transport, client)
        
        # Instead of appending a system message, let's just inject a user message with the instruction
        # to ensure compatibility if multiple system messages are blocked.
        messages.append(
            {
                "role": "user",
                "content": f"System Update: The user has connected. Their User ID is '{client_id}'. Use this ID when calling fetch_user_image.",
            }
        )
        
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info(f"Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=runner_args.handle_sigint)

    await runner.run(task)


async def bot(runner_args: RunnerArguments):
    """Main bot entry point compatible with Pipecat Cloud."""
    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
