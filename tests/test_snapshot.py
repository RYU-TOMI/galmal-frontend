# -*- coding: utf-8 -*-
"""snapshot — 받은 v1 응답이 한 발행분인가 (SPLIT.md M5 T6d · CONTRACT.md §공통 규칙).

2026-09-17 신형 크론 첫 실행에서 사이트가 **어제 데이터로 구워졌다.** 백엔드 신호가 API
배포보다 먼저 왔고, API 앞 CDN 캐시가 파일마다 따로 걸려 있어 **날짜가 섞인 사이트**도
가능하다. 화면은 멀쩡해 보여서 아무도 모른다.

여기서 지키는 건 넷이다:
  1. 노선·목록·참조 데이터(vocab)는 meta 와 같은 시각이어야 한다
  2. deals 는 평소엔 같고, **보존일(preserved)엔 더 이전**이어야 한다
  3. 백엔드가 신호로 알려준 시각이 있으면 meta 와 같아야 한다
  4. 끝내 안 맞으면 **아무것도 쓰기 전에** 멈춘다

2번 보존일 분기는 **실데이터로는 그날이 와야만 볼 수 있다** — 그래서 여기서 고정한다.
처음엔 「39개 전부 같다」로 짰다가 백엔드 반례(보존일엔 deals 만 어제 시각)로 고쳤다.
그대로 뒀으면 보존일마다 배포가 통째로 멈췄다.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site"))

import snapshot  # noqa: E402

G = "2026-09-17T11:45:25+09:00"
YESTERDAY = "2026-09-16T15:49:59+09:00"


def snap(meta=G, index=G, deals=G, vocab=G, routes=None, preserved=False):
    routes = routes if routes is not None else {"ICN-FUK": G, "ICN-NRT": G}
    return {
        "meta": {"generated": meta, "preserved": preserved},
        "index": {"generated": index, "routes": [{"code": c} for c in routes]},
        "deals": {"generated": deals},
        "vocab": {"generated": vocab},
        "routes": {c: {"generated": g} for c, g in routes.items()},
    }


class SnapshotTest(unittest.TestCase):

    def test_one_publish_passes(self):
        self.assertEqual(snapshot.problems(snap()), [])

    def test_stale_route_is_caught(self):
        """목록은 오늘인데 노선 하나가 어제 — CDN 이 파일마다 따로 캐시해서 생기는 섞임."""
        bad = snapshot.problems(snap(routes={"ICN-FUK": G, "ICN-NRT": YESTERDAY}))
        self.assertEqual(len(bad), 1)
        self.assertIn("ICN-NRT", bad[0])

    def test_stale_index_is_caught(self):
        self.assertTrue(snapshot.problems(snap(index=YESTERDAY)))

    def test_stale_deals_on_normal_day_is_caught(self):
        self.assertTrue(snapshot.problems(snap(deals=YESTERDAY, preserved=False)))

    def test_preserved_day_older_deals_passes(self):
        """보존일엔 deals 만 어제 시각이 정상이다. 이걸 막으면 그날 배포가 통째로 멈춘다."""
        self.assertEqual(snapshot.problems(snap(deals=YESTERDAY, preserved=True)), [])

    def test_preserved_day_same_deals_is_contradiction(self):
        """보존일인데 deals 가 오늘 시각이면 계약과 모순이다."""
        self.assertTrue(snapshot.problems(snap(deals=G, preserved=True)))

    def test_preserved_compares_times_not_strings(self):
        """오프셋이 달라도 시각으로 비교한다. 문자열 비교면 +00:00 이 +09:00 보다 뒤로 정렬될 수 있다."""
        earlier_utc = "2026-09-17T01:00:00+00:00"   # = 10:00 KST, G(11:45 KST)보다 이전
        self.assertEqual(snapshot.problems(snap(deals=earlier_utc, preserved=True)), [])

    def test_vocab_one_second_off_is_caught(self):
        """탐침 — vocab 만 1초 어긋나도 잡는다. 초 단위 차이는 사람 눈엔 같은 발행으로 보인다."""
        one_sec = "2026-09-17T11:45:26+09:00"
        bad = snapshot.problems(snap(vocab=one_sec))
        self.assertEqual(len(bad), 1)
        self.assertIn("vocab", bad[0])

    def test_vocab_on_preserved_day_is_still_today(self):
        """보존일에도 참조 데이터는 매 발행 새로 쓴다 — deals 만 어제, vocab 은 오늘 G."""
        self.assertEqual(snapshot.problems(snap(deals=YESTERDAY, vocab=G, preserved=True)), [])
        self.assertTrue(snapshot.problems(snap(deals=YESTERDAY, vocab=YESTERDAY, preserved=True)))

    def test_backend_signal_mismatch_is_caught(self):
        """백엔드는 새로 발행했다고 알렸는데 우리가 받은 meta 는 옛것 — 옛 캐시를 받았다."""
        bad = snapshot.problems(snap(), expect="2026-09-18T09:00:00+09:00")
        self.assertEqual(len(bad), 1)
        self.assertIn("옛 캐시", bad[0])

    def test_backend_signal_match_passes(self):
        self.assertEqual(snapshot.problems(snap(), expect=G), [])

    def test_no_signal_still_checks_mixing(self):
        """신호가 없는 실행(수동·push)도 섞임 검사는 한다 — 특정 값을 강요하지 않고 섞이지 않았다만 본다."""
        self.assertTrue(snapshot.problems(snap(routes={"ICN-FUK": YESTERDAY}), expect=None))


class LoadTest(unittest.TestCase):

    def test_gives_up_and_exits(self):
        """끝내 안 맞으면 SystemExit — 호출자는 산출물을 쓰기 전에 멈춘다."""
        orig = snapshot.fetch_all
        snapshot.fetch_all = lambda api: snap(routes={"ICN-FUK": YESTERDAY})
        try:
            with self.assertRaises(SystemExit):
                snapshot.load("x", retries=2, wait=0, log=lambda *a: None)
        finally:
            snapshot.fetch_all = orig

    def test_recovers_when_cache_catches_up(self):
        """첫 번째는 옛 캐시, 두 번째는 새것 — 재시도로 회복한다."""
        calls = []
        orig = snapshot.fetch_all

        def fake(api):
            calls.append(1)
            return snap(routes={"ICN-FUK": YESTERDAY}) if len(calls) == 1 else snap()
        snapshot.fetch_all = fake
        try:
            got = snapshot.load("x", retries=3, wait=0, log=lambda *a: None)
            self.assertEqual(got["meta"]["generated"], G)
            self.assertEqual(len(calls), 2)
        finally:
            snapshot.fetch_all = orig


if __name__ == "__main__":
    unittest.main()
