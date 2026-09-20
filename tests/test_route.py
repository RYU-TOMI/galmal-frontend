# -*- coding: utf-8 -*-
"""노선 페이지가 만드는 것 중 **틀려도 화면이 멀쩡한 것들** (BACKLOG B55).

`site/route.py` · `fmt.py` · `seo.py` 에는 테스트가 없었다. 산출물은 맞았다(2026-09-19 중간점검 — 36장 전수 대조로
불일치 0). 없던 것은 **고칠 때 지켜 줄 것**이다. 여기 모은 것은 전부 같은 얼굴을 하고 있다 — 예외도 안 나고
페이지도 나가고 사람만 모른다:

  | 무엇 | 틀리면 |
  |---|---|
  | 구독 `mailto:` | 구독이 실패하는 게 아니라 **「전 노선 구독」이 된다** — 파서가 코드를 못 찾으면 `ALL` 이다 |
  | `machine_date()` | sitemap·`dateModified` 가 하루 어긋난다. **실제로 틀렸었다**(2026-09-11, KST 날짜를 UTC 자리에) |
  | 주장의 임계 | 버킷이 하나뿐인데 「9월 출발이 가장 저렴합니다」라고 쓴다(BB28) |
  | `weekday_name()` | 0=일 규약이 어긋나면 **요일이 하루씩 밀린다** — 값은 맞고 이름만 틀린다 |
  | sitemap | 노선이 빠지거나 날짜가 갈려도 XML 은 멀쩡하다 |

픽스처(`fixtures/v1/`)의 실제 노선 36개로도 돌린다 — 손으로 만든 예시 하나가 통과하는 것과 오늘 실린 노선
전부가 통과하는 것은 다른 주장이다.
"""
import glob
import io
import json
import os
import re
import sys
import unittest
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import fmt    # noqa: E402
import route  # noqa: E402
import seo    # noqa: E402
import shell  # noqa: E402

FX = os.path.join(ROOT, "fixtures", "v1")


def _load(*parts):
    with io.open(os.path.join(FX, *parts), encoding="utf-8") as f:
        return json.load(f)


META = _load("meta.json")
INDEX = _load("routes", "index.json")
VOCAB = _load("vocab.json")
ROUTES = {r["code"]: _load("routes", r["code"] + ".json") for r in INDEX["routes"]}

# 🔴 백엔드 파서가 노선을 뽑는 정규식의 **사본**이다(`galmal-backend/collector/subscriptions.py` `ROUTE_RE`).
# 계약(`meta.subscribe`)은 주소·제목·`route_token` 만 주고 **파서가 무엇을 읽는지는 주지 않는다** — 그래서
# 여기 옮겨 적을 수밖에 없다. 사본이라 갈릴 수 있다: 백엔드가 파서를 바꾸면 이 테스트는 초록인데 구독이 깨진다.
# (계약에 넣을지는 기획·백엔드 몫 — BACKLOG B63.)
BACKEND_ROUTE_RE = re.compile(r"\b([A-Z]{3})\s*[-→~]\s*([A-Z]{3})\b")


def _mailto_parts(href):
    assert href.startswith("mailto:")
    addr, _, query = href[len("mailto:"):].partition("?")
    q = urllib.parse.parse_qs(query, keep_blank_values=True, strict_parsing=True)
    return addr, q["subject"][0], q["body"][0]


def _first_route(text):
    m = BACKEND_ROUTE_RE.search(text or "")
    return "%s-%s" % m.groups() if m else None


