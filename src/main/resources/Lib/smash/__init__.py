"""Smash is a simple port of the legendary Breakout to libgdx."""
import random

from com.badlogic.gdx.backends.lwjgl import LwjglApplication
from com.badlogic.gdx.backends.lwjgl import LwjglApplicationConfiguration
from com.badlogic.gdx.utils import TimeUtils, Array
from com.badlogic.gdx.math import MathUtils, Rectangle, Circle, Vector3, Vector2
from com.badlogic.gdx import ApplicationListener, Gdx, Input, InputProcessor
from com.badlogic.gdx.graphics.g2d import SpriteBatch, BitmapFont
from com.badlogic.gdx.graphics import Texture, OrthographicCamera, GL10
from datetime import datetime

BLOCK_DIM = 32
BLOCK_ROWS = 7
BLOCK_COLS = 20

WIDTH = 800
HEIGHT = 700

PLAYING = 1
PAUSED = 2
LOST = 3
WON = 4

CONFIG = LwjglApplicationConfiguration(
    title="Smash!",
    width=WIDTH,
    height=HEIGHT,
    vSyncEnabled=True)


TPS = 30
TICK_TIME = 1.0 / TPS
BALL_SPEED = 200 # px/sn

class InputSnapshot(object):
    def __init__(self, keys, touched):
        super(InputSnapshot, self).__init__()
        self.keys = set(keys)
        self.touched = touched and Vector3(touched)

    def is_left_pressed(self):
        return Input.Keys.LEFT in self.keys

    def is_right_pressed(self):
        return Input.Keys.RIGHT in self.keys

class SmashInput(InputProcessor):
    """Input achieves two things:

    - the callbacks here are called by Gdx itself, so we know we won't
      miss events by polling at the wrong times, and

    - since we have all inputs received up to any point in time, we
      can snapshot the input state at every tick to create a full
      history of input; so, we could save replays, reverse time, etc.

    """
    def __init__(self):
        super(SmashInput, self).__init__()
        self.keys = set()
        self.touched = None
        self.is_touching = False

    def keyDown(self, keyCode):
        self.keys.add(keyCode)
        return True

    def keyTyped(self, ch):
        return False

    def keyUp(self, keyCode):
        self.keys.discard(keyCode)
        return False

    def mouseMoved(self, screenX, screenY):
        return False

    def scrolled(self, amount):
        return False

    def touchDown(self, screenX, screenY, pointer, button):
        self.is_touching = True
        self.touched = Vector3(screenX, screenY, 0)
        return True

    def touchDragged(self, screenX, screenY, pointer):
        self.touched = Vector3(screenX, screenY, 0)
        return False

    def touchUp(self, screenX, screenY, pointer, button):
        self.is_touching = False
        return True

    def tick(self, delta, camera):
        touched = self.touched and Vector3(self.touched)
        if touched:
            camera.unproject(touched)
        snapshot = InputSnapshot(self.keys, touched)
        if not self.is_touching:
            self.touched = None
        return snapshot

class PowerUp(object):

    """Base class for all powerups."""
    def __init__(self, lifetime):
        super(PowerUp, self).__init__()
        self.lifetime = lifetime
        self.time_remaining = 0

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
    def __init__(self, lifetime):
        super(FireBall, self).__init__(lifetime)
        self.texture = Texture("assets/fire_ball.png")

    def apply_effect(self, ball):
        ball.blockDirectionChange = 1
        ball.set_texture(self.texture)

    def remove_effect(self, ball):
        ball.reset_block_direction_change()
        ball.reset_texture()

    def __str__(self):
        return "Fireball(%.1f)" % (self.time_remaining, )


class LargeBall(PowerUp):
    def __init__(self, lifetime):
        super(LargeBall, self).__init__(lifetime)
        self.texture = Texture("assets/red_ball_32_32.png")

    def apply_effect(self, ball):
        ball.set_radius(16)
        ball.set_texture(self.texture)

    def remove_effect(self, ball):
        ball.reset_radius()
        ball.reset_texture()

    def __str__(self):
        return "Largeball(%.1f)" % (self.time_remaining, )


class Block(object):
    def __init__(self, x, y, texture, hit_sound, power_up=None):
        super(Block, self).__init__()
        self.rectangle = Rectangle(x, y, BLOCK_DIM, BLOCK_DIM)
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


