# -*- coding: utf-8 -*-
"""카드 정리 셋 — 호버 미니카드 · 공유 아이콘 · ⓘ 설명 (사용자 2026-09-28, 기획 승인).

세 가지가 한 챕터인 이유는 **같은 증상**을 고치기 때문이다: 확장/미니 카드가 **말이 너무 많거나
있어야 할 때 없고 없어야 할 때 있다.**

  ① 호버 미니카드가 **안 사라진다** — 핀에서 벗어나도, 심지어 출발지를 바꿔도 남았다.
  ② 공유가 **전폭 버튼**이라 상세에서 가장 큰 요소였다. 공유는 부차적 행동이다.
  ③ 「중앙값」이 전문용어다 — **뜻만** ⓘ 뒤로 접는다.

🔴 **이 파일이 지키는 가장 중요한 것은 ③의 경계다.** 확장 상세 420자 중 **169자(40%)가 고지**인데,
「글자가 많다」를 고지를 접어서 푸는 길이 항상 열려 있다. `(광고)` 수수료 고지와 「조회 시점 기준」은
법적 항목이고(`SESSIONS.md`) B61 이 순서까지 정했다. **숨긴 고지는 고지가 아니다.**
그래서 「ⓘ 안에 고지 문구가 들어갔나」를 **문자열로 직접** 본다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()

# 🔴 **법적 고지** — 이 문구들은 **절대** ⓘ 뒤로 못 들어간다.
# 제휴 수수료 고지와 「조회 시점 기준」은 `SESSIONS.md` 법적 항목이고 B61 이 순서까지 정했다.
AD_NOTE = "(광고) 표시는 예약하시면 저희가 수수료를 받는 링크예요"
PRICE_NOTE = "항공권 가격은 예약 사이트가 마지막으로 조회한 값이라"
SCAN_NOTE = "위 가격은 발견가(스캔 시점)"
DISCLOSURES = (AD_NOTE, PRICE_NOTE, SCAN_NOTE)

# ⚠️ `가격은 성인 1인 왕복 기준이에요…` 는 **이 목록에서 뺐다**(2026-09-28, 사용자 결정).
# 법적 항목이 아니라 **우리가 정한 설명**이고, 무엇보다 **그것이 말하는 사실이 화면에 남아 있다**:
# 상세 가격 옆에 `1인 왕복` 단위가 붙는다. 접힌 건 「인원을 고르면 무슨 일이 일어나나」다.
# 🔒 **단위가 사라지면 이 예외도 사라진다** — 아래 `test_folding_is_allowed_only_while_the_fact_shows` 가 건다.
PAX_NOTE = "가격은 성인 1인 왕복 기준이에요"


def _fn(name):
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def _rule(sel):
    m = re.search(re.escape(sel) + r"\{([^}]*)\}", CSS)
    return m.group(1) if m else None


class HoverTest(unittest.TestCase):
    """① 떼면 사라진다 — 다만 **후하게**."""

    def test_grace_exists_and_is_cancellable(self):
        body = _fn("hoverOut")
        self.assertIsNotNone(body, "hoverOut() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다")
        self.assertIn("HOVER_GRACE", body)
        self.assertIn("var HOVER_GRACE = 260", JS)
        self.assertIn("clearTimeout", _fn("hoverHold"))

    def test_expanded_detail_is_out_of_scope(self):
        """🔴 펼친 상세는 마우스가 스쳤다고 닫히면 안 된다 — 닫는 건 `×` 와 배경이다(SPEC §CH4)."""
        self.assertIn("expandedI !== null) return;", _fn("hoverOut"))

    def test_leave_is_wired_to_pin_card_and_hovercard(self):
        """셋 다 걸려야 한다. 하나라도 빠지면 그 경로로 나갈 때 카드가 남는다."""
        self.assertEqual(JS.count('addEventListener("mouseleave", hoverOut)'), 3)
        self.assertIn('hc.addEventListener("mouseenter", hoverHold)', JS)

    def test_touch_devices_are_left_alone(self):
        """터치엔 호버가 없다 — 합성 이벤트로 카드가 사라지면 탭이 먹통이 된다."""
        self.assertIn("if (!hoverable() || expandedI !== null) return;", _fn("hoverOut"))

    def test_changing_origin_clears_the_card(self):
        """🔴 사용자가 잡은 버그 — `expandedI = null` 은 **상태**고 `show` 가 **화면**이다.
        안 지우면 **직전 출발지의 딜**이 화면에 남는다."""
        body = _fn("pickOrigin")
        self.assertIsNotNone(body)
        self.assertIn('hc.classList.remove("show", "expanded")', body)
        self.assertIn("hoverHold()", body)
        self.assertLess(body.index("hc.classList.remove"), body.index("render()"))


class ShareTest(unittest.TestCase):
    """② 아이콘, `×` 옆. 전폭 CTA 는 예약처 링크뿐이다."""

    def test_is_an_icon_button_with_a_label(self):
        self.assertIn('class="hc-share" aria-label="공유"', JS)
        self.assertIn("var SHARE_SVG = '<svg", JS)
        self.assertNotIn('class="hc-share">공유</button>', JS)

    def test_sits_next_to_the_close_button(self):
        share, close = _rule(".hc-share"), _rule(".hc-x")
        self.assertIsNotNone(share)
        self.assertIn("position:absolute", share)
        self.assertIn("top:7px", share)
        self.assertIn("top:7px", close)
        self.assertIn("right:37px", share)      # 7(×) + 24(폭) + 6(사이)
        self.assertNotIn("width:100%", share)

    def test_feedback_does_not_wipe_the_icon(self):
        """🔴 아이콘 버튼이라 `textContent` 를 바꾸면 **SVG 가 지워진다.**"""
        body = _fn("shareCurrent")
        self.assertNotIn("textContent", body)
        self.assertIn('classList.add("copied")', body)
        self.assertIn('data-msg="링크를 복사했어요"', JS)
        self.assertIn("content:attr(data-msg)", CSS)

    def test_only_booking_links_stay_full_width(self):
        """전폭 요소는 예약처 링크(`.cmp`)와 그 CTA 뿐이다(DESIGN.md).
        둘은 `display:flex`/블록이라 폭을 따로 안 적는다 — **`width:100%` 를 적은 버튼이 있으면**
        그게 전폭 CTA 를 자처한 것이다. 공유가 다시 그렇게 되면 여기서 잡힌다."""
        self.assertIn("display:flex", _rule(".cmp"))
        for sel in (".hc-share", ".info"):
            self.assertNotIn("width:100%", _rule(sel) or "", sel)


class InfoTest(unittest.TestCase):
    """③ **설명을 접는 것과 고지를 숨기는 것을 가른다.**"""

    def _tips(self):
        """ⓘ 뒤에 들어가는 **모든** 글을 모은다.

        처음엔 `medianTip()` 하나만 봤다. 그런데 ⓘ 가 둘이 되자(인원) 그 검사는 새 ⓘ 를
        **한 글자도 안 보고** 통과했다(2026-09-28). 검사가 자라지 않으면 조용히 눈을 감는다 —
        그래서 **`infoHTML(...)` 에 넘기는 인자를 소스에서 찾아** 그 이름들을 다 훑는다.
        """
        # `function infoHTML(text)` 정의 자체는 부르는 자리가 아니다 — 빼고 찾는다.
        args = set(re.findall(r"(?<!function )infoHTML\(([A-Za-z_][\w.]*)\s*(?:\(\))?\)", JS))
        self.assertTrue(args, "infoHTML() 을 부르는 자리를 못 찾았다 — 검사를 할 수 없으면 실패다")
        out = {}
        for a in args:
            name = a.rstrip("()")
            body = _fn(name)
            if body is None:                       # 함수가 아니라 상수면 그 값을 읽는다
                m = re.search(r"var %s = (\"(?:[^\"\\\\]|\\\\.)*\");" % re.escape(name), JS)
                self.assertIsNotNone(m, "%s 의 값을 못 찾았다" % name)
                body = m.group(1)
            out[name] = body
        return out

    def test_every_info_is_checked(self):
        """탐침 — ⓘ 가 몇 개든 **전부** 모였나. 지금 둘(중앙값·인원)이다."""
        tips = self._tips()
        self.assertGreaterEqual(len(tips), 2, tips.keys())
        self.assertIn("medianTip", tips)
        self.assertIn("PAX_TIP", tips)

    def test_no_legal_disclosure_ever_goes_behind_the_info(self):
        """🔴 이 파일에서 가장 중요한 검사. **어느** ⓘ 안에든 법적 고지가 들어가면 실패다."""
        for name, body in self._tips().items():
            for d in DISCLOSURES:
                self.assertNotIn(d, body, "%s 안에 %s" % (name, d))
        self.assertNotIn("(광고)", _fn("infoHTML") or "")

    def test_folding_is_allowed_only_while_the_fact_shows(self):
        """🔴 **접은 건 설명이지 사실이 아니다.**

        인원 문장을 ⓘ 뒤로 보낼 수 있었던 유일한 이유는 그것이 말하는 사실(`1인 왕복`)이
        **상세 가격 옆에 그대로 보이기** 때문이다. 단위를 떼는 순간 「설명을 접은 것」이
        「고지를 숨긴 것」이 된다 — 그때는 이 검사가 막는다.
        """
        body = _fn("bodyTop")
        self.assertIsNotNone(body)
        self.assertIn("1인 왕복", body)
        self.assertIn("detail ?", body)
        self.assertIn(PAX_NOTE, self._tips()["PAX_TIP"])

    def test_disclosures_still_stand_on_their_own(self):
        """탐침 — 고지가 화면에서 사라지지 않았는지. 셋 다 `detailHTML` 에 그대로 있어야 한다."""
        body = _fn("detailHTML") or JS
        for d in (AD_NOTE, PRICE_NOTE, SCAN_NOTE, PAX_NOTE):
            self.assertIn(d, JS, d)

    def test_only_the_jargon_moved(self):
        """숫자·막대·`발견가` 줄은 **화면에 그대로** 있다 — 접은 건 뜻풀이뿐이다."""
        body = _fn("priceCompare")
        self.assertIn("평소 시세", body)
        self.assertNotIn("평소 시세(중앙값)", body)
        self.assertIn("pc-bar", body)
        self.assertIn("발견가", body)
        self.assertIn("infoHTML(medianTip())", body)

    def test_window_is_not_a_hand_copy(self):
        """🔴 **창은 백엔드가 정한다**(`CLAUDE.md`). 프론트가 `30` 을 적으면 백엔드가 바꾼 날
        화면만 옛 숫자를 말한다 — 예외도 안 나고 사람만 모른다."""
        tip = _fn("medianTip")
        self.assertIn("WINDOW_DAYS", tip)
        self.assertNotIn("30", tip)
        self.assertIn("var WINDOW_DAYS = window.__WINDOW", JS)

    def test_build_fails_without_the_window(self):
        """**소스에 `raise` 가 있는지가 아니라 실제로 터지는지**를 본다.

        처음엔 문자열로만 봤더니 `if not window_days:` 를 `if False:` 로 바꾼 돌연변이가
        **조용히 통과했다**(2026-09-28). `raise` 줄은 그대로 있고 닿지 않을 뿐이었다 —
        「부르는 것과 재는 것은 다르다」(함정 14)의 같은 모양이다. 그래서 돌려 본다.
        """
        import json
        import sys
        sys.path.insert(0, os.path.join(ROOT, "site"))
        import home

        def _fx(*parts):
            with io.open(os.path.join(ROOT, "fixtures", "v1", *parts), encoding="utf-8") as f:
                return json.load(f)

        payload, index, vocab = _fx("deals.json"), _fx("routes", "index.json"), _fx("vocab.json")
        meta = _fx("meta.json")
        for bad in ({}, None, dict(meta, window_days=0), dict(meta, window_days=None)):
            self.assertRaises(ValueError, home.render_home,
                              payload, "[]", "{}", index, vocab, bad, "2026-09-28")
        page = home.render_home(payload, "[]", "{}", index, vocab, meta, "2026-09-28")
        self.assertIn("window.__WINDOW=%d;" % meta["window_days"], page)

    def test_the_unflattering_sentence_stays(self):
        """홈의 `median` 은 직항/경유를 안 가른다 — 불리하지만 사실이라 더더욱 뺄 수 없다."""
        self.assertIn("직항·경유는 가르지 않았어요", _fn("medianTip"))

    def test_works_without_hover(self):
        """모바일엔 호버가 없다 — 버튼이고 탭으로 열고 닫는다."""
        self.assertIn('<button type="button" class="info" aria-expanded="false"', _fn("infoHTML"))
        self.assertIn('inf.setAttribute("aria-expanded"', JS)

    def test_touch_target_is_44px(self):
        """글리프가 작아도 **누를 판은 44px** 이다 — 모바일 손잡이와 같은 값.
        글리프 크기는 `em` 이라 주변 글자를 따라간다(2026-09-28) — 그래서 **판만 고정값**이다."""
        before = _rule(".info::before")
        self.assertIsNotNone(before)
        self.assertIn("width:44px", before)
        self.assertIn("height:44px", before)
        rule = _rule(".info")
        # 크기는 **옆 글자와 같다**(2026-09-28: 「글자랑 크기가 딱 맞았으면」) — `1em`.
        self.assertIn("width:1em", rule)
        self.assertNotIn("width:16px", rule, "크기를 px 로 못 박으면 머리말이 바뀔 때 혼자 커진다")
        self.assertIn("width:100%", _rule(".info-g"))

    def test_tip_is_kept_inside_the_card(self):
        """🔴 말풍선이 카드 밖으로 나가면 **글이 잘린다**(실측: 폭 238px 카드에서 68px 넘침).
        넘치는 양은 ⓘ 가 줄 어디에 있느냐가 정하고 그건 글자 길이가 정한다 — CSS 로는 못 막는다.
        그래서 **열릴 때 재서 밀어 넣는다.** 탭으로 여는 길과 호버로 여는 길 **둘 다** 걸려야 한다."""
        body = _fn("placeTip")
        self.assertIsNotNone(body, "placeTip() 를 못 찾았다")
        self.assertIn("getBoundingClientRect", body)
        self.assertIn("tip.style.left", body)
        self.assertIn("if (open) placeTip(inf);", JS)          # 탭
        self.assertIn('hc.addEventListener("mouseover"', JS)   # 호버

    def test_hover_path_exists_too(self):
        self.assertIn(".info:hover .info-tip", CSS)
        self.assertIn(".info:focus-visible .info-tip", CSS)
        self.assertIn('.info[aria-expanded="true"] .info-tip{display:block}', CSS)


if __name__ == "__main__":
    unittest.main()


class StageClickTest(unittest.TestCase):
    """빈 지도를 누르면 상세가 닫힌다 (사용자 2026-09-28).

    예전엔 `svg` 에만 걸려 있어서 **지도 위에 얹힌 것들이 클릭을 삼켰다** —
    실측으로 지도 왼쪽 위를 누르면 `.prompt`(안내 말풍선)가 받고 아무 일도 안 났다.
    이제 **무대 전체**에서 받고 **눌러야 할 것만** 뺀다.
    """

    KEEP = ".hovercard,#pins,.stagebar,#stepper,#fdock,.emptyday"

    def test_closing_listens_on_the_stage_not_just_the_svg(self):
        """닫는 것은 **무대 전체**가 받는다 — `svg` 에만 걸면 위에 얹힌 것들이 클릭을 삼킨다.

        PH5c 부터 `svg` 에도 `click` 이 하나 붙는데 **하는 일이 다르다**: 팬으로 끝난 제스처를
        클릭으로 세지 않게 **막는** 것이다(캡처 단계). 지도를 끌 때마다 상세가 닫히면 안 된다.
        그래서 「svg 에 click 이 없다」가 아니라 **「닫는 일은 무대가 한다」**를 잰다."""
        self.assertIn('stageEl.addEventListener("click"', JS)
        m = re.search(r'svg\.addEventListener\("click", function \(e\) \{(.*?)\}, true\);', JS, re.S)
        self.assertIsNotNone(m, "svg 의 click 은 캡처 단계의 팬 억제여야 한다")
        self.assertIn("stopPropagation", m.group(1))
        self.assertNotIn("closeByUser", m.group(1), "닫는 일을 svg 가 하면 안 된다")

    def test_keep_list_has_no_dead_selectors(self):
        """🔴 **무대 안에 실제로 있는 것만 적는다.** 처음 적은 아홉 중 셋이 죽어 있었다(실측):
        `.gm-zoom`(홈엔 없다) · `.originwrap`·`#firstnote`(머리에 있어 무대 클릭 대상이 될 수 없다).
        쓰지 않는 선택자를 남기면 다음 사람이 「여기 뭐가 있나」부터 찾는다(B44 죽은 키와 같은 축)."""
        self.assertIn('var KEEP = "%s";' % self.KEEP, JS)
        # ⚠️ **목록만 본다.** 처음엔 파일 전체에서 찾았다가 틀렸다 —
        # `.originwrap`·`#firstnote` 는 **딜 0건 화면을 치우는 `off` 목록에서 여전히 쓰는** 살아 있는 선택자다.
        # 「이 목록에서 죽었다」와 「파일에서 죽었다」는 다른 말이고, 검사는 재려는 것만 재야 한다.
        for dead in (".gm-zoom", ".originwrap", "#firstnote"):
            self.assertNotIn(dead, self.KEEP, dead)
        self.assertEqual(len(self.KEEP.split(",")), 6)
        # `.gm-zoom` 만은 홈 어디에도 없어야 한다 — 노선 페이지 CSS 의 이름이다.
        self.assertNotIn(".gm-zoom", re.sub(r"(?m)^\s*//.*$", "", JS))

    def test_the_hint_never_swallows_a_click(self):
        """안내 말풍선은 **누르는 것이 아니다** — 그 위를 눌러도 지도를 누른 것으로 친다."""
        self.assertIn("pointer-events:none", _rule(".prompt"))
        self.assertNotIn(".prompt", self.KEEP)

    def test_close_goes_through_the_user_path(self):
        """`collapse()` 가 아니라 `closeByUser()` 다 — 공유 링크로 들어온 사람의 히스토리를 지킨다(B58)."""
        m = re.search(r'stageEl\.addEventListener\("click", function \(e\) \{(.*?)\n  \}\);', JS, re.S)
        self.assertIsNotNone(m)
        self.assertIn("closeByUser()", m.group(1))


class StampRoomTest(unittest.TestCase):
    """기운 도장이 **아랫줄을 파고들지 않게** (사용자 2026-09-28).

    실측(칭다오 31%↓, 1440·390 둘 다): 도장 줄의 높이는 15px 인데 **기운 도장의 바깥 상자는 25px** 이라
    아랫줄 `인천 출발 · 1인 왕복` 을 아래로 파고들었다.

    🔴 **원인을 두 번 틀리게 짚었다.** 처음엔 줄 **사이**(`gap`)로 보고 16px 로 늘렸는데 **하나도 안 변했다** —
    도장과 신기록은 나란히 **같은 줄**에 있어서 벌어져야 할 것은 사이가 아니라 **그 줄의 높이**였다.
    잰 값이 안 움직이면 고친 게 원인이 아니다.
    """

    def test_angles_are_one_set_everywhere(self):
        """🔒 **자리마다 각이 다르면 같은 표식이 두 모양**이 된다(직항 배지를 없앤 것과 같은 이유).
        2026-09-28 에 7·8·9° → 4·5·6° 로 줄였지만 **세 단계 모두, 모든 자리에서 같이** 줄였다.
        줄인 이유는 기운 사각형이 세로로 더 먹는 양이 `폭 × sin(각)` 이라서다 —
        79px 도장이 8° 에서 **+11px**(실측), 그게 아랫줄 글자를 건드렸다."""
        for tier, deg in (("t1", "-4deg"), ("t2", "-5deg"), ("t3", "-6deg")):
            self.assertIn("rotate(%s)" % deg, _rule(".stamp.%s" % tier) or "", tier)
        # 떠오르는 t3 규칙도 같은 각이어야 한다 — 한 곳만 고치면 t3 만 다른 각이 된다.
        for old in ("rotate(-7deg)", "rotate(-8deg)", "rotate(-9deg)"):
            self.assertNotIn(old, CSS, old)

    def test_lift_is_off_where_the_stamp_is_not_on_a_photo(self):
        """⚠️ `translateY(-16px)` 는 도장이 **사진 위**에 얹혀 있을 때의 규칙이다(DESIGN.md).
        2026-09-28 부터 확장 상세의 도장은 사진이 아니라 **가격 옆 줄**에 있다 —
        그대로 두면 t3 만 가격 줄을 16px 뚫고 올라간다.
        오늘 데이터에 t3(42%+)가 없어 화면으로 못 봤다. **나올 때까지 기다리지 않고 지금 막는다.**"""
        self.assertIn(".hc-marks .stamp.t3{transform:rotate(-6deg)}", CSS)

    def test_marks_are_stacked_not_side_by_side(self):
        """🔴 **도장 위, 신기록 아래** — 오른쪽 정렬(사용자 안, 2026-09-28).
        나란히 두면 기운 도장이 아랫줄에 3px 까지 붙는다. 쌓으면 **14px** 이 난다.
        대신 아래 내용이 11px 내려가는데, 그 비용은 **표식이 둘 다 있는 카드에만** 든다
        (오늘 142건 중 2건). 표식이 하나면 어느 쪽이든 한 줄이다."""
        rule = _rule(".hc-marks")
        self.assertIn("flex-direction:column", rule)
        self.assertIn("align-items:flex-end", rule)
        self.assertNotIn("flex-wrap", rule, "쌓는 배치엔 줄바꿈이 필요 없다")

    def test_room_is_made_by_the_stamp_not_the_row(self):
        """여백은 **도장이 있을 때만** 줄을 키운다 — 줄에 주면 신기록만 있는 카드에도 빈 자리가 생긴다."""
        self.assertIn(".hc-marks .stamp{margin:", CSS)
        self.assertNotIn("gap:16px", _rule(".hc-marks") or "")


class InfoHoverTest(unittest.TestCase):
    """마우스로 연 말풍선은 **마우스가 떠나면 닫힌다** (사용자 2026-09-28).

    탭으로 연 것은 붙박이(`aria-expanded="true"`)가 맞다 — 터치엔 닫을 다른 길이 없다.
    그런데 마우스로 여는 사람은 **지나가는 김에** 읽는 것이지 열어 두려는 게 아니다.
    사용자: 「마우스를 아래로 내리니까 안 사라져서 불편해」.
    """

    def test_closes_on_leave_only_where_hover_exists(self):
        m = re.search(r'hc\.addEventListener\("mouseout", function \(e\) \{(.*?)\n  \}\);', JS, re.S)
        self.assertIsNotNone(m, "mouseout 핸들러를 못 찾았다")
        body = m.group(1)
        self.assertIn('matchMedia("(hover:hover)")', body)
        self.assertIn('setAttribute("aria-expanded", "false")', body)

    def test_moving_into_the_tip_is_not_leaving(self):
        """말풍선 안으로 들어간 것은 떠난 게 아니다 — 그렇게 안 하면 읽으러 가는 순간 닫힌다."""
        m = re.search(r'hc\.addEventListener\("mouseout", function \(e\) \{(.*?)\n  \}\);', JS, re.S)
        self.assertIn("inf.contains(e.relatedTarget)", m.group(1))

    def test_tap_toggle_survives(self):
        """터치 기기는 탭으로 열고 탭으로 닫는 그대로다."""
        self.assertIn('inf.setAttribute("aria-expanded", open ? "true" : "false");', JS)


class CardWidthTest(unittest.TestCase):
    """확장 상세의 폭 — **결정하는 자리가 스캔하는 자리보다 좁으면 안 된다** (사용자 2026-09-28).

    238px 이었다. 피드 카드는 340px 이다(`SPEC` §CH3). 30% 좁은 쪽이 **결정하는 자리**였고,
    그 좁음이 하루에 세 가지를 만들었다(실측):
      · 도장·신기록이 가격 옆에 못 붙는다 — 안쪽 214px < 가격 110 + 표식 190
      · ⓘ 말풍선을 카드 폭에 맞춰 깎아야 한다
      · 고지가 세 줄씩 접힌다
    """

    def test_wide_desktop_matches_the_feed_card(self):
        self.assertIn("@media(min-width:1000px){.hovercard.expanded{width:340px}}", CSS)

    def test_compact_card_fits_a_mark_beside_the_price(self):
        """미니(호버) 카드도 같은 병이었다 — 폭 **184px**, 안쪽 160px 에
        `가격 100 + 사이 8 + 도장 80 = 188` 이라 도장이 아랫줄로 밀렸다(사용자 2026-09-28).
        184 도 **스펙에 없는 값**이고 코드에만 있었다 — 238 과 같은 종류다.

        🔒 **오늘 값이 아니라 최악으로 잡는다**: 가장 긴 가격 123px + 가장 넓은 도장(t3) 93px
        + 사이 8 + 안쪽 여백 24 = **248px**. 오늘 도장(80px)에만 맞췄으면 42% 딜이 뜨는 날 다시 내려간다.
        """
        self.assertIn(".hovercard{position:absolute;width:250px;", CSS)

    def test_narrow_desktop_keeps_the_old_width(self):
        """🔴 **없는 자리를 우겨 넣지 않는다.** 861~999px 에서는 무대가 521~659px 인데 도크가 270px 을 쓴다 —
        900px 실측으로 도크 왼쪽까지 **266px** 뿐이라 340px 카드는 도크를 통째로 덮었다.
        덮으면 그 뒤의 필터를 못 쓴다(B16 과 같은 뿌리)."""
        self.assertIn(".hovercard.expanded{width:238px;", CSS)

    def test_edge_clamp_is_measured_not_copied(self):
        """🔴 위치 계산에 `120`(=238/2)이 **손으로 박혀 있었다.** 폭만 바꾸면 카드가 무대 밖으로 나간다 —
        같은 사실(카드 폭)이 CSS 와 JS 두 곳에 있으면 갈린다. 이제 실제 폭에서 잰다.

        ⚠️ 여유를 **더하지 않는다.** `halfW + 8` 로 했더니 861px 에서 도크를 덮었다(실측) —
        예전 `120` 은 `119 + 1` 이라 **반폭 그 자체**가 원래 뜻이었다."""
        body = re.search(r"function positionCard\(c, at\) \{(.*?)\n  \}\n", JS, re.S)
        self.assertIsNotNone(body)
        code = re.sub(r"(?m)^\s*//.*$", "", body.group(1))
        self.assertIn("var edge = Math.min(halfW, box.width / 2);", code)
        self.assertNotIn("120", code, "카드 폭의 사본이 다시 박혔다")
