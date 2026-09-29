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
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import home  # noqa: E402

CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()

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
        """이름을 못 얻으면 **그 칩이 말없이 빈다** — 그 지역 딜은 어느 칩으로도 갈 수 없다."""
        with self.assertRaises(ValueError):
            home.region_chips(VOCAB, DEALS + [{"region": "af"}])

    def test_a_region_missing_from_the_order_stops_the_build(self):
        v = dict(VOCAB, region=["jp"])      # 이름은 있는데 순서에 없다
        with self.assertRaises(ValueError):
            home.region_chips(v, DEALS)

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


class FitTest(unittest.TestCase):
    """칩 10개가 **한 줄**에 든다 (기획 2026-09-29: 두 줄로 접지 않는다)."""

    def test_the_bar_never_wraps(self):
        self.assertIn(".stagebar{flex-wrap:nowrap}", CSS)

    def test_narrow_desktops_get_tighter_chips(self):
        """실측: 칩 10개에 554px 필요한데 861px 화면의 무대는 503px 였다.
        글꼴이 아니라 **패딩**을 줄인다 — 12px 하한(B57) 아래로 내려가지 않는다."""
        self.assertRegex(CSS, r"@media\(max-width:1000px\)\{\.stagebar\{gap:5px\}\.stagebar \.pill\{padding:6px 7px\}\}")
        self.assertNotRegex(CSS, r"@media\(max-width:1000px\)\{[^}]*\.stagebar \.pill\{[^}]*font-size")


if __name__ == "__main__":
    unittest.main()
