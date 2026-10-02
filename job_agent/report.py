"""Отчёт-шортлист в Markdown: что прошло фильтр и почему."""

from __future__ import annotations

from .scoring import Verdict
from .telegram import Post


def first_line(text: str, limit: int = 90) -> str:
    line = next((l.strip() for l in text.splitlines() if l.strip()), "")
    return line if len(line) <= limit else line[: limit - 1] + "…"


def build_shortlist(items: list[tuple[Post, Verdict]], top: int = 25) -> str:
    passed = sorted((x for x in items if x[1].passed), key=lambda x: -x[1].score)[:top]
    review = [x for x in items if not x[1].passed and x[1].score >= 40]

    lines = [
        "# Шортлист вакансий",
        "",
        f"Проверено постов: {len(items)} · прошли фильтр: {len(passed)} · на ручную проверку: {len(review)}",
        "",
        "> Перед откликом: таблица соответствия требованиям + сопроводительное письмо → подтверждение человеком.",
        "",
        "| Скор | Вакансия | Флаги | Источник |",
        "|---|---|---|---|",
    ]
    for post, v in passed:
        flags = "; ".join(v.flags) or "—"
        lines.append(f"| {v.score} | {first_line(post.text)} | {flags} | [{post.channel}]({post.url}) |")
    if review:
        lines += ["", "## Похоже на профиль, но есть стоп-флаги", ""]
        for post, v in review:
            lines.append(f"- {first_line(post.text)} — {'; '.join(v.flags)} ([ссылка]({post.url}))")
    return "\n".join(lines) + "\n"
