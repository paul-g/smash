smash
=====

A port of breakout to libgdx.

# Dependencies

We are using [jython 2.7b1](http://www.jython.org/downloads.html).

Unless otherwise stated, all gdx libs are version
[0.9.9](https://github.com/libgdx/libgdx/releases/tag/0.9.9-xamarin).

# Instructions

Add the following to the classpath (for Windows you should probably change ':' to ';'):

```
export CLASSPATH=libs/gdx.jar:libs/gdx-backend-lwjgl.jar:libs/gdx-natives.jar:libs/gdx-sources.jar:libs/gdx-backend-lwjgl-natives.jar
```

Then run `jython smash.py`

# Self-contained jar

To build a self-contained jar and run it, use:

    mvn package
    java -jar target/smash-1.0-jar-with-dependencies.jar eval