class Blocks(object):
    def __init__(self, blockLayout, textures, hit_sound, power_ups):
        super(Blocks, self).__init__()
        self.blocks = Array()
        # Center horizontally
        offsetX = (WIDTH - ((BLOCK_DIM + 1) * BLOCK_COLS)) / 2
        # Flush top vertically
        offsetY = HEIGHT - ((BLOCK_DIM + 1) * (BLOCK_ROWS + 1)) - 10
        for j in xrange(len(blockLayout)):
            for i in xrange(len(blockLayout[j])):
                cell = blockLayout[j][i]
                if cell != ' ':
                    x = offsetX + i * (BLOCK_DIM + 1)
                    y = offsetY + j * (BLOCK_DIM + 1)
                    power_up = self.getPowerUp(power_ups[cell])
                    self.blocks.add(
                        Block(x, y, textures[cell], hit_sound, power_up))

    def getPowerUp(self, power_up):
        return power_up[0] if random.random() < power_up[1] else None

    def draw(self, batch):
        for block in self.blocks:
            block.draw(batch)

    def checkHit(self, ball):
        iterator = self.blocks.iterator()
        while iterator.hasNext():
            block = iterator.next()
            if block.hits(ball):
                block.hit()
                iterator.remove()
                return block


class Paddle(object):
    def __init__(self, texture):
        super(Paddle, self).__init__()
        self.texture = texture
        paddleWidth = 100
        paddleHeight = 50
        self.rectangle = Rectangle((WIDTH - paddleWidth) / 2, 0,
                                   paddleWidth, paddleHeight)

    def draw(self, batch):
        batch.draw(self.texture, self.rectangle.x,
                   self.rectangle.y, self.rectangle.width,
                   self.rectangle.height)

    def hits(self, ball):
        return self.rectangle.overlaps(ball.rectangle)

    def move(self, delta, direction=1):
        """direction is 1 for right, -1 for left."""
        self.rectangle.x += direction * 200 * delta

    def get_speed(self):
        pass

class Ball(object):
    def __init__(self, texture):
        super(Ball, self).__init__()
        self.direction = Vector2(-1, 1).nor()
        self.speed = BALL_SPEED
        self.position = Vector2(100, 100)
        self.default_texture = texture
        self.texture = texture
        self.power_ups = set()

        self.default_radius = 8

        self.ball = Circle()
        self.ball.setPosition(self.position)
        self.ball.radius = self.default_radius

        self.rectangle = Rectangle()
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
        for power_up in self.power_ups:
            power_up.tick(delta)
        expired_power_ups = [p for p in self.power_ups if  p.has_expired()]
        map(self.remove_power_up, expired_power_ups)

    def update_coordinates(self, delta, check_hits_block, check_hits_paddle):
        # Do we bounce?
        movement = Vector2(self.direction)
        movement.scl(self.speed * delta, self.speed * delta)
        new_position = Vector2(self.position).add(movement)

        new_x = new_position.x
        new_y = new_position.y
        radius = self.ball.radius

        if new_x < radius or new_x > WIDTH - radius:
            # left or right wall collision
            self.direction.x *= -1
        elif new_y > HEIGHT - radius or new_y < radius:
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
        self.power_ups.add(power_up)
        power_up.apply_effect(self)

    def remove_power_up(self, power_up):
        power_up.remove_effect(self)
        self.power_ups.remove(power_up)

    def get_power_ups_string(self):
        if len(self.power_ups) > 0:
            return " ".join([str(power_up) for power_up in self.power_ups])
        else:
            return "Lame"

