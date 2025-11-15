# Socket Programming Project: Gomoku

A real-time, multiplayer Gomoku (Five-in-a-Row) game implemented using Python, `asyncio`, and `websockets`. This project allows multiple players to connect to a central server to play games, spectate ongoing matches, and communicate through real-time chat.

## Table of Contents

- [How to Run](#how-to-run)
- [Dependencies](#dependencies)
- [Protocol Specification](#protocol-specification)
- [Features](#features)
- [Advanced Features](#advanced-features)

## How to Run

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation Steps

1. **Clone or navigate to the project directory:**

   ```bash
   cd /path/to/hw3
   ```

2. **Install dependencies:**

   ```bash
   pip install websockets
   ```

   Alternatively, if you have a `requirements.txt` file:

   ```bash
   pip install -r requirements.txt
   ```

### Starting the Application

1. **Start the server:**

   ```bash
   python server.py
   ```

   The server will start on `ws://localhost:8765` and display:

   ```
   Starting Gomoku server on ws://localhost:8765
   ```

2. **Run client instances:**
   Open multiple terminal windows (one for each player/spectator) and run:

   ```bash
   python client.py
   ```

   Each client will prompt for:

   - **User ID**: A unique identifier (e.g., `player123`)
   - **Display Name**: Your display name (e.g., `Alice`)

   **Note:** To test reconnection, use the exact same User ID when restarting the client.

3. **Game Commands:**
   - In the lobby: `list`, `create <room_name>`, `join <room_id>`, `spectate <room_id>`, `reconnect`
   - During game: `move <row> <col>`, `chat <message>`, `board`
   - As spectator: `chat <message>`, `schat <message>`, `board`
   - Type `help` for a full list of commands

## Dependencies

### Required Libraries

- **websockets** (v15.0+): WebSocket library for Python providing both client and server functionality
  - Installation: `pip install websockets`
  - Documentation: https://websockets.readthedocs.io/

### Python Standard Library Modules

- `asyncio`: Asynchronous I/O framework for handling concurrent connections
- `json`: JSON message serialization/deserialization
- `random`: Random room ID generation
- `string`: String utilities for room ID generation
- `sys`: System-specific parameters and functions

### Installation

```bash
pip install websockets
```

Or create a `requirements.txt` file:

```
websockets>=15.0
```

Then install:

```bash
pip install -r requirements.txt
```

## Protocol Specification

The client and server communicate using JSON messages over WebSocket connections. All messages are JSON objects with a `type` field indicating the message type.

### Client-to-Server Messages (C2S)

#### Lobby Operations

**List Rooms**

```json
{
  "type": "list_rooms"
}
```

**Create Room**

```json
{
  "type": "create_room",
  "name": "My Room",
  "user_id": "player123",
  "user_name": "Alice"
}
```

**Join Room**

```json
{
  "type": "join_room",
  "room_id": "abc123",
  "user_id": "player456",
  "user_name": "Bob"
}
```

**Spectate Room**

```json
{
  "type": "spectate_room",
  "room_id": "abc123",
  "user_id": "spectator1",
  "user_name": "Charlie"
}
```

**Reconnect**

```json
{
  "type": "reconnect",
  "user_id": "player123",
  "room_id": "abc123",
  "token": "reconnection_token_here"
}
```

Note: `room_id` and `token` are optional. The server will find the room by `user_id` if `room_id` is not provided.

#### Game Operations

**Place Stone (Move)**

```json
{
  "type": "move",
  "move": {
    "r": 7,
    "c": 7
  }
}
```

**Player Chat**

```json
{
  "type": "chat",
  "message": "Hello, everyone!"
}
```

**Spectator Chat (Spectators Only)**

```json
{
  "type": "spectator_chat",
  "message": "Great move!"
}
```

**Leave Room**

```json
{
  "type": "leave_room"
}
```

### Server-to-Client Messages (S2C)

#### Room Information

**Room List**

```json
{
  "type": "room_list",
  "rooms": [
    {
      "room_id": "abc123",
      "name": "My Room",
      "player_count": 1,
      "spectator_count": 0,
      "player_names": ["Alice"],
      "game_state": "WAITING"
    }
  ]
}
```

**Room Update**

```json
{
  "type": "room_update",
  "room": {
    "room_id": "abc123",
    "name": "My Room",
    "player_count": 2,
    "spectator_count": 1,
    "player_names": ["Alice", "Bob"],
    "game_state": "IN_PROGRESS"
  }
}
```

**Room Removed**

```json
{
  "type": "room_removed",
  "room_id": "abc123"
}
```

#### Game State

**Join Success**

```json
{
  "type": "join_success",
  "room_id": "abc123",
  "token": "reconnection_token_here",
  "your_stone": 1
}
```

Note: `your_stone` is 1 for Black (first player) or 2 for White (second player).

**Spectate Success**

```json
{
  "type": "spectate_success",
  "room_id": "abc123"
}
```

**Reconnect Success**

```json
{
  "type": "reconnect_success",
  "room_id": "abc123",
  "your_stone": 1
}
```

**Game State**

```json
{
  "type": "game_state",
  "board": [[0, 0, ...], [0, 0, ...], ...],
  "current_turn": "player123",
  "game_state": "IN_PROGRESS",
  "players": {
    "player123": "Alice",
    "player456": "Bob"
  },
  "win_line": []
}
```

Note: Board is a 15x15 matrix where 0 = empty, 1 = Black, 2 = White.

**Move**

```json
{
  "type": "move",
  "player_id": "player123",
  "r": 7,
  "c": 7,
  "stone": 1
}
```

**Turn Change**

```json
{
  "type": "turn_change",
  "current_turn": "player456"
}
```

**Timer Notification**

```json
{
  "type": "timer_notification",
  "player": "player123",
  "time_left": 10,
  "player_name": "Alice"
}
```

Note: Sent once when 10 seconds remain for the current player's turn.

**Game Over**

```json
{
  "type": "game_over",
  "winner_name": "Alice",
  "winner_id": "player123",
  "line": [(7, 7), (7, 8), (7, 9), (7, 10), (7, 11)]
}
```

#### Chat Messages

**Player Chat**

```json
{
  "type": "chat",
  "sender": "Alice",
  "message": "Hello, everyone!"
}
```

**Spectator Chat**

```json
{
  "type": "spectator_chat",
  "sender": "Charlie",
  "message": "Great move!"
}
```

#### Error Messages

**Error**

```json
{
  "type": "error",
  "message": "Room not found."
}
```

## Features

### Core Features

1. **Game Lobby System**

   - Create game rooms with custom names
   - List all available rooms with their status
   - Join rooms as a player (maximum 2 players per room)
   - Spectate ongoing games in real-time
   - Automatic room cleanup when empty

2. **15x15 Gomoku Board**

   - Standard 15x15 game board
   - Turn-based gameplay
   - Real-time board state synchronization
   - Visual board display with Black (B) and White (W) stones

3. **Win Detection**

   - Automatic detection of five-in-a-row (horizontal, vertical, diagonal)
   - Win line highlighting
   - Game state management (WAITING, IN_PROGRESS, FINISHED)

4. **Real-Time Communication**

   - Player chat: All players and spectators can see
   - Spectator-only chat: Only visible to spectators
   - System messages for game events
   - Real-time game state updates

5. **Server Architecture**

   - Asynchronous WebSocket server using `asyncio` and `websockets`
   - Non-blocking concurrent connection handling
   - Separate connection handler for each client
   - Efficient message broadcasting

6. **Game Flow Management**
   - Automatic game start when 2 players join
   - Turn-based move validation
   - Automatic return to lobby after game ends
   - Room state synchronization

## Advanced Features

The following advanced features have been implemented for extra credit:

### 1. Spectator-Only Chat Mode (5%)

**Description:** Spectators have a separate chat channel that is not visible to players. This allows spectators to communicate among themselves without interfering with the players' game experience.

**Implementation:**

- Spectators can use the `schat <message>` command to send messages only to other spectators
- Players cannot see spectator-only chat messages
- Spectators can still use the `chat <message>` command to participate in the general chat visible to all

**How to Test:**

1. Start a game with two players
2. Join as a spectator using `spectate <room_id>`
3. Use `schat Hello spectators!` - only other spectators will see this
4. Use `chat Hello everyone!` - all players and spectators will see this

### 2. Move Timer / Time Limits per Player (5%)

**Description:** Each player has 30 seconds to make a move. If a player fails to move within the time limit, their turn is automatically skipped.

**Implementation:**

- Server-side timer management using `asyncio` tasks
- Timer starts when a player's turn begins
- Push notification sent when 10 seconds remain
- Automatic turn skip if time expires
- Timer cancellation when a move is made

**How to Test:**

1. Start a game and wait for your turn
2. Wait without making a move
3. You will receive a notification when 10 seconds remain
4. If you don't move within 30 seconds, your turn will be skipped automatically

**Configuration:**

- Timer duration: 30 seconds (defined as `MOVE_TIMER_DURATION` in `server.py`)
- Notification threshold: 10 seconds remaining

### 3. Reconnection Support for Disconnected Players (10%)

**Description:** If a player disconnects during a game, they have 30 seconds to reconnect using their User ID. The server will restore their game session and allow them to continue playing.

**Implementation:**

- User ID-based reconnection (token optional)
- Automatic room discovery by User ID
- 30-second reconnection window
- Game state restoration upon reconnection
- Automatic game termination if reconnection fails

**How to Test:**

1. Start a game as a player
2. Disconnect the client (Ctrl+C or close terminal)
3. Restart the client with the same User ID
4. The client will automatically attempt to reconnect
5. Alternatively, use the `reconnect` command in the lobby
6. Your game state will be restored and you can continue playing

**Reconnection Process:**

- Player disconnects → Server starts 30-second timer
- Player reconnects with same User ID → Server validates and restores session
- Game state (board, turn, etc.) is sent to reconnected player
- If 30 seconds pass without reconnection → Game ends, other player wins

**Configuration:**

- Reconnection timeout: 30 seconds (defined as `RECONNECTION_TIME` in `server.py`)

## Testing

### Local Testing

To test the multiplayer functionality on a single machine:

1. Start the server in one terminal
2. Open multiple terminal windows
3. Run `python client.py` in each terminal
4. Use different User IDs and Display Names for each client
5. Create a room, join as players, and spectate to test all features

### Testing Scenarios

- **Basic Gameplay:** Create room, join with 2 players, play until win
- **Spectator Mode:** Join as spectator, watch game, use spectator chat
- **Reconnection:** Disconnect during game, reconnect with same User ID
- **Timer:** Wait without moving to test automatic turn skip
- **Chat:** Test both player chat and spectator-only chat

## Project Structure

```
hw3/
├── server.py          # WebSocket server implementation
├── client.py          # WebSocket client implementation
└── README.md          # This file
```

## License

This project is created for educational purposes as part of a network programming course.
