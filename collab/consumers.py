import json
import logging
import urllib.parse
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404
from .token_store import TokenStore

logger = logging.getLogger(__name__)

class MyConsumer(AsyncWebsocketConsumer):
    file_clients = {}
    collaboration_rooms = {}  # Store room -> set of clients mapping

    @database_sync_to_async
    def get_file_and_content(self, file_id):
        from filesys.models import File  # Import inside function
        file_instance = get_object_or_404(File, id=file_id)
        file_path = os.path.join(file_instance.repository.location, file_instance.path)
        
        logger.info(f"Attempting to read file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning(f"File not found at path: {file_path}")
            return file_instance, ""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Successfully read file content, length: {len(content)}")
            return file_instance, content
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            raise

    @database_sync_to_async
    def verify_file_access(self, file_id):
        from filesys.models import File
        file_instance = get_object_or_404(File, id=file_id)
        # Add your permission logic here if needed
        return True

    @database_sync_to_async
    def get_file_instance(self, file_id):
        from filesys.models import File
        file_instance = get_object_or_404(File, id=file_id)
        return file_instance

    async def connect(self):
        logger.info("WebSocket connection attempt")
        
        try:
            # Accept all initial connections
            await self.accept()
            logger.info("Base WebSocket connection established")
            
            # Check if this is a collaboration request
            query_string = self.scope['query_string'].decode('utf-8')
            query_params = dict(urllib.parse.parse_qsl(query_string))
            token = query_params.get('token')
            
            if token:
                # This is a collaboration connection attempt
                if TokenStore.verify_token(token):
                    logger.info(f"Collaboration token verified: {token}")
                    if token not in self.collaboration_rooms:
                        self.collaboration_rooms[token] = set()
                    self.collaboration_rooms[token].add(self)
                    await self.send(text_data=json.dumps({
                        'type': 'collaboration_started',
                        'message': 'Joined collaboration session'
                    }))
                else:
                    logger.warning(f"Invalid collaboration token: {token}")
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Invalid collaboration token'
                    }))
            
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        # Remove from file clients
        for file_id, clients in self.file_clients.items():
            if self in clients:
                clients.remove(self)
                if not clients:
                    del self.file_clients[file_id]
        
        # Remove from collaboration rooms
        for token, clients in self.collaboration_rooms.items():
            if self in clients:
                clients.remove(self)
                if not clients:
                    del self.collaboration_rooms[token]
                    TokenStore.remove_token(token)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            file_id = data.get('fileId')
            
            logger.info(f"Received message - Type: {message_type}, FileID: {file_id}")

            if not message_type or not file_id:
                raise ValueError("Missing required fields")

            if message_type == 'openFile':
                logger.info(f"Processing openFile request for file_id: {file_id}")
                await self.handle_open_file(file_id)
            elif message_type == 'codeUpdate':
                content = data.get('content')
                if content is None:
                    raise ValueError("Missing content field")
                logger.info(f"Processing codeUpdate request for file_id: {file_id}")
                await self.handle_code_update(file_id, content)
            else:
                raise ValueError(f"Unknown message type: {message_type}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            await self.send_error("Invalid message format")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send_error(str(e))

    async def handle_open_file(self, file_id):
        try:
            # Verify access before proceeding
            if not await self.verify_file_access(file_id):
                raise PermissionError("Access denied to this file")
            
            logger.info(f"Getting file content for file_id: {file_id}")
            file_instance, content = await self.get_file_and_content(file_id)
            
            logger.info(f"Adding client to file_clients for file_id: {file_id}")
            if file_id not in self.file_clients:
                self.file_clients[file_id] = []
            self.file_clients[file_id].append(self)

            # Add debug logging
            logger.info(f"File content: {content[:100]}...")  # Log first 100 chars
            
            response_data = {
                'type': 'fileData',
                'fileId': file_id,
                'content': content,
            }
            logger.info(f"Sending file data - FileID: {file_id}, Content length: {len(content)}")
            await self.send(text_data=json.dumps(response_data))
            logger.info("File data sent successfully")

        except Exception as e:
            logger.error(f"Error opening file: {str(e)}")
            await self.send_error(f"Failed to open file: {str(e)}")
            raise  # Re-raise to see full traceback in logs

    async def handle_code_update(self, file_id, content):
        try:
            file_instance = await self.get_file_instance(file_id)
            file_path = os.path.join(file_instance.repository.location, file_instance.path)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Find all clients that should receive this update
            recipients = set()
            
            # Add clients viewing this file
            if file_id in self.file_clients:
                recipients.update(self.file_clients[file_id])
            
            # Add clients in the same collaboration room
            for token, clients in self.collaboration_rooms.items():
                if self in clients:
                    recipients.update(clients)
            
            # Send updates to all unique recipients except sender
            for client in recipients:
                if client != self:
                    await client.send(text_data=json.dumps({
                        'type': 'update',
                        'fileId': file_id,
                        'content': content,
                    }))

        except Exception as e:
            logger.error(f"Error updating file: {str(e)}")
            await self.send_error(f"Failed to update file: {str(e)}")

    async def send_error(self, message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))