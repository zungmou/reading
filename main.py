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


async def create_tasks(callback):
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
    # audio_filename = f"./audios/{date_title}.mp3"

    # 将所有的 <p>内容</p> 替换为 <p>内容</p>\n\n
    content = re.sub(
        r"<p>(.*?)</p>", r"<p>\1</p>\n\n", content, flags=re.S | re.IGNORECASE
    )
    content = clean_p(content)

    # if not os.path.exists(audio_filename):
    # 将待转换的纯文本写入临时文件
    # with open("tts.txt", "w", encoding="utf-8") as f:
    #     f.write(html.unescape(clean_html(content)))

    # 创建音频文件夹
    # os.makedirs("audios", exist_ok=True)

    # 调用 Python 子进程执行 TTS 转换
    # subprocess.run(
    #     [
    #         "python",
    #         "tts.py",
    #         "-f",
    #         "tts.txt",
    #         "-m",
    #         "zh-CN-YunyangNeural",
    #         "-o",
    #         audio_filename,
    #     ],
    #     shell=True,
    # )

    # 删除临时文件
    # os.remove("tts.txt")

    # content += f'<audio id="audio" src="/reading/audios/{urllib.parse.quote(date_title)}.mp3"></audio>\n\n'
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


async def scrape(session: aiohttp.ClientSession):
    assert isinstance(session, aiohttp.ClientSession)

    async def scrape_article(url: str, referer: str, date: datetime.date):
        assert isinstance(url, str)
        assert isinstance(referer, str)
        assert isinstance(date, datetime.date)

        async def fetch():
            async with http_request(session, url, referer=referer) as resp:
                return await resp.text()

        text = await fetch()

        if match := re.search(r"<h1>(.*?)</h1>", text, flags=re.S | re.IGNORECASE):
            title = match.group(1)
            title = title.strip()
            title = re.sub(r"<[^>]*?>", "", title)
            title = title.strip()
        else:
            title = "未知标题"

        del match

        # 查找 p.sec 代码块
        sec = '<p class="sec">(.*?)</p>'
        sec = re.search(sec, text, flags=re.S | re.IGNORECASE)

        match sec:
            case re.Match():
                sec = sec.group(1)
                sec = clean_comment(sec)

                # 查找第一个 < 符号前的所有字符
                author = "(.*?)<"
                author = re.search(author, sec, flags=re.S | re.IGNORECASE)

                match author:
                    case re.Match():
                        author = author.group(1).strip()
                        author = re.sub(r"\s*", "", author)

                    case _:
                        raise ValueError("无法解析作者")

                # 查找 span.date 代码块
                date = r'<span class="date">(.*)</span>'
                date = re.search(date, sec, flags=re.S | re.IGNORECASE)

                match date:
                    case re.Match():
                        date = date.group(1).strip()
                        date = clean_html(date)
                        date = edition = (
                            date.replace("\r", "")
                            .replace("\n", "")
                            .replace("&nbsp;", "")
                            .replace(" ", "")
                        )
                        date = date[date.find("（") + 1 : date.find("）")]
                        date = date[: date.find("第")]
                        date = datetime.datetime.strptime(date, "%Y年%m月%d日").date()

                    case _:
                        raise ValueError("无法解析日期")

            case _:
                raise ValueError("无法解析文章页")

        match date:
            case d if d <= datetime.date(2024, 11, 30):
                if match := re.search(
                    r'<div style="display:none" id="articleContent">(.*?)</div>',
                    text,
                    flags=re.S | re.IGNORECASE,
                ):
                    article = match.group(1)
                    article = clean_comment(article)
                    article = article.strip()
                    attachments = ""

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
                            attachments += f'<p><img src="{image_url}"></p>'
                            attachments += f"<p>{image_desc}</p>" if image_desc else ""

                        del image_match

                    article = attachments + article

            case _:
                # 查找 div.attachment 代码块
                attachment = r'<div class="attachment">(.*)</div>.*?<div id="ozoom">'
                attachment = re.search(attachment, text, flags=re.S | re.IGNORECASE)
                attachments = []

                match attachment:
                    case re.Match():
                        attachment = attachment.group(1)
                        attachment = clean_comment(attachment)

                        # 查找 <img...</div> 代码块
                        imgs = r'<img src="(.*?)".*?</div>'
                        imgs = re.finditer(imgs, attachment, flags=re.S | re.IGNORECASE)

                        for img in imgs:
                            src = img.group(1)
                            src = urllib.parse.urljoin(url, src)
                            src = urllib.parse.quote(src, safe=":/")
                            src = f"https://wsrv.nl/?url={src}"
                            attachments.append(f'<p><img src="{src}"></p>')

                            att_content = '<div class="att-content">(.*?)</div>'
                            att_content = re.search(
                                att_content, img.group(0), flags=re.S | re.IGNORECASE
                            )
                            match att_content:
                                case re.Match():
                                    att_content = att_content.group(1)
                                    att_content = clean_comment(att_content)
                                    att_content = clean_u3000(att_content)
                                    attachments.append(att_content)
                                case _:
                                    raise ValueError("无法解析附件描述")
                    case _:
                        # 没有附件
                        pass

                attachments = "".join(attachments)

                # 查找 div#ozoom 代码块
                ozoom = r'<div id="ozoom">(.*?)</div>'
                ozoom = re.search(ozoom, text, flags=re.S | re.IGNORECASE)

                match ozoom:
                    case re.Match():
                        ozoom = ozoom.group(1)
                        ozoom = re.sub(
                            "</?html>", "", ozoom, flags=re.S | re.IGNORECASE
                        )
                        ozoom = re.sub(
                            "</?head>", "", ozoom, flags=re.S | re.IGNORECASE
                        )
                        ozoom = re.sub(
                            "</?body>", "", ozoom, flags=re.S | re.IGNORECASE
                        )
                        ozoom = clean_comment(ozoom)
                        ozoom = ozoom.strip()
                        article = attachments + ozoom
                    case _:
                        raise ValueError("无法解析正文")

        save_to_reading(title, author, date, edition, article)

    async def scrape_articles(edition: str, referer: str, date: datetime.date):
        assert isinstance(edition, str)
        assert isinstance(referer, str)
        assert isinstance(date, datetime.date)

        async def fetch():
            async with http_request(session, edition, referer=referer) as resp:
                return await resp.text()

        def iter_items(text: str):
            assert isinstance(text, str)

            match date:
                case d if d <= datetime.date(2024, 11, 30):
                    pattern = (
                        r"<a href=("
                        + b64text("bncuRDExMDAwMHJlbm1yYl8=")
                        + r"\d{8}_\d{1,2}-\d{2}.htm)>(.*?)</a>"
                    )

                case _:
                    pattern = (
                        r'<a href="('
                        + b64text("W14iXStjb250ZW50Xw==")
                        + r'\d{8}.html)">(.*?)</a>'
                    )

            items = re.finditer(pattern, text, flags=re.S | re.IGNORECASE)
            items = map(lambda x: (x.group(1), x.group(2).strip()), items)
            items = map(lambda x: (urllib.parse.urljoin(edition, x[0]), x[1]), items)
            items = filter(lambda x: x[1] not in (b64text("5Zu+54mH5oql6YGT"),), items)
            items = filter(
                lambda x: not x[1].startswith(b64text("5pys54mI6LSj57yW")), items
            )

            return items

        for url, title in iter_items(await fetch()):
            logger.info(f"文章 | {title} - {url}")
            await scrape_article(url, edition, date=date)

    def get_home_url(date: datetime.date):
        assert isinstance(date, datetime.date)

        match date:
            case d if d <= datetime.date(2024, 11, 30):
                url = "aHR0cDovL3BhcGVyLnBlb3BsZS5jb20uY24vcm1yYi9odG1sL3swfS9uYnMuRDExMDAwMHJlbm1yYl8wMS5odG0="
                url = b64text(url)
                url = url.format(date.strftime("%Y-%m/%d"))
            case _:
                url = "aHR0cDovL3BhcGVyLnBlb3BsZS5jb20uY24vcm1yYi9wYy9sYXlvdXQvezB9L25vZGVfMDEuaHRtbA=="
                url = b64text(url)
                url = url.format(date.strftime("%Y%m/%d"))

        return url

    async def fetch_home(date: datetime.date):
        assert isinstance(date, datetime.date)

        url = get_home_url(date=date)
        referer = "aHR0cDovL3BhcGVyLnBlb3BsZS5jb20uY24vcm1yYi9wYXBlcmluZGV4Lmh0bQ=="
        referer = b64text(referer)

        async with http_request(session, url, referer=referer) as resp:
            return await resp.text()

    def iter_editions(home_url: str, text: str, date: datetime.date):
        assert isinstance(home_url, str)
        assert isinstance(text, str)
        assert isinstance(date, datetime.date)

        match date:
            case d if d <= datetime.date(2024, 11, 30):
                pattern = r"<a id=pageLink href=(.*?)>(.*?)</a>"
            case _:
                pattern = r'<a id="pageLink" href="(.*?)">(.*?)</a>'

        items = re.finditer(pattern, text, flags=re.S)
        items = map(lambda x: (x.group(1), x.group(2)), items)
        items = map(lambda x: (urllib.parse.urljoin(home_url, x[0]), x[1]), items)
        items = filter(
            lambda x: x[1].endswith(b64text("5Ymv5YiK")),
            items,
        )
        items = map(lambda x: x[0], items)

        return items

    date = datetime.date(2024, 12, 1)  # - datetime.timedelta(days=1)

    while date <= datetime.date.today():
        logger.info(f'正在爬取 {date.strftime("%Y-%m-%d")} 的报纸')
        home = get_home_url(date=date)

        for edition in iter_editions(home, await fetch_home(date), date=date):
            await scrape_articles(edition, home, date=date)

        date = date + datetime.timedelta(days=1)


async def main():
    await asyncio.gather(*[create_tasks(scrape)])


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
