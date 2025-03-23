# server.py
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

# Server settings - use Render's environment variables
HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 10000))

class GameServer:
    def __init__(self):
        self.clients = {}  # websocket -> (name, lobby_code)
        self.lobbies = {}  # lobby_code -> [websockets]
        logger.info(f"Server initialized, ready to accept connections on port {PORT}")
    
    def generate_lobby_code(self):
        # Generate a random 4-character code
        code = ''.join(random.choices(string.ascii_uppercase, k=4))
        while code in self.lobbies:
            code = ''.join(random.choices(string.ascii_uppercase, k=4))
        return code
    
    async def update_player_list(self, lobby_code):
        if lobby_code not in self.lobbies:
            return
            
        # Get all player names in this lobby
        players = [self.clients[client][0] for client in self.lobbies[lobby_code]]
        
        # Send updated list to all players in lobby
        message = json.dumps({
            "type": "player_list",
            "players": players
        })
        
        await asyncio.gather(
            *[client.send(message) for client in self.lobbies[lobby_code]]
        )
        logger.info(f"Updated player list for lobby {lobby_code}: {players}")
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path):
        try:
            logger.info(f"New connection established")
            
            async for message in websocket:
                try:
                    msg = json.loads(message)
                    
                    if msg["type"] == "create_lobby":
                        player_name = msg["name"]
                        lobby_code = self.generate_lobby_code()
                        
                        # Store client info
                        self.clients[websocket] = (player_name, lobby_code)
                        
                        # Create new lobby
                        self.lobbies[lobby_code] = [websocket]
                        
                        # Notify client
                        await websocket.send(json.dumps({
                            "type": "lobby_created",
                            "code": lobby_code
                        }))
                        
                        # Send player list
                        await self.update_player_list(lobby_code)
                        logger.info(f"Lobby created: {lobby_code} by {player_name}")
                        
                    elif msg["type"] == "join_lobby":
                        player_name = msg["name"]
                        lobby_code = msg["code"]
                        
                        if lobby_code in self.lobbies:
                            # Store client info
                            self.clients[websocket] = (player_name, lobby_code)
                            
                            # Add to existing lobby
                            self.lobbies[lobby_code].append(websocket)
                            
                            # Notify client
                            await websocket.send(json.dumps({
                                "type": "lobby_joined"
                            }))
                            
                            # Update player list for all in lobby
                            await self.update_player_list(lobby_code)
                            logger.info(f"Player {player_name} joined lobby {lobby_code}")
                        else:
                            # Notify join failure
                            await websocket.send(json.dumps({
                                "type": "join_failed"
                            }))
                            logger.info(f"Failed join attempt: lobby {lobby_code} doesn't exist")
                
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received: {message}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.info("Connection closed")
        finally:
            await self.handle_disconnect(websocket)
    
    async def handle_disconnect(self, websocket):
        if websocket in self.clients:
            player_name, lobby_code = self.clients[websocket]
            
            # Remove from lobby
            if lobby_code in self.lobbies and websocket in self.lobbies[lobby_code]:
                self.lobbies[lobby_code].remove(websocket)
                
                # If lobby is empty, remove it
                if not self.lobbies[lobby_code]:
                    del self.lobbies[lobby_code]
                    logger.info(f"Lobby {lobby_code} removed (empty)")
                else:
                    # Update player list for remaining players
                    await self.update_player_list(lobby_code)
            
            # Remove client info
            del self.clients[websocket]
            logger.info(f"Player {player_name} disconnected from lobby {lobby_code}")

    async def start_server(self):
        server = await websockets.serve(
            self.handle_client, HOST, PORT, ping_interval=None, ping_timeout=None
        )
        logger.info(f"Server started on {HOST}:{PORT}")
        return server


# For running on Render
if __name__ == "__main__":
    server = GameServer()
    loop = asyncio.get_event_loop()
    start_server = server.start_server()
    server_task = loop.run_until_complete(start_server)
    
    try:
        logger.info("Server is running. Press Ctrl+C to stop.")
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Server shutting down...")
    finally:
        server_task.close()
        loop.run_until_complete(server_task.wait_closed())
        loop.close()