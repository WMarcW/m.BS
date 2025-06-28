
import random
import typing
import copy
from collections import deque

# === KONSTANTEN ===
delta = {
    "up": (0, 1), "down": (0, -1), "left": (-1, 0), "right": (1, 0)
}

# === ZOBRIST INITIALISIERUNG ===
ZOB_SNAKE = {}
ZOB_FOOD = [[random.getrandbits(64) for _ in range(11)] for _ in range(11)]
current_hash = 0
transposition_table = {}

# === API INFO ===
def info():
    return {
        "apiversion": "1",
        "author": "team-WIN",
        "color": "#97FF3C",
        "head": "gamer",
        "tail": "bolt"
    }

# === SPIELSTART ===
def start(game_state):
    global current_hash
    for snake in game_state['board']['snakes']:
        sid = snake['id']
        if sid not in ZOB_SNAKE:
            ZOB_SNAKE[sid] = [[random.getrandbits(64) for _ in range(11)] for _ in range(11)]
    current_hash = compute_initial_hash(game_state)

# === SPIELENDE ===
def end(game_state):
    print("GAME OVER")

# === HASH INITIALISIERUNG ===
def compute_initial_hash(state):
    h = 0
    for snake in state['board']['snakes']:
        sid = snake['id']
        for seg in snake['body']:
            h ^= ZOB_SNAKE[sid][seg['x']][seg['y']]
    for f in state['board']['food']:
        h ^= ZOB_FOOD[f['x']][f['y']]
    return h

# === ZUGAUSWAHL ===
def move(game_state):
    board = game_state['board']
    you = game_state['you']
    my_head = you['body'][0]
    my_id = you['id']
    my_health = you['health']
    my_length = you['length']
    enemy = next(s for s in board['snakes'] if s['id'] != my_id)
    enemy_length = enemy['length']

    is_safe = {m: is_move_safe(my_head, m, game_state, my_id) for m in delta}
    safe_moves = [m for m, ok in is_safe.items() if ok]
    if not safe_moves:
        return {"move": "down"}  # fallback

    mode = determine_mode(my_length, enemy_length, my_health)

    if mode in ("aggressive", "recovery", "kill_mode"):
        eval_fn = {
            "aggressive": evaluate_aggressive,
            "recovery": evaluate_recovery,
            "kill_mode": evaluate_kill_mode
        }[mode]
        best_val = -float("inf")
        best_move = None
        for m in safe_moves:
            val = evaluate_move_3ply(m, game_state, is_safe, eval_fn, -float("inf"), float("inf"), 3)
            if val > best_val:
                best_val = val
                best_move = m

    else:
        best_move = max(safe_moves, key=lambda m: calculate_free_space(apply_delta(my_head, m), game_state)[0])
    print(f"Head: {my_head}, Chosen Move: {best_move}, Mode: {mode}, Safe: {safe_moves}")
    return {"move": best_move}

# === MOVE-UTILS ===
def apply_delta(pos, direction):
    dx, dy = delta[direction]
    return {"x": pos['x'] + dx, "y": pos['y'] + dy}

def is_move_safe(head, move, game_state, my_id):
    nx, ny = apply_delta(head, move).values()
    board = game_state['board']
    if not (0 <= nx < board['width'] and 0 <= ny < board['height']):
        return False
    for s in board['snakes']:
        for segment in s['body']:
            if segment['x'] == nx and segment['y'] == ny:
                return False
    return True

# === MOVE-SIMULATION ===
def apply_moves(game_state, move_dict):
    global current_hash
    board = game_state['board']
    changes = []
    food_set = {(f['x'], f['y']) for f in board['food']}

    for snake in board['snakes']:
        sid = snake['id']
        move = move_dict[sid]
        new_head = apply_delta(snake['body'][0], move)
        current_hash ^= ZOB_SNAKE[sid][snake['body'][0]['x']][snake['body'][0]['y']]
        current_hash ^= ZOB_SNAKE[sid][new_head['x']][new_head['y']]

        snake['body'].insert(0, new_head)

        if (new_head['x'], new_head['y']) in food_set:
            board['food'] = [f for f in board['food'] if not (f['x'] == new_head['x'] and f['y'] == new_head['y'])]
            current_hash ^= ZOB_FOOD[new_head['x']][new_head['y']]
            changes.append((sid, True, new_head))
        else:
            tail = snake['body'].pop()
            current_hash ^= ZOB_SNAKE[sid][tail['x']][tail['y']]
            changes.append((sid, False, tail))

    return changes

