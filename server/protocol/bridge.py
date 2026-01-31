"""WebSocket bridge - handles communication with game adapters."""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    WebSocketServerProtocol = Any

from .messages import (
    Message, MessageType, Command, Event,
    PerceptionEvent, ChatReceivedEvent, ActionCompleteEvent,
    CombatEvent, TimeUpdateEvent, parse_event,
    MoveCommand, GatherCommand, ChatMessage, AttackCommand,
    BuildCommand, TradeOffer, TradeRespond,
)


class ConnectionState(Enum):
    """State of an adapter connection."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class AdapterConnection:
    """Represents a connection to a game adapter."""
    adapter_id: str
    game_type: str  # minecraft, textadv, etc.
    websocket: Optional[WebSocketServerProtocol] = None
    state: ConnectionState = ConnectionState.CONNECTING
    agents: list[str] = field(default_factory=list)  # Agent IDs managed by this adapter
    last_heartbeat: float = 0.0
    message_queue: asyncio.Queue = field(default_factory=asyncio.Queue)

    async def send(self, message: Message) -> bool:
        """Send a message to this adapter."""
        if not self.websocket or self.state != ConnectionState.CONNECTED:
            return False

        try:
            await self.websocket.send(message.to_json())
            return True
        except Exception as e:
            print(f"Failed to send to adapter {self.adapter_id}: {e}")
            self.state = ConnectionState.ERROR
            return False

    async def send_command(self, command: Command) -> bool:
        """Send a command to this adapter."""
        return await self.send(command.to_message())


class GameBridge:
    """
    WebSocket bridge that manages connections to game adapters.

    Responsibilities:
    - Accept connections from game adapters (Minecraft, text adventure, etc.)
    - Route commands from agents to appropriate adapters
    - Route events from adapters to appropriate agent handlers
    - Handle heartbeats and connection management
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.adapters: dict[str, AdapterConnection] = {}
        self.agent_to_adapter: dict[str, str] = {}  # agent_id -> adapter_id

        # Callbacks
        self.on_perception: Optional[Callable[[str, dict], Any]] = None
        self.on_chat_received: Optional[Callable[[str, str, str], Any]] = None
        self.on_action_complete: Optional[Callable[[str, str, dict], Any]] = None
        self.on_combat: Optional[Callable[[str, dict], Any]] = None
        self.on_time_update: Optional[Callable[[int, str, bool], Any]] = None
        self.on_adapter_connected: Optional[Callable[[str, str], Any]] = None
        self.on_adapter_disconnected: Optional[Callable[[str], Any]] = None

        self._server = None
        self._running = False

    async def start(self) -> None:
        """Start the WebSocket server."""
        if not WEBSOCKETS_AVAILABLE:
            raise RuntimeError("websockets library not installed. Install with: pip install websockets")

        self._running = True
        self._server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )
        print(f"Game bridge listening on ws://{self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Close all adapter connections
        for adapter in self.adapters.values():
            if adapter.websocket:
                await adapter.websocket.close()

    async def _handle_connection(self, websocket: WebSocketServerProtocol,
                                 path: str) -> None:
        """Handle a new WebSocket connection."""
        adapter_id = None

        try:
            # Wait for registration message
            raw_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            message = Message.from_json(raw_message)

            if message.type != MessageType.REGISTER:
                await websocket.close(1002, "Expected REGISTER message")
                return

            adapter_id = message.payload.get("adapter_id", f"adapter_{len(self.adapters)}")
            game_type = message.payload.get("game_type", "unknown")
            agents = message.payload.get("agents", [])

            # Create connection
            connection = AdapterConnection(
                adapter_id=adapter_id,
                game_type=game_type,
                websocket=websocket,
                state=ConnectionState.CONNECTED,
                agents=agents,
                last_heartbeat=time.time(),
            )

            self.adapters[adapter_id] = connection

            # Map agents to this adapter
            for agent_id in agents:
                self.agent_to_adapter[agent_id] = adapter_id

            # Send acknowledgment
            ack = Message(
                type=MessageType.REGISTER_ACK,
                agent_id="server",
                timestamp=time.time(),
                payload={"adapter_id": adapter_id, "status": "connected"}
            )
            await websocket.send(ack.to_json())

            # Notify callback
            if self.on_adapter_connected:
                await self._call_callback(self.on_adapter_connected, adapter_id, game_type)

            print(f"Adapter connected: {adapter_id} ({game_type}) with agents {agents}")

            # Main message loop
            await self._message_loop(connection)

        except asyncio.TimeoutError:
            print("Connection timed out waiting for registration")
        except websockets.exceptions.ConnectionClosed:
            print(f"Connection closed: {adapter_id}")
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            if adapter_id and adapter_id in self.adapters:
                await self._handle_disconnect(adapter_id)

    async def _message_loop(self, connection: AdapterConnection) -> None:
        """Main message processing loop for a connection."""
        while self._running and connection.state == ConnectionState.CONNECTED:
            try:
                raw_message = await asyncio.wait_for(
                    connection.websocket.recv(),
                    timeout=30.0  # Heartbeat timeout
                )

                message = Message.from_json(raw_message)
                await self._process_message(connection, message)

            except asyncio.TimeoutError:
                # Send heartbeat
                heartbeat = Message(
                    type=MessageType.HEARTBEAT,
                    agent_id="server",
                    timestamp=time.time(),
                )
                try:
                    await connection.websocket.send(heartbeat.to_json())
                except:
                    break

            except websockets.exceptions.ConnectionClosed:
                break
            except json.JSONDecodeError as e:
                print(f"Invalid JSON from {connection.adapter_id}: {e}")
            except Exception as e:
                print(f"Error processing message: {e}")

    async def _process_message(self, connection: AdapterConnection,
                              message: Message) -> None:
        """Process an incoming message from an adapter."""
        connection.last_heartbeat = time.time()

        if message.type == MessageType.HEARTBEAT:
            return

        event = parse_event(message)

        # Route to appropriate handler
        if message.type == MessageType.PERCEPTION:
            if self.on_perception:
                perception_event = PerceptionEvent.from_message(message)
                await self._call_callback(
                    self.on_perception,
                    message.agent_id,
                    perception_event.perception.to_dict()
                )

        elif message.type == MessageType.CHAT_RECEIVED:
            if self.on_chat_received:
                chat_event = ChatReceivedEvent.from_message(message)
                await self._call_callback(
                    self.on_chat_received,
                    message.agent_id,
                    chat_event.sender,
                    chat_event.message
                )

        elif message.type == MessageType.ACTION_COMPLETE:
            if self.on_action_complete:
                action_event = ActionCompleteEvent.from_message(message)
                await self._call_callback(
                    self.on_action_complete,
                    message.agent_id,
                    action_event.action,
                    action_event.result
                )

        elif message.type == MessageType.COMBAT:
            if self.on_combat:
                combat_event = CombatEvent.from_message(message)
                await self._call_callback(
                    self.on_combat,
                    message.agent_id,
                    {
                        "opponent": combat_event.opponent,
                        "damage_dealt": combat_event.damage_dealt,
                        "damage_received": combat_event.damage_received,
                        "outcome": combat_event.outcome,
                    }
                )

        elif message.type == MessageType.TIME_UPDATE:
            if self.on_time_update:
                time_event = TimeUpdateEvent.from_message(message)
                await self._call_callback(
                    self.on_time_update,
                    time_event.day,
                    time_event.period,
                    time_event.is_night
                )

    async def _call_callback(self, callback: Callable, *args) -> Any:
        """Call a callback, handling both sync and async."""
        result = callback(*args)
        if asyncio.iscoroutine(result):
            return await result
        return result

    async def _handle_disconnect(self, adapter_id: str) -> None:
        """Handle adapter disconnection."""
        if adapter_id not in self.adapters:
            return

        connection = self.adapters[adapter_id]
        connection.state = ConnectionState.DISCONNECTED

        # Remove agent mappings
        for agent_id in connection.agents:
            self.agent_to_adapter.pop(agent_id, None)

        del self.adapters[adapter_id]

        if self.on_adapter_disconnected:
            await self._call_callback(self.on_adapter_disconnected, adapter_id)

        print(f"Adapter disconnected: {adapter_id}")

    # Command sending methods

    async def send_move(self, agent_id: str, direction: str,
                       x: Optional[float] = None, y: Optional[float] = None,
                       z: Optional[float] = None) -> bool:
        """Send a move command to an agent's adapter."""
        adapter_id = self.agent_to_adapter.get(agent_id)
        if not adapter_id or adapter_id not in self.adapters:
            return False

        command = MoveCommand(
            agent_id=agent_id,
            timestamp=time.time(),
            direction=direction,
            x=x, y=y, z=z
        )
        return await self.adapters[adapter_id].send_command(command)

    async def send_gather(self, agent_id: str, resource_type: str,
                         location: Optional[dict] = None) -> bool:
        """Send a gather command."""
        adapter_id = self.agent_to_adapter.get(agent_id)
        if not adapter_id or adapter_id not in self.adapters:
            return False

        command = GatherCommand(
            agent_id=agent_id,
            timestamp=time.time(),
            resource_type=resource_type,
            location=location
        )
        return await self.adapters[adapter_id].send_command(command)

    async def send_chat(self, agent_id: str, message: str,
                       target: Optional[str] = None) -> bool:
        """Send a chat message."""
        adapter_id = self.agent_to_adapter.get(agent_id)
        if not adapter_id or adapter_id not in self.adapters:
            return False

        command = ChatMessage(
            agent_id=agent_id,
            timestamp=time.time(),
            message=message,
            target=target
        )
        return await self.adapters[adapter_id].send_command(command)

    async def send_attack(self, agent_id: str, target: str) -> bool:
        """Send an attack command."""
        adapter_id = self.agent_to_adapter.get(agent_id)
        if not adapter_id or adapter_id not in self.adapters:
            return False

        command = AttackCommand(
            agent_id=agent_id,
            timestamp=time.time(),
            target=target
        )
        return await self.adapters[adapter_id].send_command(command)

    async def send_build(self, agent_id: str, structure_type: str,
                        location: Optional[dict] = None,
                        materials: Optional[list[str]] = None) -> bool:
        """Send a build command."""
        adapter_id = self.agent_to_adapter.get(agent_id)
        if not adapter_id or adapter_id not in self.adapters:
            return False

        command = BuildCommand(
            agent_id=agent_id,
            timestamp=time.time(),
            structure_type=structure_type,
            location=location,
            materials=materials or []
        )
        return await self.adapters[adapter_id].send_command(command)

    async def send_trade_offer(self, agent_id: str, target_agent: str,
                              offering: list[dict],
                              requesting: list[dict]) -> bool:
        """Send a trade offer."""
        adapter_id = self.agent_to_adapter.get(agent_id)
        if not adapter_id or adapter_id not in self.adapters:
            return False

        command = TradeOffer(
            agent_id=agent_id,
            timestamp=time.time(),
            target_agent=target_agent,
            offering=offering,
            requesting=requesting
        )
        return await self.adapters[adapter_id].send_command(command)

    async def broadcast_to_adapters(self, message: Message) -> int:
        """Broadcast a message to all connected adapters."""
        sent = 0
        for adapter in self.adapters.values():
            if await adapter.send(message):
                sent += 1
        return sent

    def get_adapter_for_agent(self, agent_id: str) -> Optional[AdapterConnection]:
        """Get the adapter connection for an agent."""
        adapter_id = self.agent_to_adapter.get(agent_id)
        if adapter_id:
            return self.adapters.get(adapter_id)
        return None

    def get_connected_agents(self) -> list[str]:
        """Get list of all connected agents."""
        return list(self.agent_to_adapter.keys())

    def get_status(self) -> dict:
        """Get bridge status."""
        return {
            "running": self._running,
            "adapter_count": len(self.adapters),
            "agent_count": len(self.agent_to_adapter),
            "adapters": [
                {
                    "id": a.adapter_id,
                    "game_type": a.game_type,
                    "state": a.state.value,
                    "agents": a.agents,
                }
                for a in self.adapters.values()
            ]
        }
