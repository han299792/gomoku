import asyncio
import json
import websockets
import sys

STATE = {
    'room_id': None,
    'user_id': None,
    'user_name': None,
    'token': None,
    'is_player': False,
    'is_spectator': False,
    'my_stone': 0,
    'board': [],
    'current_turn': None,
    'game_state': 'LOBBY'
}

def print_board(board):
    if not board:
        return
        
    print("\n   " + " ".join([f"{i:2}" for i in range(15)]))
    print("  +" + "--"*15 + "-")
    for r_idx, row in enumerate(board):
        print(f"{r_idx:2}|", end=" ")
        for cell in row:
            if cell == 1:
                char = 'B'
            elif cell == 2:
                char = 'W'
            else:
                char = '.'
            print(f"{char} ", end="")
        print()
    print()

def display_prompt():
    if STATE['game_state'] == 'LOBBY':
        prompt = "[Lobby] > "
    elif STATE['game_state'] == 'WAITING':
        prompt = f"[Room: {STATE['room_id']} - Waiting] > "
    elif STATE['game_state'] == 'IN_PROGRESS':
        if STATE['is_player'] and STATE['current_turn'] == STATE['user_id']:
            prompt = "[Your Turn] > "
        else:
            prompt = f"[Game: {STATE['room_id']}] > "
    elif STATE['game_state'] == 'FINISHED':
        prompt = f"[Game Over: {STATE['room_id']}] > "
    else:
        prompt = "> "
        
    print(f"\n{prompt}", end="")
    sys.stdout.flush()

async def listen_to_server(ws):
    async for message in ws:
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'room_list':
                print("\n[Available Rooms]")
                if not data['rooms']:
                    print("  No rooms available. Type 'create <room_name>' to start.")
                for room in data['rooms']:
                    print(f"  - {room['name']} ({room['room_id']}) [{room['player_count']}/2 Players, {room['spectator_count']} Specs] ({room['game_state']})")
            
            elif msg_type == 'room_update':
                room = data['room']
                print(f"\n[Room Update] {room['name']} ({room['room_id']}) [{room['player_count']}/2 Players, {room['spectator_count']} Specs] ({room['game_state']})")

            elif msg_type == 'room_removed':
                print(f"\n[Room Removed] Room {data['room_id']} has been closed.")

            elif msg_type == 'join_success':
                STATE['room_id'] = data['room_id']
                STATE['token'] = data['token']
                STATE['is_player'] = True
                STATE['is_spectator'] = False
                STATE['my_stone'] = data['your_stone']
                STATE['game_state'] = 'WAITING'
                stone_name = 'Black (B)' if STATE['my_stone'] == 1 else 'White (W)'
                print(f"\nJoined room {data['room_id']}. You are {stone_name}.")
                print("Waiting for another player...")
            
            elif msg_type == 'spectate_success':
                STATE['room_id'] = data['room_id']
                STATE['is_player'] = False
                STATE['is_spectator'] = True
                STATE['game_state'] = 'SPECTATING'
                print(f"\nSpectating room {data['room_id']}.")

            elif msg_type == 'reconnect_success':
                STATE['room_id'] = data['room_id']
                STATE['is_player'] = True
                STATE['is_spectator'] = False
                STATE['my_stone'] = data['your_stone']
                print(f"\nReconnected successfully to room {data['room_id']}.")

            elif msg_type == 'game_state':
                STATE['board'] = data['board']
                STATE['current_turn'] = data['current_turn']
                STATE['game_state'] = data['game_state']
                print("\n--- Game State Update ---")
                player_names = " vs ".join(data['players'].values())
                print(f"Players: {player_names}")
                print_board(STATE['board'])
                if data['game_state'] == 'IN_PROGRESS':
                    turn_player_name = data['players'].get(data['current_turn'], 'Unknown')
                    print(f"Current Turn: {turn_player_name}")

            elif msg_type == 'move':
                r, c, stone = data['r'], data['c'], data['stone']
                STATE['board'][r][c] = stone
                stone_char = 'B' if stone == 1 else 'W'
                print(f"\n[Move] Player ({stone_char}) placed at ({r}, {c})")
                print_board(STATE['board'])
            
            elif msg_type == 'turn_change':
                STATE['current_turn'] = data['current_turn']
                if STATE['is_player'] and STATE['current_turn'] == STATE['user_id']:
                    print("\n*** It's YOUR turn! ***")
                else:
                    print(f"\nTurn changed. Waiting for other player...")
            
            elif msg_type == 'timer_update':
                if STATE['game_state'] == 'IN_PROGRESS':
                    if STATE['is_player'] and data['player'] == STATE['user_id']:
                        print(f"\r[Your Timer]: {data['time_left']}s   ", end="")
                        sys.stdout.flush()
                    else:
                        print(f"\r[Opponent Timer]: {data['time_left']}s   ", end="")
                        sys.stdout.flush()

            elif msg_type == 'game_over':
                print(f"\n--- GAME OVER ---")
                print(f"Winner: {data['winner_name']}")
                STATE['game_state'] = 'FINISHED'

            elif msg_type == 'chat':
                print(f"\n[Player Chat] {data['sender']}: {data['message']}")
            
            elif msg_type == 'spectator_chat':
                print(f"\n[Spectator Chat] {data['sender']}: {data['message']}")

            elif msg_type == 'error':
                print(f"\n[Server Error] {data['message']}")
                if 'reconnection' in data['message']:
                    STATE['token'] = None

            else:
                print(f"\n[Server] {data}")

        except Exception as e:
            print(f"\nError processing message: {e}")
            print(f"Raw message: {message}")
            
        display_prompt()

