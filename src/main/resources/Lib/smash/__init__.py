"""Smash is a simple port of the legendary Breakout to libgdx."""
import random
import math

from com.badlogic.gdx.backends.lwjgl import LwjglApplication
from com.badlogic.gdx.backends.lwjgl import LwjglApplicationConfiguration
from com.badlogic.gdx.utils import TimeUtils, Array
from com.badlogic.gdx.math import MathUtils, Rectangle, Circle, Vector3, Vector2
from com.badlogic.gdx import ApplicationListener, Gdx, Input, InputProcessor
from com.badlogic.gdx.graphics.g2d import SpriteBatch, BitmapFont
from com.badlogic.gdx.graphics import Texture, OrthographicCamera, GL10
from com.badlogic.gdx.physics.box2d import Body, World, BodyDef
from com.badlogic.gdx.physics.box2d import CircleShape, PolygonShape, FixtureDef
from com.badlogic.gdx.physics.box2d import Box2DDebugRenderer
from com.badlogic.gdx.physics.box2d.BodyDef import BodyType
from datetime import datetime

from powerups import *
from game_objects import *

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

class Blocks(object):
    def __init__(self, blockLayout, textures, hit_sound, power_ups):
        super(Blocks, self).__init__()
        self.blocks = Array()
        # Center horizontally
        offset_x = (WIDTH - ((BLOCK_DIM + 1) * BLOCK_COLS)) / 2
        # Flush top vertically
        offset_y = HEIGHT - ((BLOCK_DIM + 1) * (BLOCK_ROWS + 1)) - 10
        for j in xrange(len(blockLayout)):
            for i in xrange(len(blockLayout[j])):
                cell = blockLayout[j][i]
                if cell != ' ':
                    x = offset_x + i * (BLOCK_DIM + 1)
                    y = offset_y + j * (BLOCK_DIM + 1)
                    power_up = self.get_power_up(power_ups[cell])
                    self.blocks.add(Block(textures[cell], hit_sound,
                                          Rectangle(x, y, BLOCK_DIM, BLOCK_DIM),
                                          power_up))

    def get_power_up(self, power_up):
        return power_up[0] if random.random() < power_up[1] else None

    def draw(self, batch):
        for block in self.blocks:
            block.draw(batch)

    def check_hit(self, ball):
        iterator = self.blocks.iterator()
        while iterator.hasNext():
            block = iterator.next()
            if block.hits(ball):
                block.hit()
                iterator.remove()
                return block


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

    def screen_width(self):
        return WIDTH

    def screen_height(self):
        return HEIGHT

    def create_ground(self, position):
        """Create the ground shape.
        position = -1 / 1 for top / bottom respectively."""
        ground_poly = PolygonShape()
        ground_poly.setAsBox(50, 1)
        ground_body_def = BodyDef()
        ground_body_def.type = BodyType.StaticBody
        ground_body_def.position.set(1.0, position * 15.0)
        ground_body = self.world.createBody(ground_body_def)
        ground_body.createFixture(ground_poly, 10)
        ground_poly.dispose()

    def create_wall(self, position):
        """Create a wall in the given position.
        position = -1 / 1 for west / east wall respectively."""
        wall_poly = PolygonShape()
        wall_poly.setAsBox(50, 1)
        wall_def = BodyDef()
        wall_def.type = BodyType.StaticBody
        wall_def.angle = math.radians(90)
        wall_def.position.set(position * 24, 0)
        wall_body = self.world.createBody(wall_def)
        wall_body.createFixture(wall_poly, 10)
        wall_poly.dispose()

    def create_world(self):
        self.create_ground(-1)
        self.create_ground(1)
        self.create_wall(-1)
        self.create_wall(1)

        self.paddle = PaddlePro(self.world)

        circleShape = CircleShape()
        circleShape.setRadius(1)

        fd = FixtureDef()
        fd.shape = circleShape
        fd.density = 1.0
        fd.restitution = 1.0

        circleBodyDef = BodyDef()
        circleBodyDef.type = BodyType.DynamicBody
        circleBodyDef.position.x = 10
        circleBodyDef.position.y = 10
        SPEED = 10
        circleBodyDef.linearVelocity.set(2 * SPEED, -2 * SPEED)
        circleBody = self.world.createBody(circleBodyDef)
        circleBody.createFixture(fd)

        circleShape.dispose();


    def create(self):

        # Create the world
        gravity = Vector2(0.0, 0.0)
        self.world = World(gravity, True)
        self.renderer = Box2DDebugRenderer()

        # add a camera
        self.camera = OrthographicCamera(48, 32)
        self.camera.position.set(0, 15, 0)
        self.input = SmashInput()
        Gdx.input.setInputProcessor(self.input)

