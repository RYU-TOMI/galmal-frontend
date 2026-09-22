# -*- coding: utf-8 -*-
"""교통 표기는 **거리와 무관하게 텍스트 하나다** (사용자 결정 2026-09-22 · SPEC §CH3 · DECISIONS (8)).

예전엔 중·장거리 직항만 청록 배지(`✈ 직항`)였고 근거리 직항은 그냥 `직항` 이었다.
규칙 자체는 말이 됐다 — 「근거리 직항은 당연하고 장거리 직항은 소식이다」.
그런데 사용자가 실사용에서 물었다: **「어떤 직항은 아이콘 배지고 어떤 건 두 글자던데 의도된 거냐」**

🔴 **규칙을 아는 사람에게만 규칙이었다.** 화면에 「이건 거리가 멀어서 배지다」라고 적혀 있지 않으니
읽는 쪽에는 들쭉날쭉으로 보이고, 같은 말을 두 모양으로 그리면 **두 모양이 다른 뜻이라고 읽는다** —
없는 구분을 만들어 낸 셈이다. 이 테스트는 그 구분이 **다시 생기지 않게** 막는다.

실측(1440, 픽스처 78장): 배지 12 → 0 · 텍스트 66 → 78 · **바뀐 줄 12, 그대로인 줄 66.**
경유 카드는 한 글자도 안 건드렸다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()


def _fn(name):
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


class TransportTest(unittest.TestCase):

    def setUp(self):
        self.body = _fn("transportHTML")
        self.assertIsNotNone(self.body, "transportHTML() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다")

    def test_one_shape_only(self):
        """🔴 나가는 모양이 **`.trx` 하나**다. 두 모양이 있으면 사용자가 뜻을 나눠 읽는다."""
        self.assertEqual(self.body.count('class="trx"'), 2)      # 직항 · 경유 두 문구, 같은 모양
        self.assertNotIn("bdg", self.body)
        self.assertNotIn("✈", self.body)

    def test_distance_no_longer_decides(self):
        """`haul` 로 갈리지 않는다 — 거리는 무대(`stageIdxOf`)가 쓰는 값이지 교통 표기의 값이 아니다."""
        self.assertNotIn("haul", self.body)
        self.assertNotIn("short", self.body)

    def test_only_transfers_decides(self):
        self.assertIn("dl.transfers > 0", self.body)
        self.assertIn("경유 ", self.body)
        self.assertIn("직항", self.body)

    def test_dead_rule_is_gone(self):
        """쓰는 데 없는 CSS 를 남기면 다음 사람이 「어디서 쓰나」부터 찾는다(B44 죽은 키와 같은 축).
        `.bdg` 는 이 배지만 쓰던 규칙이라 같이 지웠다 — **정말 아무 데서도 안 쓰는지** 여기서 센다."""
        self.assertEqual(JS.count("bdg"), 0)
        # 주석은 걷어내고 센다 — **왜 지웠나는 남겨야** 다음 사람이 배지를 다시 만들지 않는다.
        # 주석 속 `.bdg` 에 걸려 규칙이 살아 있다고 오해하면, 이 검사는 문서를 벌하는 검사가 된다.
        rules = re.sub(r"/\*.*?\*/", "", CSS, flags=re.S)
        self.assertEqual(rules.count(".bdg"), 0)
        self.assertIn(".bdg", CSS, "왜 지웠는지가 주석에 남아 있어야 한다")

    def test_date_badge_survives(self):
        """탐침 — 「배지를 다 지웠나」가 아니다. 날짜 배지(`.when`)는 그대로여야 한다."""
        self.assertIn(".when{", CSS)
        self.assertIn('class="when"', JS)


if __name__ == "__main__":
    unittest.main()