class SubscribeLinkTest(unittest.TestCase):
    """메일 본문의 노선 표기는 표시가 아니라 **전선 규약**이다."""

    def test_parts_come_from_the_contract(self):
        addr, subject, body = _mailto_parts(route.subscribe_link(META["subscribe"], "ICN-FUK", "인천 → 후쿠오카"))
        self.assertEqual(addr, META["subscribe"]["address"])
        self.assertEqual(subject, META["subscribe"]["subject_subscribe"])
        self.assertIn("ICN-FUK", body)

    def test_every_real_route_parses_to_its_own_code(self):
        """픽스처의 노선 전부 — 파서가 **처음 찾는** 코드가 그 노선이어야 한다(`search` 는 첫 매치를 쓴다)."""
        self.assertGreaterEqual(len(ROUTES), 30)
        wrong = []
        for code, r in ROUTES.items():
            label = "%s → %s" % (r["o_name"], r["d_name"])
            _, subject, body = _mailto_parts(route.subscribe_link(META["subscribe"], code, label))
            got = _first_route(subject) or _first_route(body)
            if got != code:
                wrong.append((code, got))
        self.assertEqual(wrong, [])

    def test_subject_carries_no_route(self):
        """제목에 코드가 있으면 파서는 본문을 안 본다 — 제목은 계약 문자열 그대로여야 한다."""
        _, subject, _ = _mailto_parts(route.subscribe_link(META["subscribe"], "ICN-FUK", "인천 → 후쿠오카"))
        self.assertIsNone(_first_route(subject))

    def test_label_cannot_hijack_the_code(self):
        """표시명에 코드처럼 생긴 글자가 있어도 **앞에 오는 것은 진짜 코드**다."""
        _, _, body = _mailto_parts(route.subscribe_link(META["subscribe"], "ICN-FUK", "SEL-NRT 특별 → 도쿄"))
        self.assertEqual(_first_route(body), "ICN-FUK")

    def test_special_characters_survive_the_url(self):
        """`&`·`?`·`#`·줄바꿈이 mailto 쿼리를 깨지 않는다 — 깨지면 본문이 잘려 코드가 사라지고 `ALL` 이 된다."""
        _, subject, body = _mailto_parts(route.subscribe_link(META["subscribe"], "ICN-FUK", "A&B?C#D = 100%"))
        self.assertEqual(subject, META["subscribe"]["subject_subscribe"])
        self.assertIn("A&B?C#D = 100%", body)
        self.assertIn("\n", body)
        self.assertEqual(_first_route(body), "ICN-FUK")

    def test_route_token_is_honoured(self):
        """토큰 모양은 계약이 정한다. 백엔드가 `{code}` 를 `[{code}]` 로 바꾸면 따라가야 한다."""
        sub = dict(META["subscribe"], route_token="[{code}]")
        _, _, body = _mailto_parts(route.subscribe_link(sub, "ICN-FUK", "인천 → 후쿠오카"))
        self.assertIn("[ICN-FUK]", body)

    def test_probe_missing_code_would_mean_all(self):
        """탐침 — 코드가 빠진 본문에서 이 검사가 **정말 아무것도 못 찾는지**. 못 찾으면 백엔드는 `ALL` 로 친다."""
        self.assertIsNone(_first_route("노선: (인천 → 후쿠오카)\n\n이 메일을 그대로 보내주시면 구독이 신청됩니다."))


class MachineDateTest(unittest.TestCase):
    """`generated` 는 KST, 기계용 날짜는 UTC — 앞 10글자를 자르면 하루 어긋난다."""

    def test_morning_kst_is_previous_utc_day(self):
        # 2026-09-20 새 크론 슬롯의 실제 값. KST 아침은 UTC 로 전날이다.
        self.assertEqual(route.machine_date("2026-09-20T07:19:28+09:00"), "2026-09-19")

    def test_afternoon_kst_is_same_utc_day(self):
        self.assertEqual(route.machine_date("2026-09-19T16:04:43+09:00"), "2026-09-19")

    def test_boundary_is_nine_am_kst(self):
        self.assertEqual(route.machine_date("2026-09-20T08:59:59+09:00"), "2026-09-19")
        self.assertEqual(route.machine_date("2026-09-20T09:00:00+09:00"), "2026-09-20")

    def test_probe_slicing_would_be_wrong(self):
        """탐침 — 2026-09-11 까지의 구현(`generated[:10]`)은 아침 발행에서 다른 답을 낸다."""
        g = "2026-09-20T07:19:28+09:00"
        self.assertNotEqual(g[:10], route.machine_date(g))

    def test_offset_is_respected_not_assumed(self):
        self.assertEqual(route.machine_date("2026-09-20T01:00:00+00:00"), "2026-09-20")

    def test_page_and_sitemap_share_the_date(self):
        """노선 페이지 `dateModified` 와 sitemap `lastmod` 는 같은 값이어야 한다 — 갈리면 한쪽만 고쳐진다."""
        day = route.machine_date(META["generated"])
        snap = {"meta": META, "index": INDEX, "vocab": VOCAB, "routes": ROUTES}
        pages = route.build_all(snap)
        sm = seo.sitemap(INDEX, day, ROUTES)
        for name, html_text in pages.items():
            self.assertIn('"dateModified":"%s"' % day, html_text, name)
        self.assertEqual(sm.count("<lastmod>%s</lastmod>" % day), len(INDEX["routes"]) + 1)


