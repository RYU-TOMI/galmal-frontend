# -*- coding: utf-8 -*-
"""인원 — 「1인 기준」을 말하고, 고른 인원은 **예약처 링크에만** 넘긴다
(SPEC §CH4 보강 · COPY.md §인원 · 계약 `links[].pax_url`, 2026-09-22).

🔴 **이 챕터는 「틀려도 화면이 멀쩡한」 종류다.** 칩은 그려지고 링크도 열리고 예약처도 뜬다 —
인원만 조용히 1명으로 간다. 사용자는 `4명` 을 고르고 4명 값을 본다고 믿은 채 1인 가격을 본다.
**우리가 화면에서 한 약속이 거짓이 되는데 아무 예외도 안 난다.** 그래서 검사를 세 겹으로 둔다:

  ① `site/pax.py` — 빌드가 **쓰기 전에** 막는다(`{n}`→`1` ≠ `url` 이면 배포 안 됨)
  ② 여기 `SourceTest` — JS 가 **`{n}` 하나만** 치환하는가, 1명은 원래 `url` 그대로인가
  ③ 여기 `CopyTest`·`OrderTest` — 고지 문구와 **순서**(B61 사슬)가 그대로인가

`site/pax.py` 를 직접 돌려 본다 — 파이썬이라 옮겨 적은 사본이 아니다. JS 쪽은 소스를 읽는다
(이 저장소엔 Node 빌드가 없다, `CLAUDE.md`). 화면에서 실제로 도는지는 CDP 로 따로 본다(`FRONTEND.md` §3).
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

import pax     # noqa: E402
import route   # noqa: E402
import shell   # noqa: E402

JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()
DEALS = json.load(io.open(os.path.join(ROOT, "fixtures", "v1", "deals.json"), encoding="utf-8"))["deals"]


def _fx(*parts):
    with io.open(os.path.join(ROOT, "fixtures", "v1", *parts), encoding="utf-8") as f:
        return json.load(f)


_INDEX = _fx("routes", "index.json")
# `build_all()` 이 받는 모양 그대로 — 빌드가 쓰는 길로 구워야 「소스엔 있는데 산출물엔 없는」 일이 안 생긴다.
_SNAP = {"meta": _fx("meta.json"), "index": _INDEX,
         "routes": {r["code"]: _fx("routes", r["code"] + ".json") for r in _INDEX["routes"]},
         "vocab": _fx("vocab.json")}

UNIT = "1인 왕복"
NOTE = "가격은 성인 1인 왕복 기준이에요. 인원을 고르면 예약처에서 그 인원으로 조회돼요."
CANT = "1인 기준으로 열려요"
FOOT = "시세는 성인 1인 왕복 기준입니다."
AD_NOTE = "(광고) 표시는 예약하시면 저희가 수수료를 받는 링크예요"
PRICE_NOTE = "항공권 가격은"


def _fn(name):
    """`function name(...) { … }` 한 덩이. 주석은 걷어낸다 — 주석 속 문구에 속지 않는다."""
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def _detail():
    m = re.search(r"function detailHTML\(c\) \{(.*?)\n  \}\n", JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def _one_link():
    for d in DEALS:
        for ln in d.get("links") or []:
            if ln.get("pax_url"):
                return copy.deepcopy(d), ln["name"]
    raise AssertionError("치환 가능한 링크가 픽스처에 하나도 없다 — 검사가 눈을 감는다")


class GateTest(unittest.TestCase):
    """① 빌드 게이트 — **망가뜨려 보고 실제로 무는지** 본다. 픽스처는 손대지 않는다(메모리에서만)."""

    def _broken(self, mutate):
        d, name = _one_link()
        for ln in d["links"]:
            if ln["name"] == name:
                mutate(ln)
        return pax.problems([d])

    def test_fixture_is_clean(self):
        self.assertEqual(pax.problems(DEALS), [])

    def test_missing_key_is_caught(self):
        bad = self._broken(lambda l: l.pop("pax_url"))
        self.assertTrue(any("키가 없다" in b for b in bad), bad)

    def test_zero_tokens_is_caught(self):
        bad = self._broken(lambda l: l.__setitem__("pax_url", l["url"]))
        self.assertTrue(any("0 개" in b for b in bad), bad)

    def test_two_tokens_is_caught(self):
        bad = self._broken(lambda l: l.__setitem__("pax_url", l["pax_url"] + "&x={n}"))
        self.assertTrue(any("2 개" in b for b in bad), bad)

    def test_one_person_must_equal_the_plain_url(self):
        """🔴 **핵심.** 인원을 안 고른 사람의 링크가 바뀌면 안 된다 — 지금까지와 같은 주소여야 한다."""
        bad = self._broken(lambda l: l.__setitem__("pax_url", l["pax_url"] + "&extra=1"))
        self.assertTrue(any("바이트" in b or "다르다" in b for b in bad), bad)

    def test_null_passes(self):
        """`null` 은 **뜻이 있는 값**이다 — 그 예약처는 인원을 못 받는다(화면에 그렇게 쓴다)."""
        self.assertEqual(self._broken(lambda l: l.__setitem__("pax_url", None)), [])

    def test_build_actually_runs_the_gate(self):
        """🔴 **검사를 만들어 놓고 안 부르면 없는 것과 같다.** 이 저장소가 겪은 결함의 모양 그대로다
        (신기록은 판정 함수 없이 3주, B65 는 링크 없이 3주). 부르는 자리까지 잠근다 —
        **산출물을 쓰기 전**, 정적 자산 복사보다 앞이어야 반쪽 폴더가 안 남는다."""
        src = io.open(os.path.join(ROOT, "site", "build.py"), encoding="utf-8").read()
        self.assertIn("import pax", src)
        call = src.index("pax.problems(")
        self.assertIn("sys.exit", src[call:call + 600])
        self.assertLess(call, src.index("shutil.copytree"), "쓰기 시작한 뒤에 막으면 반쪽이 남는다")
        # 🔴 **무엇을 먹이는지까지 본다.** 돌연변이로 빈 목록을 먹여 봤더니 **조용히 통과했다**(2026-09-22).
        # 부르는 것과 재는 것은 다르다 — 검사에 아무것도 안 주면 검사는 늘 초록이다.
        self.assertIn('deals_list = snap["deals"]["deals"]', src)
        self.assertIn("pax.problems(deals_list)", src)
        self.assertIn("pax.summary(deals_list)", src)

    def test_summary_counts_every_link(self):
        """여집합으로 센다 — 어느 갈래에도 안 든 링크가 있으면 검사가 그 링크를 안 본 것이다."""
        ok, none, total = pax.summary(DEALS)
        self.assertEqual(ok + none, total)
        self.assertGreater(total, 0)
        self.assertEqual(total, sum(len(d.get("links") or []) for d in DEALS))


class FixtureTest(unittest.TestCase):

    def test_contract_field_is_present(self):
        """계약이 `required` 라 했다 — 사본에도 전건 있어야 위 검사들이 실제로 무언가를 잰다."""
        missing = [d["ko"] for d in DEALS for ln in (d.get("links") or []) if "pax_url" not in ln]
        self.assertEqual(missing, [])

    def test_token_is_the_only_difference(self):
        """계약의 약속을 **소비 쪽에서 다시 잰다** — 생산자 테스트가 있어도 여기서 또 본다."""
        for d in DEALS:
            for ln in d.get("links") or []:
                if ln.get("pax_url"):
                    self.assertEqual(ln["pax_url"].replace("{n}", "1"), ln["url"], d["ko"] + " " + ln["name"])


class SourceTest(unittest.TestCase):
    """② JS — `{n}` **하나만** 치환하고, 1명은 원래 `url` 을 그대로 쓴다."""

    def test_default_path_is_untouched(self):
        body = _fn("bookURL")
        self.assertIsNotNone(body, "bookURL() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다")
        self.assertIn("if (PAX === 1 || !l.pax_url) return l.url;", body)

    def test_only_the_token_is_replaced(self):
        body = _fn("bookURL")
        self.assertIn('l.pax_url.replace("{n}", PAX)', body)
        for banned in ("+ PAX", "adult", "quantity", "&", "?"):
            self.assertNotIn(banned, body.split("replace")[1], banned)

    def test_no_total_price_is_computed(self):
        """🔴 **`×n` 총액을 만들지 않는다.** 가격·도장·비교 막대는 그대로 1인이다(SPEC)."""
        for fn in ("bookURL", "setPax", "paxHTML"):
            body = _fn(fn) or ""
            self.assertNotIn("price", body, fn)

    def test_range_is_one_to_four(self):
        self.assertIn("var PAX = 1, PAX_MAX = 4;", JS)
        self.assertIn("if (!(n >= 1 && n <= PAX_MAX) || n === PAX) return;", _fn("setPax"))

    def test_not_persisted(self):
        """세션 안에서만 기억한다 — 「지난주에 고른 4명」이 오늘 조용히 살아 있으면 안 된다.

        이 파일은 `localStorage` 를 **이미 쓴다**(출발지 기억, `lsGet`/`lsSet`). 그래서 「어디에도 없다」가
        아니라 **인원이 그 길에 들어가지 않았나**를 본다 — 저장을 금지한 게 아니라 이 값만 안 저장하는 것이다."""
        for fn in ("setPax", "paxHTML", "bookURL", "paxNote"):
            body = _fn(fn) or ""
            for banned in ("localStorage", "sessionStorage", "document.cookie", "lsSet", "lsGet"):
                self.assertNotIn(banned, body, "%s 에 %s" % (fn, banned))
        self.assertNotIn("pax", JS[JS.index("function lsGet"):], "저장 키에 인원이 끼어들었다")

    def test_choosing_updates_all_three(self):
        """칩 상태 · 「1인 기준」 표시 · 링크 주소 — 하나라도 빠지면 화면과 링크가 갈린다."""
        body = _fn("setPax")
        self.assertIn("paxchip", body)
        self.assertIn("paxmulti", body)
        self.assertIn('els[i].href', body)

    def test_hrefs_are_rebuilt_from_the_dom(self):
        """`data-u`·`data-p` 를 링크에 실어 둔다 — 딜 객체를 다시 찾지 않아 화면과 계산이 갈릴 자리가 없다."""
        self.assertIn('data-u="', JS)
        self.assertIn('data-p="', JS)
        self.assertIn('els[i].getAttribute("data-u")', _fn("setPax"))

    def test_provider_is_never_guessed_by_name(self):
        """🔴 어느 예약처가 인원을 받는지는 **계약이 말한다** — 이름으로 추측하지 않는다(`ad` 와 같은 이유)."""
        body = _fn("paxNote")
        self.assertIn("l.pax_url", body)
        for name in ("스카이스캐너", "네이버", "구글", "Trip", "Aviasales"):
            self.assertNotIn(name, body, name)


class CopyTest(unittest.TestCase):
    """문구는 `COPY.md` §인원 표 그대로다 — 없는 문자열을 지어내지 않는다."""

    def test_unit_on_home_card(self):
        self.assertIn('<span class="unit">%s</span>' % UNIT, JS)

    def test_unit_on_route_hero(self):
        src = io.open(os.path.join(ROOT, "site", "route.py"), encoding="utf-8").read()
        self.assertIn('<span class="unit">%s</span>' % UNIT, src)

    def test_footer_sentence_comes_first(self):
        foot = shell.footer("x@example.com")
        self.assertIn(FOOT, foot)
        self.assertLess(foot.index(FOOT), foot.index("중앙값입니다"), "중앙값 고지 **앞**이다(COPY.md)")

    def test_detail_note_exists(self):
        self.assertIn(NOTE, JS)

    def test_cant_take_pax_wording(self):
        self.assertIn(CANT, JS)

    def test_label_and_chips(self):
        body = _fn("paxHTML")
        self.assertIn("몇 명이 가요?", body)
        self.assertIn("'명</button>'", body.replace('"', "'"))


class OrderTest(unittest.TestCase):
    """③ **고지 사슬을 가르지 않는다** (B61) — 인원이 끼어들어 순서를 흐트리지 않았는가."""

    def test_chain_still_holds(self):
        body = _detail()
        self.assertIsNotNone(body)
        note, lst, disc = body.index(AD_NOTE), body.index("compareHTML(c.links)"), body.index(PRICE_NOTE)
        self.assertLess(note, lst)
        self.assertLess(lst, disc)

    def test_pax_block_sits_above_the_compare_header(self):
        """머리말과 목록 사이에 끼면 **머리말이 자기 목록과 떨어진다**(실측 후 옮긴 자리)."""
        body = _detail()
        self.assertLess(body.index("paxHTML()"), body.index("어디가 제일 싼지"))

    def test_pax_note_sits_directly_above_the_price_note(self):
        body = _detail()
        self.assertLess(body.index(NOTE), body.index(PRICE_NOTE))
        self.assertLess(body.index("compareHTML(c.links)"), body.index(NOTE))

    def test_pax_ui_is_hidden_when_there_are_no_links(self):
        """예약처가 없는 날 「인원을 고르면 예약처에서…」는 **없는 것을 설명하는** 말이 된다.
        칩도 고지도 `c.links` 가 있을 때만 그린다 — 두 자리가 **각각** 막혀 있는지 본다."""
        body = _detail()
        guards = [m.start() for m in re.finditer(r"c\.links && c\.links\.length", body)]
        self.assertEqual(len(guards), 2, "인원 칩·인원 고지 두 자리가 각각 `c.links` 로 막혀 있어야 한다")
        chips, note = body.index("paxHTML()"), body.index(NOTE)
        self.assertLess(guards[0], chips)     # 첫 조건이 칩을 막는다
        self.assertLess(chips, guards[1])     # 둘째 조건은 그 뒤에 따로 있다
        self.assertLess(guards[1], note)      # 그리고 고지를 막는다


class ShapeTest(unittest.TestCase):

    def _rule(self, sel):
        m = re.search(re.escape(sel) + r"\{([^}]*)\}", CSS)
        self.assertIsNotNone(m, sel)
        return m.group(1)

    def test_cant_note_is_hidden_at_one_person(self):
        """1명이면 모든 링크가 1인이라 알릴 차이가 없다 — 매 예약처에 붙으면 고지가 아니라 소음이다."""
        self.assertIn("display:none", self._rule(".cmp-pax"))
        self.assertIn(".hc-compare.paxmulti .cmp-pax{display:inline}", CSS)

    def test_cant_note_meets_the_disclosure_floor(self):
        """불리한 사실을 말하는 자리다 — `tests/test_disclosure.py` 와 같은 하한(12px·`--sub`)."""
        rule = self._rule(".cmp-pax")
        self.assertIn("font-size:.75rem", rule)
        self.assertIn("color:var(--sub)", rule)
        self.assertNotIn("opacity", rule)

    def test_unit_is_lighter_than_the_price(self):
        """단위는 값이 아니다 — 가격과 **다른 무게**로 둔다. `~`(가격의 일부)와 헷갈리면 안 된다."""
        rule = self._rule(".unit")
        self.assertIn("color:var(--sub)", rule)
        self.assertNotIn("var(--accent)", rule)
        self.assertIn("font:inherit;color:inherit", self._rule(".tilde"))

    def test_selected_chip_is_unmistakable(self):
        self.assertIn("background:var(--accent)", self._rule(".paxchip.on"))


class RoutePageTest(unittest.TestCase):
    """구운 노선 페이지에 실제로 있는가 — 소스에만 있고 산출물엔 없는 일을 막는다."""

    def test_every_rendered_page_says_it(self):
        """**여집합으로 센다** — 한 장이라도 단위나 푸터 고지가 빠지면 실패한다.
        빌드가 쓰는 길(`build_all`)로 굽는다 — 「소스엔 있는데 산출물엔 없는」 일을 막는다."""
        pages = route.build_all(_SNAP)
        self.assertGreater(len(pages), 1)
        missing = [n for n, p in pages.items()
                   if ('<span class="unit">%s</span>' % UNIT) not in p or FOOT not in p]
        self.assertEqual(missing, [])
        one = pages[sorted(pages)[0]]
        self.assertLess(one.index(FOOT), one.index("중앙값입니다"))


if __name__ == "__main__":
    unittest.main()
