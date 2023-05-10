import telegram
from typing import Protocol


class SubscriberService(Protocol):
    owner: str
    subscriber_list: list[str]

    def send_to_owner(self, message: str) -> None:
        """Send message to owner"""

    def send_to_all(self, message: str) -> None:
        """Send message to all subscribers"""


class TelegramService:
    instance: telegram.Bot
    owner: str
    subscriber_list: list[str]

    def __init__(
        self, instance: telegram.Bot, owner: str, subscribers: list[str]
    ) -> None:
        self.instance = instance
        self.owner = owner
        self.subscriber_list = subscribers

    async def send_to_owner(self, message: str) -> None:
        """Send message to owner"""
        await self.instance.send_message(chat_id=self.owner, text=message)

    async def send_to_all(self, message: str) -> None:
        """Send message to all subscribers"""
        for id in self.subscriber_list:
            await self.instance.send_message(chat_id=id, text=message)


class Broadcaster:
    telegram_service: TelegramService = None

    def register_telegram(self, service: TelegramService):
        self.telegram_service = service

    async def over_all(self, message: str) -> None:
        """
        Send message to all subscribers of all registered services.

        :message - message to send
        """
        if self.telegram_service:
            await self.telegram_service.send_to_all(message)

    async def over_telegram(self, message: str) -> None:
        """
        Send message to all Telegram subscribers.

        :message - message to send
        """
        if self.telegram_service:
            await self.telegram_service.send_to_all(message)
        else:
            raise Exception("Telegram service not initialized")

    async def to_owner(self, message: str) -> None:
        """
        Try to reach the owner over all channels.

        :message - message to send
        """
        if self.telegram_service:
            await self.telegram_service.send_to_owner(message)