class ThresholdTest(unittest.TestCase):
    """임계는 프론트가 가진다 — 하나는 비교가 아니고, 얇은 버킷은 근거가 못 된다."""

    def test_usable_needs_two(self):
        self.assertFalse(route.usable([]))
        self.assertFalse(route.usable([{"x": 1}]))
        self.assertTrue(route.usable([{"x": 1}, {"x": 2}]))

    def test_months_drop_thin_buckets_and_cap_at_ten(self):
        months = [{"m": "2026-%02d" % i, "n": 3 if i != 2 else 2, "price": 100 + i} for i in range(1, 13)]
        shown = route.months_shown(months)
        self.assertNotIn("2026-02", [m["m"] for m in shown])          # n=2 는 빠진다
        self.assertEqual(len(shown), route.MONTH_CAP)
        self.assertEqual([m["m"] for m in shown][:2], ["2026-01", "2026-03"])   # 앞에서부터

    def test_months_arrive_sorted_in_real_data(self):
        """🔴 `months_shown()` 은 **정렬하지 않고** 앞에서 10개를 자른다 — 백엔드가 월 오름차순으로 준다는 전제에 기댄다.
        전제가 깨지면 엉뚱한 달 10개가 조용히 실린다. 코드는 안 고쳤다(BACKLOG B63) — 여기선 전제가 오늘 성립하는지만 본다."""
        unsorted = [c for c, r in ROUTES.items() if [m["m"] for m in r["months"]] != sorted(m["m"] for m in r["months"])]
        self.assertEqual(unsorted, [])

    def test_airlines_sorted_by_price_and_capped(self):
        rows = [{"name": "A%d" % i, "min": 1000 - i, "n": 1} for i in range(12)]
        shown = route.airlines_shown(rows)
        self.assertEqual(len(shown), route.AIRLINE_CAP)
        self.assertEqual([a["min"] for a in shown], sorted(a["min"] for a in shown))
        self.assertEqual(shown[0]["min"], min(a["min"] for a in rows))


def _route(months=(), weekdays=()):
    return {"code": "ICN-FUK", "o_name": "인천", "d_name": "후쿠오카", "region": "JP",
            "summary": {"cheapest": 132536, "median": 306708, "n": 1784},
            "months": list(months), "weekdays": list(weekdays), "airlines": [], "trend": []}


def _render(r):
    return route.render(r, {"routes": []}, META, "2026-09-19", VOCAB["region_name"])[1]


