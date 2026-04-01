from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

User = get_user_model()

class CustomAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope['user'] = await self.get_user(scope)
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, scope):
        try:
            query_string = parse_qs(scope['query_string'].decode())
            token = query_string.get('token')  # list of values
            if not token:
                return AnonymousUser()

            token = token[0]  # get first token
            access_token = AccessToken(token)

            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
            return user
        except (User.DoesNotExist, TokenError, InvalidToken, Exception):
    
            return AnonymousUser()

