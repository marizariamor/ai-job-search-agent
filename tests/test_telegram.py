from job_agent.report import build_shortlist
from job_agent.scoring import Profile, score_vacancy
from job_agent.telegram import fetch_channel, parse_channel_page

PAGE = """
<div class="tgme_widget_message_wrap"><div data-post="demo_jobs/102">
<div class="tgme_widget_message_text js-message_text">Специалист по <b>внедрению ИИ</b><br/>Удалённо, от 200 000 ₽</div>
<time datetime="2026-09-28T10:00:00+00:00"></time></div></div>
<div class="tgme_widget_message_wrap"><div data-post="demo_jobs/101">
<div class="tgme_widget_message_text js-message_text">Бесплатный вебинар по карьере</div>
<time datetime="2026-09-20T10:00:00+00:00"></time></div></div>
"""


def test_parse_channel_page():
    posts = parse_channel_page(PAGE)
    assert [p.post_id for p in posts] == [102, 101]
    assert posts[0].text.startswith("Специалист по внедрению ИИ\nУдалённо")
    assert posts[0].url == "https://t.me/demo_jobs/102"
    assert posts[0].date == "2026-09-28"


def test_fetch_stops_at_since_date():
    calls = []

    def fake_get(url):
        calls.append(url)
        return PAGE

    posts = fetch_channel("demo_jobs", since="2026-09-25", get=fake_get, pause=0)
    assert [p.post_id for p in posts] == [102]
    assert len(calls) == 1


def test_shortlist_contains_passed_vacancy():
    profile = Profile(target_keywords={"внедрени": 20, "ии": 15})
    posts = parse_channel_page(PAGE)
    md = build_shortlist([(p, score_vacancy(p.text, profile)) for p in posts])
    assert "Специалист по внедрению ИИ" in md
    assert "вебинар" not in md
