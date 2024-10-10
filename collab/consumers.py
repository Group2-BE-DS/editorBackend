import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging

logger = logging.getLogger(__name__)

class MyConsumer(AsyncWebsocketConsumer):
    # Keep track of connected clients
    connected_clients = []

    async def connect(self):
        logger.info("WebSocket connection attempt")
        self.connected_clients.append(self)  # Add this instance to the list of connected clients
        await self.accept()
        logger.info("WebSocket connected successfully")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        self.connected_clients.remove(self)  # Remove this instance from the list on disconnect

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        data = json.loads(text_data)
        message = data.get('content', '')  # Update to get 'content' instead of 'message'

        # Broadcast the message to all connected clients
        for client in self.connected_clients:
            if client != self:  # Prevent sending the message back to the sender
                await client.send(text_data=json.dumps({
                    'type': 'update',
                    'content': message
                }))
        
        logger.info("Broadcast message sent to all clients")

