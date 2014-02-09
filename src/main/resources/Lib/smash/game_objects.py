"""This module contains game objects for smash."""

class Block(object):
    """A block to smash with the ball."""    
    def __init__(self, x, y, texture, hit_sound, rectangle, power_up=None):
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
        return self.rectangle.overlaps(ball.rectangle)

    def draw(self, batch):
        batch.draw(self.texture, self.rectangle.x,
                   self.rectangle.y, self.rectangle.width,
                   self.rectangle.height)

    def hit(self):
        self.hit_sound.play()

    def getPowerUp(self):
        return self.power_up



