# -*- coding: utf-8 -*-
"""어휘 키 매핑(TAG_GRAD · HAUL2STAGE)이 어휘를 다 덮는가 — 빠지면 빌드 실패 (CONTRACT §5).

이 두 매핑은 색·지도 단계라 계약에 없어야 맞고, 그래서 받아 없앨 수가 없다. 대신 **빠지면 조용히
폴백한다** — 새 태그는 기본 색, 새 haul 은 「아주 멀리」. 여기서는 그 폴백이 빌드 실패로 바뀌는지 본다.

탐침은 실제 `discover.js` 를 읽는다 — 가짜 JS 로 검사하면 진짜 파일의 모양이 바뀌었을 때를 못 잡는다.
"""
import io
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import coverage  # noqa: E402

JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
VOCAB = {"tags": {"top": ["해변", "도시", "미식", "자연", "문화", "온천"]},
         "haul": ["short", "mid", "long"]}
DEALS = [{"ko": "오사카", "tags": ["미식", "도시"]}, {"ko": "다낭", "tags": ["리조트", "해변"]}]


class CoverageTest(unittest.TestCase):

    def test_real_js_covers_vocab(self):
        self.assertEqual(coverage.problems(JS, VOCAB, DEALS), [])

    def test_new_top_tag_without_color_fails(self):
        """탐침 — 백엔드가 대표 태그를 하나 더하면, 색을 정하기 전까지 빌드가 멈춘다."""
        v = dict(VOCAB, tags={"top": VOCAB["tags"]["top"] + ["스키"]})
        bad = coverage.problems(JS, v, DEALS)
        self.assertEqual(len(bad), 1)
        self.assertIn("스키", bad[0])

    def test_new_haul_fails(self):
        """탐침 — 새 haul 은 지금 `|| "far"` 로 조용히 「아주 멀리」에 뜬다."""
        v = dict(VOCAB, haul=VOCAB["haul"] + ["ultra"])
        bad = coverage.problems(JS, v, DEALS)
        self.assertEqual(len(bad), 1)
        self.assertIn("ultra", bad[0])

    def test_deal_without_colored_tag_fails(self):
        """구조 검사(대표 6개에 색)는 「모든 딜이 대표 태그를 가진다」 전제 위에서만 충분하다.
        그 전제가 깨진 딜 — 색 없는 하위 태그만 가진 딜 — 은 실데이터 검사가 잡는다."""
        deals = DEALS + [{"ko": "제주", "tags": ["리조트"]}]
        bad = coverage.problems(JS, VOCAB, deals)
        self.assertEqual(len(bad), 1)
        self.assertIn("제주", bad[0])

    def test_sub_tag_color_is_fine(self):
        """하위 태그 일부는 자기 색이 있다(야시장 등) — 그 색을 받아도 정상이다."""
        self.assertEqual(coverage.problems(JS, VOCAB, [{"ko": "타이베이", "tags": ["야시장", "미식"]}]), [])

    def test_unreadable_map_is_failure_not_pass(self):
        """이름이 바뀌어 정규식이 빈손이면 「빠진 게 없다」로 읽히면 안 된다."""
        broken = JS.replace("var TAG_GRAD =", "var TAG_COLORS =")
        bad = coverage.problems(broken, VOCAB, DEALS)
        self.assertTrue(any("TAG_GRAD" in b and "못 읽었다" in b for b in bad))
        broken = JS.replace("var HAUL2STAGE =", "var HAUL_MAP =")
        bad = coverage.problems(broken, VOCAB, DEALS)
        self.assertTrue(any("HAUL2STAGE" in b and "못 읽었다" in b for b in bad))


if __name__ == "__main__":
    unittest.main()
