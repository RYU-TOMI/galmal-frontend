# -*- coding: utf-8 -*-
"""실제 출발 공항 — **`서울`은 인천+김포다** (SPEC §CH4 · COPY.md §2 S5 · 계약 `deals[].oa`).

헤더 알약은 `서울 출발` 이라 말하지만 `SEL` 은 **가상 허브**다. 김포 딜을 보고 인천공항으로 갈까
헷갈릴 자리다. 2026-09-01 에 확정됐는데 3주 넘게 화면에 없었다 — 전수 대조에서 센 다섯 중 넷째다.

🔴 **프론트가 만들 수 없는 값이다.** 2026-09-22 에 쟀을 때 `SEL` 딜 78건 중 공항을 알 수 있는 건
`route` 가 있는 26건뿐이었다(67% 는 알 길 없음). 그래서 백엔드가 판정해 계약에 싣고 프론트는 표시만 한다.
**3분의 1에만 붙이는 것은 안 붙이는 것보다 나쁘다** — 없는 쪽을 인천이라고 읽게 된다.

여기서 잠그는 것 셋:
  ① 빌드 게이트(`site/origin.py`) — 이름을 못 얻거나 `route` 와 어긋나면 **배포하지 않는다**
  ② 이름은 **어휘에서 온다** — `discover.js` 에 `{"ICN":"인천"}` 손 사본을 두지 않는다
  ③ 자리 — **가격 줄 바로 아래**, 확장 상세에만, 배지가 아니라 텍스트
"""
import copy
import io
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import home     # noqa: E402
import origin   # noqa: E402
import route    # noqa: E402

JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()


def _fx(*parts):
    with io.open(os.path.join(ROOT, "fixtures", "v1", *parts), encoding="utf-8") as f:
        return json.load(f)


PAYLOAD = _fx("deals.json")
DEALS = PAYLOAD["deals"]
VOCAB = _fx("vocab.json")
INDEX = _fx("routes", "index.json")
META = _fx("meta.json")
# `build_all()` 이 받는 모양 그대로 — 빌드가 쓰는 길로 구워야 「소스엔 있는데 산출물엔 없는」 일이 안 생긴다.
_SNAP = {"meta": META, "index": INDEX,
         "routes": {r["code"]: _fx("routes", r["code"] + ".json") for r in INDEX["routes"]},
         "vocab": VOCAB}


