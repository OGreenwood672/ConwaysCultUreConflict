
# --- CONFIGURATION ---
WIDTH, HEIGHT = 800, 600
FPS = 60

# Colors (R, G, B)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

# Game Settings
PLAYER_ACCEL = 0.15
PLAYER_FRICTION = 0.99
PLAYER_ROTATION_SPEED = 4
BULLET_SPEED = 10
BULLET_LIFETIME = 60  # Frames
ASTEROID_SPEED = 2

def wrap_position(x, y):
    """Wraps coordinates around the screen edges."""
    if x > WIDTH: x = 0
    elif x < 0: x = WIDTH
    if y > HEIGHT: y = 0
    elif y < 0: y = HEIGHT
    return x, y

def rotate_point(point, angle, origin):
    """Rotates a point around an origin. Angle is in degrees."""
    ox, oy = origin
    px, py = point
    rad = math.radians(angle)
    qx = ox + math.cos(rad) * (px - ox) - math.sin(rad) * (py - oy)
    qy = oy + math.sin(rad) * (px - ox) + math.cos(rad) * (py - oy)
    return qx, qy