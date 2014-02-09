"""This module contains game objects for smash."""

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
    def __init__(self, texture, rectangle):
        """rectangle should implement:
           - overlaps(rect): return true iff this rectangle overalps with rect
        """
        super(Paddle, self).__init__()
        self.texture = texture
        self.rectangle = rectangle

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

    def get_speed(self):
        """Returns the paddle's speed, as seen by the user."""
        # TODO(paul-g): we need to compute this so that we can adjust
        #the ball direction/speed based on the paddle's
        pass
