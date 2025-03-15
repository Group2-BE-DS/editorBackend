import json
from channels.generic.websocket import AsyncWebsocketConsumer
import logging
from .token_store import TokenStore
import urllib.parse

logger = logging.getLogger(__name__)

class MyConsumer(AsyncWebsocketConsumer):
    # Track clients and their associated files
    file_clients = {}

    async def connect(self):
        logger.info("WebSocket connection attempt")
        
        try:
            # Get token from query string
            query_string = self.scope['query_string'].decode('utf-8')
            query_params = dict(urllib.parse.parse_qsl(query_string))
            token = query_params.get('token')
            
            logger.info(f"Attempting connection with token: {token}")
            
            # Verify token exists and is valid
            if not token or not TokenStore.verify_token(token):
                logger.warning(f"Invalid or missing token: {token}")
                await self.close()
                return

            await self.accept()
            logger.info(f"WebSocket connected successfully with token: {token}")
            
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await self.close()
            return

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        # Remove this client from all file-specific lists
        for file_id, clients in self.file_clients.items():
            if self in clients:
                clients.remove(self)
                if not clients:  # If no clients are left for this file, remove the entry
                    del self.file_clients[file_id]

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'openFile':
            # Handle file opening
            file_id = data.get('fileId')
            content = data.get('content')

            # Add this client to the list of clients editing this file
            if file_id not in self.file_clients:
                self.file_clients[file_id] = []
            self.file_clients[file_id].append(self)

            # Send the current file content to the client
            await self.send(text_data=json.dumps({
                'type': 'fileData',
                'fileId': file_id,
                'content': content,
            }))

        elif message_type == 'codeUpdate':
            # Handle file updates
            file_id = data.get('fileId')
            content = data.get('content')

            # Broadcast the update to all clients editing this file
            if file_id in self.file_clients:
                for client in self.file_clients[file_id]:
                    if client != self:  # Don't send the update back to the sender
                        await client.send(text_data=json.dumps({
                            'type': 'update',
                            'fileId': file_id,
                            'content': content,
                        }))