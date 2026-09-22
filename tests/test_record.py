# -*- coding: utf-8 -*-
"""신기록 «N일 중 최저» — **시점을 말하는 표식** (SPEC §CH3, COPY.md §2, 2026-09-22 문구 확정).

`low`·`obs_days` 는 계약에 있고 응답에도 매일 들어오는데 `discover.js` 가 **한 번도 안 읽었다**
(두 이름이 소스에 0회). 2026-09-01 에 확정된 것이 3주간 화면에 없었다 — 전수 대조에서 센 다섯 중 둘째다.
「✅ 확정」과 「화면에 있음」은 다른 말이고, 그 둘을 이어 주는 검사가 없어서 조용히 통과했다.

여기서 잠그는 것 넷:

  ① **자격 넷을 다 넘어야 한다.** 하나만 빼도 말이 안 되는 자리가 생긴다 —
     `obs` 하한이 없으면 「사흘 중 최저」, 여유 5% 가 없으면 「1원 차이 신기록」이 나간다.
  ② 🔴 **`%` 로 쓰지 않는다.** 도장(`41%↓`)은 «얼마나 싼가», 신기록은 «언제 이후 처음인가» —
     단위가 달라서 한 자로 재면 **더 드문 쪽이 초라해 보인다.**
  ③ **한 자리에 표식 하나.** 카드는 도장 우선, 없으면 신기록. 확장 상세만 둘 다.
  ④ **스캔용은 짧게, 확인용은 문장으로.** 카드는 `{N}일 중 최저`, 확장 상세와 `aria-label` 은
     `{N}일 중 가장 싼 가격이에요`. 눈으로 읽는 사람과 귀로 듣는 사람이 **같은 사실**을 받아야 한다.

JS 를 파이썬으로 읽는다 — 이 저장소엔 Node 빌드가 없다(`CLAUDE.md`). 화면에서 실제로 그려지는지는
CDP 로 따로 본다(`FRONTEND.md` §3). 그래서 **조건식의 모양**과 **문구**를 소스에서 같이 본다.
"""
import io
import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()
DEALS = json.load(io.open(os.path.join(ROOT, "fixtures", "v1", "deals.json"), encoding="utf-8"))["deals"]

MIN_OBS = 14
MARGIN = 0.05
SHORT = "일 중 최저"
LONG = "일 중 가장 싼 가격이에요"


def _fn(name):
    """`function name(...) { … }` 한 덩이. 주석은 걷어낸다 — 주석 속 문구에 속지 않는다."""
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def record_days(d):
    """`recordDays()` 를 파이썬으로 옮긴 것 — 경계값을 실제로 돌려 본다.
    옮긴 사본이라 JS 와 갈릴 수 있다: 아래 `SourceTest` 가 조건식 모양을 같이 지킨다."""
    low = d.get("low") or 0
    obs = d.get("obs_days") or 0
    p = d["price"]
    if not low or obs < MIN_OBS or p >= low or (1 - p / float(low)) < MARGIN:
        return 0
    return obs


class RuleTest(unittest.TestCase):
    """자격 넷 — 하나씩 떨어뜨려 본다. 통과하는 딜 하나를 놓고 **한 조건만** 깬다."""

    OK = {"price": 90000, "low": 100000, "obs_days": 20}

    def test_all_four_pass(self):
        self.assertEqual(record_days(self.OK), 20)

    def test_no_low_is_no_record(self):
        """기록 자체가 없으면 「최저」를 말할 밑천이 없다."""
        for low in (None, 0):
            self.assertEqual(record_days(dict(self.OK, low=low)), 0, low)

    def test_short_observation_is_no_record(self):
        """「사흘 중 최저」는 사흘 중 하나라는 뜻이다. 13일과 14일이 **갈려야** 한다."""
        self.assertEqual(record_days(dict(self.OK, obs_days=13)), 0)
        self.assertEqual(record_days(dict(self.OK, obs_days=14)), 14)
        self.assertEqual(record_days(dict(self.OK, obs_days=0)), 0)

    def test_tie_is_not_a_record(self):
        self.assertEqual(record_days(dict(self.OK, price=100000)), 0)
        self.assertEqual(record_days(dict(self.OK, price=110000)), 0)

    def test_margin_cuts_noise(self):
        """`low` 를 1원 밑도는 것을 신기록이라 부르지 않는다. 5% 는 넘고 4.9% 는 못 넘는다."""
        self.assertEqual(record_days(dict(self.OK, price=99999)), 0)      # 0.001%
        self.assertEqual(record_days(dict(self.OK, price=95100)), 0)      # 4.9%
        self.assertEqual(record_days(dict(self.OK, price=95000)), 20)     # 5.0%

    def test_n_is_obs_days(self):
        """N 은 며칠 봤나다 — 가격도 할인율도 아니다."""
        self.assertEqual(record_days(dict(self.OK, obs_days=17)), 17)
        self.assertEqual(record_days(dict(self.OK, obs_days=30)), 30)


