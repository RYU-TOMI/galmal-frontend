# -*- coding: utf-8 -*-
"""키보드·스크린리더 — CH10 (B11 · C-8, `SPEC.md` §CH6 2026-09-01 확정 · 2026-10-01 갱신).

**착수 실측(2026-10-01)**: 화면의 조작 거리 **88개 중 탭으로 닿는 것 30개** — 58개를 키보드로
못 만졌다. Tab 을 끝까지 눌러도 **딜에 닿는 길은 하나**(hero 의 안쪽 버튼)뿐이었고,
나머지 23개 딜은 **열 수 없었다.** `aria-live` 0개 · 예산 슬라이더 이름 없음 ·
`Esc` 는 출발지 드롭다운만 닫음.

**고친 뒤**: 88개 중 **63개**. 못 닿는 25개는 **핀 24 + hero 카드 1** — 둘 다 **의도한 것**이다
(핀은 `aria-hidden`, hero 는 안쪽 버튼이 그 정지점). 즉 **닿아야 할 것은 전부 닿는다.**

🔴 **불변식 — 키보드만으로 모든 딜에 닿는다**(§CH6). 실측: 지역 칩 10개를 차례로 눌러
피드에 뜬 딜의 합집합 **75곳 == 그 출발지 전체 75곳**.

⚠️ 이 챕터에서 **자를 네 번 고쳤다**:
  ① CDP `rawKeyDown` 은 **네이티브 버튼을 못 누른다**(문자 단계가 없다) — 「지역 칩 Enter 가 안 먹는다」로
     보였는데 `keyDown`+`text` 로 보내니 마우스 클릭과 똑같이 동작했다.
  ② `[aria-live]` 만 세어 `role="status"`(암묵적 live 영역)를 **0개로 셌다.**
  ③ `:focus` CSS 규칙 세기가 **구글 폰트 시트(교차 출처)에서 예외가 나** 통째로 0 이 됐다.
  ④ 건너뛰기 링크의 「안 보인다」는 **전환 0.12초를 안 기다린 것**이었다(0.3초 뒤 `top:0`).
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()
HOME = io.open(os.path.join(ROOT, "site", "home.py"), encoding="utf-8").read()
CODE = re.sub(r"(?m)^\s*//.*$", "", JS)          # 주석 속 옛 코드에 속지 않는다
COPY_MD = os.path.join(ROOT, "..", "galmal-plan", "COPY.md")


def fn(name):
    i = JS.index("function " + name + "(")
    d, j, started = 0, i, False
    while j < len(JS):
        if JS[j] == "{":
            d += 1
            started = True
        elif JS[j] == "}":
            d -= 1
            if started and d == 0:
                return JS[i:j + 1]
        j += 1
    raise AssertionError(name + " 의 본문을 못 찾았다")


def body(name):
    """주석을 걷어낸 본문 — 「없다」를 셀 때는 **반드시** 이걸 쓴다(CH8·PH8·CH9 에서 다섯 번 걸렸다)."""
    return re.sub(r"(?m)^\s*//.*$", "", fn(name))


class MapIsAPictureTest(unittest.TestCase):
    """**핀은 카드의 시각적 표현이지 별도 조작 대상이 아니다**(§CH6).

    핀 24개를 탭 정지점으로 만들면 **같은 24곳을 두 번** 훑게 된다 — 피드가 곧 지도다.
    """

    def test_pins_are_hidden_from_the_tree(self):
        self.assertIn('g.setAttribute("aria-hidden", "true");', CODE)

    def test_the_map_name_says_how_many_are_on_it(self):
        """이름이 「여행지 발견 지도」로 고정이면 **몇 곳이 보이는지**를 말하지 못한다."""
        self.assertIn('svg.setAttribute("aria-label", vis.length', CODE)
        self.assertIn("곳이 찍힌 지도예요. 같은 곳이 목록에 있어요.", CODE)
        self.assertIn("지도에 찍힌 곳이 없어요.", CODE)      # 0곳인 날

    def test_the_name_has_no_direction_words(self):
        """「왼쪽·오른쪽」은 쓰지 않는다 — 낭독기에는 방향이 없다(COPY §2)."""
        i = CODE.index('svg.setAttribute("aria-label"')
        seg = CODE[i:i + 400]
        for w in ("왼쪽", "오른쪽", "좌측", "우측"):
            self.assertNotIn(w, seg)

    def test_the_map_label_is_set_where_the_count_exists(self):
        """⚠️ 처음에 `moveOnly()` 에 넣었다가 거기엔 `vis` 가 없어 **프레임마다 ReferenceError** 가
        날 뻔했다. 빌드도 테스트도 JS 를 돌려 보지 않으므로 **어느 함수 안인지**를 검사가 본다."""
        self.assertIn('svg.setAttribute("aria-label", vis.length', body("render"))
        self.assertNotIn("aria-label", body("moveOnly"))


class SkipTest(unittest.TestCase):
    """건너뛰기 **둘**(기획 결정 2026-10-01 (3)) — DOM 순서를 뒤집지 않고 조작에 먼저 닿는 길."""

    def test_both_links_exist_in_order(self):
        i = HOME.index("목록으로 건너뛰기")
        j = HOME.index("지역·필터로 건너뛰기")
        self.assertLess(i, j, "목록 → 지역·필터 순서다")
        self.assertIn('<div class="skips">', HOME)

    def test_they_hide_until_focused(self):
        """`display:none` 이면 포커스도 못 받는다 — **자리를 옮기는** 방식이어야 한다."""
        self.assertRegex(CSS, r"\.skips a\{[^}]*top:-60px")
        self.assertIn(".skips a:focus{top:0}", CSS)

    def test_we_move_the_focus_ourselves(self):
        """🔴 `href="#id"` 만으로는 둘 다 안 된다 — 실측: ① 주소가 `#SEL` 로 **되돌아갔고**
        (우리 hash 라우팅이 모르는 값을 덮는다) ② 포커스가 `body` 에 **남았다**(앵커는 스크롤만 한다).
        링크로 읽히게 `href` 는 두고 **가는 일만** 우리가 한다."""
        self.assertIn('var links = document.querySelectorAll(".skips a")', CODE)
        # ⚠️ `preventDefault` 를 **파일 전체**에서 세면 다른 데 있는 것에 걸려 통과한다 —
        # 돌연변이로 알았다. 이 핸들러 **안**에 있는지 본다.
        i = CODE.index('var links = document.querySelectorAll(".skips a")')
        handler = CODE[i:i + 700]
        self.assertIn("e.preventDefault();", handler)
        self.assertIn('feed.querySelector(".fcard .go") || feed.querySelector(".fcard")', CODE)
        self.assertIn('.stagebar .pill[tabindex=', CODE)


class CardTest(unittest.TestCase):
    """카드가 정지점이다 — 이름은 **카드 안 글자 그대로**."""

    def test_cards_are_operable(self):
        self.assertIn('if (!hero) { card.tabIndex = 0; card.setAttribute("role", "button"); }', CODE)

    def test_enter_and_space_open_the_detail(self):
        self.assertIn('e.key === "Enter"', CODE)
        self.assertIn('e.key === " "', CODE)

    def test_focus_behaves_like_hover(self):
        """포커스가 호버와 같다 — 그 핀이 강조된다. **지도는 움직이지 않는다**(§CH6)."""
        self.assertIn('el.addEventListener("focus", function () { hoverIn(i, false); });', CODE)
        self.assertIn('el.addEventListener("blur", hoverOut);', CODE)

    def test_the_card_name_is_not_overridden(self):
        """통째 `aria-label` 로 덮으면 **보이는 글자와 갈린다**(COPY §2)."""
        self.assertNotIn('card.setAttribute("aria-label"', CODE)


class RegionBarTest(unittest.TestCase):
    """지역바는 **정지점 하나** — 칩마다 두면 피드 앞에 탭 10번이 쌓인다."""

    def test_it_is_a_toolbar_with_a_name(self):
        self.assertIn('role="toolbar" aria-label="지역으로 이동"', HOME)

    def test_chips_are_buttons_with_one_stop(self):
        self.assertIn('aria-pressed="false" tabindex="0">전체</button>', HOME)
        self.assertIn('tabindex="-1"', HOME)

    def test_arrows_move_between_chips(self):
        self.assertIn('e.key === "ArrowRight" || e.key === "ArrowDown"', CODE)
        self.assertIn('e.key === "ArrowLeft" || e.key === "ArrowUp"', CODE)
        self.assertIn('e.key === "Home"', CODE)
        self.assertIn('e.key === "End"', CODE)

    def test_hidden_chips_are_skipped(self):
        """그 출발지에 딜이 없는 지역은 칩이 숨는다 — 화살표가 **안 보이는 데로** 가면 안 된다."""
        self.assertIn("if (all[i].offsetWidth > 0) o.push(all[i]);", CODE)

    def test_pressed_comes_from_the_same_decision_as_the_light(self):
        """보이는 불과 읽히는 상태를 **한 곳에서** 맞춘다 — 따로 두면 갈린다(B70 에서 겪었다)."""
        b = body("syncStageBar")
        self.assertIn("var isOn = lit !== null", b)
        self.assertIn('pills[i].classList.toggle("on", isOn);', b)
        self.assertIn('pills[i].setAttribute("aria-pressed", isOn ? "true" : "false");', b)


class DetailFocusTest(unittest.TestCase):
    """상세 — 포커스가 **안으로**, `Esc` 로 닫고 **누른 카드로 복귀**. 가두지 않는다."""

    def test_focus_moves_in(self):
        self.assertIn("if (expanded) { lastExpanded = i; focusDetail(); }", CODE)

    def test_escape_closes_the_same_way_as_the_x(self):
        """`×` 와 **같은 길**로 닫는다 — 사용자가 한 일이므로 히스토리도 같게 다뤄야 한다(B58·B59).

        ⚠️ 이 문장은 `takeView`(지도를 움직이면 닫는다)에도 **똑같이** 있다 — `Esc` 핸들러 안을 본다."""
        i = CODE.index('if (e.key !== "Escape") return;')
        handler = CODE[i:i + 300]
        self.assertIn("closeDrop();", handler)
        self.assertIn("if (expandedI !== null) closeByUser();", handler)

    def test_focus_returns_only_when_it_was_inside(self):
        """🔴 `collapse()` 는 **정렬·필터·지역을 바꿀 때도** 부수 효과로 돈다 — 그때 되돌리면
        **필터를 누를 때마다 포커스를 뺏는다.** 「누가 닫았나」 플래그 대신 **지금 포커스가 어디 있나**를 본다.
        실측: 필터 칩을 누른 뒤 포커스가 그 칩에 남았다."""
        self.assertIn("if (!hc.contains(document.activeElement)) return;", body("restoreFocus"))

    def test_it_survives_a_rerender(self):
        """카드가 다시 그려져 사라졌으면 **같은 딜의 새 카드**를 찾는다."""
        self.assertIn("lastExpanded", body("restoreFocus"))


class NamesTest(unittest.TestCase):
    """보이지 않는 문자열 — **COPY §2 표에 없는 이름을 짓지 않는다.**"""

    def test_marks_read_as_sentences(self):
        """`41%↓` 를 낭독기는 「사십일 퍼센트 아래 화살표」로 읽는다."""
        self.assertIn("평소보다 ", fn("stampHTML"))
        self.assertIn("% 싸요", fn("stampHTML"))
        self.assertIn("일 중 가장 싼 가격이에요", fn("recShort"))

    def test_the_close_button_is_named_as_the_copy_says(self):
        self.assertIn('class="hc-x" aria-label="닫기"', CODE)

    def test_zoom_buttons_say_what_they_do(self):
        self.assertIn('aria-label="지도 확대"', HOME)
        self.assertIn('aria-label="지도 축소"', HOME)

    def test_the_slider_has_a_name_and_a_spoken_value(self):
        """보이는 값과 읽히는 값을 **한 곳에서** 맞춘다 — 세 곳에서 따로 고치면
        `aria-valuetext` 는 영원히 처음 값이다."""
        self.assertIn('aria-label="예산"', HOME)
        self.assertIn('aria-valuetext="제한 없음"', HOME)
        b = body("setBudgetLabel")
        self.assertIn("bval.textContent = t", b)
        self.assertIn('bslider.setAttribute("aria-valuetext", t)', b)
        self.assertEqual(CODE.count("bval.textContent"), 1, "값을 고치는 자리는 한 곳이다")

    def test_the_count_is_announced_without_a_new_string(self):
        """부제가 그대로 읽힌다(COPY §2: 따로 짓지 않는다). 실측: 지역 24→20→12→75,
        필터 「조건에 맞는 26곳」 — **모든 조작에서** 바뀐다."""
        self.assertIn('<span role="status">', CODE)

    @unittest.skipUnless(os.path.exists(COPY_MD), "기획 저장소가 없다(CI) — 로컬에서만 대조한다")
    def test_names_match_the_copy_table(self):
        """기획 파일과 대조한다. 표에 없는 이름을 지으면 여기서 걸린다."""
        copy = io.open(COPY_MD, encoding="utf-8").read()
        for want in ("목록으로 건너뛰기", "지역·필터로 건너뛰기", "지도 확대", "지도 축소",
                     "지역으로 이동", "제한 없음"):
            self.assertIn(want, copy, "COPY §2 에 없는 이름을 쓰고 있다: " + want)


class FocusRingTest(unittest.TestCase):
    """포커스 표시 — **두 겹**(DESIGN §접근성). 한 색은 어딘가에서 묻힌다."""

    def test_two_tone_on_focus_visible_only(self):
        self.assertIn(":focus-visible{outline:2px solid var(--ink);outline-offset:2px;box-shadow:0 0 0 2px #fff}", CSS)

    def test_the_photo_buttons_flip_the_tones(self):
        """사진 위에 앉는 둘은 **바탕 색을 모른다** — 흰 링에 어두운 테두리를 겹친다."""
        self.assertIn(".hc-x:focus-visible,.hc-share:focus-visible{outline-color:#fff", CSS)

    def test_it_is_not_plain_focus(self):
        """마우스로 눌렀을 때는 안 뜬다 — 그 사람은 어디를 눌렀는지 안다."""
        self.assertNotRegex(CSS, r"(?m)^:focus\{")


if __name__ == "__main__":
    unittest.main()
