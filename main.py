import typing
from collections import deque

# === NEU: Bewegungsdeltas ===
delta = {
    "up":    (0, 1),
    "down":  (0, -1),
    "left":  (-1, 0),
    "right": (1, 0)
}
#funktionenH
def compute_voronoi(board, you_head, enemy_head):

    width, height = board['width'], board['height']
    snakes = board['snakes']

    visited = {}
    q = deque()

    q.append((you_head['x'], you_head['y'], 'you'))
    q.append((enemy_head['x'], enemy_head['y'], 'enemy'))

    you_score = 0
    enemy_score = 0
    neutral_score = 0

    while q:
        x, y, owner = q.popleft()

        if (x, y) in visited:
            if visited[(x, y)] != owner and visited[(x, y)] != 'neutral':
                visited[(x, y)] = 'neutral'
                neutral_score += 1
                if visited[(x, y)] == 'you':
                    you_score -= 1
                else:
                    enemy_score -= 1
            continue

        visited[(x, y)] = owner

        if owner == 'you':
            you_score += 1
        elif owner == 'enemy':
            enemy_score += 1

        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height and
                not is_occupied(nx, ny, snakes) and (nx, ny) not in visited):
                q.append((nx, ny, owner))

    return you_score, enemy_score, neutral_score

# === NEU: Agent-Klasse ===
class VoronoiAgent:
    def __init__(self, game_state):
        self.board = game_state['board']
        self.you = game_state['you']
        self.enemy = [s for s in self.board['snakes'] if s['id'] != self.you['id']][0]
        self.my_head = self.you['body'][0]
        self.my_tail = self.you['body'][-1]
        self.my_health = self.you['health']
        self.my_length = self.you['length']
        self.board_width = self.board['width']
        self.board_height = self.board['height']

    def choose_move(self):
        mode = "neutral"
        if self.my_health < 40 or self.my_length <= len(self.enemy['body']):
            mode = "food_hunter"
        elif self.my_length >= len(self.enemy['body']) + 2 and self.my_health >= 50:
            you_area, enemy_area, _ = compute_voronoi(self.board, self.my_head, self.enemy['body'][0])
            if you_area >= enemy_area:
                mode = "aggressive"


        safe_moves = []
        for m, (dx, dy) in delta.items():
            new_x = self.my_head['x'] + dx
            new_y = self.my_head['y'] + dy

            if not (0 <= new_x < self.board_width and 0 <= new_y < self.board_height):
                continue

            ate_food = any(f['x'] == new_x and f['y'] == new_y for f in self.board['food'])
            ignore_tail = self.you if not ate_food else None
            if is_occupied(new_x, new_y, self.board['snakes'], ignore_tail=ignore_tail):
                continue

            is_risky_head_on = False
            for other in self.board['snakes']:
                if other['id'] == self.you['id']:
                    continue
                enemy_head = other['body'][0]
                if abs(enemy_head['x'] - new_x) + abs(enemy_head['y'] - new_y) == 1:
                    if self.my_length <= len(other['body']):
                        is_risky_head_on = True
                        break
            if is_risky_head_on:
                continue

            new_head = {'x': new_x, 'y': new_y}
            if len(safe_moves) > 0:
                if detect_dead_end(new_head, self.board, self.board['snakes']) and not is_tail_reachable(new_head, self.my_tail, self.board, self.board['snakes']):
                    continue


            safe_moves.append(m)

        if not safe_moves:
            return "up"
        if len(safe_moves) == 1:
            return safe_moves[0]



        best_score = -9999
        best_move = safe_moves[0]

        for move in safe_moves:
            dx, dy = delta[move]
            new_head = {'x': self.my_head['x'] + dx, 'y': self.my_head['y'] + dy}
            flood_score, quality = flood_fill(new_head, self.board, limit=50)
            score = 0

            if mode == "food_hunter":
                dist = closest_food_distance(new_head, self.board['food'])
                if dist is not None:
                    score += (50 - dist) * 2
                score += flood_score + quality

            elif mode == "aggressive":
                enemy_score, _ = flood_fill(self.enemy['body'][0], self.board, limit=50)
                score += flood_score * 2 - enemy_score * 3 + quality
                you_area, enemy_area, _ = compute_voronoi(self.board, new_head, self.enemy['body'][0])
                score += (you_area - enemy_area)

            else:
                score += flood_score + quality
                you_area, enemy_area, _ = compute_voronoi(self.board, new_head, self.enemy['body'][0])
                score += (you_area - enemy_area)


            if score > best_score:
                best_score = score
                best_move = move
        return best_move

# === ERSETZT move() durch Agentennutzung ===
def move(game_state: typing.Dict) -> typing.Dict:
    agent = VoronoiAgent(game_state)
    return {"move": agent.choose_move()}


# === Bestehende Helferfunktionen bleiben gleich ===
def detect_dead_end(start, board, snakes, depth_limit=10):
    visited = set()
    queue = deque()
    queue.append((start['x'], start['y'], 0))
    visited.add((start['x'], start['y']))

    board_width, board_height = board['width'], board['height']
    occupied = {(seg['x'], seg['y']) for s in snakes for seg in s['body']}

    reachable_tiles = 0
    for_count = 0
    while queue and for_count < 100:
        x, y, depth = queue.popleft()
        for_count += 1
        if depth >= depth_limit:
            continue
        reachable_tiles += 1
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < board_width and 0 <= ny < board_height and 
                (nx, ny) not in visited and (nx, ny) not in occupied):
                visited.add((nx, ny))
                queue.append((nx, ny, depth + 1))

    return reachable_tiles < depth_limit // 2

def is_tail_reachable(start, tail, board, snakes):
    visited = set()
    queue = deque()
    queue.append((start['x'], start['y']))
    visited.add((start['x'], start['y']))

    board_w, board_h = board['width'], board['height']
    occupied = {(seg['x'], seg['y']) for s in snakes for seg in s['body']}
    occupied.remove((tail['x'], tail['y']))

    while queue:
        x, y = queue.popleft()
        if (x, y) == (tail['x'], tail['y']):
            return True
        for dx, dy in delta.values():
            nx, ny = x + dx, y + dy
            if (0 <= nx < board_w and 0 <= ny < board_h and
                (nx, ny) not in visited and (nx, ny) not in occupied):
                visited.add((nx, ny))
                queue.append((nx, ny))
    return False

def is_occupied(x, y, snakes, ignore_tail=None):
    for s in snakes:
        for i, b in enumerate(s['body']):
            if s == ignore_tail and i == len(s['body']) - 1:
                continue
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
            if 0 <= nx < board_w and 0 <= ny < board_h:
                if (nx, ny) not in visited and not is_occupied(nx, ny, snakes):
                    visited.add((nx, ny))
                    q.append((nx, ny))
                    free_neighbors += 1

        quality += free_neighbors

    return count, quality

def closest_food_distance(pos, food_list):
    if not food_list:
        return None
    return min(abs(pos['x'] - f['x']) + abs(pos['y'] - f['y']) for f in food_list)



def info() -> typing.Dict:
    return {
        "apiversion": "1",
        "author": "flood-fighter",
        "color": "#69420",
        "head": "tiger-king",
        "tail": "bolt"
    }

def start(game_state: typing.Dict):
    print("Game started")

def end(game_state: typing.Dict):
    print("Game over")

if __name__ == "__main__":
    from server import run_server
    run_server({"info": info, "start": start, "move": move, "end": end})
