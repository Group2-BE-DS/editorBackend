from channels.generic.websocket import AsyncWebsocketConsumer
import json

class MyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()  # Accept the WebSocket connection

    async def disconnect(self, close_code):
        pass  # Handle disconnection

    async def receive(self, text_data):
        data = json.loads(text_data)  # Load the incoming data
        message = data['message']  # Extract the message

        # Optionally send a response
        await self.send(text_data=json.dumps({
            'message': message
        }))
