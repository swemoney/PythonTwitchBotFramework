import warnings
import json
import websockets

from typing import Optional
from asyncio import sleep

__all__ = [
    'PubSubClient'
]


class PubSubClient:
    URL = 'wss://pubsub-edge.twitch.tv'
    LISTEN = 'LISTEN'
    NONCE = 'NONCE'

    def __init__(self):
        self.socket: Optional[websockets.client.WebSocketClientProtocol] = None
        self.listen_count = 0

    @classmethod
    async def _create_channel_points_topic(cls, channel_name: str) -> Optional[str]:
        from ..util import get_user_id

        user_id = await get_user_id(channel_name)
        if user_id == -1:
            warnings.warn(f'[PUBSUB-CLIENT] unable to get user id in pubsub client for channel "{channel_name}"')
            return None

        return f'channel-subscribe-events-v1.{user_id}'

    @classmethod
    async def _create_channel_chat_topic(cls, channel_name: str) -> Optional[str]:
        from ..util import get_user_id

        user_id = await get_user_id(channel_name)
        if user_id == -1:
            warnings.warn(f'[PUBSUB-CLIENT] unable to get user id in pubsub client for channel "{channel_name}"')
            return None

        return f'chat_moderator_actions.{user_id}'

    @property
    def connected(self):
        return self.socket and self.socket.open

    def create_listen_request_data(self, nonce: str = None, topics=()) -> str:
        """
        returns the json data (as a string) for listening to topic(s) on twitch's PUBSUB
        :param nonce: optional
        :param topics:
        """
        from twitchbot import get_oauth

        data = {
            'type': self.LISTEN,
            'data': {
                'topics': topics,
                'auth_token': get_oauth(remove_prefix=True),
            },
        }

        if nonce:
            data[self.NONCE] = nonce

        return json.dumps(data)

    async def listen_to_channel(self, channel_name: str, points: bool = True, chat: bool = True):
        if not self.socket or not self.socket.open:
            await self._connect()
            await sleep(.5)

        # debug
        await sleep(.5)  # small thing to rate limit to a degree

        topics = []

        if points:
            topics.append(await self._create_channel_points_topic(channel_name))

        if chat:
            topics.append(await self._create_channel_chat_topic(channel_name))

        if not topics:
            return

        await self.socket.send(
            self.create_listen_request_data(topics=topics)
        )

    async def read(self) -> Optional[str]:
        data = await self.socket.recv()
        if isinstance(data, bytes):
            return data.decode('utf-8')
        return data

    async def _connect(self) -> 'PubSubClient':
        self.socket = await websockets.connect(self.URL)
        return self