#        self.camera = OrthographicCamera()
#        self.camera.setToOrtho(False, WIDTH, HEIGHT)
        self.batch = SpriteBatch()
        self.state = PLAYING

        self.create_world()

        self.background = Texture("assets/swahili.png")
        self.ball = Ball(Texture("assets/red_ball_16_16.png"),
                         BALL_SPEED, Circle(), Rectangle())
        self.dropimg = Texture("assets/red_rectangle.png")
        self.textures = {
            "r": Texture("assets/red_rectangle.png"),
            "b": Texture("assets/blue_rectangle.png"),
            "g": Texture("assets/green_rectangle.png"),
        }
        self.hud_font = BitmapFont()
        self.power_ups = {
            "r": (FireBall(2, Texture("assets/fire_ball.png")), 0.9),
            "b": (None, 1),
            "g": (LargeBall(2, Texture("assets/red_ball_32_32.png")), 0.9)
            }

        paddle_width = 100
        paddle_height = 50
        # self.paddle = Paddle(Texture("assets/paddle.png"),
        #                      Rectangle((WIDTH - paddle_width) / 2, 0,
        #                                paddle_width, paddle_height), self)
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
        print "tick"
#        if self.state == PLAYING:
        if True:

            self.play_time += delta

            if input.touched:
                # not tested
                self.paddle.set_x(input.touched.x - (64 / 2))
            elif input.is_left_pressed():
                print "Pressed left"
                self.paddle.move(delta, -1)
            elif input.is_right_pressed():
                print "Presed right"
                self.paddle.move(delta, 1)
            else:
                # no input, slow down
                self.paddle.slow_down(delta)

            if (self.ball.rectangle.y < self.paddle.top()
                and not self.paddle.hits(self.ball)):
                self.state = LOST

            if self.blocks.blocks.size == 0:
                self.state = WON

            self.ball.tick(delta)
            self.ball.update_coordinates(
                delta, WIDTH, HEIGHT,
                check_hits_block=self.check_hits_block,
                check_hits_paddle=self.paddle.hits)

    def render(self):

        self.world.step(Gdx.app.getGraphics().getDeltaTime(), 3, 3)

        Gdx.gl.glClearColor(0, 0, 0, 0)
        Gdx.gl.glClear(GL10.GL_COLOR_BUFFER_BIT)

        self.renderer.render(self.world, self.camera.combined)

        self.delta_acc += Gdx.graphics.getDeltaTime()
        while self.delta_acc > TICK_TIME:
            input = self.input.tick(TICK_TIME, self.camera)
            self.tick(TICK_TIME, input)
            self.delta_acc -= TICK_TIME

        # self.draw()

    def big_centered_text(self, batch, text):
        self.hud_font.draw(
            batch, text,
            (WIDTH - self.hud_font.getBounds(text).width) / 2,
            HEIGHT / 3 * 2)

    def check_hits_block(self, ball):
        block = self.blocks.check_hit(ball)
        if block:
            self.broken_blocks += 1
            power_up = block.get_power_up()
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
