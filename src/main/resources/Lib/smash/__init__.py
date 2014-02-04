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
HEIGHT = 700

PLAYING = 1
PAUSED = 2
LOST = 3
WON = 4

config = LwjglApplicationConfiguration(
    title = "Smash!",
    width = WIDTH,
    height = HEIGHT)

TICK_TIME = 1.0 / 30

class PowerUp(object):
    def __init__(self, lifetime):
        self.lifetime = lifetime
        self.timeRemaining = 0

    def applyEffect(self, ball):
        raise NotImplementedError()

    def removeEffect(self, ball):
        raise NotImplementedError()

    def tick(self, delta):
        self.timeRemaining -= delta

    def resetRemaining(self):
        self.timeRemaining = self.lifetime

    def hasExpired(self):
        return self.timeRemaining <= 0


class FireBall(PowerUp):
    def __init__(self, lifetime):
        super(FireBall, self).__init__(lifetime)
        self.texture = Texture("assets/fire_ball.png")

    def applyEffect(self, ball):
        ball.blockDirectionChange = 1
        ball.setTexture(self.texture)

    def removeEffect(self, ball):
        ball.resetBlockDirectionChange()
        ball.resetTexture()

    def __str__(self):
        return "Fireball(%.1f)" % (self.timeRemaining, )


class LargeBall(PowerUp):
    def __init__(self, lifetime):
        super(LargeBall, self).__init__(lifetime)
        self.texture = Texture("assets/red_ball_32_32.png")

    def applyEffect(self, ball):
        ball.setRadius(16)
        ball.setTexture(self.texture)

    def removeEffect(self, ball):
        ball.resetRadius()
        ball.resetTexture()

    def __str__(self):
        return "Largeball(%.1f)" % (self.timeRemaining, )

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
        return powerUp[0] if random.random() < powerUp[1] else None

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
        self.SPEED = 3
        self.direction = Vector2(-1, 1).scl(self.SPEED)
        self.position = Vector2(100, 100)
        self.defaultTexture = texture
        self.texture = texture
        self.powerUps = set()

        self.defaultRadius = 8

        self.ball = Circle()
        self.ball.setPosition(self.position)
        self.ball.radius = self.defaultRadius

        self.rectangle = Rectangle()
        self.setRectanglePosition()

        self.blockDirectionChange = -1

    def setRectanglePosition(self):
        self.rectangle.setPosition(self.position.sub(
            Vector2(self.ball.radius, self.ball.radius)))
        self.rectangle.width = 2 * self.ball.radius
        self.rectangle.height = 2 * self.ball.radius

    def draw(self, batch):
        batch.draw(self.texture, self.ball.x - self.ball.radius, self.ball.y - self.ball.radius)

    def setRadius(self, radius):
        self.ball.radius = radius
        self.setRectanglePosition()

    def resetRadius(self):
        self.ball.radius = self.defaultRadius
        self.setRectanglePosition()

    def setTexture(self, texture):
        self.texture = texture

    def resetTexture(self):
        self.texture = self.defaultTexture

    def resetBlockDirectionChange(self):
        self.blockDirectionChange = -1

    def tick(self, delta):
        for powerUp in self.powerUps:
            powerUp.tick(delta)
        expiredPowerUps = [powerUp for powerUp in self.powerUps if  powerUp.hasExpired()]
        for p in expiredPowerUps:
            self.removePowerUp(p)

    def updateCoordinates(self, checkHitsBlock, checkHitsPaddle):
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
        self.powerUps.add(powerUp)
        powerUp.applyEffect(self)

    def removePowerUp(self, powerUp):
        powerUp.removeEffect(self)
        self.powerUps.remove(powerUp)

    def getPowerUpsString(self):
        if len(self.powerUps) > 0:
            return " ".join([str(powerUp) for powerUp in self.powerUps])
        else:
            return "Lame"

