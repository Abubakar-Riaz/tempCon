# notifications/consumers.py

from __future__ import annotations

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from accounts.models import DealershipMembership, MembershipStatus
from notifications.channels.websocket import get_notification_group_name


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.dealership_public_id = self.scope["url_route"]["kwargs"]["dealership_id"]

        if not self.user or not self.user.is_authenticated:
            await self.accept()
            await self.send_json(
                {
                    "type": "auth.token_expired_or_invalid",
                    "detail": "Refresh token using REST API, then reconnect websocket.",
                }
            )
            await self.close(code=4001)
            return

        has_access = await self.user_has_dealership_access(
            user_id=self.user.id,
            dealership_public_id=self.dealership_public_id,
        )

        if not has_access:
            await self.close(code=4003)
            return

        self.group_name = get_notification_group_name(
            dealership_public_id=self.dealership_public_id,
            user_public_id=self.user.public_id,
        )

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send_json(
            {
                "type": "notification.socket_connected",
                "dealership_id": self.dealership_public_id,
            }
        )

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)

        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def send_notification(self, event):
        await self.send_json(event["payload"])

    @database_sync_to_async
    def user_has_dealership_access(self, *, user_id: int, dealership_public_id: str) -> bool:
        return DealershipMembership.objects.filter(
            user_id=user_id,
            dealership__public_id=dealership_public_id,
            status=MembershipStatus.ACTIVE,
            user__is_active=True,
            dealership__is_active=True,
            company__is_active=True,
        ).exists()