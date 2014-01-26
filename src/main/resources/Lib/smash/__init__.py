import random

from com.badlogic.gdx.backends.lwjgl import LwjglApplication, LwjglApplicationConfiguration
from com.badlogic.gdx.utils import TimeUtils, Array
from com.badlogic.gdx.math import MathUtils, Rectangle, Circle, Vector3, Vector2
from com.badlogic.gdx import ApplicationListener, Gdx, Input
from com.badlogic.gdx.graphics.g2d import SpriteBatch, BitmapFont
from com.badlogic.gdx.graphics import Texture, OrthographicCamera, GL10
from datetime import datetime

BLOCK_DIM = 32
BLOCK_ROWS = 7
BLOCK_COLS = 20

WIDTH = 800
HEIGHT = 480

PLAYING = 1
PAUSED = 2
LOST = 3
WON = 4

config = LwjglApplicationConfiguration(
    title = "Smash!",
    width = WIDTH,
    height = HEIGHT)


class PowerUp(object):
    def __init__(self):
        pass

    def applyEffect(self, ball):
        print "Applying power up effect"

class FireBall(PowerUp):
    def __init__(self):
        super(FireBall, self).__init__()

    def applyEffect(self, ball):
        print "Fireball effect"
        ball.blockDirectionChange = 1

    def removeEffect(self, ball):
        ball.resetBlockDirectionChange()

class Block(object):
    def __init__(self, x, y, texture, hitSound, powerUp = None):
        super(Block, self).__init__()
        self.rectangle = Rectangle(x, y, BLOCK_DIM, BLOCK_DIM)
        self.texture = texture
        self.hitSound = hitSound
        self.powerUp = powerUp

    def hits(self, ball):
        return self.rectangle.overlaps(ball.rectangle)

    def draw(self, batch):
        batch.draw(self.texture, self.rectangle.x, self.rectangle.y, self.rectangle.width, self.rectangle.height)

    def hit(self):
        self.hitSound.play()

    def getPowerUp(self):
        return self.powerUp


class Blocks(object):
    def __init__(self, blockLayout, textures, hitSound, powerUps):
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
                    powerUp = self.getPowerUp(powerUps[cell])
                    self.blocks.add(
                        Block(x, y, textures[cell], hitSound, powerUp))

    def getPowerUp(self, powerUp):
        return powerUp[0]
#        return powerUp[0] if random.random() < powerUp[1] else None


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
        self.rectangle = Rectangle((WIDTH - paddleWidth) / 2, 0, paddleWidth, paddleHeight)

    def draw(self, batch):
        batch.draw(self.texture, self.rectangle.x, self.rectangle.y, self.rectangle.width, self.rectangle.height)

    def hits(self, ball):
        return self.rectangle.overlaps(ball.rectangle)


class Ball(object):
    def __init__(self, texture):
        super(Ball, self).__init__()
        self.SPEED = 5
        self.direction = Vector2(-1, 1).scl(self.SPEED)
        self.position = Vector2(100, 100)
        self.texture = texture
        self.powerUps = []

        self.ball = Circle()
        self.ball.setPosition(self.position)
        self.ball.radius = 8

        self.rectangle = Rectangle()
        self.rectangle.setPosition(self.position.sub(
            Vector2(self.ball.radius, self.ball.radius)))
        self.rectangle.width = 16
        self.rectangle.height = 16

        self.blockDirectionChange = -1

    def Draw(self, batch):
        batch.draw(self.texture, self.ball.x - self.ball.radius, self.ball.y - self.ball.radius)

    def resetBlockDirectionChange(self):
        self.blockDirectionChange = -1

    def UpdateCoordinates(self, checkHitsBlock, checkHitsPaddle):
        prevPosition = Vector2(self.position)

        newPosition = prevPosition.add(self.direction)

        newX = newPosition.x
        newY = newPosition.y
        radius = self.ball.radius

        if newX < radius or newX > WIDTH - radius:
            # left or right wall collision
            self.direction.x *= -1
        elif newY > HEIGHT - radius or newY < radius:
            self.direction.y *= -1

        newPosition = self.position.add(self.direction)

        self.ball.setPosition(newPosition)
        self.rectangle.setPosition(newPosition)

        block = checkHitsBlock(self)
        if block:
            # Hit a block
            blockBottom = block.rectangle.getY()
            blockTop = blockBottom + block.rectangle.height
            ballTop = self.position.y + self.ball.radius
            ballBottom = self.position.y - self.ball.radius
            if blockBottom >= ballTop or blockTop <= ballBottom:
                self.direction.y *= self.blockDirectionChange
            else:
                self.direction.x *= self.blockDirectionChange

        if checkHitsPaddle(self):
            self.direction.y *= -1

    def addPowerUp(self, powerUp):
        self.powerUps.append(powerUp)
        powerUp.applyEffect(self)

    def removePowerUp(self, powerUp):
        # how do I do this?
        powerUp.removeEffect(self)

