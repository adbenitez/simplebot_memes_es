import io
import mimetypes
import re

import bs4
import requests
import simplebot
from simplebot import DeltaBot
from simplebot.bot import Replies

__version__ = "1.0.0"
HEADERS = {
    "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0)"
    " Gecko/20100101 Firefox/60.0"
}


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    _getdefault(bot, "max_meme_size", 1024 * 1024 * 5)


@simplebot.command
def cuantarazon(bot: DeltaBot, replies: Replies) -> None:
    """Devuelve un meme al azar de https://m.cuantarazon.com"""
    replies.add(**_get_meme(bot, "https://m.cuantarazon.com/aleatorio/"))


@simplebot.command
def cuantocabron(bot: DeltaBot, replies: Replies) -> None:
    """Devuelve un meme al azar de https://m.cuantocabron.com"""
    replies.add(**_get_meme(bot, "https://m.cuantocabron.com/aleatorio"))


def _get_image(url: str) -> tuple:
    with requests.get(url, headers=HEADERS) as res:
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, "html.parser")
    img = soup("div", class_="storyContent")[-1].img
    return (img["title"], img["src"])


def _get_meme(bot: DeltaBot, url: str) -> dict:
    img = b""
    max_meme_size = int(_getdefault(bot, "max_meme_size"))
    for _ in range(10):
        img_desc, img_url = _get_image(url)
        with requests.get(img_url, headers=HEADERS) as r:
            r.raise_for_status()
            if len(r.content) <= max_meme_size:
                img = r.content
                ext = _get_ext(r) or ".jpg"
                break
            if not img or len(img) > len(r.content):
                img = r.content
                ext = _get_ext(r) or ".jpg"

    text = "{}\n\n{}".format(img_desc, img_url)
    return dict(text=text, filename="meme" + ext, bytefile=io.BytesIO(img))


def _get_ext(r) -> str:
    d = r.headers.get("content-disposition")
    if d is not None and re.findall("filename=(.+)", d):
        fname = re.findall("filename=(.+)", d)[0].strip('"')
    else:
        fname = r.url.split("/")[-1].split("?")[0].split("#")[0]
    if "." in fname:
        ext = "." + fname.rsplit(".", maxsplit=1)[-1]
    else:
        ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
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
    def test_cuantarazon(self, mocker):
        msg = mocker.get_one_reply("/cuantarazon")
        assert msg.filename
        # assert msg.is_image()

    def test_cuantocabron(self, mocker):
        msg = mocker.get_one_reply("/cuantocabron")
        assert msg.filename
        # assert msg.is_image()
