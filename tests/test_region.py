# -*- coding: utf-8 -*-
"""지역바 — CH8 (사용자 결정 2026-09-29 · `SPEC.md` §CH1 「단계바 → 지역바」).

사용자: 「가까운곳 조금더멀리 말고 유럽, 동남아시아, 이런식으로 인기 관광지 모여있는 곳」.

**목록은 사용자가 말한 6개가 아니라 계약의 9개다.** 6개(유럽·동남아시아·북미·남미·아프리카·호주)로
하면 오늘 데이터에서 아프리카 0건·남미 0건 버튼 둘이 비고, 일본 26·중화권 27·국내 3 = **56건은 갈
버튼이 없다.** 실측을 대고 물었고 사용자가 9개를 골랐다.

여기서 잠그는 것 넷:
  ① **어휘에서 온다** — 순서까지. 손 사본을 만들면 백엔드가 지역을 바꾼 날 화면만 옛 목록을 말한다.
  ② **그날 딜이 있는 지역만** 나온다 — 빈 칩은 「눌렀는데 아무 일도 안 나는 버튼」이다.
  ③ **「전체」가 맨 앞에 있다** — 없으면 피드의 `전체로 보면 {M}곳이에요` 가 누를 데 없는 말이 된다.
  ④ **이름 없는 지역은 빌드를 멈춘다** — 빈 문자열은 예외가 아니라 **말없이 빈 칩**이 된다.
"""
import io
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import home  # noqa: E402

CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()


# 🔴 주석을 걷어낸 몸통. 이 파일에서 셋을 그냥 `JS`·`CSS` 로 재다 **셋 다 주석에 걸렸다** —
# 「예전엔 …였다」를 남겨 두는 문서 습관과 「그 코드가 없다」를 세는 검사가 정면으로 부딪친다.
CODE = re.sub(r"(?m)^\s*//.*$", "", JS)
CSS_CODE = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)


def body(name):
    """함수 하나의 본문만 — 파일 전체에서 찾으면 **다른 함수의 문장**을 세고도 통과한다."""
    i = JS.index("function " + name + "(")
    d, j, started = 0, i, False
    while j < len(JS):
        if JS[j] == "{":
            d += 1; started = True
        elif JS[j] == "}":
            d -= 1
            if started and d == 0:
                return JS[i:j + 1]
        j += 1
    raise AssertionError(name + " 의 본문을 못 찾았다")

VOCAB = {
    "region": ["jp", "cn", "sea", "eu", "etc"],
    "region_name": {"jp": "일본", "cn": "중화권", "sea": "동남아", "eu": "유럽", "etc": "그 외"},
    "tags": {"top": ["해변"]}, "when": {"fixed": []},
}
DEALS = [{"region": "eu"}, {"region": "jp"}, {"region": "jp"}, {"region": "sea"}]


