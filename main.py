import typing
import random
from collections import deque

# === MOVE DELTA ===
delta = {
    "up":    (0, 1),
    "down":  (0, -1),
    "left":  (-1, 0),
    "right": (1, 0)
}

# === MAIN LOGIC ===
def move(game_state: typing.Dict) -> typing.Dict:
    board = game_state['board']
    you = game_state['you']

    my_head = you['body'][0]
    my_health = you['health']
    my_length = you['length']
    board_width = board['width']
    board_height = board['height']
    enemy = [s for s in board['snakes'] if s['id'] != you['id']][0]

    # === Determine Mode ===
    mode = "neutral"
    if my_health < 40 or my_length <= enemy['length']:
        mode = "food_hunter"
    elif my_length >= enemy['length'] + 2:
        mode = "aggressive"

    # === Determine Safe Moves ===
    safe_moves = []
    for m, (dx, dy) in delta.items():
        new_x = my_head['x'] + dx
        new_y = my_head['y'] + dy
        if not (0 <= new_x < board_width and 0 <= new_y < board_height):
            continue
        if is_occupied(new_x, new_y, board['snakes']):
            continue
        safe_moves.append(m)

    if not safe_moves:
        return {"move": "up"}  # fallback

    # === Score each move ===
    best_score = -9999
    best_move = safe_moves[0]

    for move in safe_moves:
        dx, dy = delta[move]
        new_head = {'x': my_head['x'] + dx, 'y': my_head['y'] + dy}
        flood_score, quality = flood_fill(new_head, board, limit=50)
        score = 0

        if mode == "food_hunter":
            dist = closest_food_distance(new_head, board['food'])
            score += (50 - dist) * 2 if dist is not None else 0
            score += flood_score + quality
        elif mode == "aggressive":
            enemy_score, _ = flood_fill(enemy['body'][0], board, limit=50)
            score += flood_score * 2 - enemy_score * 3 + quality
        else:  # neutral
            score += flood_score + quality

        if score > best_score:
            best_score = score
            best_move = move

    return {"move": best_move}


# === HELPERS ===
def is_occupied(x, y, snakes):
    for s in snakes:
        for b in s['body']:
            if b['x'] == x and b['y'] == y:
                return True
    return False

def flood_fill(start: dict, board: dict, limit: int = 50):
    visited = set()
    q = deque()
    q.append((start['x'], start['y']))
    visited.add((start['x'], start['y']))

    board_w, board_h = board['width'], board['height']
    snakes = board['snakes']
    count = 0
    quality = 0

    while q and count < limit:
        x, y = q.popleft()
        count += 1
        free_neighbors = 0

        for dx, dy in delta.values():
            nx, ny = x + dx, y + dy
            if 0 <= nx < board_w and 0 <= ny < board_h and (nx, ny) not in visited and not is_occupied(nx, ny, snakes):
                visited.add((nx, ny))
                q.append((nx, ny))
                free_neighbors += 1

        quality += free_neighbors

    return count, quality

def closest_food_distance(pos, food_list):
    if not food_list:
        return None
    return min(abs(pos['x'] - f['x']) + abs(pos['y'] - f['y']) for f in food_list)


# === SERVER ENTRY ===
def info() -> typing.Dict:
    return {
        "apiversion": "1",
        "author": "flood-fighter",
        "color": "#11cc99",
        "head": "beluga",
        "tail": "bolt"
    }

def start(game_state: typing.Dict):
    print("Game started")

def end(game_state: typing.Dict):
    print("Game over")

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
