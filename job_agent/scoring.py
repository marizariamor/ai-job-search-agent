"""Фильтрация и скоринг вакансий по профилю кандидата.

Правила выросли из реальных отказов (см. README → «Чему научили отказы»):
- вакансии «только из РФ» отсеиваются, если кандидат живёт за рубежом и нет ГПХ/ИП;
- роли, где главное — код, CI/CD или архитектура, отсеиваются для профиля «аналитик / менеджер внедрения»;
- требования к английскому выше уровня кандидата помечаются.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RE_AD = re.compile(r"курс|вебинар|мастер-класс|бесплатн\w* урок|буткемп|регистрируй|промокод|розыгрыш", re.I)
RE_RESUME = re.compile(r"#резюме|#resume|#cv\b|#ищуработу|#opentowork", re.I)
RE_REMOTE = re.compile(r"удал[её]нн?|удаленк|удалёнк|remote|из любой (точки|страны)|релокац", re.I)
RE_RF_ONLY = re.compile(
    r"только (из |в )?(рф|росси)|локаци[яи]:?\s*рф|удал[её]нно по (рф|россии)|"
    r"находиться в (рф|россии)|налоговы\w* резидент\w* рф",
    re.I,
)
RE_GPH = re.compile(r"гпх|самозанят|\bип\b|договор подряда|contractor|b2b", re.I)
RE_OFFICE_ONLY = re.compile(r"\bофис\b|на месте работодателя|в офисе", re.I)  # проверяется, только если нет «удалённо»
RE_ENGLISH_HIGH = re.compile(r"\b(B2|C1|C2)\b|upper[- ]intermediate|fluent|advanced english", re.I)
RE_TECH_HEAVY = re.compile(
    r"\bpython\b.*(уверенн|хорош|опыт разработ)|ci/cd|kubernetes|docker|микросервис|"
    r"langchain|langgraph|backend|frontend|fullstack|разработчик|developer|engineer",
    re.I,
)
RE_SALARY = re.compile(
    r"(?:от\s*)?(\d[\d\s ]{2,})(?:\s*[–-]\s*(\d[\d\s ]{2,}))?\s*(?:₽|руб|р\.|k\b|к\b|тыс)",
    re.I,
)


@dataclass
class Profile:
    target_keywords: dict[str, int]       # ключевое слово -> вес
    lives_abroad: bool = True
    can_contract: bool = True              # ГПХ / самозанятость / ИП
    english_level: str = "A2"
    min_salary_rub: int = 100_000
    skip_tech_heavy: bool = True


@dataclass
class Verdict:
    score: int
    passed: bool
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    salary_rub: int | None = None


def parse_salary_rub(text: str) -> int | None:
    """Верхняя граница вилки в рублях, если указана (для сравнения с минимальным порогом)."""
    best = None
    for m in RE_SALARY.finditer(text):
        nums = [int(re.sub(r"\D", "", g)) for g in m.groups() if g]
        if not nums:
            continue
        value = max(nums)
        unit = m.group(0).lower()
        if ("k" in unit or "к" in unit.split()[-1] or "тыс" in unit) and value < 10_000:
            value *= 1000
        if value >= 10_000:
            best = max(best or 0, value)
    return best


def keyword_pattern(kw: str) -> re.Pattern:
    """Короткие слова (ИИ, AI, BI, KPI) — только целиком, чтобы «ии» не находилось в «компании».
    Длинные — как основа слова: «внедрени» найдёт «внедрение», «внедрения»."""
    body = re.escape(kw)
    tail = r"\b" if len(kw) <= 4 else ""
    return re.compile(rf"(?<![\w]){body}{tail}", re.I)


def score_vacancy(text: str, profile: Profile) -> Verdict:
    reasons: list[str] = []
    flags: list[str] = []

    if RE_AD.search(text[:400]):
        return Verdict(0, False, ["реклама курса или мероприятия"])
    if RE_RESUME.search(text):
        return Verdict(0, False, ["это резюме кандидата, а не вакансия"])

    score = 0
    for kw, weight in profile.target_keywords.items():
        if keyword_pattern(kw).search(text):
            score += weight
            reasons.append(f"+{weight} «{kw}»")

    remote = bool(RE_REMOTE.search(text))
    if remote:
        score += 15
        reasons.append("+15 удалённо")
    elif RE_OFFICE_ONLY.search(text):
        return Verdict(0, False, ["только офис"])

    if profile.lives_abroad and RE_RF_ONLY.search(text):
        if profile.can_contract and RE_GPH.search(text):
            flags.append("локация РФ, но есть ГПХ/ИП — уточнить")
        else:
            return Verdict(0, False, ["только из РФ"])

    if profile.skip_tech_heavy and RE_TECH_HEAVY.search(text):
        score -= 30
        flags.append("техническая роль: код / CI/CD / разработка")

    if RE_ENGLISH_HIGH.search(text) and profile.english_level in ("A1", "A2", "B1"):
        score -= 20
        flags.append(f"английский выше {profile.english_level}")

    salary = parse_salary_rub(text)
    if salary is not None and salary < profile.min_salary_rub:
        return Verdict(0, False, [f"зарплата до {salary:,} ₽ ниже порога".replace(",", " ")], salary_rub=salary)

    passed = score >= 40 and not any("техническая" in f for f in flags)
    return Verdict(max(0, min(score, 100)), passed, reasons, flags, salary)