class PyGdx(ApplicationListener):
    def __init__(self):
        self.camera = None
        self.batch = None
        self.textures = None
        self.paddle = None
        self.dropSound = None
        self.rainMusic = None
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
        self.hudFont = BitmapFont()
        self.powerUps = {
            "r": (FireBall(2), 0.1),
            "b": (None, 1),
            "g": (LargeBall(2), 0.1)
            }

        self.paddle = Paddle(Texture("assets/paddle.png"))
        self.dropSound = Gdx.audio.newSound(Gdx.files.internal("assets/drop.wav"))
        self.rainMusic = Gdx.audio.newSound(Gdx.files.internal("assets/rain.mp3"))

        with open("assets/checker_board.level") as f:
            blockLayout = f.read().split("\n")
        self.blocks = Blocks(blockLayout = blockLayout,
                             textures = self.textures,
                             hitSound = self.dropSound,
                             powerUps = self.powerUps)

        self.brokenBlocks = 0
        self.deltaAcc = 0
        self.playTime = 0

    def score(self):
        return "Blocks %d, Time %.1f, Rating: %s" % (
            self.brokenBlocks, self.playTime, self.ball.getPowerUpsString())

    def lose(self):
        pass

    def draw(self):
        """ Do any and all drawing. """
        self.camera.update()
        self.batch.setProjectionMatrix(self.camera.combined)
        self.batch.begin()
        self.batch.draw(self.background, 0, 0, WIDTH, HEIGHT)
        self.blocks.draw(self.batch)
        self.paddle.draw(self.batch)
        self.ball.draw(self.batch)
        self.hudFont.draw(self.batch, self.score(), 20, 20)
        if self.state == LOST:
            self.bigCenteredText(self.batch, "You are lose!")
        elif self.state == WON:
            self.bigCenteredText(self.batch, "A winner is you!")
        self.batch.end()

    def tick(self, delta):
        """ Another 1/60 seconds have passed.  Update state. """
        if self.state == PLAYING:
            self.playTime += delta

            if Gdx.input.isTouched():
                touchpos = Vector3()
                touchpos.set(Gdx.input.getX(), Gdx.input.getY(), 0)
                self.camera.unproject(touchpos)
                self.paddle.rectangle.x = touchpos.x - (64 / 2)
            if Gdx.input.isKeyPressed(Input.Keys.LEFT):
                self.paddle.rectangle.x -= 200 * delta
            if Gdx.input.isKeyPressed(Input.Keys.RIGHT):
                self.paddle.rectangle.x += 200 * delta

            if self.paddle.rectangle.x < 0:
                self.paddle.rectangle.x = 0
            if self.paddle.rectangle.x > (WIDTH - self.paddle.rectangle.width):
                self.paddle.rectangle.x = WIDTH - self.paddle.rectangle.width

            if self.ball.rectangle.y < self.paddle.rectangle.height - 5:
                self.state = LOST

            if self.blocks.blocks.size == 0:
                self.state = WON

            self.ball.tick(delta)
            self.ball.updateCoordinates(
                checkHitsBlock = lambda ball: self.checkHitsBlock(ball),
                checkHitsPaddle = lambda ball: self.paddle.hits(ball))

    def render(self):
        Gdx.gl.glClearColor(0, 0, 0, 0)
        Gdx.gl.glClear(GL10.GL_COLOR_BUFFER_BIT)

        self.deltaAcc += Gdx.graphics.getDeltaTime()
        while self.deltaAcc > TICK_TIME:
            self.tick(TICK_TIME)
            self.deltaAcc -= TICK_TIME

        self.draw()

    def bigCenteredText(self, batch, text):
        self.hudFont.draw(batch, text, (WIDTH - self.hudFont.getBounds (text).width) / 2, HEIGHT / 3 * 2)

    def checkHitsBlock(self, ball):
        block = self.blocks.checkHit(ball)
        if block:
            self.brokenBlocks += 1
            powerUp = block.getPowerUp()
            if powerUp:
                ball.addPowerUp(powerUp)
                powerUp.resetRemaining()
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
        self.batch.dispose()
        for (_, texture) in self.textures.items():
            texture.dispose()
        self.paddle.texture.dispose()
        self.dropSound.dispose()
        self.rainMusic.dispose()
        self.hudFont.dispose()

def main():
    LwjglApplication(PyGdx(), config)

if __name__ == '__main__':
    main()
