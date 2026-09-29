# -*- coding: utf-8 -*-
"""항로선 — CH8 T1 (사용자 2026-09-29: 「그 점에 호버링한채로 줌인 줌아웃하면 경로선이 이상해져」).

**원인은 점선 패턴이 선 길이를 못 따라간 것이다.** 실측(대조군, 고치기 전):
휠 153프레임 중 **86프레임**에서 `stroke-dasharray` 101.95 인데 실제 길이 259.9 —
101.95 그리고 101.95 띄고… 해서 **끊긴 선**이 된다. 끝점은 핀에 붙어 있었고(어긋남 0.00px)
활성 도시도 안 바뀌었다 — **보이는 것만** 깨졌다.

드래그에서는 고치기 전에도 0프레임이었다. 드래그는 배율을 안 바꿔 길이가 13→26 밖에
안 움직이기 때문이다 — **그래서 사용자도 줌에서만 봤다.** 조작마다 따로 재야 이걸 안다.

고치는 길 셋을 다 재고 골랐다:
  ⓐ 움직이는 동안 숨긴다 — 비용 0, 그런데 선이 사라진다 (사용자 1안)
  ⓑ 매 프레임 길이를 다시 재 패턴을 맞춘다 — 6배 느린 CPU 에서 **+0.34ms**/프레임
  ⓒ `pathLength` 로 길이를 **고정**한다 — 길이를 아예 안 재므로 **추가 비용 0**, 줌 중에도 정확
→ ⓒ. (사용자가 준 두 안을 둘 다 재고 더 나은 쪽을 골랐다고 보고했다.)

여기서 잠그는 것 넷:
  ① 실제 길이를 **재지 않는다** — `getTotalLength` 가 코드에서 사라져야 한다
  ② 되감기가 **한 군데**다 — 두 벌이면 한쪽만 고쳐진다
  ③ 같은 도시면 **다시 그리지 않는다** — 줌 한 번에 2번 다시 그려 깜빡였다
  ④ 트윈 중에도 항로는 **보인다** — 숨기면 지역 칩으로 날아가는 동안 「어디서 어디로」가 사라진다
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()


def _body(name):
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


class LengthTest(unittest.TestCase):
    """① 실제 길이를 재지 않는다 — 이게 버그의 뿌리였다."""

    def test_real_length_is_never_measured(self):
        """🔴 `getTotalLength` 가 **한 곳도** 없어야 한다.

        되돌리려는 사람이 「한 군데만 쓰면 되지」로 다시 넣는 것을 막는다 — 그 한 군데가
        패턴을 실제 길이에 묶는 순간 줌 중에 다시 끊긴다."""
        self.assertNotIn("getTotalLength", JS,
                         "실제 길이를 다시 재고 있다 — 패턴이 또 뒤처진다")

    def test_pattern_length_is_fixed_and_shared(self):
        """패턴 길이는 **상수 하나**다. 숫자를 여기저기 박으면 한쪽만 바뀐다."""
        self.assertRegex(JS, r"var ARC_LEN = \d+;")
        d = _body("drawArc")
        self.assertIn('arc.setAttribute("pathLength", ARC_LEN)', d)
        self.assertIn("strokeDasharray = ARC_LEN", d)
        self.assertIn("strokeDashoffset = ARC_LEN", d)   # 감긴 상태에서 출발한다

    def test_the_drawn_path_still_follows_the_pin(self):
        """길이를 고정해도 **모양은 따라가야** 한다 — 지도가 움직이면 `d` 를 고친다."""
        self.assertIn('arc.setAttribute("d", arcPath(ac))', JS)


class RewindTest(unittest.TestCase):
    """② 되감기가 한 군데다."""

    def test_rewind_lives_in_one_place(self):
        self.assertEqual(JS.count("function hideArc("), 1)
        self.assertGreaterEqual(JS.count("hideArc("), 3)          # 정의 1 + 부르는 곳 2 이상
        # 인라인 되감기가 다시 생기면 잡는다 — `hideArc` 안에서만 offset 을 ARC_LEN 으로 되돌린다.
        outside = JS.replace(_body("hideArc"), "")
        self.assertNotIn("strokeDashoffset = ARC_LEN", outside.replace(_body("drawArc"), ""))

    def test_hiding_forgets_which_city_was_drawn(self):
        """되감은 뒤에는 「그려져 있다」가 거짓이다 — 같은 도시에 다시 올리면 **다시 그려져야** 한다.
        안 잊으면 카드를 닫았다 여는데 선이 안 나타난다."""
        for f in ("clearHi", "collapse"):
            b = _body(f)
            self.assertIn("hideArc(", b, f + " 가 항로를 안 되감는다")
            self.assertIn("arcAt = null", b, f + " 가 그려진 도시를 안 잊는다")


class RedrawTest(unittest.TestCase):
    """③ 같은 도시면 다시 그리지 않는다."""

    def test_same_city_keeps_the_animation(self):
        b = _body("showCard")
        self.assertIn("arcAt === i", b)
        self.assertIn('arc.setAttribute("d", arcPath(c))', b)     # 모양만 고친다
        self.assertRegex(b, r"else \{ drawArc\(c\); arcAt = i; \}")

    def test_the_mobile_path_uses_the_same_gate(self):
        """길이 둘이면 한쪽만 고쳐진다 — 모바일 핀 탭도 같은 문을 지난다."""
        b = _body("pinTap")
        self.assertIn("arcAt !== i", b)
        self.assertIn("arcAt = i", b)


class TweenTest(unittest.TestCase):
    """④ 트윈 중에도 항로는 보인다."""

    def test_tween_hides_labels_but_not_the_route(self):
        m = re.search(r"^\.tweening [^\n{]*\{[^}]*\}", CSS, re.M)
        self.assertIsNotNone(m, ".tweening 규칙이 없다")
        rule = m.group(0)
        self.assertIn(".plabel", rule)          # 움직이는 글자는 못 읽는다 — 글자는 계속 숨긴다
        self.assertNotIn(".arc", rule,
                         "항로를 숨기고 있다 — 날아가는 동안 「어디서 어디로」가 사라진다")

    def test_the_reason_is_kept_next_to_the_rule(self):
        """되돌리려는 사람이 **왜 바뀌었는지**를 먼저 읽게 한다."""
        self.assertIn("pathLength", CSS)


if __name__ == "__main__":
    unittest.main()
