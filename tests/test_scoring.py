"""Тесты фильтра. Формулировки — из реальных вакансий (обезличены), на которых агент учился."""

import json
from pathlib import Path

import pytest

from job_agent.scoring import Profile, keyword_pattern, parse_salary_rub, score_vacancy

PROFILE = Profile(**json.loads((Path(__file__).parent.parent / "config" / "profile.example.json").read_text(encoding="utf-8")))


def test_good_ai_implementation_role_passes():
    text = ("Специалист по внедрению ИИ. Задача — найти процессы, где ИИ даёт измеримый эффект, "
            "запустить пилоты и посчитать эффект в деньгах. Формат работы: удалённо. 200 000 – 350 000 ₽")
    v = score_vacancy(text, PROFILE)
    assert v.passed, v
    assert v.score >= 40


def test_rf_only_is_rejected_for_candidate_abroad():
    text = "Менеджер IT-проектов. Удалённо по России. Локация: РФ. 80 000 – 170 000 ₽"
    v = score_vacancy(text, PROFILE)
    assert not v.passed
    assert "только из РФ" in v.reasons


def test_rf_location_with_gph_is_flagged_not_rejected():
    text = "Project Manager внедрение ИИ. Удалённо, локация: РФ. Оформление: ГПХ или ИП. от 150 000 ₽"
    v = score_vacancy(text, PROFILE)
    assert any("ГПХ" in f for f in v.flags)


def test_tech_heavy_role_is_not_passed():
    text = "Delivery manager. Удалённо. Понимание CI/CD, Kubernetes, ветвление, feature flags. Координация релизов."
    v = score_vacancy(text, PROFILE)
    assert not v.passed
    assert any("техническая" in f for f in v.flags)


def test_high_english_is_flagged():
    text = "AI Project Manager. Remote. English C1 for negotiations with US clients. 250 000 ₽"
    v = score_vacancy(text, PROFILE)
    assert any("английский" in f for f in v.flags)


def test_low_salary_rejected():
    v = score_vacancy("Менеджер проектов, удалённо, автоматизация. до 70 000 ₽", PROFILE)
    assert not v.passed


def test_ads_and_resumes_are_skipped():
    assert not score_vacancy("Бесплатный вебинар: как стать AI Project Manager", PROFILE).passed
    assert not score_vacancy("#резюме #opentowork Project Manager, удалённо, от 150 000 ₽", PROFILE).passed


def test_office_only_rejected():
    v = score_vacancy("Руководитель проектов внедрения ИИ. Работа в офисе в центре Москвы.", PROFILE)
    assert not v.passed


@pytest.mark.parametrize("text,expected", [
    ("от 200 000 ₽", 200_000),
    ("180 000 – 250 000 ₽ на руки", 250_000),
    ("зарплата 150к", 150_000),
    ("ЗП не указана", None),
])
def test_parse_salary(text, expected):
    assert parse_salary_rub(text) == expected


def test_short_keywords_match_whole_words_only():
    assert keyword_pattern("ии").search("внедрение ИИ в процессы")
    assert not keyword_pattern("ии").search("крупной компании")
    assert keyword_pattern("внедрени").search("Внедрения")