class ChipTest(unittest.TestCase):

    def test_order_comes_from_vocab_not_from_the_deals(self):
        """🔴 딜에 나온 순서(eu, jp, sea)가 아니라 **어휘 순서**(jp, cn, sea, eu)여야 한다.
        딜 순서를 쓰면 매일 버튼이 자리를 바꾼다 — 같은 버튼을 두 번 못 누른다."""
        html_out = home.region_chips(VOCAB, DEALS)
        got = [x.split('"')[0] for x in html_out.split('data-region="')[1:]]
        self.assertEqual(got, ["", "jp", "sea", "eu"])

    def test_only_regions_with_deals_appear(self):
        """`cn`·`etc` 는 어휘에 있지만 그날 딜이 없다 — 칩도 없다."""
        html_out = home.region_chips(VOCAB, DEALS)
        self.assertNotIn('data-region="cn"', html_out)
        self.assertNotIn('data-region="etc"', html_out)
        self.assertIn("일본", html_out)

    def test_all_chip_is_first_and_lit(self):
        html_out = home.region_chips(VOCAB, DEALS)
        self.assertTrue(html_out.startswith('<span class="pill on" data-region="">전체</span>'))

    def test_a_region_without_a_name_stops_the_build(self):
        """이름을 못 얻으면 **그 칩이 말없이 빈다** — 그 지역 딜은 어느 칩으로도 갈 수 없다.

        ⚠️ 처음엔 `{"region": "af"}` 로 쟀는데, `af` 는 **순서에도 없어서** 다른 검사가 먼저
        터졌다 — 이름 검사를 꺼도 테스트가 초록이었다(돌연변이가 통과). 지금은 `순서에는 있고
        이름만 없는` 키를 쓴다. **어느 검사가 터졌는지까지** 봐야 그 검사를 지키는 것이다."""
        v = dict(VOCAB, region=VOCAB["region"] + ["af"])      # 순서에는 있다
        with self.assertRaises(ValueError) as e:
            home.region_chips(v, DEALS + [{"region": "af"}])
        self.assertIn("이름이 없는", str(e.exception))

    def test_a_region_missing_from_the_order_stops_the_build(self):
        """순서에 없으면 그 지역은 **그릴 자리가 없다** — 위 검사와 다른 문장으로 터져야 한다."""
        v = dict(VOCAB, region=["jp"])      # 이름은 있는데 순서에 없다
        with self.assertRaises(ValueError) as e:
            home.region_chips(v, DEALS)
        self.assertIn("순서에 없는", str(e.exception))

    def test_no_deals_means_only_the_all_chip(self):
        """딜 0건인 날에도 「전체」는 남는다 — 지도는 그대로 있다."""
        self.assertEqual(home.region_chips(VOCAB, []),
                         '<span class="pill on" data-region="">전체</span>')

    def test_keys_and_names_are_escaped(self):
        v = {"region": ['a"b'], "region_name": {'a"b': 'c"d'}, "tags": {"top": []}, "when": {"fixed": []}}
        out = home.region_chips(v, [{"region": 'a"b'}])
        self.assertIn('data-region="a&quot;b"', out)
        self.assertIn("c&quot;d", out)


class GateTest(unittest.TestCase):
    """빌드가 막는가 — 검사에 **무엇을 먹이는지**가 검사가 무엇을 지키는지를 정한다(함정 14)."""

    def _page(self, vocab, deals):
        return home.region_chips(vocab, deals) + home.filter_dock(vocab)

    def test_a_correct_bar_passes(self):
        page = self._page(VOCAB, DEALS)
        self.assertEqual([p for p in home.chip_problems(page, VOCAB, DEALS) if "지역" in p], [])

    def test_wrong_order_is_caught(self):
        page = self._page(VOCAB, DEALS).replace(
            '<span class="pill" data-region="jp">일본</span><span class="pill" data-region="sea">동남아</span>',
            '<span class="pill" data-region="sea">동남아</span><span class="pill" data-region="jp">일본</span>')
        self.assertTrue([p for p in home.chip_problems(page, VOCAB, DEALS) if "지역" in p])

    def test_a_missing_chip_is_caught(self):
        page = self._page(VOCAB, DEALS).replace('<span class="pill" data-region="jp">일본</span>', "")
        self.assertTrue([p for p in home.chip_problems(page, VOCAB, DEALS) if "지역" in p])

    def test_a_chip_for_a_region_with_no_deals_is_caught(self):
        """빈 칩이 섞여 들어오면 잡는다 — 눌렀는데 아무 일도 안 나는 버튼."""
        page = self._page(VOCAB, DEALS) + '<span class="pill" data-region="cn">중화권</span>'
        self.assertTrue([p for p in home.chip_problems(page, VOCAB, DEALS) if "지역" in p])

    def test_losing_the_all_chip_is_caught(self):
        page = self._page(VOCAB, DEALS).replace('<span class="pill on" data-region="">전체</span>', "")
        self.assertTrue([p for p in home.chip_problems(page, VOCAB, DEALS) if "지역" in p])


