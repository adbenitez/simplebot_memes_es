"""Plugin's hooks and commands definitions."""

import functools
import io
import mimetypes
import os
import random
import re

import bs4
import requests
import simplebot
from cachelib import BaseCache, FileSystemCache, NullCache
from pkg_resources import DistributionNotFound, get_distribution
from simplebot import DeltaBot
from simplebot.bot import Replies


class Planetaneperiano:
    """Get memes from https://www.planetaneperiano.com"""

    def __init__(self, cache: BaseCache = NullCache()) -> None:
        self.cache = cache
        self.max_page = {
            "general": 950,
            "gamer": 350,
            "otaku": 1300,
        }

    def get(self, category: str) -> dict:
        page = random.randint(1, self.max_page[category])
        url = f"https://www.planetaneperiano.com/neperianadas/latest/{category}?page={page}"
        with session.get(url) as resp:
            resp.raise_for_status()
            soup = bs4.BeautifulSoup(resp.text, "html.parser")
        memes = []
        for div in soup("div", class_="neperianadas"):
            if div.img:
                memes.append((div.img.get("alt"), div.img["src"]))

        desc, url = random.choice(memes)
        if url.startswith("/"):
            url = f"https://www.planetaneperiano.com{url}"
        img, ext = self.cache.get(url) or b"", ""
        if not img:
            with session.get(url) as resp:
                resp.raise_for_status()
                img = resp.content
                ext = _get_ext(resp) or ".jpg"
            self.cache.set(url, (img, ext))
        return dict(text=desc, filename="meme" + ext, bytefile=io.BytesIO(img))


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"
session = requests.Session()
session.headers.update(
    {
        "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }
)
session.request = functools.partial(session.request, timeout=15)  # type: ignore
pnep = Planetaneperiano()


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    _getdefault(bot, "max_meme_size", 1024 * 1024 * 5)


@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    path = os.path.join(os.path.dirname(bot.account.db_path), __name__)
    if not os.path.exists(path):
        os.makedirs(path)
    pnep.cache = FileSystemCache(
        path, threshold=2000, default_timeout=60 * 60 * 24 * 30
    )


@simplebot.command
def planetaneperiano(replies: Replies) -> None:
    """Devuelve un meme al azar de la categoría general de https://www.planetaneperiano.com"""
    replies.add(**pnep.get("general"))


@simplebot.command
def gamer(replies: Replies) -> None:
    """Devuelve un meme al azar de la categoría gamer de https://www.planetaneperiano.com"""
    replies.add(**pnep.get("gamer"))


@simplebot.command
def otaku(replies: Replies) -> None:
    """Devuelve un meme al azar de la categoría otaku de https://www.planetaneperiano.com"""
    replies.add(**pnep.get("otaku"))


@simplebot.command
def cuantarazon(bot: DeltaBot, replies: Replies) -> None:
    """Devuelve un meme al azar de https://m.cuantarazon.com"""
    replies.add(**_get_meme(bot, "https://m.cuantarazon.com/aleatorio/"))


@simplebot.command
def cuantocabron(bot: DeltaBot, replies: Replies) -> None:
    """Devuelve un meme al azar de https://m.cuantocabron.com"""
    replies.add(**_get_meme(bot, "https://m.cuantocabron.com/aleatorio"))


def _get_meme(bot: DeltaBot, url: str) -> dict:
    def _get_image(url: str) -> tuple:
        with session.get(url) as res:
            res.raise_for_status()
            soup = bs4.BeautifulSoup(res.text, "html.parser")
        img = soup("div", class_="storyContent")[-1].img
        return (img["title"], img["src"])

    img = b""
    max_meme_size = int(_getdefault(bot, "max_meme_size"))
    for _ in range(10):
        img_desc, img_url = _get_image(url)
        with session.get(img_url) as resp:
            resp.raise_for_status()
            if len(resp.content) <= max_meme_size:
                img = resp.content
                ext = _get_ext(resp) or ".jpg"
                break
            if not img or len(img) > len(resp.content):
                img = resp.content
                ext = _get_ext(resp) or ".jpg"

    return dict(text=img_desc, filename="meme" + ext, bytefile=io.BytesIO(img))


def _get_ext(resp: requests.Response) -> str:
    disp = resp.headers.get("content-disposition")
    if disp is not None and re.findall("filename=(.+)", disp):
        fname = re.findall("filename=(.+)", disp)[0].strip('"')
    else:
        fname = resp.url.split("/")[-1].split("?")[0].split("#")[0]
    if "." in fname:
        ext = "." + fname.rsplit(".", maxsplit=1)[-1]
    else:
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype == "text/plain":
            ext = ".txt"
        elif ctype == "image/jpeg":
            ext = ".jpg"
        else:
            ext = mimetypes.guess_extension(ctype)
    return ext


def _getdefault(bot: DeltaBot, key: str, value=None) -> str:
    val = bot.get(key, scope=__name__)
    if val is None and value is not None:
        bot.set(key, value, scope=__name__)
        val = value
    return val


class TestPlugin:
    """Online tests"""

    def test_planetaneperiano(self, mocker) -> None:
        msg = mocker.get_one_reply("/planetaneperiano")
        assert msg.filename

    def test_cuantarazon(self, mocker) -> None:
        msg = mocker.get_one_reply("/cuantarazon")
        assert msg.filename

    def test_cuantocabron(self, mocker) -> None:
        msg = mocker.get_one_reply("/cuantocabron")
        assert msg.filename
