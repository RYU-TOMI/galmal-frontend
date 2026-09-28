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
                              payload, "[]", "{}", index, vocab, bad)
        page = home.render_home(payload, "[]", "{}", index, vocab, meta)
        self.assertIn("window.__WINDOW=%d;" % meta["window_days"], page)

    def test_the_unflattering_sentence_stays(self):
        """홈의 `median` 은 직항/경유를 안 가른다 — 불리하지만 사실이라 더더욱 뺄 수 없다."""
        self.assertIn("직항·경유는 가르지 않았어요", _fn("medianTip"))

    def test_works_without_hover(self):
        """모바일엔 호버가 없다 — 버튼이고 탭으로 열고 닫는다."""
        self.assertIn('<button type="button" class="info" aria-expanded="false"', _fn("infoHTML"))
        self.assertIn('inf.setAttribute("aria-expanded"', JS)

    def test_touch_target_is_44px(self):
        """글리프는 16px 이어도 **누를 판은 44px** 이다 — 모바일 손잡이와 같은 값."""
        before = _rule(".info::before")
        self.assertIsNotNone(before)
        self.assertIn("width:44px", before)
        self.assertIn("height:44px", before)
        self.assertIn("width:16px", _rule(".info"))

    def test_hover_path_exists_too(self):
        self.assertIn(".info:hover .info-tip", CSS)
        self.assertIn(".info:focus-visible .info-tip", CSS)
        self.assertIn('.info[aria-expanded="true"] .info-tip{display:block}', CSS)


if __name__ == "__main__":
    unittest.main()
