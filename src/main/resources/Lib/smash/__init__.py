from com.badlogic.gdx.backends.lwjgl import LwjglApplication, LwjglApplicationConfiguration
from com.badlogic.gdx.utils import TimeUtils, Array
from com.badlogic.gdx.math import MathUtils, Rectangle, Vector3
from com.badlogic.gdx import ApplicationListener, Gdx, Input
from com.badlogic.gdx.graphics.g2d import SpriteBatch
from com.badlogic.gdx.graphics import Texture, OrthographicCamera, GL10

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
    def __init__(self, blockLayout, textures, hitSound, height, width):
        self.blocks = Array()
        for j in xrange(len(blockLayout)):
            for i in xrange(len(blockLayout[j])):
                cell = blockLayout[j][i]
                if cell != ' ':
                    x = i * 17
                    y = height - ((j + 1) * 17)
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

        self.lastdrop = 0
        self.width = 800
        self.height = 480


    def spawndrop(self):
        raindrop = Rectangle()
        raindrop.x = MathUtils.random(0, self.width - 64)
        raindrop.y = self.height
        raindrop.width = 64
        raindrop.height = 64
        self.raindrops.add(raindrop)
        self.lastdrop = TimeUtils.nanoTime()

    def create(self):
        self.camera = OrthographicCamera()
        self.camera.setToOrtho(False, self.width, self.height)
        self.batch = SpriteBatch()

        self.textures = {
            "r": Texture("assets/red_rectangle.png"),
            "b": Texture("assets/blue_rectangle.png"),
            "g": Texture("assets/green_rectangle.png"),
        }

        self.bucketimg = Texture("assets/bucket.png")
        self.dropsound = Gdx.audio.newSound(Gdx.files.internal("assets/drop.wav"))
        self.rainmusic = Gdx.audio.newSound(Gdx.files.internal("assets/rain.mp3"))

        self.bucket = Rectangle()
        self.bucket.x = (self.width / 2) - (64 / 2)
        self.bucket.y = 20
        self.bucket.width = 64
        self.bucket.height = 64

        self.raindrops = Array()
        self.spawndrop()

        triangle = ["r br r r rb r",
                    " b  r   r  b ",
                    "  gg     gg  ",
                    "    rr rr    ",
                    "      r      "]
        self.blocks = Blocks(blockLayout = triangle,
                             textures = self.textures,
                             hitSound = self.dropsound,
                             height = self.height,
                             width = self.width)

        self.rainmusic.setLooping(True, True)
        self.rainmusic.play()

    def render(self):
        Gdx.gl.glClearColor(0,0,0.2,0)
        Gdx.gl.glClear(GL10.GL_COLOR_BUFFER_BIT)

        self.camera.update()

        self.batch.setProjectionMatrix(self.camera.combined)
        self.batch.begin()
        self.blocks.draw(self.batch)
        self.batch.draw(self.bucketimg, self.bucket.x, self.bucket.y)
        self.batch.end()

        if Gdx.input.isTouched():
            touchpos = Vector3()
            touchpos.set(Gdx.input.getX(), Gdx.input.getY(), 0)
            self.camera.unproject(touchpos)
            self.bucket.x = touchpos.x - (64 / 2)
        if Gdx.input.isKeyPressed(Input.Keys.LEFT): self.bucket.x -= 200 * Gdx.graphics.getDeltaTime()
        if Gdx.input.isKeyPressed(Input.Keys.RIGHT): self.bucket.x += 200 * Gdx.graphics.getDeltaTime()

        if self.bucket.x < 0: self.bucket.x = 0
        if self.bucket.x > (self.width - 64): self.bucket.x = self.width - 64

        if (TimeUtils.nanoTime() - self.lastdrop) > 1000000000: self.spawndrop()

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
    cfg = LwjglApplicationConfiguration()
    cfg.title = "PyGdx";
    cfg.width = 800
    cfg.height = 480

    LwjglApplication(PyGdx(), cfg)


if __name__ == '__main__':
    main()