async def handle_user_input(ws):
    loop = asyncio.get_event_loop()
    
    while True:
        try:
            message = await loop.run_in_executor(None, sys.stdin.readline)
            message = message.strip().lower()
            
            if not message:
                continue

            parts = message.split(' ')
            cmd = parts[0]
            payload = {}
            
            if cmd == 'help':
                print("\n--- Commands ---")
                print("  help         : Show this message")
                print("  list         : List available rooms")
                print("  create <name>: Create a new room")
                print("  join <id>    : Join a room as a player")
                print("  spectate <id>: Spectate a room")
                print("  move <r> <c> : Place your stone at (row, col)")
                print("  chat <msg>   : Send a message to players/spectators")
                print("  schat <msg>  : (Spectators Only) Send a message to spectators")
                print("  board        : Show the board")
                print("  exit         : Exit the game")
                display_prompt()
                continue
            
            if cmd == 'exit':
                print("Disconnecting...")
                await ws.close()
                break

            if STATE['game_state'] == 'LOBBY':
                if cmd == 'list':
                    payload = {'type': 'list_rooms'}
                elif cmd == 'create' and len(parts) > 1:
                    payload = {'type': 'create_room', 'name': " ".join(parts[1:]), 'user_id': STATE['user_id'], 'user_name': STATE['user_name']}
                elif cmd == 'join' and len(parts) > 1:
                    payload = {'type': 'join_room', 'room_id': parts[1], 'user_id': STATE['user_id'], 'user_name': STATE['user_name']}
                elif cmd == 'spectate' and len(parts) > 1:
                    payload = {'type': 'spectate_room', 'room_id': parts[1]}
                else:
                    print("Invalid lobby command. Type 'help'.")
                    display_prompt()
                    continue

            elif STATE['is_player']:
                if cmd == 'move' and len(parts) == 3:
                    payload = {'type': 'move', 'move': {'r': parts[1], 'c': parts[2]}}
                elif cmd == 'chat':
                    payload = {'type': 'chat', 'message': " ".join(parts[1:])}
                elif cmd == 'board':
                    print_board(STATE['board'])
                    display_prompt()
                    continue
                else:
                    print("Invalid player command. Type 'help'.")
                    display_prompt()
                    continue
            
            elif STATE['is_spectator']:
                if cmd == 'chat':
                    payload = {'type': 'chat', 'message': " ".join(parts[1:])}
                elif cmd == 'schat':
                    payload = {'type': 'spectator_chat', 'message': " ".join(parts[1:])}
                elif cmd == 'board':
                    print_board(STATE['board'])
                    display_prompt()
                    continue
                else:
                    print("Invalid spectator command. Type 'help'.")
                    display_prompt()
                    continue

            if payload:
                await ws.send(json.dumps(payload))
                
        except (KeyboardInterrupt, EOFError):
            print("Disconnecting...")
            await ws.close()
            break
        except Exception as e:
            print(f"Error reading input: {e}")
            await ws.close()
            break

async def attempt_reconnection(uri):
    print(f"Attempting to reconnect as {STATE['user_id']} to room {STATE['room_id']}...")
    try:
        async with websockets.connect(uri) as ws:
            payload = {
                'type': 'reconnect',
                'user_id': STATE['user_id'],
                'room_id': STATE['room_id'],
                'token': STATE['token']
            }
            await ws.send(json.dumps(payload))
            
            response_str = await ws.recv()
            response = json.loads(response_str)
            
            if response.get('type') == 'reconnect_success':
                print("Reconnection successful!")
                return ws
            else:
                print(f"Reconnection failed: {response.get('message')}")
                STATE['token'] = None
                STATE['room_id'] = None
                STATE['is_player'] = False
                STATE['game_state'] = 'LOBBY'
                return None
                
    except Exception as e:
        print(f"Failed to reconnect: {e}")
        return None

async def main():
    uri = "ws://localhost:8765"
    
    while True:
        if STATE['user_id'] is None:
            user_id = input("Enter your User ID (e.g., player123): ").strip()
            user_name = input("Enter your Display Name (e.g., Alice): ").strip()
            if not user_id or not user_name:
                print("ID and Name cannot be empty.")
                continue
            STATE['user_id'] = user_id
            STATE['user_name'] = user_name

        ws_connection = None
        try:
            if STATE['token'] and STATE['room_id']:
                ws_connection = await attempt_reconnection(uri)
                if not ws_connection:
                    print("Could not reconnect, returning to lobby.")

            if not ws_connection:
                STATE['game_state'] = 'LOBBY'
                STATE['is_player'] = False
                STATE['is_spectator'] = False
                STATE['room_id'] = None
                
                print(f"Connecting to {uri} as {STATE['user_name']} ({STATE['user_id']})...")
                ws_connection = await websockets.connect(uri)
                print("Connected! Type 'list' to see rooms or 'help' for commands.")
                display_prompt()

            listen_task = asyncio.create_task(listen_to_server(ws_connection))
            input_task = asyncio.create_task(handle_user_input(ws_connection))
            
            await asyncio.gather(listen_task, input_task)

        except websockets.exceptions.ConnectionClosed as e:
            print(f"\nConnection lost (Code: {e.code}).")
            if STATE['is_player'] and STATE['token'] and STATE['game_state'] == 'IN_PROGRESS':
                print(f"Will attempt to reconnect in 5 seconds...")
                await asyncio.sleep(5)
            else:
                print("Connection closed. Exiting.")
                break
        except (ConnectionRefusedError, asyncio.TimeoutError):
            print("Could not connect to server. Is it running?")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except (KeyboardInterrupt, EOFError):
            print("Exiting client.")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\nClient shut down.")