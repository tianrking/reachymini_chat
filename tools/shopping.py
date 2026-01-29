import json
from loguru import logger
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.services.llm_service import FunctionCallParams

async def place_order(params: FunctionCallParams):
    """Places an order for an item."""
    
    item_name = params.arguments.get("item_name")
    quantity = params.arguments.get("quantity", 1)
    
    logger.info(f"🛒 Placing Order: {quantity}x {item_name}")
    
    # TODO: Backend Integration
    # Create a payload and send it to your backend API
    # payload = {"item": item_name, "qty": quantity, "user": "current_user"}
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post("https://api.example.com/orders", json=payload)
    #     result = resp.json()

    # Mock success response
    order_id = "ORD-12345-XYZ"
    status = "confirmed"
    
    result_message = f"Order placed successfully! Order ID: {order_id}. You bought {quantity} {item_name}(s)."
    
    # Return the result to the LLM so it can tell the user
    await params.result_callback(result_message)

NAME = "place_order"
DESCRIPTION = "Place an order for a product when the user explicitly wants to buy something."

SCHEMA = FunctionSchema(
    name=NAME,
    description=DESCRIPTION,
    properties={
        "item_name": {
            "type": "string",
            "description": "The name of the item to purchase.",
        },
        "quantity": {
            "type": "integer",
            "description": "The number of items to purchase. Defaults to 1.",
        },
    },
    required=["item_name"],
)

HANDLERS = {
    NAME: place_order
}
