import os
import json
import asyncio
import random
import string
import websockets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use Render's assigned PORT (default: 10000)
HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", 10000))

class GameServer:
    def __init__(self):
        self.clients = {}  # websocket -> (name, lobby_code)
        self.lobbies = {}  # lobby_code -> [websockets]
        logger.info(f"Server initialized on port {PORT}")

    def generate_lobby_code(self):
        """Generate a unique 4-character lobby code."""
        while True:
            code = "".join(random.choices(string.ascii_uppercase, k=4))
            if code not in self.lobbies:
                return code

    async def update_player_list(self, lobby_code):
        """Notify all players in a lobby of the updated player list."""
        if lobby_code not in self.lobbies:
            return

        players = [self.clients[client][0] for client in self.lobbies[lobby_code]]
        message = json.dumps({"type": "player_list", "players": players})

        await asyncio.gather(*[client.send(message) for client in self.lobbies[lobby_code]])
        logger.info(f"Updated player list for lobby {lobby_code}: {players}")

    async def handle_client(self, websocket, path):
        """Handle WebSocket connections from clients."""
        try:
            logger.info("New WebSocket connection established")

            async for message in websocket:
                try:
                    msg = json.loads(message)

                    if msg["type"] == "create_lobby":
                        player_name = msg["name"]
                        lobby_code = self.generate_lobby_code()

                        # Store client and create lobby
                        self.clients[websocket] = (player_name, lobby_code)
                        self.lobbies[lobby_code] = [websocket]

                        await websocket.send(json.dumps({"type": "lobby_created", "code": lobby_code}))
                        await self.update_player_list(lobby_code)
                        logger.info(f"Lobby {lobby_code} created by {player_name}")

                    elif msg["type"] == "join_lobby":
                        player_name = msg["name"]
                        lobby_code = msg["code"]

                        if lobby_code in self.lobbies:
                            self.clients[websocket] = (player_name, lobby_code)
                            self.lobbies[lobby_code].append(websocket)

                            await websocket.send(json.dumps({"type": "lobby_joined"}))
                            await self.update_player_list(lobby_code)
                            logger.info(f"Player {player_name} joined lobby {lobby_code}")
                        else:
                            await websocket.send(json.dumps({"type": "join_failed"}))
                            logger.info(f"Failed join attempt: Lobby {lobby_code} doesn't exist")

                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            await self.handle_disconnect(websocket)

    async def handle_disconnect(self, websocket):
        """Remove disconnected client from the lobby."""
        if websocket in self.clients:
            player_name, lobby_code = self.clients.pop(websocket, (None, None))

            if lobby_code and lobby_code in self.lobbies:
                self.lobbies[lobby_code].remove(websocket)

                if not self.lobbies[lobby_code]:  # Remove empty lobby
                    del self.lobbies[lobby_code]
                    logger.info(f"Lobby {lobby_code} removed (empty)")
                else:
                    await self.update_player_list(lobby_code)

            logger.info(f"Player {player_name} disconnected from lobby {lobby_code}")

    async def start_server(self):
        """Start the WebSocket server."""
        server = await websockets.serve(
            self.handle_client, HOST, PORT, ping_interval=30, ping_timeout=60
        )
        logger.info(f"WebSocket server running on {HOST}:{PORT}")
        return server

if __name__ == "__main__":
    server = GameServer()
    loop = asyncio.get_event_loop()
    start_server = server.start_server()
    server_task = loop.run_until_complete(start_server)

    try:
        logger.info("Server is running. Press Ctrl+C to stop.")
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
    finally:
        loop.run_until_complete(asyncio.gather(server_task.wait_closed()))
        loop.close()
