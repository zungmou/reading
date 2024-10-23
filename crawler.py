import asyncio
import base64
import contextlib
import datetime
import html
import logging
import os
import re
import subprocess
import traceback
import urllib.parse

import aiohttp

logger = logging.getLogger(__name__)


# 定义一个清理 <!-- 与 --> 之间的内容的函数
def clean_comment(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


# 定义一个清理 p 段落中开头的全角空格的函数
def clean_p(text: str) -> str:
    return re.sub(r"<p>　*", "<p>", text, flags=re.S | re.IGNORECASE)


# 定义一个清理文本中所有 \u3000 的函数
def clean_u3000(text: str) -> str:
    return text.replace("\u3000", "")


# 定义一个将 base64 解码为文本的函数
def b64text(s: str) -> str:
    return base64.b64decode(s).decode("utf-8")


# 定义一个将文本编码为 base64 的函数
def textb64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("utf-8")


# 定义一个清理所有 HTML 标签的函数
def clean_html(text: str) -> str:
    return re.sub(r"<.*?>", "", text, flags=re.S | re.IGNORECASE)


async def create_crawl_task(callback):
    headers = {
        "UserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            await callback(session)
        except:
            logger.error(traceback.format_exc())


@contextlib.asynccontextmanager
async def http_request(
    session: aiohttp.ClientSession,
    url: str,
    method: str = "GET",
    referer: str = None,
    **kwargs,
):
    assert isinstance(session, aiohttp.ClientSession)
    assert isinstance(url, str)
    assert isinstance(method, str)

    headers: dict = kwargs.get("headers", {})

    if referer:
        headers.setdefault("Referer", referer)

    async with session.request(method, url, **kwargs) as response:
        response.raise_for_status()
        yield response


def save_to_reading(
    title: str, author: str, date: datetime.date, edition: str, content: str
):
    assert isinstance(title, str)
    assert isinstance(author, str)
    assert isinstance(date, datetime.date)
    assert isinstance(edition, str)
    assert isinstance(content, str)

    # 将日期与标题拼接
    date_title = date.strftime("%Y-%m-%d-") + title

    # 生成音频文件名
    audio_filename = f"./audios/{date_title}.mp3"

    # 将所有的 <p>内容</p> 替换为 <p>内容</p>\n\n
    content = re.sub(
        r"<p>(.*?)</p>", r"<p>\1</p>\n\n", content, flags=re.S | re.IGNORECASE
    )
    content = clean_p(content)

    if not os.path.exists(audio_filename):
        # 将待转换的纯文本写入临时文件
        with open("tts.txt", "w", encoding="utf-8") as f:
            f.write(html.unescape(clean_html(content)))

        # 创建音频文件夹
        os.makedirs("audios", exist_ok=True)

        # 调用 Python 子进程执行 TTS 转换
        subprocess.run(
            [
                "python",
                "tts.py",
                "-f",
                "tts.txt",
                "-m",
                "zh-CN-YunyangNeural",
                "-o",
                audio_filename,
            ]
        )

        # 删除临时文件
        os.remove("tts.txt")

    content += f'<audio id="audio" src="/reading/audios/{urllib.parse.quote(date_title)}.mp3"></audio>\n\n'
    post_content = (
        f"""---
layout: post
title: "{title}"
author: "{author}"
source: "{edition}"
comments: true
---\n\n"""
        + content
    )

    with open(f"./_posts/{date_title}.html", "w", encoding="utf-8") as f:
        f.write(post_content)


async def crawl(session: aiohttp.ClientSession):
    assert isinstance(session, aiohttp.ClientSession)

    async def crwal_article(url: str, referer: str):
        assert isinstance(url, str)
        assert isinstance(referer, str)

        async with http_request(session, url, referer=referer) as response:
            text = await response.text()

            if match := re.search(r"<h1>(.*?)</h1>", text, flags=re.S | re.IGNORECASE):
                title = match.group(1)
                title = title.strip()
                title = re.sub(r"<[^>]*?>", "", title)
            else:
                title = "未知标题"

            del match

            if match := re.search(
                r'<p class="sec">(.*?)</p>', text, flags=re.S | re.IGNORECASE
            ):
                p_sec = match.group(1)
                p_sec = clean_comment(p_sec)

                if match2 := re.search(
                    r'(.*?)<span class="date">(.*?)</span>',
                    p_sec,
                    flags=re.S | re.IGNORECASE,
                ):
                    author = match2.group(1).strip()
                    author = re.sub(r"\s*", "", author)
                    edition = match2.group(2)
                    edition = (
                        edition.replace("\r", "")
                        .replace("\n", "")
                        .replace("&nbsp;", "")
                        .replace(" ", "")
                    )
                    date = edition[edition.find("（") + 1 : edition.find("）")]
                    date = date[: date.find("第")]
                    date = datetime.datetime.strptime(date, "%Y年%m月%d日").date()
                    del match2
                else:
                    # 没有搜索到作者和日期
                    return

                del match, p_sec
            else:
                # 没有搜索到包含作者和日期的内容块
                return

            if match := re.search(
                r'<div style="display:none" id="articleContent">(.*?)</div>',
                text,
                flags=re.S | re.IGNORECASE,
            ):
                article = match.group(1)
                article = clean_comment(article)
                article = article.strip()
                images = ""

                for item_match in re.finditer(
                    r'<TABLE class="pci_c" width="400">(.*?)</TABLE>',
                    text,
                    flags=re.S | re.IGNORECASE,
                ):
                    if image_match := re.search(
                        r'<td align="center"><img src="(.*?)"></td>.*?<p>(.*?)</p>',
                        item_match.group(1),
                        flags=re.S | re.IGNORECASE,
                    ):
                        image_url = image_match.group(1)
                        image_url = urllib.parse.urljoin(url, image_url)
                        image_url = urllib.parse.quote(image_url, safe=":/")
                        image_url = f"https://wsrv.nl/?url={image_url}"
                        image_desc = image_match.group(2)
                        image_desc = clean_u3000(image_desc)
                        images += f'<p><img src="{image_url}"></p>'
                        images += f"<p>{image_desc}</p>" if image_desc else ""

                    del image_match

                article = images + article
                save_to_reading(title, author, date, edition, article)

    async def crawl_list(url: str, referer: str):
        assert isinstance(url, str)
        assert isinstance(referer, str)

        async with http_request(session, url, referer=referer) as resp_c:
            text = await resp_c.text()

            for match in re.finditer(
                r"<a href=("
                + b64text("bncuRDExMDAwMHJlbm1yYl8=")
                + r"\d{8}_\d{1,2}-\d{2}.htm)>(.*?)</a>",
                text,
                flags=re.S | re.IGNORECASE,
            ):
                article_url = urllib.parse.urljoin(url, match.group(1))
                article_title = match.group(2)
                article_title = article_title.strip()

                if article_title in (b64text("5Zu+54mH5oql6YGT"),):
                    continue

                if article_title.startswith(b64text("5pys54mI6LSj57yW")):
                    continue

                logger.info(f"文章 | {article_title} - {article_url}")
                await crwal_article(article_url, url)

                del match, article_url, article_title

    referer = b64text(
        "aHR0cDovL3BhcGVyLnBlb3BsZS5jb20uY24vcm1yYi9wYXBlcmluZGV4Lmh0bQ=="
    )
    start_date = datetime.date.today()
    end_date = start_date - datetime.timedelta(days=1)  # datetime.date(2023, 11, 25)  #

    while start_date >= end_date:

        logger.info(f'正在爬取 {start_date.strftime("%Y-%m-%d")} 的报纸')
        daily_url = b64text(
            "aHR0cDovL3BhcGVyLnBlb3BsZS5jb20uY24vcm1yYi9odG1sL3swfS9uYnMuRDExMDAwMHJlbm1yYl8wMS5odG0="
        ).format(start_date.strftime("%Y-%m/%d"))

        async with http_request(session, daily_url, referer=referer) as resp_b:
            text = await resp_b.text()

            for match in re.finditer(
                r"<a id=pageLink href=(.*?)>(.*?)</a>", text, flags=re.S
            ):
                edition_url = urllib.parse.urljoin(daily_url, match.group(1))
                edition_title = match.group(2)

                if not edition_title.endswith(b64text("5Ymv5YiK")):
                    continue

                await crawl_list(edition_url, daily_url)

                del match, edition_url, edition_title

            del resp_b, text

        start_date = start_date - datetime.timedelta(days=1)


async def main():
    await asyncio.gather(*[create_crawl_task(crawl)])


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        event_loop = asyncio.get_event_loop()
        event_loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
