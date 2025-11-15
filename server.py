import asyncio
import json
import websockets
import random
import string

GAME_ROOMS = {}
RECONNECTION_TIME = 30
MOVE_TIMER_DURATION = 30

class GameRoom:
    def __init__(self, room_id, name):
        self.room_id = room_id
        self.name = name
        self.players = {}
        self.spectators = {}
        self.board = [[0 for _ in range(15)] for _ in range(15)]
        self.current_turn_uid = None
        self.game_state = 'WAITING'
        self.win_line = []
        self.timer_task = None
        self.player_tokens = {}
        self.reconnection_timers = {}

    def get_room_info(self):
        player_names = [p['name'] for p in self.players.values()]
        return {
            'room_id': self.room_id,
            'name': self.name,
            'player_count': len(self.players),
            'spectator_count': len(self.spectators),
            'player_names': player_names,
            'game_state': self.game_state
        }

    def get_full_game_state(self):
        return {
            'type': 'game_state',
            'board': self.board,
            'current_turn': self.current_turn_uid,
            'game_state': self.game_state,
            'players': {uid: p['name'] for uid, p in self.players.items()},
            'win_line': self.win_line
        }

    async def broadcast_room_info(self):
        info = self.get_room_info()
        lobby_clients = [c for c in ALL_CLIENTS.values() if c['room_id'] is None]
        await broadcast_message(lobby_clients, {'type': 'room_update', 'room': info})

    async def broadcast(self, message, include_spectators=True, exclude_ws=None):
        clients = []
        for p in self.players.values():
            if p['ws'] and p['ws'] != exclude_ws:
                clients.append(p['ws'])
        
        if include_spectators:
            for ws in self.spectators.keys():
                if ws != exclude_ws:
                    clients.append(ws)

        tasks = [send_message(client, message) for client in clients]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_to_spectators(self, message, exclude_ws=None):
        clients = []
        for ws in self.spectators.keys():
            if ws != exclude_ws:
                clients.append(ws)
        tasks = [send_message(client, message) for client in clients]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def add_player(self, ws, user_id, user_name):
        if len(self.players) >= 2:
            await ws.send(json.dumps({'type': 'error', 'message': 'This room is full.'}))
            return

        token = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        self.player_tokens[user_id] = token
        
        self.players[user_id] = {'ws': ws, 'name': user_name, 'id': user_id, 'stone': 0}
        
        if len(self.players) == 1:
            self.players[user_id]['stone'] = 1
        else:
            self.players[user_id]['stone'] = 2
        
        await ws.send(json.dumps({'type': 'join_success', 'room_id': self.room_id, 'token': token, 'your_stone': self.players[user_id]['stone']}))
        await self.broadcast_room_info()
        
        if len(self.players) == 2:
            await self.start_game()

    async def add_spectator(self, ws, user_id=None, user_name=None):
        self.spectators[ws] = {
            'user_id': user_id or f'spec_{id(ws) % 10000}',
            'user_name': user_name or f'Spectator-{id(ws) % 1000}'
        }
        await ws.send(json.dumps({'type': 'spectate_success', 'room_id': self.room_id}))
        await ws.send(json.dumps(self.get_full_game_state()))
        await self.broadcast_room_info()

    async def handle_reconnection(self, ws, user_id, token=None):
        if user_id not in self.players:
            await ws.send(json.dumps({'type': 'error', 'message': 'Invalid user ID for this room.'}))
            return
        
        if token:
            if user_id not in self.player_tokens or self.player_tokens[user_id] != token:
                await ws.send(json.dumps({'type': 'error', 'message': 'Invalid reconnection token.'}))
                return
        else:
            if self.game_state != 'IN_PROGRESS' or self.players[user_id]['ws'] is not None:
                if user_id not in self.reconnection_timers:
                    await ws.send(json.dumps({'type': 'error', 'message': 'No active reconnection session found. Please provide token.'}))
                    return

        if user_id in self.reconnection_timers:
            self.reconnection_timers[user_id].cancel()
            del self.reconnection_timers[user_id]
            
        self.players[user_id]['ws'] = ws
        ALL_CLIENTS[ws] = {'room_id': self.room_id, 'user_id': user_id}
        
        await ws.send(json.dumps({'type': 'reconnect_success', 'room_id': self.room_id, 'your_stone': self.players[user_id]['stone']}))
        await ws.send(json.dumps(self.get_full_game_state()))
        
        player_name = self.players[user_id]['name']
        await self.broadcast({'type': 'chat', 'sender': 'System', 'message': f'Player {player_name} has reconnected.'}, exclude_ws=ws)
        print(f"Player {user_id} reconnected to room {self.room_id}")

    async def start_game(self):
        self.game_state = 'IN_PROGRESS'
        player_uids = list(self.players.keys())
        self.current_turn_uid = player_uids[0]
        
        message = self.get_full_game_state()
        await self.broadcast(message)
        await self.broadcast_room_info()
        await self.start_move_timer()
        print(f"Game started in room {self.room_id}")

    async def start_move_timer(self):
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
            
        self.timer_task = asyncio.create_task(self.move_timer_logic())

    async def move_timer_logic(self):
        try:
            if self.current_turn_uid not in self.players:
                return
            current_player_name = self.players[self.current_turn_uid]['name']
            for i in range(MOVE_TIMER_DURATION, -1, -1):
                if self.game_state != 'IN_PROGRESS' or self.current_turn_uid not in self.players:
                    return
                if i == 10:
                    await self.broadcast({'type': 'timer_notification', 'player': self.current_turn_uid, 'time_left': i, 'player_name': current_player_name})
                await asyncio.sleep(1)
            
            if self.game_state == 'IN_PROGRESS' and self.current_turn_uid in self.players:
                await self.broadcast({'type': 'chat', 'sender': 'System', 'message': f"Player {current_player_name} ran out of time. Turn skipped."})
                await self.next_turn()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Timer error: {e}")

    def check_win(self, r, c, stone):
        directions = [(0, 1), (1, 0), (1, 1), (1, -1)]
        for dr, dc in directions:
            count = 1
            line = [(r, c)]
            
            for i in range(1, 5):
                nr, nc = r + dr * i, c + dc * i
                if 0 <= nr < 15 and 0 <= nc < 15 and self.board[nr][nc] == stone:
                    count += 1
                    line.append((nr, nc))
                else:
                    break
                    
            for i in range(1, 5):
                nr, nc = r - dr * i, c - dc * i
                if 0 <= nr < 15 and 0 <= nc < 15 and self.board[nr][nc] == stone:
                    count += 1
                    line.append((nr, nc))
                else:
                    break
            
            if count >= 5:
                return line
        return None

    async def handle_move(self, user_id, move):
        if user_id != self.current_turn_uid:
            return
        
        if self.game_state != 'IN_PROGRESS':
            return
            
        try:
            r, c = int(move['r']), int(move['c'])
            if not (0 <= r < 15 and 0 <= c < 15 and self.board[r][c] == 0):
                return
        except:
            return

        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass

        stone = self.players[user_id]['stone']
        self.board[r][c] = stone
        
        win_line = self.check_win(r, c, stone)
        
        if win_line:
            self.game_state = 'FINISHED'
            self.win_line = win_line
            
            winner_name = self.players[user_id]['name']
            message = self.get_full_game_state()
            await self.broadcast(message)
            await self.broadcast({'type': 'game_over', 'winner_name': winner_name, 'winner_id': user_id, 'line': win_line})
            await self.broadcast_room_info()
            print(f"Game ended in room {self.room_id}. Winner: {winner_name}")
        else:
            await self.broadcast({'type': 'move', 'player_id': user_id, 'r': r, 'c': c, 'stone': stone})
            await self.next_turn()

    async def next_turn(self):
        player_uids = list(self.players.keys())
        if self.current_turn_uid == player_uids[0]:
            self.current_turn_uid = player_uids[1]
        else:
            self.current_turn_uid = player_uids[0]
            
        await self.broadcast({'type': 'turn_change', 'current_turn': self.current_turn_uid})
        await self.start_move_timer()

    async def handle_chat(self, user_id, message):
        sender_name = self.players[user_id]['name']
        chat_msg = {'type': 'chat', 'sender': sender_name, 'message': message}
        await self.broadcast(chat_msg)
        
    async def handle_spectator_chat(self, ws, message):
        if ws not in self.spectators:
            await send_message(ws, {'type': 'error', 'message': 'Only spectators can use spectator chat.'})
            return
        
        sender_name = self.spectators[ws]['user_name']
        chat_msg = {'type': 'spectator_chat', 'sender': sender_name, 'message': message}
        await self.broadcast_to_spectators(chat_msg, exclude_ws=None)

    async def handle_client_disconnect(self, ws, user_id):
        if user_id in self.players:
            player_name = self.players[user_id]['name']
            self.players[user_id]['ws'] = None
            
            if self.game_state == 'IN_PROGRESS':
                await self.broadcast({'type': 'chat', 'sender': 'System', 'message': f'Player {player_name} has disconnected. They have {RECONNECTION_TIME} seconds to reconnect.'}, exclude_ws=ws)
                
                timer = asyncio.create_task(self.start_reconnection_timer(user_id))
                self.reconnection_timers[user_id] = timer
            else:
                del self.players[user_id]
                del self.player_tokens[user_id]
                await self.broadcast_room_info()

        elif ws in self.spectators:
            del self.spectators[ws]
            await self.broadcast_room_info()
        
        print(f"Client {user_id or id(ws)} disconnected from room {self.room_id}")

    async def start_reconnection_timer(self, user_id):
        try:
            await asyncio.sleep(RECONNECTION_TIME)
            
            if user_id in self.players and self.players[user_id]['ws'] is None:
                player_name = self.players[user_id]['name']
                await self.broadcast({'type': 'chat', 'sender': 'System', 'message': f'Player {player_name} failed to reconnect. Game over.'})
                
                other_player_id = None
                for pid in self.players:
                    if pid != user_id:
                        other_player_id = pid
                        break
                
                if other_player_id:
                    other_player_name = self.players[other_player_id]['name']
                    self.game_state = 'FINISHED'
                    self.win_line = []
                    await self.broadcast({'type': 'game_over', 'winner_name': other_player_name, 'winner_id': other_player_id, 'line': []})
                
                await self.broadcast_room_info()
                
        except asyncio.CancelledError:
            pass
        finally:
            if user_id in self.reconnection_timers:
                del self.reconnection_timers[user_id]
            if user_id in self.players and self.players[user_id]['ws'] is None and self.game_state != 'IN_PROGRESS':
                 del self.players[user_id]
                 if user_id in self.player_tokens:
                    del self.player_tokens[user_id]


