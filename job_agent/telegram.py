"""Сбор вакансий из публичных Telegram-каналов через веб-превью t.me/s/<канал>.

Не требует входа в Telegram и токенов: читаются только открытые каналы.
"""

from __future__ import annotations

import html
import re
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable

USER_AGENT = "Mozilla/5.0 (job-search-agent; personal use)"


@dataclass(frozen=True)
class Post:
    channel: str
    post_id: int
    date: str  # YYYY-MM-DD
    text: str

    @property
    def url(self) -> str:
        return f"https://t.me/{self.channel}/{self.post_id}"


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "ignore")


def parse_channel_page(page: str) -> list[Post]:
    """Разбирает HTML страницы t.me/s/<канал> в список постов."""
    posts = []
    for block in re.split(r'<div class="tgme_widget_message_wrap', page)[1:]:
        ref = re.search(r'data-post="([^"/]+)/(\d+)"', block)
        if not ref:
            continue
        body = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
        date = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', block)
        text = ""
        if body:
            text = re.sub(r"<br\s*/?>", "\n", body.group(1))
            text = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
        posts.append(Post(ref.group(1), int(ref.group(2)), date.group(1) if date else "", text))
    return posts


def fetch_channel(
    channel: str,
    since: str,
    max_pages: int = 8,
    get: Callable[[str], str] = http_get,
    pause: float = 0.5,
) -> list[Post]:
    """Листает канал назад, пока не дойдёт до даты since (включительно)."""
    collected: list[Post] = []
    before = None
    for _ in range(max_pages):
        url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
        page_posts = parse_channel_page(get(url))
        if not page_posts:
            break
        collected.extend(p for p in page_posts if not p.date or p.date >= since)
        oldest = min(page_posts, key=lambda p: p.post_id)
        if oldest.date and oldest.date < since:
            break
        before = oldest.post_id
        time.sleep(pause)
    unique = {p.post_id: p for p in collected}
    return sorted(unique.values(), key=lambda p: p.post_id, reverse=True)
