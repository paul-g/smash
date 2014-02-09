"""Module for smash powerups."""

class PowerUp(object):

    """Base class for all powerups."""
    def __init__(self, lifetime, texture=None):
        super(PowerUp, self).__init__()
        self.lifetime = lifetime
        self.time_remaining = 0
        self.texture = texture

    def apply_effect(self, ball):
        raise NotImplementedError()

    def remove_effect(self, ball):
        raise NotImplementedError()

    def tick(self, delta):
        self.time_remaining -= delta

    def reset_remaining(self):
        self.time_remaining = self.lifetime

    def has_expired(self):
        return self.time_remaining <= 0


class FireBall(PowerUp):
    """A fireball powerup makes a ball go through blocks."""
    def __init__(self, lifetime, texture):
        super(FireBall, self).__init__(lifetime, texture)

    def apply_effect(self, ball):
        ball.blockDirectionChange = 1
        ball.set_texture(self.texture)

    def remove_effect(self, ball):
        ball.reset_block_direction_change()
        ball.reset_texture()

    def __str__(self):
        return "Fireball(%.1f)" % (self.time_remaining, )


class LargeBall(PowerUp):
    def __init__(self, lifetime, texture):
        super(LargeBall, self).__init__(lifetime, texture)

    def apply_effect(self, ball):
        ball.set_radius(16)
        ball.set_texture(self.texture)

    def remove_effect(self, ball):
        ball.reset_radius()
        ball.reset_texture()

    def __str__(self):
        return "Largeball(%.1f)" % (self.time_remaining, )
