# -*- coding: utf-8 -*-
"""확장 상세가 제자리를 지킨다 — CH9 (B59 · B60, 2026-10-01).

둘 다 **데스크톱에서 재현되는** 버그다. 백로그엔 「PH5b(모바일) 뒤로 미룬다」가 붙어 있었는데,
사용자가 2026-09-28 에 「모바일은 최후미, 데스크톱을 먼저 완벽히」로 순서를 뒤집어 보류가 풀렸다.

**B59 — `×` 가 앞 상세를 되살렸다.** 실측(고치기 전): 제주 상세 → 후쿠오카 상세 → `×` →
**제주가 다시 열리고** 주소도 `#SEL-CJU`. 스펙 **두 줄**이 같이 어긋나 있었다(§CH4 열고닫기):
「`×` 는 카드만 닫힌다」와 「브라우저 뒤로가기 → 상세만 닫힌다 · `#{허브}`」 —
상세마다 `pushState` 를 쌓으니 뒤로가기도 `#{허브}` 가 아니라 `#{허브}-A` 로 갔다.
→ **히스토리에도 「동시에 하나만」**(기획 결정 2026-10-01 (1)): 상세가 이미 열려 있으면 `replaceState`.
`×` 의 구현(=`history.back()`)은 **안 건드린다** — 건드리면 B58(`×` 가 사이트를 떠남)이 되살아난다.

**B60 — 창 크기를 바꾸면 카드가 핀에서 떨어졌다.** 실측(카드 아래 ~ 핀 위, 1440→1200):
고치기 전 **150px** → 고친 뒤 **−5px**(창을 바꾸기 전과 같은 값). 1440→1000 도 155 → −5.
뿌리는 **`render()` 가 열린 상세를 다시 놓지 않은 것** — 위치 계산이 `moveOnly()` 안에만 있었고
그나마 호버 미니카드만 대상이었다. 이제 계산은 `followCard()` **한 벌**이고
「언제 따라가나」만 부르는 쪽이 정한다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CODE = re.sub(r"(?m)^\s*//.*$", "", JS)          # 주석 속 옛 코드에 속지 않는다


def body(name):
    """주석을 **걷어낸** 함수 본문.

    🔴 이 저장소에서 반복해 당한 함정이다 — 「그 코드가 없다」를 세는 검사와 「왜 없는지」를
    주석에 남기는 습관이 정면으로 부딪친다. CH8 에서 두 번, PH8 에서 두 번 걸렸고
    여기서 또 걸렸다(`pinTarget()` 을 **쓰지 않는다**고 적은 주석에).
    **`없다`를 셀 때는 반드시 이 함수를 쓴다.**"""
    return re.sub(r"(?m)^\s*//.*$", "", fn(name))


def fn(name):
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


class HistoryTest(unittest.TestCase):
    """B59 — 히스토리에도 「동시에 하나만」."""

    def test_a_second_detail_replaces_instead_of_pushing(self):
        b = fn("expand")
        self.assertIn("var hadDetail = (expandedI !== null);", b)
        self.assertIn('writeHash(ORIGIN_KEY + "-" + c.dcode, !hadDetail)', b)

    def test_it_reads_the_flag_before_overwriting_it(self):
        """🔴 `expandedI = i` **뒤에** 보면 언제나 「열려 있다」가 된다 — 그러면 **첫 상세도**
        히스토리를 안 쌓고, 뒤로가기가 상세를 못 닫는다."""
        b = fn("expand")
        self.assertLess(b.index("var hadDetail"), b.index("expandedI = i;"),
                        "`expandedI` 를 덮은 뒤에 읽고 있다")

    def test_the_close_button_still_walks_history(self):
        """`×` 의 구현은 **안 건드린다** — 건드리면 B58(`×` 가 사이트를 떠남)이 되살아난다.
        우리가 쌓은 항목일 때만 `history.back()` 이고, 아니면(딥링크 진입) `collapse()` 다."""
        b = fn("closeByUser")
        self.assertIn("history.state && history.state.gm", b)
        self.assertIn("history.back()", b)
        self.assertIn("else collapse()", b)

    def test_the_marker_survives_a_replace(self):
        """교체할 때 `{gm:1}` 표식을 물려줘야 `×` 가 「우리 항목」인 줄 안다."""
        self.assertIn("history.replaceState(history.state,", fn("writeHash"))


class FollowTest(unittest.TestCase):
    """B60 — 지도가 움직였으면 카드도 자기 핀으로."""

    def test_render_puts_the_card_back(self):
        """`render()` 는 창 크기·출발지·필터 등 **뷰와 무관한 이유로도** 돌지만,
        돌 때마다 핀 좌표를 다시 계산하므로 카드도 다시 놓아야 한다."""
        self.assertIn("followCard();", fn("render"))

    def test_the_position_math_lives_in_one_place(self):
        """두 벌이면 한쪽만 자란다 — 이 저장소가 다섯 번 겪은 그것이다."""
        self.assertEqual(CODE.count("positionCard("), 3, "정의 1 + 부르는 곳 2(showCard·followCard)")
        self.assertIn("positionCard(", fn("showCard"))
        self.assertIn("positionCard(", fn("followCard"))

    def test_it_anchors_to_where_the_pin_is_now(self):
        """🔴 둘째 인자는 **「핀이 도착할 자리」**이고, 붙이는 자리와 **카드 높이 상한**을 같이 정한다.
        지도가 미끄러지는 동안에는 `pinTarget()` 이지만 여기서는 **이미 움직인 뒤**다.

        ⚠️ 두 번 틀렸다: `pinTarget()` 을 쓰니 가로가 3 → **-107px**, `null` 로 바꾸니
        높이 상한이 풀려 카드가 핀 **아래로 뒤집혔다**(세로 587px)."""
        self.assertIn("positionCard(ac, expandedI !== null ? svgToClient(ac.x, ac.y) : null)",
                      fn("followCard"))
        self.assertNotIn("pinTarget()", body("followCard"))

    def test_dragging_still_closes_the_detail(self):
        """PH5c 의 규칙은 그대로다 — **끄는 동안**엔 미니카드만 따라가고 상세는 닫힌다.
        창 크기 변경은 **한 번의 점프**라 그 이유가 적용되지 않는다(기획 동의 2026-10-01)."""
        self.assertIn("if (expandedI !== null) closeByUser();", fn("takeView"))
        self.assertIn("if (expandedI === null) followCard();", fn("moveOnly"))

    def test_the_arc_follows_without_restarting(self):
        self.assertIn("arcPath(ac)", fn("followCard"))
        self.assertNotIn("drawArc", body("followCard"))

    def test_nothing_happens_without_an_open_card(self):
        """열린 카드가 없으면 아무 일도 안 한다 — `render()` 는 늘 돈다."""
        f = fn("followCard")
        self.assertIn('if (active === null || !hc.classList.contains("show")) return;', f)
        self.assertIn("if (!ac || ac.x == null) return;", f)


if __name__ == "__main__":
    unittest.main()
