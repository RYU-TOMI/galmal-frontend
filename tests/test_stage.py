# -*- coding: utf-8 -*-
"""거리 단계 — **버튼이 동작하는데 화면만 안 따라오는** 상태를 막는다 (BACKLOG B70).

2026-09-22 사용자가 실사용 중 찾았다: 「날짜를 지정하면 지도가 줌아웃 되는데 **다시 가까이 갈 방법이 없어**」.
`render()` 가 `viewOf(anyFilter() ? "far" : STAGES[stageIdx])` 로 **필터 중에는 뷰를 아주 멀리에 잠갔다.**
`setStage()`·스테퍼는 `stageIdx` 를 바꾸고 단계바 불도 켜지는데 `render()` 가 그 값을 안 봤다 —
**예외도 안 나고 버튼도 눌리고 사람만 「왜 안 움직이지」 한다.** 거기에 CSS 가 단계 버튼을 숨기고 있어서
그 시점 스테퍼의 `－가까이` 는 잠긴 상태였다 — **누를 수 있는 버튼이 하나도 없었다.**

여기서 잠그는 것:
  1. 뷰는 **언제나** `stageIdx` 를 따른다 — `render()` 안에서 `anyFilter()` 로 뷰를 고르지 않는다.
  2. 「아주 멀리로 옮기기」는 **필터를 켜는 순간 한 번**뿐이다(`applyFilter`), 끌 때 되돌리지 않는다.
  3. 필터 중에도 **단계 버튼이 보인다**(CSS 로 숨기지 않는다).
  4. 단계바의 「켜짐」은 **한 곳에서만** 켠다 — 여러 곳에서 켜면 새 경로가 생길 때 불과 지도가 어긋난다
     (고치는 중 실제로 그랬다: 필터를 켠 직후 지도는 아주 멀리인데 불은 가까운 곳).

Node 빌드가 없는 저장소라 JS 를 정규식으로 읽는다. 화면에서의 확인은 CDP 로 따로 한다(`FRONTEND.md` §3).
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()


def fn(js, name):
    """`function name(...) { … }` 한 덩이 — 주석은 걷어낸다(주석 속 옛 코드에 속지 않는다)."""
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), js, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def problems(js, css):
    """B70 이 되살아났는지. 맞으면 빈 목록."""
    out = []
    render = fn(js, "render")
    if render is None:
        return ["render() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다"]

    # 1. 뷰가 필터에 잠기지 않는다
    m = re.search(r"viewOf\(([^;]*?)\)", render)
    if not m:
        out.append("render() 에서 viewOf(...) 를 못 찾았다")
    else:
        arg = m.group(1)
        if "anyFilter" in arg:
            out.append("render() 가 `viewOf(%s)` — 필터로 뷰를 고르면 **단계 버튼이 화면을 못 바꾼다**(B70)" % arg.strip())
        if "STAGES[stageIdx]" not in arg:
            out.append("render() 의 뷰가 `STAGES[stageIdx]` 를 안 쓴다 — 무엇을 따르는지 알 수 없다")

    # 2. 옮기는 것은 「켜는 순간」 한 번
    ap = fn(js, "applyFilter")
    if ap is None:
        out.append("applyFilter() 를 못 찾았다")
    else:
        if "stageIdx" not in ap:
            out.append("applyFilter() 가 stageIdx 를 안 건드린다 — 필터를 켤 때 아주 멀리로 옮기는 자리가 없다")
        elif not re.search(r"!\s*wasFiltering|!\s*\w*[Ff]iltering", ap):
            out.append("applyFilter() 가 **켜는 순간**(꺼짐→켜짐)을 가리지 않는다 — 매번 옮기면 다시 잠금이다")
        if re.search(r"stageIdx\s*=\s*0", ap):
            out.append("applyFilter() 가 stageIdx 를 0 으로 되돌린다 — 끌 때 뷰를 되돌리지 않기로 했다")

    # 3. 필터 중에도 단계 버튼이 보인다
    c = strip_comments(css)
    if re.search(r"\.stagebar\.allregions\s+\.pill\s*\{[^}]*display\s*:\s*none", c):
        out.append("CSS 가 필터 중 단계 버튼을 숨긴다 — 그러면 누를 버튼이 없다(B70)")

    # 4. 「켜짐」을 켜는 곳이 하나
    lit = len(re.findall(r'classList\.toggle\("on",\s*\w+\s*===\s*(?:idx|stageIdx)\)', re.sub(r"(?m)^\s*//.*$", "", js)))
    if lit == 0:
        out.append("단계바의 「켜짐」을 켜는 곳이 없다")
    elif lit > 1:
        out.append("단계바의 「켜짐」을 켜는 곳이 %d 곳이다 — 한 곳이어야 새 경로에서 불과 지도가 안 어긋난다" % lit)
    sb = fn(js, "syncStageBar")
    if sb is None:
        out.append("syncStageBar() 를 못 찾았다")
    elif 'classList.toggle("on"' not in sb:
        out.append("단계바의 「켜짐」이 syncStageBar() 밖에 있다 — render() 가 늘 부르는 자리여야 한다")
    return out


class StageTest(unittest.TestCase):

    def test_now_clean(self):
        self.assertEqual(problems(JS, CSS), [])

    def test_view_locked_to_far_is_caught(self):
        """탐침 — 2026-09-22 까지 실제로 있던 코드. 이게 B70 이다."""
        old = JS.replace("var v = viewOf(STAGES[stageIdx]);",
                         'var v = viewOf(anyFilter() ? "far" : STAGES[stageIdx]);')
        self.assertNotEqual(old, JS, "탐침이 아무것도 안 바꿨다 — render() 모양이 달라졌으면 탐침을 고친다")
        bad = problems(old, CSS)
        self.assertTrue(any("단계 버튼이 화면을 못 바꾼다" in b for b in bad), bad)

    def test_hidden_stage_buttons_are_caught(self):
        old = CSS + "\n.stagebar.allregions .pill{display:none}"
        self.assertTrue(any("누를 버튼이 없다" in b for b in problems(JS, old)))

    def test_moving_every_time_is_caught(self):
        """탐침 — 켤 때마다(=조건 없이) 옮기면 그것도 잠금이다."""
        ap = fn(JS, "applyFilter")
        self.assertIn("wasFiltering", ap)
        old = JS.replace("if (nowFiltering && !wasFiltering) stageIdx = STAGES.length - 1;",
                         "if (nowFiltering) stageIdx = STAGES.length - 1;")
        self.assertNotEqual(old, JS)
        self.assertTrue(any("켜는 순간" in b for b in problems(old, CSS)))

    def test_two_places_lighting_the_pill_is_caught(self):
        """탐침 — 불을 켜는 곳이 둘이면 잡는다. 고치는 중 실제로 어긋났던 자리다."""
        old = JS.replace("  function setStage(idx) {",
                         '  function setStage(idx) {\n    var bs=document.querySelectorAll(".stagebar .pill");\n'
                         '    for (var k=0;k<bs.length;k++) bs[k].classList.toggle("on", k === idx);')
        self.assertNotEqual(old, JS)
        self.assertTrue(any("한 곳이어야" in b for b in problems(old, CSS)))

    def test_unreadable_is_failure_not_pass(self):
        self.assertTrue(problems(JS.replace("function render()", "function draw()"), CSS))


if __name__ == "__main__":
    unittest.main()
