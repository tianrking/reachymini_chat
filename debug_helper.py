from loguru import logger
from PIL import Image
import io

from pipecat.frames.frames import Frame, UserImageRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIProcessor

class ImageSaver(FrameProcessor):
    def __init__(self, save_path: str = "capture.png"):
        super().__init__()
        self.save_path = save_path

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if isinstance(frame, UserImageRawFrame):
            # Only save the image if it's a response to a specific request (trigger-based)
            if getattr(frame, "request", None):
                try:
                    logger.debug(f"Saving requested image to {self.save_path} (Format: {frame.format})")
                    if frame.format == "RGB":
                        image = Image.frombytes("RGB", frame.size, frame.image)
                    else:
                        image = Image.open(io.BytesIO(frame.image))
                    image.save(self.save_path)
                except Exception as e:
                    logger.error(f"Error saving image: {e}")
        
        await self.push_frame(frame, direction)

class VisionRTVIProcessor(RTVIProcessor):
    pass