class MoveTest(unittest.TestCase):
    """칩을 누르면 **그 지역으로 날아간다** (T3). 실측은 CDP 로 했다(FRONTEND §3) —
    여기서는 **규칙의 모양**을 본다. 칩 10개를 눌러 본 결과:
    전체 76핀/k0.9 · 일본 17/8.4 · 중화권 27/6.4 · 동남아 28/4.7 · 섬 59/1.5 ·
    대양주 5/6.0 · 유럽 11/6.7 · 미주 6/4.0 · 그 외 26/3.5 · 국내 24/6.9. 예외 0건."""

    def test_the_list_is_read_from_the_chips(self):
        """🔴 손 사본을 만들지 않는다 — 목록은 **그려진 칩에서** 읽는다(TAG_TOP·WHEN_CHIPS 와 같은 규칙)."""
        self.assertIn('var REGIONS = chipList(".stagebar .pill", "region")', CODE)
        for name in ("일본", "중화권", "동남아", "대양주"):
            self.assertNotIn('"' + name + '"', CODE, "지역 표시명이 JS 에 박혀 있다 — 어휘에서 와야 한다")

    def test_the_city_carries_its_region(self):
        """도시가 지역을 모르면 어느 칩으로도 그 도시를 못 찾는다."""
        self.assertIn('region: dl.region || ""', body("toCity"))

    def test_the_span_math_lives_in_one_place(self):
        """「전체」와 지역이 **같은 규칙**으로 중심을 찾는다 — 두 벌이면 날짜변경선이 한쪽만 고쳐진다."""
        self.assertEqual(CODE.count("360 - gap"), 1)
        self.assertIn("spanOf(ls)", body("farArc"))
        self.assertIn("spanOf(lons)", body("viewOfRegion"))

    def test_all_chip_is_the_old_far_view(self):
        self.assertIn("if (!key) return farView();", body("viewOfRegion"))

    def test_the_origin_is_not_framed_with_the_region(self):
        """「유럽」을 눌렀는데 한국이 들어오려고 배율이 내려가면 **보려던 것이 작아진다.**"""
        self.assertNotIn("ORIGIN", body("viewOfRegion"))

    def test_a_region_view_is_never_wider_than_all(self):
        """섬(-158°~146°)·그 외(52°~107°)는 계산값이 세계지도만큼 넓어진다 —
        「전체」보다 넓어지면 버튼이 거짓말을 한다."""
        self.assertIn("Math.max(far.scale, Math.min(sLon, sLat))", body("viewOfRegion"))

    def test_no_hardcoded_region_views(self):
        """고정값 표는 **오늘 데이터에서만** 맞다(`farArc` 이 계산식인 것과 같은 이유)."""
        self.assertNotRegex(CODE, r'REGION_VIEWS?\s*=')
        self.assertIn("var RAD = Math.PI / 180", body("viewOfRegion"))

    def test_clicking_uses_the_key_not_the_position(self):
        """그날 딜이 없는 지역은 칩이 빠져 **번호가 밀린다**(대구는 넷이 빠진다) —
        번호로 묶으면 「유럽」을 눌렀는데 「미주」로 간다."""
        self.assertIn('setRegion(el.getAttribute("data-region") || "")', CODE)
        self.assertNotIn("setStage(", CODE)

    def test_a_chip_is_a_quick_move_so_it_takes_the_view(self):
        """PH5c 가 단계 버튼에 둔 예외를 그대로 물려받는다 — 누르면 만져 둔 뷰를 버린다."""
        b = body("setRegion")
        self.assertIn("userV = viewOfRegion(key)", b)
        self.assertIn("collapse()", b)
        self.assertIn("tweenTo(from, CURV, 400)", b)