ALL_CLIENTS = {}

async def send_message(ws, message):
    try:
        await ws.send(json.dumps(message))
    except websockets.exceptions.ConnectionClosed:
        pass

async def broadcast_message(clients, message):
    tasks = [send_message(c['ws'], message) for c in clients if c.get('ws')]
    if tasks:
        await asyncio.wait(tasks)

async def send_room_list(ws):
    room_list = [room.get_room_info() for room in GAME_ROOMS.values()]
    await send_message(ws, {'type': 'room_list', 'rooms': room_list})

def find_room_by_user_id(user_id):
    for room_id, room in GAME_ROOMS.items():
        if user_id in room.players:
            if room.game_state == 'IN_PROGRESS' and (room.players[user_id]['ws'] is None or user_id in room.reconnection_timers):
                return room_id, room
            elif user_id in room.player_tokens:
                return room_id, room
    return None, None

async def handle_connection(websocket):
    ALL_CLIENTS[websocket] = {'room_id': None, 'user_id': None}
    print(f"New client connected: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                msg_type = data.get('type')
                
                client_info = ALL_CLIENTS[websocket]
                room_id = client_info.get('room_id')
                user_id = client_info.get('user_id')
                
                if room_id and room_id in GAME_ROOMS:
                    room = GAME_ROOMS[room_id]
                    
                    if msg_type == 'move':
                        await room.handle_move(user_id, data.get('move'))
                    elif msg_type == 'chat':
                        await room.handle_chat(user_id, data.get('message'))
                    elif msg_type == 'spectator_chat':
                        await room.handle_spectator_chat(websocket, data.get('message'))
                    elif msg_type == 'leave_room':
                        await room.handle_client_disconnect(websocket, user_id)
                        client_info['room_id'] = None
                        client_info['user_id'] = None

                else:
                    if msg_type == 'list_rooms':
                        await send_room_list(websocket)
                    
                    elif msg_type == 'create_room':
                        room_name = data.get('name', 'New Room')
                        user_id = data.get('user_id', 'Player')
                        user_name = data.get('user_name', 'Player')
                        
                        room_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
                        GAME_ROOMS[room_id] = GameRoom(room_id, room_name)
                        
                        client_info['room_id'] = room_id
                        client_info['user_id'] = user_id
                        await GAME_ROOMS[room_id].add_player(websocket, user_id, user_name)

                    elif msg_type == 'join_room':
                        room_id = data.get('room_id')
                        user_id = data.get('user_id', 'Player')
                        user_name = data.get('user_name', 'Player')
                        
                        if room_id in GAME_ROOMS:
                            client_info['room_id'] = room_id
                            client_info['user_id'] = user_id
                            await GAME_ROOMS[room_id].add_player(websocket, user_id, user_name)
                        else:
                            await send_message(websocket, {'type': 'error', 'message': 'Room not found.'})

                    elif msg_type == 'spectate_room':
                        room_id = data.get('room_id')
                        user_id = data.get('user_id')
                        user_name = data.get('user_name')
                        if room_id in GAME_ROOMS:
                            client_info['room_id'] = room_id
                            client_info['user_id'] = user_id
                            await GAME_ROOMS[room_id].add_spectator(websocket, user_id, user_name)
                        else:
                            await send_message(websocket, {'type': 'error', 'message': 'Room not found.'})

                    elif msg_type == 'reconnect':
                        user_id = data.get('user_id')
                        token = data.get('token')
                        room_id = data.get('room_id')
                        
                        if not user_id:
                            await send_message(websocket, {'type': 'error', 'message': 'User ID is required for reconnection.'})
                            continue
                        
                        if room_id and room_id in GAME_ROOMS:
                            target_room = GAME_ROOMS[room_id]
                        else:
                            found_room_id, target_room = find_room_by_user_id(user_id)
                            if target_room:
                                room_id = found_room_id
                            else:
                                await send_message(websocket, {'type': 'error', 'message': f'No active game session found for user ID: {user_id}'})
                                continue
                        
                        client_info['room_id'] = room_id
                        client_info['user_id'] = user_id
                        
                        await target_room.handle_reconnection(websocket, user_id, token)

            except json.JSONDecodeError:
                print(f"Invalid JSON from {websocket.remote_address}")
            except Exception as e:
                print(f"Error processing message: {e}")

    except websockets.exceptions.ConnectionClosed as e:
        print(f"Client disconnected: {websocket.remote_address} (Code: {e.code}, Reason: {e.reason})")
    except Exception as e:
        print(f"An unexpected error occurred with {websocket.remote_address}: {e}")
    finally:
        client_info = ALL_CLIENTS.get(websocket)
        if client_info:
            room_id = client_info.get('room_id')
            user_id = client_info.get('user_id')
            if room_id and room_id in GAME_ROOMS:
                await GAME_ROOMS[room_id].handle_client_disconnect(websocket, user_id)
                if not GAME_ROOMS[room_id].players and not GAME_ROOMS[room_id].spectators:
                    del GAME_ROOMS[room_id]
                    print(f"Room {room_id} is empty and has been deleted.")
                    await broadcast_message(ALL_CLIENTS.values(), {'type': 'room_removed', 'room_id': room_id})

        if websocket in ALL_CLIENTS:
            del ALL_CLIENTS[websocket]

async def main():
    print("Starting Gomoku server on ws://localhost:8765")
    async with websockets.serve(handle_connection, "localhost", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())