# Socket Programming Project: Gomoku

This project is a real-time, multiplayer Gomoku (Five-in-a-Row) game implemented using Python, `asyncio`, and `websockets`. It allows multiple players to connect to a central server to play games and chat.

## Features

- **Game Lobbies:** Users can create, join, or list available game rooms.
- **15x15 Gomoku:** Standard 15x15 game board with win detection for 5-in-a-row (horizontal, vertical, diagonal).
- **Real-time Gameplay:** Moves are instantly synchronized across all clients in the room.
- **Spectator Mode:** Users can join rooms as spectators and watch the game in real-time.
- **Player Chat:** Players in a game can chat with each other and with spectators.

### Implemented Advanced Features (for Extra Credit)

- **Spectator-only Chat Mode:** Spectators have a separate chat channel (`schat` command) that is not visible to players, fulfilling the requirement to manage permissions differently.
- **Move Timer:** A 30-second move timer is implemented. If a player fails to move in time, their turn is skipped. This is managed server-side.
- **Reconnection Support:** If a player disconnects during a game, they have 30 seconds to reconnect _using the same User ID_. The server will restore their session and the game will continue.

## Technologies Used

- **Language:** Python 3
- **Core Libraries:**
  - `websockets`: For handling WebSocket connections (Client/Server).
  - `asyncio`: Used for asynchronous I/O to manage simultaneous client connections without blocking, as allowed by the clarification announcement.

## How to Run

### 1\. Dependencies

You must have the `websockets` library installed.

```bash
pip install websockets
```

### 2\. Start the Server

Run the server script in a terminal.

```bash
python server.py
```

### 3\. Run Clients

Open **multiple** new terminal windows to simulate different users (players and spectators). Run the client script in each window.

```bash
python client.py
```

The client will first ask for your **User ID** and **Display Name**.

- To test reconnection, you must use the _exact same User ID_ when you restart the client.

## Socket Communication Protocol

The client and server communicate using JSON messages.

### Client-to-Server (C2S)

- `{'type': 'list_rooms'}`
- `{'type': 'create_room', 'name': 'My Room', 'user_id': 'p1', 'user_name': 'PlayerOne'}`
- `{'type': 'join_room', 'room_id': 'xyz123', 'user_id': 'p2', 'user_name': 'PlayerTwo'}`
- `{'type': 'spectate_room', 'room_id': 'xyz123'}`
- `{'type': 'reconnect', 'room_id': 'xyz123', 'user_id': 'p1', 'token': '...'}`
- `{'type': 'move', 'move': {'r': 7, 'c': 7}}`
- `{'type': 'chat', 'message': 'Hello world!'}`
- `{'type': 'spectator_chat', 'message': 'Go player 1!'}`

### Server-to-Client (S2C)

- `{'type': 'room_list', 'rooms': [...]}`
- `{'type': 'join_success', 'room_id': 'xyz123', 'token': '...', 'your_stone': 1}`
- `{'type': 'game_state', 'board': [[...]], 'current_turn': 'p1', ...}`
- `{'type': 'move', 'player_id': 'p1', 'r': 7, 'c': 7, 'stone': 1}`
- `{'type': 'turn_change', 'current_turn': 'p2'}`
- `{'type': 'timer_update', 'player': 'p1', 'time_left': 25}`
- `{'type': 'game_over', 'winner_name': 'PlayerOne', ...}`
- `{'type': 'chat', 'sender': 'PlayerOne', 'message': 'Hello!'}`
- `{'type': 'spectator_chat', 'sender': 'Spectator-789', 'message': '...'}`
- `{'type': 'error', 'message': 'Room not found.'}`
- `{'type': 'reconnect_success', 'room_id': 'xyz123', ...}`