class FixtureTest(unittest.TestCase):
    """실데이터 — 검사가 **눈을 뜨고 있나.** 해당 딜이 0건인 픽스처로는 아무것도 못 지킨다."""

    def test_fixture_has_both_kinds(self):
        """도장이 겹치는 딜과 안 겹치는 딜이 **둘 다** 있어야 「하나만」 규칙을 실제로 재 볼 수 있다.
        픽스처를 다시 받을 때 이 둘이 유지되는지 본다(`fixtures/README.md`)."""
        rec = [d for d in DEALS if record_days(d)]
        self.assertTrue(rec, "신기록 딜이 0건인 픽스처로는 이 챕터를 지킬 수 없다")
        self.assertTrue([d for d in rec if (d.get("discount") or 0) >= 15],
                        "도장과 겹치는 신기록 딜이 없다 — 「도장 우선」을 못 잰다")
        self.assertTrue([d for d in rec if (d.get("discount") or 0) < 15],
                        "도장 없는 신기록 딜이 없다 — 카드에 신기록이 뜨는 걸 못 잰다")

    def test_low_is_actually_delivered(self):
        """받는 값이 비어 있으면 위 규칙은 영원히 거짓이다 — **안 뜨는 것**과 **없는 것**을 가른다."""
        self.assertGreater(sum(1 for d in DEALS if d.get("low")), len(DEALS) * 0.5)
        self.assertTrue(any(d.get("obs_days", 0) >= MIN_OBS for d in DEALS))

    def test_record_is_rarer_than_stamp(self):
        """신기록은 **드문 사건**이다. 도장보다 흔해지면 임계가 무너진 것이다(자를 다시 본다)."""
        rec = sum(1 for d in DEALS if record_days(d))
        stamp = sum(1 for d in DEALS if (d.get("discount") or 0) >= 15)
        self.assertLess(rec, stamp)


class SourceTest(unittest.TestCase):
    """소스가 위 규칙과 **같은 모양**인가 — 파이썬 사본만 맞고 JS 가 갈리는 걸 막는다."""

    def test_threshold_values_live_in_one_place(self):
        self.assertIn("var MIN_OBS = %d, REC_MARGIN = %s;" % (MIN_OBS, MARGIN), JS)

    def test_condition_has_all_four(self):
        body = _fn("recordDays")
        self.assertIsNotNone(body, "recordDays() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다")
        self.assertRegex(
            body,
            r"if \(!low \|\| obs < MIN_OBS \|\| p >= low \|\| \(1 - p / low\) < REC_MARGIN\) return 0;")

    def test_toCity_carries_it(self):
        """판정이 카드까지 실려야 한다 — 함수만 있고 안 부르면 화면은 그대로다(이 챕터의 본래 결함)."""
        self.assertIn("rec: recordDays(dl)", _fn("toCity"))


class CopyTest(unittest.TestCase):

    def test_never_uses_percent(self):
        """🔴 이 챕터의 가장 강한 규칙. 신기록 문구를 만드는 두 함수 어디에도 `%` 가 없다."""
        for fn in ("recShort", "recLong"):
            body = _fn(fn)
            self.assertIsNotNone(body, fn)
            self.assertNotIn("%", body, fn)
            self.assertNotIn("disc", body, fn)

    def test_short_on_screen_long_for_screenreaders(self):
        """짧은 쪽엔 **반드시** 읽어 주는 문장이 붙는다 — `19일 중 최저` 만 읽어 주면 무엇의 최저인지 안 말한다."""
        body = _fn("recShort")
        self.assertIn(SHORT, body)
        self.assertIn('aria-label="', body)
        self.assertIn(LONG, body)
        self.assertLess(body.index(LONG), body.index(SHORT), "긴 쪽이 aria-label 자리에 와야 한다")

    def test_long_form_in_detail_has_no_aria(self):
        """확장 상세는 문장이 **화면에 그대로** 있다 — 같은 말을 aria 로 덧대면 두 번 읽는다."""
        body = _fn("recLong")
        self.assertIn(LONG, body)
        self.assertNotIn("aria-label", body)
        self.assertNotIn(SHORT, body)


class PlacementTest(unittest.TestCase):
    """**한 자리에 표식 하나** — 피드 카드와 축소 카드는 하나, 확장 상세만 둘."""

    def test_card_shows_exactly_one(self):
        self.assertIn("(stampHTML(c) || recShort(c))", JS)

    def test_detail_shows_both_and_compact_does_not(self):
        body = _fn("bodyTop")
        self.assertIsNotNone(body)
        self.assertIn("detail ? stampHTML(c) + recLong(c) : (stampHTML(c) || recShort(c))", body)
        self.assertIn("bodyTop(c, true)", _fn("detailHTML"))
        self.assertIn("bodyTop(c) +", JS.split("function compactHTML")[1][:200])

    def test_stamp_never_pairs_with_short_form(self):
        """도장과 짧은 신기록이 **같이** 나가는 조합이 소스에 없다 — 좁은 줄에서 둘 다 안 읽힌다."""
        self.assertNotIn("stampHTML(c) + recShort(c)", JS)


class ShapeTest(unittest.TestCase):
    """형태 — 도장과 **같은 자리, 다른 모양**. 도장처럼 그리면 둘을 같은 자로 읽는다(SPEC §CH3)."""

    def _rule(self, sel):
        m = re.search(re.escape(sel) + r"\{([^}]*)\}", CSS)
        self.assertIsNotNone(m, sel)
        return m.group(1)

    def test_record_is_plain_coral_text(self):
        rule = self._rule(".rec")
        self.assertIn("color:var(--accent)", rule)
        for banned in ("transform", "border", "background", "box-shadow"):
            self.assertNotIn(banned, rule, banned)

    def test_price_never_yields_its_line(self):
        """표식이 넓어져 `₩616,886` 과 `~` 가 갈라졌던 자리 — 가격은 안 밀린다(실측 2026-09-22)."""
        rule = self._rule(".hc-price")
        self.assertIn("white-space:nowrap", rule)
        self.assertIn("flex:none", rule)
        self.assertIn("flex-wrap:wrap", self._rule(".hc-row"))


if __name__ == "__main__":
    unittest.main()
