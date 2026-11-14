from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(token: str):
    from apps.accounts.models import User

    try:
        user_id = AccessToken(token)["user_id"]
        return User.objects.get(pk=user_id, is_active=True)
    except (TokenError, KeyError, User.DoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware:
    """WebSocket 접속 시 `?token=<access>` 로 인증 (브라우저 WebSocket 은 헤더를 못 붙이기 때문)"""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        token = parse_qs(scope.get("query_string", b"").decode()).get("token", [""])[0]
        scope["user"] = await _get_user(token) if token else AnonymousUser()
        return await self.inner(scope, receive, send)