class LightTest(unittest.TestCase):
    """불은 **지금 보고 있는 것**을 말한다 (T4)."""

    def test_the_lit_chip_is_the_pressed_one(self):
        b = body("syncStageBar")
        self.assertIn('regionKey !== null && pills[i].getAttribute("data-region") === regionKey', b)

    def test_empty_is_not_the_same_as_none(self):
        """`""`(전체 칩)과 `null`(어느 지역도 아님)을 합치면 「전체」를 눌러도 불이 안 켜진다."""
        self.assertRegex(CODE, r"var regionKey = null;")
        self.assertIn('regionKey !== null', CODE)

    def test_zoom_and_pan_turn_the_light_off(self):
        """휠·드래그로 옮긴 화면은 **어느 지역도 아니다** — 켜져 있으면 거짓말이다."""
        self.assertIn("if (!hadUser || regionKey !== null) { hadUser = true; regionKey = null; syncStageBar(); }",
                      body("takeView"))

    def test_chips_with_no_deals_are_removed(self):
        """실측: 대구는 섬·대양주·미주·그 외가 0건, 제주는 대양주·유럽·미주·국내가 0건이다.
        누르면 아무 일도 안 나는 버튼을 두지 않는다."""
        self.assertIn('pills[i].style.display = (rk && !regionHasDeals(rk)) ? "none" : ""', body("syncStageBar"))

    def test_filtering_keeps_the_chips(self):
        """🔴 지역은 거리와 달리 **필터와 양립한다**(「미식 + 동남아」는 뜻이 통한다).
        예전 규칙의 이유(「필터 중에는 거리 단계가 성립하지 않는다」)가 사라졌다."""
        self.assertNotIn(".stagebar.allregions .pill{display:none}", CSS_CODE)

    def test_the_sparse_note_points_at_a_button_that_exists(self):
        """`더 멀리까지 보면` 이 가리킨 버튼(`아주 멀리`)은 이제 없다 — 「전체」 칩이 그 자리다."""
        self.assertIn('"<b>전체로 보면 " + TOTAL + "곳이에요.</b>"', CODE)
        self.assertNotIn("더 멀리까지 보면 ", CODE)

    def test_the_note_follows_the_screen_not_the_stage(self):
        """자유 줌 뒤에는 **단계가 0 인데도** 화면이 좁을 수 있다 — 그때도 말해야 한다."""
        self.assertIn("if (vis.length < TOTAL && !anyFilter()) {", CODE)


class FitTest(unittest.TestCase):
    """칩 10개가 **한 줄**에 든다 (기획 2026-09-29: 두 줄로 접지 않는다)."""

    def test_the_bar_never_wraps(self):
        self.assertIn(".stagebar{flex-wrap:nowrap}", CSS)

    def test_chip_labels_never_break(self):
        """🔴 실측(861px · 필터 켬): 「중화권」 칩 높이가 29 → **44px** 이 됐다 — 바가 접힌 게 아니라
        **칩 안의 글자가** 두 줄이 된 것이었다. `flex:none` 이 없으면 칩은 줄어들려 하고,
        줄어들 수 없으면 글자를 접는다."""
        self.assertIn(".stagebar .pill{white-space:nowrap;flex:none}", CSS)

    def test_the_filter_note_folds_before_the_chips_do(self):
        """좁은 화면에선 버튼이 먼저다. 실측 필요 폭 칩 445 + 여백 6 + 안내 102 = 553px 인데
        900px 화면의 무대에서 쓸 수 있는 폭은 542 다 — 기준을 520 → 940px 로 옮겼다."""
        self.assertIn("@media(max-width:940px){.stagebar.allregions .allnote{display:none}}", CSS)

    def test_phones_can_reach_every_chip(self):
        """🔴 CH8 이 낸 회귀를 막는다. 칩이 3개(242px)에서 10개(445px)로 늘어, 390px 화면에서
        실측 「국내」 칩이 L418 — **화면 밖이라 누를 수 없었다.** 두 줄로 접지 않기로 했고
        글자도 더 줄일 수 없으니 가로 스크롤이다. 고친 뒤: 스크롤폭 445 / 보이는폭 370,
        끝까지 밀면 마지막 칩이 화면 안에 들어온다."""
        self.assertRegex(CSS, r"@media\(max-width:520px\)\{\.stagebar\{overflow-x:auto")
        self.assertIn(".stagebar::-webkit-scrollbar{display:none}", CSS)

    def test_narrow_desktops_get_tighter_chips(self):
        """실측: 칩 10개에 554px 필요한데 861px 화면의 무대는 503px 였다.
        글꼴이 아니라 **패딩**을 줄인다 — 12px 하한(B57) 아래로 내려가지 않는다."""
        self.assertRegex(CSS, r"@media\(max-width:1000px\)\{\.stagebar\{gap:5px\}\.stagebar \.pill\{padding:6px 7px\}\}")
        self.assertNotRegex(CSS, r"@media\(max-width:1000px\)\{[^}]*\.stagebar \.pill\{[^}]*font-size")


if __name__ == "__main__":
    unittest.main()
