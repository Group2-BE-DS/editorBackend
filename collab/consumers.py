import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from .token_store import TokenStore
import asyncio
from datetime import datetime
import random
import string

logger = logging.getLogger(__name__)

class EditorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info("WebSocket connection attempt")
        await self.accept()
        
        # Initialize consumer state
        self.user_id = ''.join(random.choices(string.digits, k=20))
        self.username = None  # Will be set from auth token
        self.joined_at = datetime.now().isoformat()
        self.status = 'active'
        self.is_collaborative = False
        self.token = None
        self.repository_slug = None
        self.room_name = None
        self.room_group_name = None
        
        logger.info(f"Connection accepted for user ID: {self.user_id}")
        logger.info("Waiting for initial message with tokens...")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected for user {self.user_id} with code: {close_code}")
        
        if self.is_collaborative and self.room_group_name:
            # Remove user from room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            if self.token:
                # Remove connection and notify others
                TokenStore.remove_connection(self.token, self.user_id)
                remaining_users = TokenStore.get_connections(self.token)
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_left',
                        'user_id': self.user_id,
                        'username': self.username,
                        'remaining_users': remaining_users
                    }
                )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            logger.info(f"Received message from user {self.user_id} - Type: {message_type}")
            
            if message_type == 'init':
                await self.handle_init(data)
            elif message_type == 'openFile':
                await self.handle_open_file(data)
            elif message_type == 'codeUpdate':
                await self.handle_code_update(data)
            elif message_type == 'status_update':
                await self.update_user_status(data.get('status', 'active'))
            else:
                logger.warning(f"Unknown message type from user {self.user_id}: {message_type}")
                
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user_id}")
        except Exception as e:
            logger.error(f"Error processing message from user {self.user_id}: {str(e)}")

    async def handle_init(self, data):
        """Handle initial connection setup with token verification"""
        token = data.get('token', '').strip()
        auth_token = data.get('authToken', '').strip()
        
        logger.info(f"Processing init message from user {self.user_id}")
        logger.info(f"Auth token present: {bool(auth_token)}")
        logger.info(f"Collab token present: {bool(token)}")
        
        # Try to get username from auth token first
        if auth_token:
            from rest_framework.authtoken.models import Token
            try:
                token_obj = await asyncio.get_event_loop().run_in_executor(None, 
                    lambda: Token.objects.select_related('user').get(key=auth_token))
                self.username = token_obj.user.username
                logger.info(f"Found username from auth token: {self.username}")
            except Token.DoesNotExist:
                logger.warning("Auth token invalid or expired")
                self.username = "Anonymous"
        else:
            self.username = "Anonymous"
            logger.warning("No auth token provided")

        if not token:
            logger.warning(f"No collaboration token provided by user {self.user_id}")
            await self.send(json.dumps({
                'type': 'solo_mode',
                'message': 'No token provided, working in solo mode'
            }))
            return

        # Verify collaboration token and get repository info
        if TokenStore.verify_token(token):
            logger.info(f"Token verified successfully for user {self.user_id}")
            self.token = token
            self.repository_slug = TokenStore.get_repository_slug(token)
            
            if not self.repository_slug:
                logger.error(f"No repository slug found for token (user: {self.user_id})")
                await self.send(json.dumps({
                    'type': 'error',
                    'message': 'Invalid repository'
                }))
                return
                
            logger.info(f"Retrieved repository slug for user {self.user_id}: {self.repository_slug}")
            
            # Add user connection to token store with actual username
            if TokenStore.add_connection(token, self.user_id, self.username):
                self.is_collaborative = True
                self.room_name = self.repository_slug.replace('/', '_')
                self.room_group_name = f'editor_{self.room_name}'
                
                # Join room group
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                
                # Get current users in room
                connected_users = TokenStore.get_connections(token)
                logger.info(f"Users in room {self.room_group_name}: {connected_users}")
                
                # Notify current user about successful connection
                await self.send(json.dumps({
                    'type': 'connected',
                    'repository': self.repository_slug,
                    'user_id': self.user_id,
                    'users': connected_users
                }))
                
                # Notify others about new user
                user_info = {
                    'username': self.username,
                    'id': self.user_id,
                    'joined_at': self.joined_at,
                    'status': self.status
                }
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_joined',
                        'user': user_info
                    }
                )
                
                logger.info(f"Successfully completed collaboration setup for user {self.username} ({self.user_id})")
            else:
                logger.error(f"Failed to add user connection for {self.user_id}")
                await self.send(json.dumps({
                    'type': 'error',
                    'message': 'Failed to join collaboration'
                }))
        else:
            logger.warning(f"Invalid token provided by user {self.user_id}, falling back to solo mode")
            await self.send(json.dumps({
                'type': 'solo_mode',
                'message': 'Invalid token, working in solo mode'
            }))

    async def handle_code_update(self, data):
        """Handle real-time code updates"""
        if not self.is_collaborative:
            logger.warning(f"Received code update from user {self.user_id} in solo mode")
            return
            
        file_id = data.get('fileId')
        content = data.get('content')
        
        if not file_id or content is None:
            logger.error(f"Missing fileId or content in codeUpdate message from user {self.user_id}")
            return
            
        logger.info(f"Broadcasting code update for file {file_id} from user {self.user_id}")
        
        # Broadcast to all users in the room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'code_updated',
                'user_id': self.user_id,
                'file_id': file_id,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
        )

    async def code_updated(self, event):
        """Handle code updated event from other users"""
        if event['user_id'] != self.user_id:  # Don't send back to sender
            logger.info(f"Received code update from user {event['user_id']} for file {event['file_id']}")
            await self.send(json.dumps({
                'type': 'codeUpdate',
                'user_id': event['user_id'],
                'file_id': event['file_id'],
                'content': event['content'],
                'timestamp': event['timestamp']
            }))

    async def get_connected_users(self):
        """Get list of currently connected users in the room"""
        if not self.is_collaborative or not self.token:
            return []
            
        # Get all connections for this token
        users = []
        connections = TokenStore.get_connections(self.token)
        if connections:
            for user_id, username in connections.items():
                users.append({
                    'username': username,  # Use actual username from token store
                    'joined_at': self.joined_at,
                    'id': user_id,
                    'status': 'active', 
                    'last_activity': datetime.now().isoformat()
                })
        return users

    async def user_joined(self, event):
        """Handle user joined event"""
        if event['user']['id'] != self.user_id:  # Don't send back to sender
            logger.info(f"User {event['user']['id']} joined room {self.room_group_name}")
            await self.send(json.dumps({
                'type': 'user_joined',
                'user': event['user']
            }))

    async def user_left(self, event):
        """Handle user left event"""
        if event['user_id'] != self.user_id:  # Don't send back to sender
            logger.info(f"User {event['user_id']} left room {self.room_group_name}")
            await self.send(json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username'],
                'remaining_users': event.get('remaining_users', [])
            }))

    async def handle_open_file(self, data):
        """Handle file open requests"""
        file_id = data.get('fileId')
        
        if not file_id:
            logger.error(f"No file ID provided in openFile message from user {self.user_id}")
            return
            
        logger.info(f"Processing openFile request from user {self.user_id} for file_id: {file_id}")
        
        # For collaboration, notify others about file open
        if self.is_collaborative:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'file_opened',
                    'user_id': self.user_id,
                    'file_id': file_id
                }
            )

    async def file_opened(self, event):
        """Handle file opened event"""
        if event['user_id'] != self.user_id:  # Don't send back to sender
            logger.info(f"User {event['user_id']} opened file {event['file_id']}")
            await self.send(json.dumps({
                'type': 'file_opened',
                'user_id': event['user_id'],
                'file_id': event['file_id']
            }))

    async def update_user_status(self, status):
        """Update user status and notify others"""
        if not self.is_collaborative:
            return

        self.status = status
        if self.room_group_name and self.token:
            # Update status in token store
            connected_users = TokenStore.get_connections(self.token)
            if connected_users:
                # Update the user's status
                for user in connected_users:
                    if user['id'] == self.user_id:
                        user['status'] = status
                        user['last_activity'] = datetime.now().isoformat()
                        break

                # Notify others about status change
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_status_changed',
                        'user': {
                            'id': self.user_id,
                            'username': self.username,
                            'status': status,
                            'last_activity': datetime.now().isoformat()
                        }
                    }
                )

    async def user_status_changed(self, event):
        """Handle user status change event"""
        if event['user']['id'] != self.user_id:  # Don't send back to sender
            await self.send(json.dumps({
                'type': 'user_status_changed',
                'user': event['user']
            }))



