# -*- coding: utf-8 -*-
"""리사이즈 — 창 크기 한 번 바뀔 때 `render()` 는 **한 번** 돈다 (B52-③, CH11 T2).

`resize` 리스너가 둘이었다. 하나는 `geoBump()` + 120ms 눌림(debounce) 뒤 `render()`,
다른 하나는 모바일 시트 높이를 `setSheet(…, true)` 로 다시 물렸다 — 그런데 `setSheet` 은
전환이 끝나는 300ms 뒤에 **자기도 `render()` 를 부른다.**

헤드리스 크롬 실측(2026-10-05, 390×844 → 390×640):

| 상황 | 옛 코드 | 고친 뒤 |
|---|---|---|
| 모바일, 리사이즈 이벤트 1번 | `render` **2번** | 1번 |
| 모바일, 연달아 12번(창을 끄는 동안) | `render` **13번** | **1번** |
| 데스크톱 1번 / 12번 | 1번 / 1번 | 1번 / 1번 |

모바일 13번이 핵심이다 — 시트 쪽 리스너에는 **눌림이 없어서** 이벤트 수만큼 타이머가 쌓였다.
브라우저는 창을 끄는 동안 초당 수십 번 보낸다. `render()` 는 핀·호·카드·라벨을 전부 다시 그린다.

끝난 화면은 같다(실측: `--sheet-h` 340px · 무대 높이 200 · 시트 탭 340↔683 · `sheet-drag` 토글 —
옛 코드와 **같은 값**). 그래서 여기서 지키는 건 모양이 아니라 **몇 번 도는가**다.

🔴 순서도 잠근다: 시트 높이가 무대 높이(`--sheet-h`)를 정하므로 **재기 전에** 먹여야 한다.
뒤로 가면 `render()` 가 **지나가는 높이**로 중심·배율을 잡는다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8") as f:
    JS = f.read()
CODE = re.sub(r"(?m)^\s*//.*$", "", JS)        # 주석이 「없음」 주장을 통과시키는 일을 막는다


def body(name):
    """`function name(` 의 중괄호 균형을 세어 본문만 떼낸다."""
    i = CODE.index("function " + name + "(")
    d, j, started = 0, i, False
    while j < len(CODE):
        if CODE[j] == "{":
            d += 1; started = True
        elif CODE[j] == "}":
            d -= 1
            if started and d == 0:
                return CODE[i:j + 1]
        j += 1
    raise AssertionError(name + " 본문을 못 찾았다")


def listener_body():
    """`resize` 리스너 본문만 떼낸다. 900자 창으로 자르면 **창 밖으로 밀어내는 돌연변이**를
    못 잡는다 — 중괄호를 센다."""
    i = CODE.index('addEventListener("resize"')
    d, j, started = 0, i, False
    while j < len(CODE):
        if CODE[j] == "{":
            d += 1; started = True
        elif CODE[j] == "}":
            d -= 1
            if started and d == 0:
                return CODE[i:j + 1]
        j += 1
    raise AssertionError("리스너 본문을 못 찾았다")


class OneListenerTest(unittest.TestCase):

    def test_there_is_exactly_one(self):
        self.assertEqual(CODE.count('addEventListener("resize"'), 1)

    def test_it_is_debounced(self):
        """눌림이 없으면 이벤트 수만큼 돈다 — 그게 13번의 원인이었다."""
        seg = listener_body()
        self.assertIn("clearTimeout(rzT)", seg)
        self.assertIn("rzT = setTimeout(", seg)

    def test_mobile_waits_for_the_transition(self):
        """모바일은 시트가 `.28s` 로 끌린다 — 그보다 짧게 재면 지나가는 높이를 잡는다."""
        seg = listener_body()
        m = re.search(r"isMobile\(\) \? (\d+) : (\d+)\)", seg)
        self.assertIsNotNone(m, "모바일/데스크톱 대기시간이 갈려 있지 않다")
        mob, desk = int(m.group(1)), int(m.group(2))
        self.assertGreater(mob, 280, "`.feed` 전환이 .28s 다 — 그보다 길어야 한다")
        self.assertEqual(desk, 120, "데스크톱은 전환이 없다 — 예전 값 그대로")

    def test_the_sheet_height_is_applied_before_the_timer(self):
        seg = listener_body()
        self.assertLess(seg.index("applySheet(sheetH)"), seg.index("rzT = setTimeout("))

    def test_the_sheet_height_is_applied_right_away(self):
        """🔴 **순서만 보면 속는다.** `applySheet` 을 `setTimeout` 으로 감싸면 글자 순서는
        그대로인데 실행은 `render()` 뒤로 간다 — 돌연변이 하나가 실제로 그렇게 통과했다.
        그래서 리스너 안의 타이머는 **눌림 하나뿐**이라고 못 박는다."""
        seg = listener_body()
        self.assertEqual(seg.count("setTimeout("), 1,
                         "리스너 안 타이머는 눌림 하나뿐이어야 한다")
        self.assertIn("rzT = setTimeout(", seg)

    def test_the_desktop_branch_still_clears_the_sheet(self):
        """데스크톱으로 넓히면 시트 흔적을 지운다 — 안 지우면 무대 아래가 비어 남는다."""
        seg = listener_body()
        self.assertIn('feed.style.height = ""', seg)
        self.assertIn('removeProperty("--sheet-h")', seg)


class ApplySheetTest(unittest.TestCase):
    """🔴 **높이 먹이기와 다시 그리기를 갈라 놨다** — 섞여 있어서 리스너를 합칠 수 없었다."""

    def test_it_does_not_render(self):
        self.assertNotIn("render(", body("applySheet"))

    def test_it_sets_both_the_height_and_the_variable(self):
        """무대는 `--sheet-h` 로, 피드는 실제 높이로 움직인다 — 하나만 바꾸면 어긋난다."""
        b = body("applySheet")
        self.assertIn('feed.style.height = h + "px"', b)
        self.assertIn('setProperty("--sheet-h", h + "px")', b)
        self.assertIn("sheet-full", b)

    def test_it_clamps_to_the_snaps(self):
        """창이 작아지면 상한도 작아진다 — 안 물리면 시트가 화면보다 커진다."""
        b = body("applySheet")
        self.assertIn("sheetSnaps()", b)
        self.assertIn("Math.max(sn[0], Math.min(sn[2], h))", b)

    def test_set_sheet_still_owns_the_drag_class_and_the_render(self):
        """`setSheet` 의 계약은 그대로다 — 끌 때는 전환을 끄고, 놓을 때 한 번 그린다."""
        b = body("setSheet")
        self.assertIn("if (!isMobile()) return;", b)
        self.assertIn('if (!animate) document.body.classList.add("sheet-drag")', b)
        self.assertIn("applySheet(h)", b)
        self.assertIn('classList.remove("sheet-drag")', b)
        self.assertIn("setTimeout(function () { render(); }, 300)", b)
        self.assertLess(b.index('classList.add("sheet-drag")'), b.index("applySheet(h)"),
                        "높이보다 먼저 전환을 꺼야 한다 — 뒤면 첫 프레임이 끌린다")


if __name__ == "__main__":
    unittest.main()