class SmashGame(ApplicationListener):
    def __init__(self):
        super(SmashGame, self).__init__()
        self.camera = None
        self.batch = None
        self.textures = None
        self.paddle = None
        self.drop_sound = None
        self.rain_music = None
        self.blocks = None
        self.background = None
        self.state = None
        self.ball = None
        self.dropimg = None
        self.hud_font = None
        self.input = None
        self.power_ups = None
        self.broken_blocks = 0
        self.delta_acc = 0
        self.play_time = 0

    def create(self):
        self.input = SmashInput()
        Gdx.input.setInputProcessor(self.input)

        self.camera = OrthographicCamera()
        self.camera.setToOrtho(False, WIDTH, HEIGHT)
        self.batch = SpriteBatch()
        self.state = PLAYING

        self.background = Texture("assets/swahili.png")
        self.ball = Ball(Texture("assets/red_ball_16_16.png"))
        self.dropimg = Texture("assets/red_rectangle.png")
        self.textures = {
            "r": Texture("assets/red_rectangle.png"),
            "b": Texture("assets/blue_rectangle.png"),
            "g": Texture("assets/green_rectangle.png"),
        }
        self.hud_font = BitmapFont()
        self.power_ups = {
            "r": (FireBall(2), 0.9),
            "b": (None, 1),
            "g": (LargeBall(2), 0.9)
            }

        self.paddle = Paddle(Texture("assets/paddle.png"))
        self.drop_sound = Gdx.audio.newSound(
            Gdx.files.internal("assets/drop.wav"))
        self.rain_music = Gdx.audio.newSound(
            Gdx.files.internal("assets/rain.mp3"))

        with open("assets/checker_board.level") as f:
            blockLayout = f.read().split("\n")
        self.blocks = Blocks(blockLayout=blockLayout,
                             textures=self.textures,
                             hit_sound=self.drop_sound,
                             power_ups=self.power_ups)

        self.broken_blocks = 0
        self.delta_acc = 0
        self.play_time = 0

    def score(self):
        return "Blocks %d, Time %.1f, Rating: %s" % (
            self.broken_blocks, self.play_time,
            self.ball.get_power_ups_string())

    def draw(self):
        """ Do any and all drawing. """
        self.camera.update()
        self.batch.setProjectionMatrix(self.camera.combined)
        self.batch.begin()
        self.batch.draw(self.background, 0, 0, WIDTH, HEIGHT)
        self.blocks.draw(self.batch)
        self.paddle.draw(self.batch)
        self.ball.draw(self.batch)
        self.hud_font.draw(self.batch, self.score(), 20, 20)
        if self.state == LOST:
            self.big_centered_text(self.batch, "You are lose!")
        elif self.state == WON:
            self.big_centered_text(self.batch, "A winner is you!")
        self.batch.end()

    def tick(self, delta, input):
        """ Another 1/60 seconds have passed.  Update state. """
        if self.state == PLAYING:
            self.play_time += delta

            if input.touched:
                self.paddle.rectangle.x = input.touched.x - (64 / 2)
            if input.is_left_pressed():
                self.paddle.move(delta, -1)
            if input.is_right_pressed():
                self.paddle.move(delta)

            paddle_rect = self.paddle.rectangle
            if paddle_rect.x < 0:
                self.paddle.rectangle.x = 0
            if paddle_rect.x > (WIDTH - paddle_rect.width):
                self.paddle.rectangle.x = WIDTH - paddle_rect.width

            if (self.ball.rectangle.y < paddle_rect.y + paddle_rect.height
                and not self.paddle.hits(self.ball)):
                self.state = LOST

            if self.blocks.blocks.size == 0:
                self.state = WON

            self.ball.tick(delta)
            self.ball.update_coordinates(
                delta,
                check_hits_block=self.check_hits_block,
                check_hits_paddle=self.paddle.hits)

    def render(self):
        Gdx.gl.glClearColor(0, 0, 0, 0)
        Gdx.gl.glClear(GL10.GL_COLOR_BUFFER_BIT)

        self.delta_acc += Gdx.graphics.getDeltaTime()
        while self.delta_acc > TICK_TIME:
            input = self.input.tick(TICK_TIME, self.camera)
            self.tick(TICK_TIME, input)
            self.delta_acc -= TICK_TIME

        self.draw()

    def big_centered_text(self, batch, text):
        self.hud_font.draw(
            batch, text,
            (WIDTH - self.hud_font.getBounds(text).width) / 2,
            HEIGHT / 3 * 2)

    def check_hits_block(self, ball):
        block = self.blocks.checkHit(ball)
        if block:
            self.broken_blocks += 1
            power_up = block.getPowerUp()
            if power_up:
                ball.add_power_up(power_up)
                power_up.reset_remaining()
        return block

    def updatePowerUps(self):
        self.ball.updatePowerUps()

    def resize(self, width, height):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def dispose(self):
        """"Handle dispose event"""
        self.batch.dispose()
        for (_, texture) in self.textures.items():
            texture.dispose()
        self.paddle.texture.dispose()
        self.drop_sound.dispose()
        self.rain_music.dispose()
        self.hud_font.dispose()

def main():
    """Main function"""
    LwjglApplication(SmashGame(), CONFIG)

if __name__ == '__main__':
    main()


