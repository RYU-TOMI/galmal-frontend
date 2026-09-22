# -*- coding: utf-8 -*-
"""데이터가 언제 것인지 화면이 말하는가 — **조용한 실패를 깨는 자리** (SPEC §CH6 C-15 · COPY §2d-2).

백엔드는 수집이 하한에 못 미친 날 `deals.json` 을 **새로 쓰지 않고 어제 것을 그대로 서빙**한다(보존, BB1).
가용성은 옳지만 **화면은 여전히 「오늘의 발견」이라고 말한다** — 사용자는 어제 가격을 오늘 가격으로 읽는다.
2026-09-01 에 정해 놓고 **3주 동안 화면에 없었다**(2026-09-22 전수 대조에서 드러남).

  | `generated` 의 KST 날짜 | 피드 헤드 뒤 |
  |---|---|
  | 오늘 | `· {HH:MM} 기준` |
  | 어제 | `· {M/D(요일)} {HH:MM} 기준 · 어제 자료예요` |
  | 그제 이상 | `· {M/D(요일)} {HH:MM} 기준 · {N}일 전 자료예요` |

🔴 **판정은 KST 로 한다.** `generated` 는 `+09:00` 이고 방문자는 해외일 수 있다 — 브라우저 로컬 날짜로
비교하면 **한국 아닌 곳에서 낡음 경고가 안 뜬다**(아래 `test_local_date_would_hide_the_warning` 이 그 차이를 센다).

Node 빌드가 없어 JS 는 정규식으로 읽고, 날짜 계산은 같은 규칙을 파이썬으로 옮겨 경계를 돌린다.
"""
import datetime as dt
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JS = io.open(os.path.join(ROOT, "public", "assets", "discover.js"), encoding="utf-8").read()
CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()

YDAY = "어제 자료예요"
OLDER = "일 전 자료예요"
KST = dt.timezone(dt.timedelta(hours=9))


def fn(name, js=None):
    m = re.search(r"function %s\([^)]*\) \{(.*?)\n  \}\n" % re.escape(name), js or JS, re.S)
    return re.sub(r"(?m)^\s*//.*$", "", m.group(1)) if m else None


def head(updated, now_utc):
    """`updatedHTML()` 의 판정을 옮긴 것 — 경계를 실제로 돌려 본다.
    옮긴 사본이라 갈릴 수 있어 아래 `SourceTest` 가 조건식 모양을 같이 지킨다."""
    day, hm = updated[:10], updated[11:16]
    if len(day) != 10 or len(hm) != 5:
        return ""
    kst_today = (now_utc + dt.timedelta(hours=9)).date()
    n = (kst_today - dt.date.fromisoformat(day)).days
    if n <= 0:
        return " · %s 기준" % hm
    return " · %s %s 기준 · %s" % ("MD", hm, YDAY if n == 1 else "%d%s" % (n, OLDER))


class RuleTest(unittest.TestCase):

    def test_three_cases(self):
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)      # = 09-22 10:00 KST
        self.assertEqual(head("2026-09-22 07:23", now), " · 07:23 기준")
        self.assertIn(YDAY, head("2026-09-21 07:23", now))
        self.assertIn("3" + OLDER, head("2026-09-19 07:23", now))

    def test_absolute_date_appears_only_when_stale(self):
        """낡았을 때만 날짜를 앞에 붙인다 — 「어제 자료」만으론 어느 어제인지 확인이 안 된다(§2d 두 단 위계)."""
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        self.assertNotIn("MD", head("2026-09-22 07:23", now))
        self.assertIn("MD", head("2026-09-21 07:23", now))

    def test_two_days_is_not_called_yesterday(self):
        """🔴 `어제` 로 고정하면 **그제인데 어제라고 말한다** — 신선도에서 「나흘·닷새」를 버린 것과 같은 함정."""
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        out = head("2026-09-20 07:23", now)
        self.assertIn("2" + OLDER, out)
        self.assertNotIn(YDAY, out)

    def test_future_or_equal_says_nothing_extra(self):
        """시계가 어긋나 미래로 보여도 경고하지 않는다 — 모르는 걸 말하지 않는다."""
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(head("2026-09-23 07:23", now), " · 07:23 기준")

    def test_garbage_says_nothing(self):
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        for bad in ("", "2026-09-22", "nonsense", "2026-09-2207:23"):
            self.assertEqual(head(bad, now), "", bad)

    def test_local_date_would_hide_the_warning(self):
        """🔴 **대조군** — 로컬 날짜로 비교하면 한국 아닌 곳에서 낡음 경고가 **사라진다.**

        09-22 01:00 UTC 는 KST 로 09-22 아침이고 뉴욕은 아직 09-21 저녁이다.
        데이터가 09-21(KST 로 어제)일 때 뉴욕 로컬 날짜로 재면 「오늘」이 되어 경고가 안 뜬다."""
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        self.assertIn(YDAY, head("2026-09-21 07:23", now))                      # KST 판정 — 뜬다
        ny_today = now.astimezone(dt.timezone(dt.timedelta(hours=-4))).date()
        self.assertEqual((ny_today - dt.date(2026, 9, 21)).days, 0)             # 로컬 판정 — 안 뜬다


class SourceTest(unittest.TestCase):

    def test_reads_kst_not_local_date(self):
        body = fn("kstToday")
        self.assertIsNotNone(body, "kstToday() 를 못 찾았다 — 검사를 할 수 없으면 통과가 아니라 실패다")
        self.assertIn("9 * 36e5", body)
        self.assertIn("toISOString", body)
        self.assertNotIn("getFullYear", body)          # 로컬 날짜로 새지 않게

    def test_all_three_strings_present(self):
        body = fn("updatedHTML")
        self.assertIsNotNone(body)
        self.assertIn("기준", body)
        self.assertIn(YDAY, body)
        self.assertIn(OLDER, body)

    def test_head_actually_uses_it(self):
        """문구를 만들어 놓고 **안 붙이면** 이 자리의 본래 결함이 그대로다."""
        self.assertIn("updatedHTML()", fn("render"))

    def test_stale_is_not_painted_with_the_deal_colour(self):
        """코랄은 이 화면에서 「싸다」의 색이다. 경고색도 만들지 않는다 — 오래된 건 위험이 아니라 사실이다."""
        m = re.search(r"\.feedhead \.stale\{([^}]*)\}", CSS)
        self.assertIsNotNone(m)
        rule = m.group(1)
        self.assertIn("color:var(--ink)", rule)
        self.assertNotIn("--accent", rule)
        self.assertNotIn("red", rule)

    def test_shows_while_filtering_too(self):
        """데이터의 나이는 **필터와 무관한 페이지 전체의 사실**이라 필터 중에도 붙는다."""
        render = fn("render")
        head_line = [l for l in render.split("\n") if "updatedHTML()" in l][0]
        self.assertNotIn("anyFilter", head_line)


if __name__ == "__main__":
    unittest.main()