def _fn(name):
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def _detail_body():
    m = re.search(r"function bodyTop\([^)]*\) \{(.*?)\n  \}\n", JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


class GateTest(unittest.TestCase):
    """① 망가뜨려 보고 **실제로 무는지**. 픽스처는 손대지 않는다(메모리에서만)."""

    def _broken(self, mutate):
        d, v = copy.deepcopy(DEALS[:1]), copy.deepcopy(VOCAB)
        mutate(d[0], v)
        return origin.problems(d, v)

    def test_fixture_is_clean(self):
        self.assertEqual(origin.problems(DEALS, VOCAB), [])

    def test_missing_oa_is_caught(self):
        self.assertTrue(any("`oa` 가 없다" in b for b in self._broken(lambda d, v: d.pop("oa"))))

    def test_unknown_airport_is_caught(self):
        """🔴 **이름을 못 얻으면 화면에서 그 줄이 말없이 빈다.** 빈 문자열은 예외가 아니다."""
        bad = self._broken(lambda d, v: d.__setitem__("oa", "XYZ"))
        self.assertTrue(any("airport_name" in b for b in bad), bad)

    def test_vocab_losing_one_airport_is_caught(self):
        """탐침 — 데이터가 아니라 **어휘가** 줄어도 잡힌다. 어느 쪽이 변해도 같은 결함이다."""
        bad = self._broken(lambda d, v: v["airport_name"].pop(d["oa"]))
        self.assertTrue(any("airport_name" in b for b in bad), bad)

    def test_route_disagreeing_is_caught(self):
        """같은 사실이 두 필드에 있다 — 갈리면 **화면으로는 어느 쪽이 맞는지 모른다**."""
        bad = self._broken(lambda d, v: d.__setitem__("route", "ZZZ-AAA"))
        self.assertTrue(any("앞 절반" in b for b in bad), bad)

    def test_no_vocab_at_all_is_a_failure_not_a_pass(self):
        """어휘를 못 읽으면 「어긴 게 없다」로 읽히면 안 된다 — 검사를 못 하면 통과가 아니라 실패다."""
        self.assertTrue(origin.problems(DEALS, {}))
        self.assertTrue(origin.problems(DEALS, None))

    def test_summary_counts_every_deal(self):
        named, crossed, total = origin.summary(DEALS, VOCAB)
        self.assertEqual(named, total, "이름을 못 얻은 딜이 있으면 위 검사가 이미 실패했어야 한다")
        self.assertLessEqual(crossed, total)
        self.assertEqual(total, len(DEALS))

    def test_build_actually_runs_the_gate_with_real_input(self):
        """**부르는 것과 재는 것은 다르다**(함정 14) — 무엇을 먹이는지까지 본다.
        그리고 **산출물을 쓰기 전**이어야 반쪽 폴더가 안 남는다."""
        src = io.open(os.path.join(ROOT, "site", "build.py"), encoding="utf-8").read()
        self.assertIn("import origin", src)
        self.assertIn('origin.problems(deals_list, snap["vocab"])', src)
        self.assertIn('origin.summary(deals_list, snap["vocab"])', src)
        call = src.index("origin.problems(")
        self.assertIn("sys.exit", src[call:call + 600])
        self.assertLess(call, src.index("shutil.copytree"))


class FixtureTest(unittest.TestCase):

    def test_contract_field_is_present(self):
        self.assertEqual([d["ko"] for d in DEALS if not d.get("oa")], [])

    def test_fixture_has_a_split_hub(self):
        """🔴 **이 기능의 이유는 허브가 갈릴 때만 실데이터로 지나간다.**
        `SEL` 딜이 전부 인천이면 「가상 허브를 푼다」가 한 번도 일하지 않는다 —
        검사는 초록인데 아무것도 안 지킨 것이다. 얇은/두꺼운 노선, 신기록 두 갈래와 같은 이유다."""
        sel = [d for d in DEALS if d.get("o") == "SEL"]
        self.assertTrue(sel, "`SEL` 허브 딜이 없다 — 이 검사가 눈을 감았다")
        kinds = {d["oa"] for d in sel}
        self.assertIn("ICN", kinds)
        self.assertIn("GMP", kinds, "김포 딜이 0건이면 「서울은 인천+김포」를 실데이터로 못 지난다")

    def test_non_hub_deals_also_have_it(self):
        """허브가 `SEL` 이 아닌 딜에도 붙인다 — 일관성(COPY.md §2 S5)."""
        other = [d for d in DEALS if d.get("o") != "SEL"]
        self.assertTrue(other)
        self.assertEqual([d["ko"] for d in other if d["oa"] not in VOCAB["airport_name"]], [])


class VocabTest(unittest.TestCase):
    """② 이름은 **어휘에서 온다** — 손 사본을 두지 않는다(CONTRACT §5)."""

    def test_no_hand_copy_in_js(self):
        """🔴 이 저장소가 **다섯 번** 같은 원인으로 사고를 냈다: 같은 사실이 두 곳에 있으면 갈린다."""
        for code, name in VOCAB["airport_name"].items():
            self.assertNotIn('"%s"' % name, JS, "%s 이름이 JS 에 박혀 있다" % code)
            self.assertNotIn("'%s'" % name, JS, "%s 이름이 JS 에 박혀 있다" % code)

    def test_js_reads_the_shipped_table(self):
        self.assertIn("var AIRPORT = window.__AIRPORTS || {};", JS)
        self.assertIn("oa: AIRPORT[dl.oa]", _fn("toCity"))

    def test_home_ships_the_table_from_vocab(self):
        page = home.render_home(PAYLOAD, "[]", "{}", INDEX, VOCAB, META, "2026-09-28")
        self.assertIn("window.__AIRPORTS=", page)
        for code, name in VOCAB["airport_name"].items():
            self.assertIn('"%s":"%s"' % (code, name), page)

    def test_home_does_not_invent_a_table(self):
        """탐침 — 어휘에서 오는지, 아니면 `home.py` 가 들고 있는지. 어휘를 비우면 빈 표가 나가야 한다."""
        page = home.render_home(PAYLOAD, "[]", "{}", INDEX, dict(VOCAB, airport_name={}), META, "2026-09-28")
        self.assertIn("window.__AIRPORTS={};", page)


class PlacementTest(unittest.TestCase):
    """③ 자리 — 가격 줄 **바로 아래**, 확장 상세에만."""

    def test_sits_between_price_and_date(self):
        body = _detail_body()
        self.assertIsNotNone(body, "bodyTop() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다")
        self.assertLess(body.index("hc-marks"), body.index("hc-oa"))
        self.assertLess(body.index("hc-oa"), body.index("hc-date"))

    def test_detail_only(self):
        """축소(호버) 카드는 고르는 자리다 — 확장 상세가 결정하는 자리(SPEC §CH4)."""
        body = _detail_body()
        self.assertIn('(detail ?', body)
        self.assertIn("hc-oa", body)
        self.assertLess(body.index("detail ?"), body.index("hc-oa"))

    def test_wording(self):
        """`{공항명} 출발` 은 그대로다. 2026-09-28 부터 **같은 줄에 `1인 왕복` 단위가 따라붙는다** —
        둘 다 「이 값이 무엇에 대한 값인가」라는 같은 종류의 사실이라 한 줄에 산다."""
        body = _detail_body().replace('"', "'")
        self.assertIn("' 출발 · '", body)
        self.assertIn("1인 왕복", body)

    def test_hidden_when_unknown(self):
        """이름을 못 얻으면 **빈 줄이 아니라 아무것도** 안 그린다 — 빌드가 막지만 화면도 안 무너진다."""
        self.assertIn('AIRPORT[dl.oa] || ""', _fn("toCity"))
        self.assertIn("c.oa ?", _detail_body())


class ShapeTest(unittest.TestCase):

    def test_is_plain_text_not_a_badge(self):
        """직항 배지를 없앤 것과 같은 이유 — 같은 성격의 사실을 다른 모양으로 그리면 없는 구분이 생긴다."""
        m = re.search(r"\.hc-oa\{([^}]*)\}", CSS)
        self.assertIsNotNone(m)
        rule = m.group(1)
        for banned in ("background", "border", "border-radius", "transform"):
            self.assertNotIn(banned, rule, banned)
        date = re.search(r"\.hc-date\{([^}]*)\}", CSS).group(1)
        self.assertEqual(rule, date, "날짜 줄과 같은 무게여야 한다")


if __name__ == "__main__":
    unittest.main()


class SiteNameTest(unittest.TestCase):
    """홈이 **자기 이름을 말한다** — B75 (기획 2026-09-28, `decisions/2026-09.md`).

    동명 서비스 때문에 「갈래말래」 브랜드 검색에서 우리 홈이 밀린다. 이름은 유지하고,
    검색엔진에 사이트 이름을 **우리가** 말한다.

    🔴 **「없다」가 아니라 「어긋나 있었다」**가 이 건의 실체다: 노선 43장은 `WebPage.isPartOf` 로
    사이트 이름을 말하고 있었는데 **정작 그 `url` 이 가리키는 홈에는 JSON-LD 가 0개**였다.
    자식들만 부모 이름을 말하고 부모는 침묵했다 — 사이트 이름 신호는 보통 홈에서 읽힌다.
    """

    ALT = "갈래말래 항공권"

    def _home(self):
        return home.render_home(PAYLOAD, "[]", "{}", INDEX, VOCAB, META, "2026-09-28")

    def _nodes(self, page):
        import re as _re
        out = []
        for b in _re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, _re.S):
            d = json.loads(b)
            out.extend(d if isinstance(d, list) else [d])
        return out

    def test_home_declares_the_site(self):
        nodes = self._nodes(self._home())
        sites = [n for n in nodes if n.get("@type") == "WebSite"]
        self.assertTrue(sites, "홈에 WebSite 노드가 없다 — 이 건의 본체다")
        self.assertEqual(sites[0]["name"], "갈래말래")
        self.assertEqual(sites[0]["alternateName"], self.ALT)
        self.assertEqual(sites[0]["url"], "https://galmal.kr/")

    def test_home_page_node_dates_the_data_not_the_build(self):
        """`dateModified` 는 **데이터 생성 시각**이다 — 노선 페이지와 같은 원칙.
        페이지가 주장하는 건 「이 데이터가 언제 것인가」지 「우리가 언제 빌드했나」가 아니다."""
        pages = [n for n in self._nodes(self._home()) if n.get("@type") == "WebPage"]
        self.assertTrue(pages)
        self.assertEqual(pages[0]["dateModified"], "2026-09-28")
        self.assertEqual(pages[0]["url"], "https://galmal.kr/")

    def test_one_site_node_for_both_surfaces(self):
        """🔴 **각자 적으면 한쪽만 자란다** — 이 저장소가 다섯 번 겪은 그것.
        실제로 그럴 뻔했다: `alternateName` 을 홈에만 넣었으면 노선 43장은 옛 이름만 말한다."""
        self.assertIn("website_node()", io.open(
            os.path.join(ROOT, "site", "route.py"), encoding="utf-8").read())
        src = io.open(os.path.join(ROOT, "site", "home.py"), encoding="utf-8").read()
        self.assertIn("website_node()", src)
        # 손으로 적은 사본이 남아 있으면 안 된다
        for p in ("home.py", "route.py"):
            body = io.open(os.path.join(ROOT, "site", p), encoding="utf-8").read()
            self.assertNotIn('"@type": "WebSite"', body, p + " 에 사본이 남았다")

    def test_every_route_page_says_it_too(self):
        """**여집합으로 센다** — 한 장이라도 빠지면 실패."""
        pages = route.build_all(_SNAP)
        missing = [n for n, p in pages.items() if self.ALT not in p]
        self.assertEqual(missing, [])
        self.assertGreater(len(pages), 1)
