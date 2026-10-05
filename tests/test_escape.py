# -*- coding: utf-8 -*-
"""백엔드가 준 문자열을 그대로 HTML 에 넣지 않는다 — CH11 T1 (B51).

**지금 깨진 것은 0건이다.** 2026-10-05 산출물 **225개가 바이트 동일**하게 나왔다 —
백로그의 「출처가 우리 백엔드라 지금은 해가 없다」를 **검사로 바꾼 것**이 이 파일이다.

⚠️ **재는 중에 자가 틀렸다.** 파이썬 `html.unescape` 로 예약 링크를 재면 **280개가 깨진다**고
나온다(`&currency` → `¤cy`). 그런데 **브라우저에 직접 물으니 속성 안에서는 안 바뀐다** —
HTML5 는 이름 실체 뒤에 영숫자나 `=` 가 오면 historical 규칙으로 통과시킨다.
실제 예약 링크 5개 전부 원본과 같았다. **파이썬은 이 예외를 모른다.**

**그래도 두르는 이유는 본문이다.** 같은 문자열을 본문에 넣으면 **지금도** 바뀐다(브라우저 실측):
  `&currency` → `¤cy` · `&lt=1` → `<=1` · `&copy=2` → `©=2`
도시 이름과 예약처 이름이 본문으로 간다 — **예약처 이름에 `&` 가 하나 들어오는 날**이 그날이다.

🔴 **두르면 안 되는 자리도 있다**: `setAttribute`·`textContent` 는 브라우저가 이미 그대로 넣으므로,
거기 이스케이프를 두르면 화면에 `&amp;` 가 **글자 그대로** 보인다 — 고치려다 만드는 버그다.
"""
import io
import os
import re
import sys
import unittest

B = chr(92)   # 역슬래시를 글자로 적으면 이 파일 자신이 같은 문제를 겪는다
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import home  # noqa: E402

JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CODE = re.sub(r"(?m)^\s*//.*$", "", JS)
TOOL = io.open(os.path.join(ROOT, "tools", "photos.py"), encoding="utf-8").read()


class EscFnTest(unittest.TestCase):
    """`esc()` 한 벌 — 다섯 글자를 다 바꾼다."""

    def test_it_exists_once(self):
        self.assertEqual(CODE.count("function esc(v)"), 1)

    def test_it_covers_all_five(self):
        b = CODE[CODE.index("function esc(v)"):CODE.index("function esc(v)") + 320]
        for pair in ('/&/g, "&amp;"', '/</g, "&lt;"', '/>/g, "&gt;"',
                     '/"/g, "&quot;"', "/'/g, \"&#39;\""):
            self.assertIn(pair, b, pair)

    def test_ampersand_goes_first(self):
        """`&` 를 **먼저** 바꿔야 한다 — 나중에 바꾸면 `&lt;` 의 `&` 가 다시 바뀌어 `&amp;lt;` 가 된다."""
        b = CODE[CODE.index("function esc(v)"):CODE.index("function esc(v)") + 320]
        self.assertLess(b.index('"&amp;"'), b.index('"&lt;"'))

    def test_it_survives_null(self):
        """`c.nights` 는 빈 값일 수 있다 — `String(null)` 이 `"null"` 이 되면 화면에 그 글자가 뜬다."""
        b = CODE[CODE.index("function esc(v)"):CODE.index("function esc(v)") + 320]
        self.assertIn('v == null ? "" : v', b)


class WrappedTest(unittest.TestCase):
    """백엔드 문자열이 HTML 문자열로 가는 자리마다 둘렀나."""

    SITES = [
        'esc(c.n) + "</text>"',                      # 핀 라벨
        'esc(ORIGIN.n) + " 출발</text>"',            # 출발지 라벨
        '<b class="fcity">\' + esc(c.n)',            # 피드 카드
        '<span class="when">\' + esc(c.when)',       # 날짜 칩
        '<span class="cityname">\' + esc(c.n)',      # 사진 위 도시명
        "href=\"/routes/' + esc(c.route)",           # 노선 링크(속성)
        'data-u="\' + esc(l.url)',                   # 예약 링크(속성)
        '<span class="cmp-name">\' + esc(l.name)',   # 예약처 이름(본문)
        '<span class="ovtag">\' + esc(x)',           # 태그(어휘에서 온다)
        'esc(D.origins[k].name)',                    # 출발지 드롭다운
    ]

    def test_every_site_is_wrapped(self):
        for s in self.SITES:
            self.assertIn(s, CODE, s)

    def test_nights_is_wrapped_in_both_cards(self):
        self.assertEqual(CODE.count('esc(c.nights)'), 2, "피드 카드와 상세 둘 다")

    def test_setattribute_is_not_wrapped(self):
        """🔴 **여기 두르면 화면에 `&amp;` 가 글자 그대로 보인다.** 브라우저가 이미 그대로 넣는다."""
        for line in CODE.split("\n"):
            if "setAttribute(" in line or "textContent" in line:
                self.assertNotIn("esc(", line, line.strip()[:80])


