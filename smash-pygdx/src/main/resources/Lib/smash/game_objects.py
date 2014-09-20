"""This module contains game objects for smash."""

from com.badlogic.gdx.math import Vector2

class Block(object):
    """A block to smash with the ball."""
    def __init__(self, texture, hit_sound, rectangle, power_up=None):
        """rectangle should implement:
           - overlaps(rect): return true iff this rectangle overalps with rect
           hit_sound should implement:
           -play(): plays the sound
        """
        super(Block, self).__init__()
        self.rectangle = rectangle
        self.texture = texture
        self.hit_sound = hit_sound
        self.power_up = power_up

    def hits(self, ball):
        """Return true iff the given ball hits this rectangle."""
        return self.rectangle.overlaps(ball.rectangle)

    def draw(self, batch):
        """Draw this rectangle.
        batch should implement:
        - draw(): draws the rectangle
        """
        batch.draw(self.texture, self.rectangle.x,
                   self.rectangle.y, self.rectangle.width,
                   self.rectangle.height)

    def hit(self):
        """Handle a hit."""
        self.hit_sound.play()

    def get_power_up(self):
        """Return this block's powerup."""
        return self.power_up


class Paddle(object):
    """A paddle to hit the ball with."""
    def __init__(self, texture, rectangle, game):
        """rectangle should implement:
           - overlaps(rect): return true iff this rectangle overalps with rect
        """
        super(Paddle, self).__init__()
        self.texture = texture
        self.rectangle = rectangle
        self.game = game

    def draw(self, batch):
        """Draw this paddle.
        batch should implement:
        - draw(): draws the paddle
        """
        batch.draw(self.texture, self.rectangle.x,
                   self.rectangle.y, self.rectangle.width,
                   self.rectangle.height)

    def hits(self, ball):
        """Return true iff the given ball hits this rectangle."""
        return self.rectangle.overlaps(ball.rectangle)

    def move(self, delta, direction=1):
        """direction is 1 for right, -1 for left."""
        self.rectangle.x += direction * 200 * delta
        self.__check()

    def get_speed(self):
        """Returns the paddle's speed, as seen by the user."""
        # TODO(paul-g): we need to compute this so that we can adjust
        #the ball direction/speed based on the paddle's
        pass

    def set_x(self, x):
        self.rectangle.x = x
        self.__check()

    def __check(self):
        if self.rectangle.x < 0:
            self.rectangle.x = 0
        width = self.game.screen_width()
        if self.rectangle.x > (width - self.rectangle.width):
            self.rectangle.x = width - self.rectangle.width

    def top(self):
        return self.rectangle.y + self.rectangle.height


class Ball(object):
    def __init__(self, texture, speed, circle, rectangle):
        """
        circle shoud have members:
        - x, y, radius
        circle should implement:
        - setPosition(Vector2)

        rectangle should have members:
        - width, height
        rectangle should implement:
        - setPosition(Vector2)
        """
        super(Ball, self).__init__()
        self.direction = Vector2(-1, 1).nor()
        self.speed = speed
        self.position = Vector2(100, 100)
        self.default_texture = texture
        self.texture = texture
        self.power_ups = set()
        self.default_radius = 8
        self.ball = circle
        self.ball.setPosition(self.position)
        self.ball.radius = self.default_radius
        self.rectangle = rectangle
        self.setRectanglePosition()
        self.block_direction_change = -1

    def setRectanglePosition(self):
        self.rectangle.setPosition(self.position.sub(
            Vector2(self.ball.radius, self.ball.radius)))
        self.rectangle.width = 2 * self.ball.radius
        self.rectangle.height = 2 * self.ball.radius

    def draw(self, batch):
        batch.draw(self.texture, self.ball.x - self.ball.radius,
                   self.ball.y - self.ball.radius)

    def set_radius(self, radius):
        self.ball.radius = radius
        self.setRectanglePosition()

    def reset_radius(self):
        self.ball.radius = self.default_radius
        self.setRectanglePosition()

    def set_texture(self, texture):
        self.texture = texture

    def reset_texture(self):
        self.texture = self.default_texture

    def reset_block_direction_change(self):
        self.block_direction_change = -1

    def tick(self, delta):
        """Apply tick to all powerups."""
        #TODO(paul-g): should this really go here? I think the
        #game should call tick on all game objects.
        for power_up in self.power_ups:
            power_up.tick(delta)
        expired_power_ups = [p for p in self.power_ups if  p.has_expired()]
        map(self.remove_power_up, expired_power_ups)

    def update_coordinates(self, delta, screen_width, screen_height, 
                           check_hits_block, check_hits_paddle):
        # Do we bounce?
        movement = Vector2(self.direction)
        movement.scl(self.speed * delta, self.speed * delta)
        new_position = Vector2(self.position).add(movement)

        new_x = new_position.x
        new_y = new_position.y
        radius = self.ball.radius

        if new_x < radius or new_x > screen_width - radius:
            # left or right wall collision
            self.direction.x *= -1
        elif new_y > screen_height - radius or new_y < radius:
            self.direction.y *= -1

        # Actually update position
        movement = Vector2(self.direction)
        movement.scl(self.speed * delta, self.speed * delta)
        self.position.add(movement)

        self.ball.setPosition(self.position)
        self.rectangle.setPosition(self.position)

        # Check hits
        block = check_hits_block(self)
        if block:
            # Hit a block
            block_bottom = block.rectangle.getY()
            block_top = block_bottom + block.rectangle.height
            ball_top = self.position.y + self.ball.radius
            ball_bottom = self.position.y - self.ball.radius
            if block_bottom >= ball_top or block_top <= ball_bottom:
                self.direction.y *= self.block_direction_change
            else:
                self.direction.x *= self.block_direction_change

        if check_hits_paddle(self):
            self.direction.y *= -1

    def add_power_up(self, power_up):
        """Add a powerup.PowerUp to this ball."""
        self.power_ups.add(power_up)
        power_up.apply_effect(self)

    def remove_power_up(self, power_up):
        """Remove a powerup.PowerUp from this ball."""
        power_up.remove_effect(self)
        self.power_ups.remove(power_up)

    def get_power_ups_string(self):
        """Return a pretty printed list of powerups active for this ball."""
        if len(self.power_ups) > 0:
            return " ".join([str(power_up) for power_up in self.power_ups])
        else:
            return "Lame"
