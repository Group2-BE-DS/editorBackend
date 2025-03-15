# editorBackend/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from collab import routing  # Adjust this according to your app name
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'editorBackend.settings')
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            routing.websocket_urlpatterns  # Define this in your app's routing.py
        )
    ),
})