class ClaimTest(unittest.TestCase):
    """문장에도 차트와 **같은** 임계를 건다(BB28) — 예전엔 버킷 하나로 「가장 저렴합니다」라고 썼다."""

    M = [{"m": "2026-09", "n": 5, "price": 200000}, {"m": "2026-10", "n": 5, "price": 180000}]
    W = [{"wd": 1, "n": 5, "price": 150000}, {"wd": 6, "n": 5, "price": 140000}]

    def test_one_bucket_makes_no_claim(self):
        page = _render(_route(months=self.M[:1], weekdays=self.W[:1]))
        self.assertNotIn("가장 저렴합니다", page)
        self.assertNotIn("가장 쌉니다", page)
        self.assertIn("데이터가 쌓이면", page)

    def test_thin_bucket_does_not_count(self):
        """두 달이어도 하나가 `n<3` 이면 비교가 아니다."""
        thin = [self.M[0], dict(self.M[1], n=2)]
        self.assertNotIn("가장 저렴합니다", _render(_route(months=thin)))

    def test_two_buckets_name_the_cheaper_one(self):
        page = _render(_route(months=self.M, weekdays=self.W))
        self.assertIn("<b>10월 출발</b>이 가장 저렴합니다 (180,000원)", page)
        self.assertIn("<b>토요일</b>이 가장 쌉니다 (140,000원)", page)      # wd=6 은 토요일(0=일)

    def test_claim_and_chart_agree_on_every_real_route(self):
        """실제 36장 — 「가장 저렴」 문장이 있는 장은 월 막대 차트도 있고, 없는 장은 차트도 없다."""
        odd = []
        for code, r in ROUTES.items():
            page = _render(r)
            claims = "출발</b>이 가장 저렴합니다" in page
            enough = len(route.months_shown(r["months"])) >= route.MIN_BUCKETS
            if claims != enough:
                odd.append(code)
        self.assertEqual(odd, [])


class FormatTest(unittest.TestCase):

    def test_weekday_is_sunday_zero(self):
        """계약 `weekdays[].wd` 는 0=일 … 6=토(SQL `%w`). 파이썬 `weekday()`(0=월)와 **다르다.**"""
        self.assertEqual([fmt.weekday_name(i) for i in range(7)], list("일월화수목금토"))

    def test_probe_python_convention_would_shift_a_day(self):
        self.assertNotEqual(fmt.weekday_name(0), fmt.WEEKDAY[0])

    def test_weekday_follows_value_not_position(self):
        """응답은 월요일부터 정렬돼 오지만 정본은 `wd` 값이다 — 순서를 뒤섞어도 이름은 값을 따른다."""
        rows = [{"wd": 6}, {"wd": 0}, {"wd": 3}]
        self.assertEqual([fmt.weekday_name(r["wd"]) for r in rows], ["토", "일", "수"])

    def test_real_weekday_values_are_in_range(self):
        bad = [(c, w["wd"]) for c, r in ROUTES.items() for w in r["weekdays"] if w["wd"] not in range(7)]
        self.assertEqual(bad, [])

    def test_date_and_month(self):
        self.assertEqual(fmt.fmt_date("2026-09-19"), "9.19(토)")
        self.assertEqual(fmt.fmt_month("2026-08"), "8월")

    def test_bad_input_does_not_raise(self):
        """빈 값이 와도 빌드가 죽지 않는다 — 다만 빈 문자열을 낸다는 걸 **알고** 쓴다."""
        self.assertEqual(fmt.fmt_date(None), "")
        self.assertEqual(fmt.fmt_month(None), "")
        self.assertEqual(fmt.weekday_name(9), "9")


class CollectDaysTest(unittest.TestCase):
    """`{D}` = 첫 수집일 ~ 마지막 수집일의 **기간**, 상한 `window_days`. 점의 개수가 아니다(COPY.md 🔒)."""

    def _r(self, dates, window=30):
        return {"trend": [{"date": d, "price": 1} for d in dates], "window_days": window}

    def test_span_not_count(self):
        """구멍이 있어도 기간으로 센다 — 3점이지만 09-01~09-19 는 19일이다."""
        self.assertEqual(route.collect_days(self._r(["2026-09-01", "2026-09-10", "2026-09-19"])), 19)

    def test_capped_at_window(self):
        self.assertEqual(route.collect_days(self._r(["2026-08-20", "2026-09-19"])), 30)     # 31일 → 30

    def test_one_day_and_none(self):
        self.assertEqual(route.collect_days(self._r(["2026-09-19"])), 1)
        self.assertEqual(route.collect_days(self._r([])), 0)
        self.assertEqual(route.collect_days({}), 0)

    def test_order_does_not_matter(self):
        self.assertEqual(route.collect_days(self._r(["2026-09-19", "2026-09-01"])), 19)

    def test_every_real_route_is_past_the_floor(self):
        """오늘 실린 노선은 전부 14일을 넘는다 — 이 챕터가 **지금 sitemap 을 안 바꾼다**는 증거."""
        self.assertEqual(sorted(c for c, r in ROUTES.items() if route.thin(r)), [])

    def test_probe_counting_points_would_strand_routes_at_28(self):
        """탐침 — 점 개수로 세면 멀쩡한 노선이 30을 못 채운다(`fetched_date` 구멍)."""
        full = [r for r in ROUTES.values() if route.collect_days(r) == 30]
        self.assertTrue(full)
        self.assertTrue(any(len(r["trend"]) < 30 for r in full))


