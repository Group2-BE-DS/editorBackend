from django.urls import path
from . import consumers  # You'll create this next

websocket_urlpatterns = [
    path('ws/somepath/', consumers.MyConsumer.as_asgi()),  # Define your WebSocket endpoint
]