class InlineScriptTest(unittest.TestCase):
    """인라인 `<script>` 안의 `</` 를 깬다 — `shell.jsonld_block` 이 이미 하던 것."""

    def test_the_payloads_are_guarded(self):
        with io.open(os.path.join(ROOT, "site", "home.py"), encoding="utf-8") as f:
            src = f.read()
        guard = '.replace("</", "<' + B + B + '/")'
        self.assertEqual(src.count(guard), 3,
                         "payload 넷 중 둘은 공통 inline(), __DEALS·__WORLD 는 따로 둘렀다")
        self.assertNotIn('"<' + B + '/"', src.replace(guard, ""),
                         "역슬래시 하나짜리는 파이썬이 경고하는 꼴이다 — 나중 버전에서 SyntaxError (B82)")
        self.assertIn("deals_json = (deals_json or \"\")", src)
        self.assertIn("world_json = (world_json or \"\")", src)

    def test_a_city_named_like_a_script_tag_cannot_end_it(self):
        """🔴 값 안에 `</script>` 가 들어오면 브라우저가 **거기서 스크립트를 끝낸다** —
        페이지가 통째로 깨지는데 **JSON 자체는 멀쩡해서** `json.loads` 로는 안 잡힌다."""
        payload = {
            "generated": "2026-10-05T03:06:55+09:00",
            "origins": {"SEL": {"name": "서울", "lon": 127, "lat": 37}},
            "deals": [{"o": "SEL", "d": "FUK", "ko": "후쿠오카</script><b>x", "lon": 130, "lat": 33,
                       "price": 1, "when": "이번 주", "dep": "2026-10-10", "ret": "2026-10-12",
                       "nights": "2박3일", "tier": "major", "haul": "short", "discount": 0,
                       "tags": {"top": ["해변"], "sub": []}, "country": "일본", "links": [],
                       "oa": "ICN", "route": None, "region": "jp", "median": 1,
                       "low": 1, "obs_days": 20, "seen": None}],
        }
        dj = home.inline_deals(payload)
        self.assertIn("</script>", dj, "어댑터 출력엔 아직 날것이다(여기서 막는 게 아니다)")
        out = home.render_home(
            payload, dj, '{"type":"FeatureCollection","features":[]}', {"routes": []},
            {"region": ["jp"], "region_name": {"jp": "일본"}, "tags": {"top": ["해변"], "sub": {}},
             "when": {"fixed": [], "patterns": []}, "airport_name": {"ICN": "인천"},
             "haul": [], "hub": [], "tier": []},
            {"generated": "2026-10-05T03:06:55+09:00", "window_days": 30,
             "subscribe": {"address": "a@b.c", "subject_subscribe": "s",
                           "subject_unsubscribe": "u", "route_token": "t"}},
            "2026-10-05")
        seg = out[out.index("window.__DEALS="):]
        seg = seg[:seg.index("</script>")]          # 첫 닫힘까지 — 그게 제자리의 닫힘이어야 한다
        self.assertTrue(seg.endswith("};"), "스크립트가 일찍 끝났다: " + seg[-40:])
        self.assertIn("<\\/script>", seg)
        self.assertNotIn("</", seg)
        # 열고 닫은 수가 맞아야 페이지가 안 깨진다
        self.assertEqual(out.count("<script"), out.count("</script>"))


class PhotoToolTest(unittest.TestCase):
    """🔴 **검수된 사진만 굽는다** (기획 2026-10-05 지적).

    이 도구는 「`photos.json` 에 있으면 다 검수된 것」이라고 **가정**하고 있었다 —
    `ok` 를 읽는 줄이 **한 줄도 없었다.** 기획이 후보를 `ok:false` 로 넣는 방식으로 바뀌면서,
    그대로 돌리면 **검수 전 사진이 그냥 나간다**(실측: 도시 82곳 중 `ok:false` 5곳).
    """

    def test_it_reads_the_flag(self):
        self.assertIn('v.get("ok") is True', TOOL)

    def test_unknown_means_no(self):
        """`ok` 키가 **없으면 굽지 않는다** — 기본값을 「허용」으로 두면 키가 바뀌는 날 또 샌다."""
        self.assertIn("def approved(v):", TOOL)
        self.assertNotIn('v.get("ok", True)', TOOL)
        self.assertNotIn('v.get("ok") is not False', TOOL)

    def test_it_says_what_it_skipped(self):
        """조용히 빠지면 **왜 없는지 아무도 모른다** — 이름까지 찍는다."""
        self.assertIn("검수 전이라 건너뜀", TOOL)

    def test_the_filter_runs_before_the_codes_are_collected(self):
        """거르기가 **코드 목록을 만들기 전**이어야 한다 — 뒤면 `credits.json` 에 행만 남는다."""
        self.assertLess(TOOL.index("cities = {ko: v for ko, v in cities.items() if approved(v)}"),
                        TOOL.index("codes = [(c, ko)"))


if __name__ == "__main__":
    unittest.main()