class SitemapTest(unittest.TestCase):

    NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    def test_home_plus_every_route_once(self):
        root = ET.fromstring(seo.sitemap(INDEX, "2026-09-19", ROUTES).encode("utf-8"))
        locs = [e.text for e in root.findall("s:url/s:loc", self.NS)]
        want = [shell.BASE_URL + "/"] + ["%s/routes/%s.html" % (shell.BASE_URL, r["code"]) for r in INDEX["routes"]]
        self.assertEqual(locs, want)
        self.assertEqual(len(locs), len(set(locs)))

    def test_every_listed_page_is_actually_built(self):
        """sitemap 에 실린 노선과 실제로 구워지는 페이지가 **같은 집합**이다 — 한쪽만 늘면 404 를 광고한다."""
        snap = {"meta": META, "index": INDEX, "vocab": VOCAB, "routes": ROUTES}
        built = set(route.build_all(snap))
        listed = set(r["code"] + ".html" for r in INDEX["routes"])
        self.assertEqual(built, listed)

    def _locs(self, index, routes):
        root = ET.fromstring(seo.sitemap(index, "2026-09-19", routes).encode("utf-8"))
        return [e.text for e in root.findall("s:url/s:loc", self.NS)]

    def test_thin_route_is_built_but_not_submitted(self):
        """수집 14일 미만 노선 — **페이지는 굽고 sitemap 에서만 뺀다.** 새 노선의 첫날은 차트가 전부 빈다."""
        new = dict(ROUTES["ICN-FUK"], code="TAE-CJU", trend=[{"date": "2026-09-19", "price": 98000}])
        index = {"routes": INDEX["routes"] + [dict(INDEX["routes"][0], code="TAE-CJU")]}
        routes = dict(ROUTES, **{"TAE-CJU": new})
        locs = self._locs(index, routes)
        self.assertNotIn("%s/routes/TAE-CJU.html" % shell.BASE_URL, locs)
        self.assertEqual(len(locs), len(INDEX["routes"]) + 1)                 # 기존 노선은 그대로 다 실린다
        snap = {"meta": META, "index": index, "vocab": VOCAB, "routes": routes}
        pages = route.build_all(snap)
        self.assertIn("TAE-CJU.html", pages)                                  # 페이지는 있다
        self.assertIn("/routes/TAE-CJU.html", pages["ICN-FUK.html"])          # 「다른 노선」 링크도 남는다

    def test_route_enters_sitemap_on_day_fourteen(self):
        """경계 — 13일째는 빠지고 14일째에 들어온다. 그리고 **기간**으로 센다(점 2개여도 14일이면 들어온다)."""
        def with_span(days):
            first = "2026-09-%02d" % (19 - days + 1)
            r = dict(ROUTES["ICN-FUK"], code="X", trend=[{"date": first, "price": 1}, {"date": "2026-09-19", "price": 1}])
            return self._locs({"routes": [dict(INDEX["routes"][0], code="X")]}, {"X": r})
        self.assertEqual(len(with_span(13)), 1)      # 홈만
        self.assertEqual(len(with_span(14)), 2)

    def test_index_entry_without_a_response_is_not_submitted(self):
        self.assertEqual(len(self._locs({"routes": [dict(INDEX["routes"][0], code="ZZZ-ZZZ")]}, {})), 1)

    def test_robots_points_at_the_sitemap(self):
        self.assertIn("Sitemap: %s/sitemap.xml" % shell.BASE_URL, seo.robots())


if __name__ == "__main__":
    unittest.main()
