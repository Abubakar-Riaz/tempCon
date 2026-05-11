# inspections/consumers.py

from __future__ import annotations

import hashlib
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from inspections.realtime_utils import (
    db_build_inspection_snapshot,
    db_can_edit_inspection,
    db_can_view_inspection,
    db_item_note_set,
    db_item_status_set,
    db_resolve_vehicle_context,
    ws_error,
)


def _inspection_group_name(vehicle_public_id: str) -> str:
    raw = f"inspection.vehicle.{vehicle_public_id}"

    if len(raw) < 100:
        return raw

    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32]
    return f"inspection.vehicle.{digest}"


class InspectionRoomConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        self.vehicle_id = self.scope["url_route"]["kwargs"]["vehicle_id"]

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

        vehicle, ctx = await db_resolve_vehicle_context(
            self.user,
            self.vehicle_id,
        )

        if not vehicle:
            await self.accept()
            await self.send_json(
                {
                    "type": "error",
                    "data": ws_error("NOT_FOUND", "Vehicle not found."),
                }
            )
            await self.close(code=4004)
            return

        if not ctx or not await db_can_view_inspection(ctx):
            await self.accept()
            await self.send_json(
                {
                    "type": "error",
                    "data": ws_error("FORBIDDEN", "You do not have permission to view inspections."),
                }
            )
            await self.close(code=4003)
            return

        self.vehicle = vehicle
        self.ctx = ctx
        self.read_only = not await db_can_edit_inspection(ctx)
        self.group_name = _inspection_group_name(str(vehicle.public_id))

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send_json(
            {
                "type": "inspection.socket_connected",
                "data": {
                    "vehicle_id": str(vehicle.public_id),
                    "read_only": self.read_only,
                    "you": {
                        "id": str(self.user.public_id),
                        "email": self.user.email,
                    },
                },
            }
        )

        snapshot = await db_build_inspection_snapshot(vehicle)
        await self.send_json(
            {
                "type": "inspection.snapshot",
                "data": snapshot,
            }
        )

    async def disconnect(self, close_code):
        group_name = getattr(self, "group_name", None)

        if group_name:
            await self.channel_layer.group_discard(
                group_name,
                self.channel_name,
            )

    async def receive_json(self, content: dict[str, Any], **kwargs):
        message_type = (content.get("type") or "").strip()
        req_id = content.get("req_id")
        data = content.get("data") or {}

        if message_type == "ping":
            await self.send_json(
                {
                    "type": "pong",
                    "req_id": req_id,
                }
            )
            return

        if message_type == "inspection.snapshot":
            snapshot = await db_build_inspection_snapshot(
                self.vehicle,
                compact=not bool(data.get("full")),
            )
            await self.send_json(
                {
                    "type": "inspection.snapshot",
                    "req_id": req_id,
                    "data": snapshot,
                }
            )
            return

        if message_type in {"item.status.set", "item.note.set"} and self.read_only:
            await self.send_json(
                {
                    "type": "error",
                    "req_id": req_id,
                    "data": ws_error("FORBIDDEN", "Read-only inspection session."),
                }
            )
            return

        try:
            if message_type == "item.status.set":
                item_id = data.get("id")
                status_value = (data.get("status") or "").strip()

                if not item_id or not status_value:
                    await self._validation(req_id, "id and status are required.")
                    return

                payload = await db_item_status_set(
                    self.user,
                    self.vehicle,
                    item_id,
                    status_value,
                )

                await self._broadcast("item.status.set", payload)
                await self._ack(req_id)
                return

            if message_type == "item.note.set":
                item_id = data.get("id")
                body = data.get("body") or ""

                if not item_id:
                    await self._validation(req_id, "id is required.")
                    return

                payload = await db_item_note_set(
                    self.user,
                    self.vehicle,
                    item_id,
                    body,
                )

                await self._broadcast("item.note.set", payload)
                await self._ack(req_id)
                return

            await self.send_json(
                {
                    "type": "error",
                    "req_id": req_id,
                    "data": ws_error("BAD_REQUEST", f"Unknown event '{message_type}'."),
                }
            )

        except ValueError as exc:
            await self.send_json(
                {
                    "type": "error",
                    "req_id": req_id,
                    "data": ws_error(str(exc), "Operation failed."),
                }
            )

    async def room_event(self, event):
        await self.send_json(
            {
                "type": event["event_type"],
                "data": event["payload"],
            }
        )

    async def _broadcast(self, event_type: str, payload: dict):
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "room.event",
                "event_type": event_type,
                "payload": payload,
            },
        )

    async def _ack(self, req_id):
        await self.send_json(
            {
                "type": "ack",
                "req_id": req_id,
                "data": {"ok": True},
            }
        )

    async def _validation(self, req_id, message: str):
        await self.send_json(
            {
                "type": "error",
                "req_id": req_id,
                "data": ws_error("VALIDATION_ERROR", message),
            }
        )