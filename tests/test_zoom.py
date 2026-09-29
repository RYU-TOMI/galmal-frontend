# -*- coding: utf-8 -*-
"""자유 줌·팬 — PH5c (SPEC §CH1, 2026-09-22 사용자 확정 · `DECISIONS.md` 2026-09-22 (1)).

사용자: 「지도를 좀 둘러보려고 했는데 안 돼」(2026-09-21 아이폰).
2026-08-22 의 「자유 줌 기각」을 뒤집은 결정이다.

여기서 잠그는 것 다섯:

  ① **뷰의 주인이 둘이다** — `userV`(사용자가 만진 것) vs 단계에서 파생한 것.
     `render()` 는 정렬·필터·출발지 등 **뷰와 무관한 이유로도** 불린다. 그때마다 단계 뷰로 되돌리면
     **사용자가 맞춰 둔 화면을 우리가 뺏는다.** 버리는 자리는 **단 둘** — 단계 버튼과 필터를 켜는 순간.
  ② **커서 아래의 땅이 머문다** — 화면 가운데 기준으로 확대하면 보려던 곳이 옆으로 흘러간다.
  ③ **한계는 값을 박지 않고 단계 뷰에서 구한다** — 하한 `아주 멀리`, 상한 `가까운 곳`의 4배.
     둘 다 출발지·화면 비율에 따라 달라진다.
  ④ **라벨은 지금 배율에서 다시 잡는다** — 규칙은 그대로고(싼 곳부터·겹치면 안 붙임·핀은 남김)
     **언제 도느냐**만 고쳤다. 매 프레임은 안 된다: `getBoundingClientRect` 를 5번 읽는다.
  ⑤ **무대·UI 상자는 캐시한다** — 지도가 움직인다고 무대와 도크가 움직이지 않는다.
     이게 「핀 24개가 76개보다 비싸다」의 원인이었다(기획 숙제, 2026-09-28).

화면에서의 확인은 CDP 로 따로 한다(`FRONTEND.md` §3). 여기서는 **규칙의 모양**을 본다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()
HOME = io.open(os.path.join(ROOT, "site", "home.py"), encoding="utf-8").read()

CODE = re.sub(r"(?m)^\s*//.*$", "", JS)


def _fn(name):
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def _rule(sel):
    m = re.search(re.escape(sel) + r"\{([^}]*)\}", CSS)
    return m.group(1) if m else None


class ViewOwnerTest(unittest.TestCase):
    """① 사용자가 만진 뷰를 우리가 뺏지 않는다."""

    def test_render_prefers_the_user_view(self):
        self.assertIn("var v = userV || viewOf(STAGES[stageIdx]);", CODE)

    def test_only_two_places_drop_it(self):
        """🔴 **버리는 자리가 늘면 그만큼 뷰를 뺏는 길이 생긴다.** 지금은 둘뿐이다 —
        단계 버튼(사용자가 「여기로 가겠다」고 말한 자리)과 필터를 **켜는 순간**(한 번만 넓힌다)."""
        # ⚠️ 선언(`var userV = null`)은 버리는 자리가 아니다 — 처음 셀 때 그걸 같이 세서 틀렸다.
        drops = re.findall(r"(?<!var )userV = null", CODE)
        self.assertEqual(len(drops), 2, "userV 를 버리는 자리가 %d 곳이다" % len(drops))
        self.assertIn("userV = null; hadUser = false;", _fn("setStage"))
        self.assertIn("userV = null; hadUser = false; }", _fn("applyFilter"))

    def test_filter_widens_once_not_locks(self):
        """B70 이 다시 나지 않는다 — 켜는 순간만 옮기고, 그 뒤 조작은 전부 먹는다."""
        ap = _fn("applyFilter")
        self.assertIn("nowFiltering && !wasFiltering", ap)
        self.assertNotIn("stageIdx = 0", ap, "끌 때 되돌리면 사용자가 만진 뷰를 뺏는 것이다")


class ZoomMathTest(unittest.TestCase):
    """② 커서 고정 · ③ 한계."""

    def test_zoom_keeps_the_point_under_the_cursor(self):
        body = _fn("zoomTarget")
        self.assertIsNotNone(body, "zoomTarget() 를 못 찾았다")
        self.assertIn("clientToSvg", body)
        self.assertIn("(p.x - XF.tx) / k0", body)      # 커서 밑의 기준 평면 점
        self.assertIn("p.x - bx * k1", body)           # 그 점을 같은 화면 자리에 되돌린다

    def test_client_to_svg_uses_the_browser_matrix(self):
        """`preserveAspectRatio=\"…slice\"` 라 단순 비율이 아니다 — 손으로 계산하면 잘린 쪽에서 어긋난다."""
        self.assertIn("getScreenCTM().inverse()", _fn("clientToSvg"))

    def test_limits_come_from_the_stage_views(self):
        """🔴 **값을 박지 않는다.** 하한·상한 모두 출발지·화면 비율에 따라 달라진다."""
        body = _fn("kBounds")
        self.assertIsNotNone(body)
        self.assertIn('viewOf("far").scale', body)
        self.assertIn('viewOf("near").scale * 4', body)

    def test_clamp_is_used_everywhere_zoom_happens(self):
        self.assertIn("clampK(k0 * factor)", _fn("zoomTarget"))


class InputTest(unittest.TestCase):
    """휠·드래그·핀치·버튼·더블클릭 — 들어오는 길이 다섯이다."""

    def test_listeners_are_on_the_svg_not_the_stage(self):
        """🔴 무대에 걸면 **필터 도크 위에서 굴려도 지도가 움직인다** — 도크는 안에서 스크롤된다(B54)."""
        for ev in ("wheel", "pointerdown", "pointermove", "dblclick"):
            self.assertIn('svg.addEventListener("%s"' % ev, CODE, ev)

    def test_trackpad_two_fingers_pan_and_pinch_zooms(self):
        """사용자: 「노트북인데 손가락 두 개로 움직일 수 있으면 좋겠다」(2026-09-28).
        ⚠️ 휠인지 트랙패드인지 **브라우저가 안 알려준다** — 표준에 그 구분이 없어 어림잡는다."""
        m = re.search(r'svg\.addEventListener\("wheel", function \(e\) \{(.*?)\n  \}, \{ passive: false \}\);', JS, re.S)
        self.assertIsNotNone(m, "wheel 핸들러를 못 찾았다")
        body = re.sub(r"(?m)^\s*//.*$", "", m.group(1))
        self.assertIn("e.ctrlKey", body)          # 핀치
        self.assertIn("panByClient(-dx, -dy)", body)
        self.assertIn("dx === 0", body)           # 가로가 없으면 휠로 본다

    def test_drag_does_not_kill_click(self):
        """핀 클릭(상세)·배경 클릭(닫기)이 살아 있어야 하고, 끌고 놓을 때는 안 닫혀야 한다.
        **움직인 거리**로 가른다 — 시트 탭 판정과 같은 축."""
        self.assertIn("var PAN_SLOP = 6", CODE)
        self.assertIn("moved < PAN_SLOP", CODE)
        self.assertIn("moved >= PAN_SLOP", CODE)

    def test_plus_is_zoom_in(self):
        """사용자: 「+,- 가 반대로 된 듯」(2026-09-28). 예전엔 단계 스테퍼라 `＋` 가 「더 멀리」였다."""
        m = re.search(r'data-step="in"[^>]*>\s*<i>(.)</i><em>([^<]*)</em>', HOME)
        self.assertIsNotNone(m, "in 버튼을 못 찾았다")
        self.assertEqual(m.group(1), "＋")
        self.assertEqual(m.group(2), "가까이")
        self.assertLess(HOME.index('data-step="in"'), HOME.index('data-step="out"'), "＋ 가 위다")

    def test_buttons_and_dblclick_glide(self):
        """사용자: 「띡띡 움직이는 느낌」. 휠·드래그는 이미 연속이라 **한 번에 튀는 것**만 부드럽게 한다."""
        self.assertIn("tweenUser(v, 220)", CODE)
        self.assertEqual(CODE.count("tweenUser(v, 220)"), 2, "버튼과 더블클릭 둘 다")
        self.assertIn("reduceMotion()", _fn("tweenUser"))


class FollowTest(unittest.TestCase):
    """지도가 움직일 때 딸려 움직여야 하는 것들."""

    def test_detail_closes_but_mini_card_follows(self):
        """🔴 **둘이 다르다.** 미니카드는 「그 핀이 무엇인지」 가리키므로 따라가야 하고,
        펼친 상세는 길고 결정하는 자리라 따라다니면 어지럽다 — 닫는다."""
        tv = _fn("takeView")
        self.assertIn("if (expandedI !== null) closeByUser();", tv)
        mv = _fn("moveOnly")
        self.assertIn("expandedI === null", mv)
        self.assertIn("positionCard(ac, null)", mv)

    def test_arc_moves_without_restarting_its_draw(self):
        """끄는 동안 매 프레임 `drawArc` 를 부르면 선이 계속 처음부터 그려져 깜빡인다."""
        self.assertIn("arcPath(ac)", _fn("moveOnly"))
        self.assertNotIn("drawArc", _fn("moveOnly"))

    def test_text_is_not_selected_while_dragging(self):
        """사용자: 「잡고 움직이면 텍스트들이 드래그됨」. 지도에는 도시 이름이 `<text>` 로 있다.
        한 겹으로는 부족하다 — 포인터를 잡아 두면 커서가 피드로 넘어가도 **선택은 번진다.**"""
        self.assertIn("user-select:none", _rule("svg.map"))
        self.assertIn("body.dragging, body.dragging *", CSS)
        self.assertIn('document.body.classList.add("dragging")', CODE)
        self.assertIn('svg.addEventListener("dragstart"', CODE)


class LabelTest(unittest.TestCase):
    """④ 라벨은 지금 배율에서 · ⑤ 무대·UI 상자는 캐시."""

    def test_placement_rule_is_unchanged(self):
        """🔴 **규칙은 안 바꿨다.** 고친 것은 **언제 도느냐**뿐이다."""
        body = _fn("placeLabels")
        self.assertIsNotNone(body)
        self.assertIn("num(a.price) - num(b.price)", body)   # 싼 곳부터
        self.assertIn("c._lab = spots[0]; c._lab.off = true;", body)   # 막히면 이름만 생략, 핀은 남는다

    def test_relabel_is_throttled_but_exact_when_it_stops(self):
        """매 프레임은 안 된다 — `getBoundingClientRect` 를 5번 읽는다.
        끄는 동안은 「대충 맞게」, 멈추면 「정확하게」. 사람은 움직이는 중의 라벨을 안 읽는다."""
        body = _fn("relabel")
        self.assertIsNotNone(body)
        self.assertIn("LAB_MS", body)
        self.assertIn("placeLabels(list)", body)
        self.assertIn("relabel(false)", CODE)        # 움직이는 동안은 라벨만, 대충
        # 멎으면 라벨보다 더 한다 — `settleView()` 가 `render()` 로 **보이는 딜부터** 다시 고른다
        # (라벨은 `render()` 가 같이 잡는다). 세 자리: 손 뗌 · 휠 멎음 · 버튼 줌 끝.
        self.assertEqual(CODE.count("settleView()"), 4, "정의 1 + 부르는 곳 3")

    def test_settling_repicks_the_visible_deals(self):
        """🔴 **더 멀리 갔는데 점이 줄어들면 안 된다**(§CH1 LOD, 2026-09-01).

        어떤 딜이 지도에 있느냐는 `visibleCities()` 가 정하고 그건 `render()` 에서만 돈다.
        자유 줌 전에는 뷰가 단계 버튼으로만 바뀌어 늘 `render()` 를 거쳤는데,
        자유 줌이 생기자 **뷰만 바뀌고 딜 집합은 그대로**가 됐다 —
        실측: 「가까운 곳」에서 휠로 끝까지 축소하면 배율은 170(아주 멀리와 같다)인데 핀이 **25개**였다
        (단계 버튼으로 가면 78개). 피드도 25장이었다. 사용자가 「줌아웃하면 핀도 사라져야 하지 않나」
        라고 물어서 재 보다 찾았다 — **묻는 방향과 반대쪽에 있던 버그다.**

        ⚠️ 움직이는 **중에는** 안 한다 — `render()` 는 핀·피드를 통째로 다시 만든다."""
        body = _fn("settleView")
        self.assertIsNotNone(body, "settleView() 를 못 찾았다")
        self.assertIn("if (!userV) return;", body)   # 단계 뷰면 이미 render() 를 거쳐 왔다
        self.assertIn("render()", body)
        tv = _fn("takeView")
        self.assertNotIn("settleView", tv, "움직이는 중에 부르면 매 프레임 피드를 갈아엎는다")

    def test_geometry_is_cached(self):
        """🔴 **「핀 24개가 76개보다 비싸다」의 원인이 여기였다**(기획 숙제 2026-09-28).
        지도가 움직인다고 무대와 도크가 움직이지 않는데 매번 레이아웃을 깨웠다.
        실측: 캐시 뒤 6배 느린 CPU 에서 25핀 3.8ms · 78핀 6.3ms — **역전이 사라지고 핀 수를 따라간다.**"""
        self.assertIn("var geoVer = 0, bandC = null, uiC = null;", CODE)
        self.assertIn("if (bandC) return bandC;", _fn("usableBand"))
        self.assertIn("if (uiC) return uiC;", _fn("uiBoxes"))

    def test_cache_is_dropped_where_geometry_really_changes(self):
        """🔒 버리는 자리가 빠지면 **낡은 상자로 라벨을 놓는다** — 도크 아래에 글자가 깔린다.
        바뀌는 건 창 크기와 `render()`(도크 높이·안내 띠) 둘뿐이다."""
        self.assertIn("geoBump()", _fn("render"))
        m = re.search(r'window\.addEventListener\("resize", function \(\) \{(.*?)\n  \}\);', JS, re.S)
        self.assertIsNotNone(m)
        self.assertIn("geoBump()", m.group(1))
        self.assertEqual(CODE.count("geoBump()"), 3, "정의 1 + 부르는 곳 2")


class StepperTest(unittest.TestCase):
    """단계 버튼은 남는다 — 사용자 결정(2026-09-28). 다만 **역할이 바뀌었다.**"""

    def test_stage_bar_survives(self):
        """사용자: 「굳이 필요한지 모르겠다」 → 재 보니 **데이터에는 영향이 없다**(피드는 화면 안에
        들어오는가로 정해진다). 그래도 남긴다: 세 뷰로 가는 길 · 처음 온 사람에게 쓰는 법 ·
        **모바일에서 이 셋이 거리 필터로 내려가므로 없애면 두 화면의 어휘가 갈린다.**"""
        self.assertIn('.stagebar .pill', CODE)
        self.assertIn("setStage(idx)", CODE)

    def test_stage_light_goes_off_when_the_user_takes_over(self):
        """사용자가 만진 뷰는 어느 단계도 아니다 — 불이 켜져 있으면 **거짓말**이 된다."""
        self.assertIn('classList.toggle("on", !userV && i === stageIdx)', CODE)

    def test_ui_sync_runs_only_on_change(self):
        """🔴 뷰가 움직일 때마다 부르면 `syncStepper()` 가 `viewOf()` 를 두 번 불러 무대를 잰다 —
        팬 한 번에 레이아웃이 여러 번 깨진다."""
        tv = _fn("takeView")
        self.assertIn("if (!hadUser)", tv)
        self.assertIn("if (lim !== atLimit)", tv)


if __name__ == "__main__":
    unittest.main()
