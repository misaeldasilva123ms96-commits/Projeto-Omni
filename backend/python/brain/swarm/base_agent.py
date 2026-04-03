from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class SwarmMessage:
    from_agent: str
    to_agent: str
    type: str
    payload: dict[str, Any]
    timestamp: str
    session_id: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["from"] = payload.pop("from_agent")
        payload["to"] = payload.pop("to_agent")
        return payload


class BaseAgent(ABC):
    def __init__(self, agent_id: str, queue: asyncio.Queue[SwarmMessage]) -> None:
        self.agent_id = agent_id
        self.queue = queue

    async def publish(
        self,
        *,
        to_agent: str,
        message_type: str,
        payload: dict[str, Any],
        session_id: str,
    ) -> SwarmMessage:
        message = SwarmMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            type=message_type,
            payload=payload,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
        )
        await self.queue.put(message)
        return message

    async def receive(self, message: SwarmMessage, context: dict[str, Any]) -> dict[str, Any]:
        thought = await self.think(message, context)
        action = await self.act(thought, context)
        return await self.respond(action, thought, context)

    @abstractmethod
    async def think(self, message: SwarmMessage, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def act(self, thought: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def respond(
        self,
        action_result: dict[str, Any],
        thought: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError
