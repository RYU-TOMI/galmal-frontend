# -*- coding: utf-8 -*-
"""상세의 「평소 시세와 비교」 — **막대가 없으면 왜 없는지 말한다** (SPEC §CH4, BACKLOG B67).

2026-09-01 에 확정된 규칙인데 2026-09-21 까지 구현이 없었다. 두 경우 모두 빈 문자열이라 **근거 자리가
말없이 사라졌다** — 확장 상세는 결정하는 자리인데 거기서 아무 말이 없으면 사용자는 "왜 근거가 없지"를
혼자 생각한다. 라이브 실측(2026-09-21, 딜 138건): `median <= price` 65건(47%) · `median` 없음 5건.
**상세 둘 중 하나가 이 자리였다.**

  | 경우 | 문구 |
  |---|---|
  | `median` 없음 | `아직 이 노선의 평소 시세를 모아두지 못했어요` — 모른다 |
  | `median <= price` · 반올림 `0%` | `지금은 평소 시세와 비슷해요` — 알아봤는데 아니다 |

**둘을 한 문구로 뭉치지 않는다.** 전자를 후자처럼 쓰면 **없는 근거를 있는 척**하는 게 된다.
「평소보다 비싸요」도 쓰지 않는다 — `price` 는 그날 최저가, `median` 은 거친 기준선이라 몇 %p 차이를
「비싸다」고 단정할 만큼 정밀하지 않다.

JS 를 파이썬으로 읽는다 — 이 저장소엔 Node 빌드가 없다(`CLAUDE.md`). 그래서 **분기 조건과 문구가
소스에 있는지**를 본다. 화면에서 실제로 그려지는지는 CDP 로 따로 확인한다(`FRONTEND.md` §3).
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

NO_MEDIAN = "아직 이 노선의 평소 시세를 모아두지 못했어요"
SIMILAR = "지금은 평소 시세와 비슷해요"


def _fn(name):
    """`function name(...) { … }` 한 덩이. 주석은 걷어낸다 — 주석 속 문구에 속지 않는다."""
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


class CopyTest(unittest.TestCase):

    def test_both_messages_exist_and_are_distinct(self):
        body = _fn("priceCompare")
        self.assertIsNotNone(body, "priceCompare() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다")
        self.assertIn(NO_MEDIAN, body)
        self.assertIn(SIMILAR, body)
        self.assertNotEqual(NO_MEDIAN, SIMILAR)

    def test_no_silent_empty_return(self):
        """🔴 이 자리의 본래 결함 — 빈 문자열로 조용히 사라지던 것. 어떤 갈래도 `return ""` 로 끝나지 않는다."""
        self.assertNotIn('return ""', _fn("priceCompare"))

    def test_never_claims_more_expensive(self):
        for banned in ("비싸요", "비쌉니다", "%↑"):
            self.assertNotIn(banned, _fn("priceCompare"), banned)

    def test_note_is_not_emphasised(self):
        """불리한 사실을 말하는 자리다 — 강조하지 않는다. 크기·색은 고지 하한과 같은 12px·`--sub`."""
        m = re.search(r"\.pc-none\{([^}]*)\}", CSS)
        self.assertIsNotNone(m)
        rule = m.group(1)
        self.assertIn("font-size:.75rem", rule)
        self.assertIn("color:var(--sub)", rule)
        self.assertNotIn("opacity", rule)
        self.assertNotIn("var(--accent)", rule)
        self.assertNotIn("font-weight:8", rule)


class BranchTest(unittest.TestCase):
    """분기 조건이 소스에 있는가 — 값 계산은 아래 `RuleTest` 가 파이썬으로 다시 돌려 본다."""

    def test_no_median_comes_first(self):
        """`median` 이 없을 때가 **먼저** 갈라져야 한다. 「비슷해요」로 새면 모르는 걸 안다고 하는 것이다."""
        body = _fn("priceCompare")
        self.assertLess(body.index(NO_MEDIAN), body.index(SIMILAR))
        self.assertIn("if (!med)", body)

    def test_rounded_zero_goes_to_similar(self):
        """반올림해 `0%` 면 「비슷해요」 — 화면에 `0%` 라고 쓰는 순간 그건 주장이 아니다(기획 2026-09-21)."""
        body = _fn("priceCompare")
        self.assertRegex(body, r"if \(med <= now \|\| pct < 1\)")
        self.assertIn(SIMILAR, body.split("pct < 1")[1][:120])


def rule(price, median):
    """`priceCompare()` 의 판정을 파이썬으로 옮긴 것 — 경계값을 실제로 돌려 본다.
    옮긴 사본이라 JS 와 갈릴 수 있다: 위 `BranchTest` 가 조건식 모양을 같이 지킨다."""
    med = median or 0
    if not med:
        return "none"
    pct = round((med - price) / med * 100)
    if med <= price or pct < 1:
        return "similar"
    return "bar"


class RuleTest(unittest.TestCase):

    def test_three_outcomes(self):
        self.assertEqual(rule(100000, None), "none")
        self.assertEqual(rule(100000, 0), "none")
        self.assertEqual(rule(100000, 100000), "similar")     # 같다
        self.assertEqual(rule(100000, 90000), "similar")      # 평소가 더 싸다
        self.assertEqual(rule(100000, 120000), "bar")

    def test_rounding_boundary(self):
        """0.4% 는 「비슷해요」, 0.6% 는 반올림하면 1% 라 막대. 파이썬 `round` 는 은행가 반올림이라
        경계 자체를 테스트하지 않고 **양쪽이 갈린다**는 것만 본다(JS `Math.round` 와 미세하게 다를 수 있다)."""
        self.assertEqual(rule(99600, 100000), "similar")      # 0.4%
        self.assertEqual(rule(98000, 100000), "bar")          # 2%

    def test_every_fixture_deal_lands_somewhere(self):
        """실데이터 전수 — 어떤 딜도 「아무 말 없음」으로 떨어지지 않는다. 그게 이 챕터의 본래 결함이다."""
        kinds = {}
        for d in DEALS:
            kinds.setdefault(rule(d["price"], d.get("median")), []).append(d.get("ko"))
        self.assertEqual(sorted(kinds), ["bar", "none", "similar"], "세 갈래가 다 나와야 검사가 눈을 뜬다")
        self.assertEqual(len(DEALS), sum(len(v) for v in kinds.values()))

    def test_fixture_mix_is_worth_testing(self):
        """말없이 비던 딜이 실제로 절반쯤이었다 — 그 비율이 이 챕터를 앞으로 당긴 근거다."""
        quiet = sum(1 for d in DEALS if rule(d["price"], d.get("median")) != "bar")
        self.assertGreater(quiet, len(DEALS) * 0.3)


if __name__ == "__main__":
    unittest.main()