def undo_moves(game_state, changes):
    global current_hash
    for sid, ate, seg in reversed(changes):
        snake = next(s for s in game_state['board']['snakes'] if s['id'] == sid)
        head = snake['body'].pop(0)
        current_hash ^= ZOB_SNAKE[sid][head['x']][head['y']]
        if ate:
            game_state['board']['food'].append(seg)
            current_hash ^= ZOB_FOOD[seg['x']][seg['y']]
        else:
            snake['body'].append(seg)
            current_hash ^= ZOB_SNAKE[sid][seg['x']][seg['y']]

# === EVALUATION ===
def evaluate_move_3ply(start_move, game_state, is_move_safe, evaluation_fn, alpha, beta, depth):
    global current_hash
    key = (current_hash, depth)
    if key in transposition_table:
        return transposition_table[key]['value']

    move_dict = {}
    my_id = game_state['you']['id']
    for s in game_state['board']['snakes']:
        sid = s['id']
        if sid == my_id:
            move_dict[sid] = start_move
        else:
            move_dict[sid] = simulate_enemy_move(game_state, s)

    changes = apply_moves(game_state, move_dict)

    if depth == 0:
        head = next(s for s in game_state['board']['snakes'] if s['id'] == game_state['you']['id'])['body'][0]
        score = evaluation_fn(start_move, head, game_state, is_move_safe)
    else:
        you_snake = next(s for s in game_state['board']['snakes'] if s['id'] == game_state['you']['id'])
        new_head = you_snake['body'][0]
        next_safe_moves = [
            m for m in delta
            if is_move_safe(new_head, m, game_state, you_snake['id'])
    ]
    if not next_safe_moves:
        score = -9999  # Kein sicherer Zug mehr möglich
    else:
        score = max(
            evaluate_move_3ply(m, game_state, is_move_safe, evaluation_fn, alpha, beta, depth - 1)
            for m in next_safe_moves
        )

    undo_moves(game_state, changes)
    transposition_table[key] = {'value': score, 'depth': depth, 'type': 'EXACT'}
    return score

# === ENEMY SIMULATION ===
def simulate_enemy_move(game_state, enemy):
    head = enemy['body'][0]
    board = game_state['board']
    moves = [m for m in delta if is_move_safe(head, m, game_state, enemy['id'])]
    return random.choice(moves) if moves else 'up'

# === STRATEGISCHE MODI ===
def determine_mode(my_len, enemy_len, hp):
    if hp < 25: return "emergency"
    if hp < 40 or my_len <= enemy_len + 1: return "recovery"
    if my_len >= enemy_len + 5: return "kill_mode"
    if my_len >= enemy_len + 2: return "aggressive"
    return "normal"

# === EVALUATIONEN ===
def calculate_free_space(start, game_state, limit=50):
    board = game_state['board']
    visited = set()
    queue = deque([(start['x'], start['y'])])
    visited.add((start['x'], start['y']))
    count = 0

    occupied = {(s['x'], s['y']) for snake in board['snakes'] for s in snake['body']}

    while queue and count < limit:
        x, y = queue.popleft()
        count += 1
        for dx, dy in delta.values():
            nx, ny = x + dx, y + dy
            if 0 <= nx < board['width'] and 0 <= ny < board['height'] and (nx, ny) not in occupied and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))
    return count, len(visited)

def evaluate_aggressive(move, head, game_state, is_safe):
    if not is_safe[move]: return -9999
    new_head = apply_delta(head, move)
    free, quality = calculate_free_space(new_head, game_state)
    return free * 3 + quality * 1.5

def evaluate_recovery(move, head, game_state, is_safe):
    if not is_safe[move]: return -9999
    new_head = apply_delta(head, move)
    food = game_state['board']['food']
    dist = min((abs(new_head['x'] - f['x']) + abs(new_head['y'] - f['y']) for f in food), default=20)
    return 500 - dist * 10

def evaluate_kill_mode(move, head, game_state, is_safe):
    if not is_safe[move]: return -9999
    new_head = apply_delta(head, move)
    free, _ = calculate_free_space(new_head, game_state)
    return free * 5

# === START ===
if __name__ == '__main__':
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
