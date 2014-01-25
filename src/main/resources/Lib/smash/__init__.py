from com.badlogic.gdx.backends.lwjgl import LwjglApplication, LwjglApplicationConfiguration
from com.badlogic.gdx.utils import TimeUtils, Array
from com.badlogic.gdx.math import MathUtils, Rectangle, Circle, Vector3, Vector2
from com.badlogic.gdx import ApplicationListener, Gdx, Input
from com.badlogic.gdx.graphics.g2d import SpriteBatch
from com.badlogic.gdx.graphics import Texture, OrthographicCamera, GL10

BLOCK_DIM = 16
BLOCK_ROWS = 14
BLOCK_COLS = 40

config = LwjglApplicationConfiguration(
    title = "Smash!",
    width = 800,
    height = 480)

class Block(object):
    def __init__(self, x, y, texture, hitSound):
        super(Block, self).__init__()
        self.rectangle = Rectangle(x, y, 64, 64)
        self.texture = texture
        self.hitSound = hitSound

    def hits(self, ball):
        self.rectangle.overlaps(ball.rectangle)

    def draw(self, batch):
        batch.draw(self.texture, self.rectangle.x, self.rectangle.y)

    def hit(self):
        self.hitSound.play()

class Blocks(object):
    def __init__(self, blockLayout, textures, hitSound):
        self.blocks = Array()
        # Center horizontally
        offsetX = (config.width - ((BLOCK_DIM + 1) * BLOCK_COLS)) / 2
        # Flush top vertically
        offsetY = config.height - ((BLOCK_DIM + 1) * (BLOCK_ROWS + 1)) - 10
        for j in xrange(len(blockLayout)):
            for i in xrange(len(blockLayout[j])):
                cell = blockLayout[j][i]
                if cell != ' ':
                    x = offsetX + i * (BLOCK_DIM + 1)
                    y = offsetY + j * (BLOCK_DIM + 1)
                    self.blocks.add(Block(x, y, textures[cell], hitSound))

    def draw(self, batch):
        for block in self.blocks:
            batch.draw(block.texture, block.rectangle.x, block.rectangle.y)

    def checkHit(self, ball):
        iterator = self.blocks.iterator()
        while iterator.hasNext():
            block = iterator.next()
            if block.hits(ball):
                block.hit()
                iterator.remove()
                return block


class Ball(object):

    def __init__(self, texture):
        self.SPEED = 5
        self.direction = Vector2(-1, 1).scl(self.SPEED)
        self.position = Vector2(20, 100)
        self.texture = texture

        self.ball = Circle()
        self.ball.setPosition(self.position)
        self.ball.radius = 8


    def Draw(self, batch):
        batch.draw(self.texture, self.ball.x, self.ball.y)


    def UpdateCoordinates(self, maxHeight, maxWidth):

        prevPosition = Vector2(self.position)

        newPosition = prevPosition.add(self.direction)

        newX = newPosition.x
        newY = newPosition.y
        radius = self.ball.radius

        if newX < radius or newX > maxWidth:
            # left or right wall collision
            self.direction.x *= -1
        elif newY + radius > maxHeight or newY < radius:
            self.direction.y *= -1

        self.ball.setPosition(self.position.add(self.direction))

        # TODO Check if ball is colliding with rectangles

        # TODO Check if ball is colliding with paddle


class PyGdx(ApplicationListener):
    def __init__(self):
        self.camera = None
        self.batch = None
        self.textures = None
        self.bucketimg = None
        self.dropsound = None
        self.rainmusic = None
        self.bucket = None
        # TODO: Remove (Not used)
        self.raindrops = None
        self.blocks = None
        self.background = None

        self.lastdrop = 0


    def spawndrop(self):
        raindrop = Rectangle()
        raindrop.x = MathUtils.random(0, config.width - 64)
        raindrop.y = config.height
        raindrop.width = 64
        raindrop.height = 64
        self.raindrops.add(raindrop)
        self.lastdrop = TimeUtils.nanoTime()

    def create(self):
        self.camera = OrthographicCamera()
        self.camera.setToOrtho(False, config.width, config.height)
        self.batch = SpriteBatch()

        self.background = Texture("assets/swahili.png")
        self.ball = Ball(Texture("assets/red_ball_16_16.png"))
        self.dropimg = Texture("assets/red_rectangle.png")
        self.textures = {
            "r": Texture("assets/red_rectangle.png"),
            "b": Texture("assets/blue_rectangle.png"),
            "g": Texture("assets/green_rectangle.png"),
        }

        self.bucketimg = Texture("assets/bucket.png")
        self.dropsound = Gdx.audio.newSound(Gdx.files.internal("assets/drop.wav"))
        self.rainmusic = Gdx.audio.newSound(Gdx.files.internal("assets/rain.mp3"))

        self.bucket = Rectangle()
        self.bucket.x = (config.width / 2) - (64 / 2)
        self.bucket.y = 20
        self.bucket.width = 64
        self.bucket.height = 64

        self.raindrops = Array()
        self.spawndrop()

        with open("assets/checker_board.level") as f:
            blockLayout = f.read().split("\n")
        self.blocks = Blocks(blockLayout = blockLayout,
                             textures = self.textures,
                             hitSound = self.dropsound)

        self.rainmusic.setLooping(True, True)
        self.rainmusic.play()

    def render(self):
        Gdx.gl.glClearColor(0, 0, 0, 0)
        Gdx.gl.glClear(GL10.GL_COLOR_BUFFER_BIT)

        self.camera.update()

        self.batch.setProjectionMatrix(self.camera.combined)
        self.batch.begin()
        self.batch.draw(self.background, 0, 0, config.width, config.height)
        self.blocks.draw(self.batch)
        self.batch.draw(self.bucketimg, self.bucket.x, self.bucket.y)
        self.ball.Draw(self.batch)
        self.batch.end()

        if Gdx.input.isTouched():
            touchpos = Vector3()
            touchpos.set(Gdx.input.getX(), Gdx.input.getY(), 0)
            self.camera.unproject(touchpos)
            self.bucket.x = touchpos.x - (64 / 2)
        if Gdx.input.isKeyPressed(Input.Keys.LEFT): self.bucket.x -= 200 * Gdx.graphics.getDeltaTime()
        if Gdx.input.isKeyPressed(Input.Keys.RIGHT): self.bucket.x += 200 * Gdx.graphics.getDeltaTime()

        if self.bucket.x < 0: self.bucket.x = 0
        if self.bucket.x > (config.width - 64): self.bucket.x = config.width - 64

        if (TimeUtils.nanoTime() - self.lastdrop) > 1000000000: self.spawndrop()

        self.ball.UpdateCoordinates(config.height, config.width)

        iterator = self.raindrops.iterator()
        while iterator.hasNext():
            raindrop = iterator.next()
            raindrop.y -= 200 * Gdx.graphics.getDeltaTime();
            if (raindrop.y + 64) < 0: iterator.remove()
            if raindrop.overlaps(self.bucket):
                self.dropsound.play()
                iterator.remove()

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
        self.bucketimg.dispose()
        self.dropsound.dispose()
        self.rainmusic.dispose()

def main():
    LwjglApplication(PyGdx(), config)


if __name__ == '__main__':
    main()
