import json
import asyncio
from datetime import datetime
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from decouple import config

from .models import Visitor


class RealtimeVoiceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        query = parse_qs(self.scope.get("query_string", b"").decode())
        visitor_id = (query.get("visitor_id") or [None])[0]
        self.openai_ws = None
        self.openai_listener_task = None
        self.conversation_lines = []
        self.pending_audio_chunks = 0
        self.pending_audio_ms = 0.0
        self.response_in_progress = False

        if not visitor_id:
            await self.close(code=4000)
            return

        self.visitor = await self.get_visitor(visitor_id)
        if not self.visitor:
            await self.close(code=4004)
            return

        await self.accept()

    async def disconnect(self, close_code):
        if self.openai_listener_task:
            self.openai_listener_task.cancel()

        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except Exception:
                pass

        if self.conversation_lines:
            await self.save_conversation("\n".join(self.conversation_lines))

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json_error("invalid json payload")
            return

        action_type = payload.get("type")
        if action_type == "start":
            await self.start_openai_realtime()
            return

        if not self.openai_ws:
            await self.send_json_error("session not started, send {type: start} first")
            return

        if action_type == "audio":
            audio_chunk = payload.get("audio")
            if not audio_chunk:
                await self.send_json_error("audio chunk is required")
                return

            await self.openai_ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": audio_chunk}))
            self.pending_audio_chunks += 1
            self.pending_audio_ms += self.estimate_audio_ms(audio_chunk)
            return

        if action_type == "commit":
            if self.response_in_progress:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "info",
                            "message": "response_in_progress",
                        }
                    )
                )
                return

            if self.pending_audio_chunks < 1 or self.pending_audio_ms < 120:
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "info",
                            "message": "not_enough_audio",
                        }
                    )
                )
                return

            await self.openai_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
            await self.openai_ws.send(
                json.dumps(
                    {
                        "type": "response.create",
                        "response": {
                            "modalities": ["audio", "text"],
                            "instructions": payload.get(
                                "instructions",
                                "Talk naturally and provide complete, detailed responses.",
                            ),
                        },
                    }
                )
            )
            self.pending_audio_chunks = 0
            self.pending_audio_ms = 0.0
            self.response_in_progress = True
            return

        if action_type == "text":
            text_value = payload.get("text", "").strip()
            if not text_value:
                await self.send_json_error("text is required")
                return

            self.conversation_lines.append(f"[{self.now_iso()}] Visitor: {text_value}")
            await self.openai_ws.send(
                json.dumps(
                    {
                        "type": "conversation.item.create",
                        "item": {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": text_value}],
                        },
                    }
                )
            )
            await self.openai_ws.send(
                json.dumps(
                    {
                        "type": "response.create",
                        "response": {"modalities": ["audio", "text"]},
                    }
                )
            )
            return

        await self.send_json_error("unsupported message type")

    async def start_openai_realtime(self):
        if self.openai_ws:
            await self.send(text_data=json.dumps({"type": "ready"}))
            return

        try:
            import importlib

            websockets = importlib.import_module("websockets")
        except ImportError:
            await self.send_json_error("websockets package is not installed on server")
            return

        api_key = config("OPENAI_API_KEY", default="")
        model = config("OPENAI_REALTIME_MODEL", default="gpt-4o-realtime-preview")
        if not api_key:
            await self.send_json_error("OPENAI_API_KEY is missing")
            return

        url = f"wss://api.openai.com/v1/realtime?model={model}"
        try:
            self.openai_ws = await websockets.connect(
                url,
                additional_headers={
                    "Authorization": f"Bearer {api_key}",
                    "OpenAI-Beta": "realtime=v1",
                },
                ping_interval=20,
                ping_timeout=20,
            )
        except Exception as exc:
            await self.send_json_error(f"failed to connect realtime api: {str(exc)}")
            return

        self.openai_listener_task = asyncio.create_task(self.listen_openai())
        await self.send(text_data=json.dumps({"type": "ready"}))

    async def listen_openai(self):
        if not self.openai_ws:
            return

        try:
            async for raw_event in self.openai_ws:
                try:
                    event = json.loads(raw_event)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type")

                if event_type == "response.created":
                    self.response_in_progress = True
                    continue

                if event_type == "response.done":
                    self.response_in_progress = False
                    await self.send(text_data=json.dumps({"type": "ai_response_done"}))
                    continue

                if event_type == "response.audio.delta":
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "ai_audio",
                                "audio": event.get("delta"),
                            }
                        )
                    )
                elif event_type in {"response.audio_transcript.delta", "response.text.delta"}:
                    delta = event.get("delta", "")
                    await self.send(text_data=json.dumps({"type": "ai_text_delta", "text": delta}))
                elif event_type in {"response.audio_transcript.done", "response.text.done"}:
                    final_text = event.get("transcript") or event.get("text") or ""
                    if final_text:
                        self.conversation_lines.append(f"[{self.now_iso()}] AI: {final_text}")
                    await self.send(text_data=json.dumps({"type": "ai_text_done", "text": final_text}))
                elif event_type == "error":
                    error_message = event.get("error", {}).get("message", "realtime error")

                    # Avoid spamming frontend with expected pacing issues.
                    if "buffer too small" in error_message.lower():
                        self.response_in_progress = False
                        await self.send(
                            text_data=json.dumps(
                                {
                                    "type": "info",
                                    "message": "not_enough_audio",
                                }
                            )
                        )
                        continue

                    await self.send_json_error(error_message)
        except Exception as exc:
            await self.send_json_error(f"realtime session closed: {str(exc)}")

    async def send_json_error(self, message):
        await self.send(text_data=json.dumps({"type": "error", "message": message}))

    @staticmethod
    def now_iso():
        return datetime.utcnow().isoformat()

    @staticmethod
    def estimate_audio_ms(base64_audio: str) -> float:
        if not base64_audio:
            return 0.0

        padding = base64_audio.count("=")
        decoded_bytes = max(0, (len(base64_audio) * 3 // 4) - padding)

        # PCM16 mono at 24kHz -> 2 bytes/sample, 24000 samples/sec
        bytes_per_second = 2 * 24000
        if bytes_per_second == 0:
            return 0.0

        return (decoded_bytes / bytes_per_second) * 1000.0

    @database_sync_to_async
    def get_visitor(self, visitor_id):
        try:
            return Visitor.objects.get(id=visitor_id)
        except Visitor.DoesNotExist:
            return None

    @database_sync_to_async
    def save_conversation(self, transcript_text):
        visitor = Visitor.objects.get(id=self.visitor.id)
        if visitor.conversission:
            visitor.conversission = f"{visitor.conversission}\n{transcript_text}".strip()
        else:
            visitor.conversission = transcript_text
        visitor.save(update_fields=["conversission"])
