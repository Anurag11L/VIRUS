# Multiplayer Lobby Game

A simple multiplayer lobby system built with Pygame and WebSockets.

## Deployment Instructions

### Server Deployment on Render

1. Create a new Web Service on Render
2. Link to your GitHub repository
3. Configure the service:
   - **Name**: `game-lobby-server`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
   - **Plan**: Free (or any other plan)

### Client Configuration

After deploying the server, update the `SERVER_URL` in the client code:

```python
# Replace with your actual Render URL
SERVER_URL = "wss://your-app-name.onrender.com"
```

## Running the Client

1. Install the required packages:

   ```
   pip install pygame websockets
   ```

2. Run the client:
   ```
   python game.py
   ```

## Features

- Player name entry
- Create and join game lobbies
- Real-time player list updates
- Secure WebSocket communication

## Directory Structure

- `server.py` - WebSocket server for Render
- `game.py` - Pygame client application
- `requirements.txt` - Dependencies for Render
- `Procfile` - Process configuration for Render

## How It Works

1. Players enter their names
2. They can create a lobby or join one with a code
3. All connected players can see who's in the lobby
4. WebSockets provide real-time updates