class PyGdx(ApplicationListener):
    def __init__(self):
        self.camera = None
        self.batch = None
        self.textures = None
        self.paddle = None
        self.dropsound = None
        self.rainmusic = None
        self.blocks = None
        self.background = None
        self.state = None

    def create(self):
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
        self.scoreFont = BitmapFont()
        self.powerUps = {
            "r": (FireBall(), 0.5),
            "b": (None, 1),
            "g": (None, 1)
            }

        self.paddle = Paddle(Texture("assets/paddle.png"))
        self.dropsound = Gdx.audio.newSound(Gdx.files.internal("assets/drop.wav"))
        self.rainmusic = Gdx.audio.newSound(Gdx.files.internal("assets/rain.mp3"))

        with open("assets/checker_board.level") as f:
            blockLayout = f.read().split("\n")
        self.blocks = Blocks(blockLayout = blockLayout,
                             textures = self.textures,
                             hitSound = self.dropsound,
                             powerUps = self.powerUps)

        self.brokenBlocks = 0
        self.gameTime = 0
        self.deltaAcc = 0
        self.updateScore()

    def updateScore(self):
        self.score = "Blocks {}, Time {}".format(
            self.brokenBlocks, self.gameTime)

    def lose(self):
        pass

    def updateTimer(self):
        self.deltaAcc += Gdx.graphics.getDeltaTime()
        if self.deltaAcc >= 1:
            self.gameTime += 1
            self.deltaAcc = 0

    def render(self):
        Gdx.gl.glClearColor(0, 0, 0, 0)
        Gdx.gl.glClear(GL10.GL_COLOR_BUFFER_BIT)

        self.updateTimer()
        self.updateScore()

        self.camera.update()
        self.batch.setProjectionMatrix(self.camera.combined)
        self.batch.begin()
        self.batch.draw(self.background, 0, 0, WIDTH, HEIGHT)
        self.blocks.draw(self.batch)
        self.paddle.draw(self.batch)
        self.ball.Draw(self.batch)
        self.scoreFont.draw(self.batch, self.score, 20, 20)
        if self.state == LOST:
            self.bigCenteredText(self.batch, "You are lose!")
        elif self.state == WON:
            self.bigCenteredText(self.batch, "A winner is you!")
        self.batch.end()

        if self.state == PLAYING:
            if Gdx.input.isTouched():
                touchpos = Vector3()
                touchpos.set(Gdx.input.getX(), Gdx.input.getY(), 0)
                self.camera.unproject(touchpos)
                self.paddle.rectangle.x = touchpos.x - (64 / 2)
            if Gdx.input.isKeyPressed(Input.Keys.LEFT):
                self.paddle.rectangle.x -= 200 * Gdx.graphics.getDeltaTime()
            if Gdx.input.isKeyPressed(Input.Keys.RIGHT):
                self.paddle.rectangle.x += 200 * Gdx.graphics.getDeltaTime()

            if self.paddle.rectangle.x < 0:
                self.paddle.rectangle.x = 0
            if self.paddle.rectangle.x > (WIDTH - self.paddle.rectangle.width):
                self.paddle.rectangle.x = WIDTH - self.paddle.rectangle.width

            if self.ball.rectangle.y < self.paddle.rectangle.height - 5:
                self.state = LOST

            if self.blocks.blocks.size == 0:
                self.state = WON

            self.ball.UpdateCoordinates(
                checkHitsBlock = lambda ball: self.checkHitsBlock(ball),
                checkHitsPaddle = lambda ball: self.paddle.hits(ball))

    def bigCenteredText(self, batch, text):
        self.scoreFont.draw(batch, text, (WIDTH - self.scoreFont.getBounds (text).width) / 2, HEIGHT / 3 * 2)

    def checkHitsBlock(self, ball):
        block = self.blocks.checkHit(ball)
        if block:
            self.brokenBlocks += 1
            powerUp = block.getPowerUp()
            if powerUp:
                ball.addPowerUp(powerUp)
        return block

    def resize(self, width, height):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def dispose(self):
        self.batch.dispose()
        for (_, texture) in self.textures.items():
            texture.dispose()
        self.paddle.texture.dispose()
        self.dropsound.dispose()
        self.rainmusic.dispose()

def main():
    LwjglApplication(PyGdx(), config)


if __name__ == '__main__':
    main()
