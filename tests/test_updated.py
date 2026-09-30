# -*- coding: utf-8 -*-
"""데이터가 언제 것인지 화면이 말하는가 — **조용한 실패를 깨는 자리** (SPEC §CH6 C-15 · COPY §2d-2).

백엔드는 수집이 하한에 못 미친 날 `deals.json` 을 **새로 쓰지 않고 어제 것을 그대로 서빙**한다(보존, BB1).
가용성은 옳지만 **화면은 여전히 「오늘의 발견」이라고 말한다** — 사용자는 어제 가격을 오늘 가격으로 읽는다.
2026-09-01 에 정해 놓고 **3주 동안 화면에 없었다**(2026-09-22 전수 대조에서 드러남).

  | `generated` 의 KST 날짜 | 피드 헤드 뒤 |
  |---|---|
  | 오늘 | `· {HH:MM} 기준` |
  | 어제 | `· **어제** {HH:MM} 기준` |
  | 그제 이상 | `· **{N}일 전** {HH:MM} 기준` |

🔴 **2026-09-29 에 줄였다** (사용자: 「어제 자료에요 라는 정보 필요할까」).
예전엔 `· 9/28(월) 03:18 기준 · 어제 자료예요` 로 **날짜와 그 날짜의 뜻**을 나란히 놨다.
실측: 그 길이가 제목을 밀어 「오늘의 발견」의 「견」이 둘째 줄로 내려갔다.
이제 절대 날짜 자리에 **상대 날짜**를 넣어 한 번만 말하고, 신선한 날의 `03:18 기준` 과 **같은 모양**이 된다.
⚠️ 이건 `COPY.md` §2d 「두 단 위계」(「어제 자료」만으론 어느 어제인지 확인이 안 된다)를 **대체한 결정**이다 —
기획에 통지했다. 근거를 지우지 않고 옮겨 적는다.

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

YDAY = "어제"
OLDER = "일 전"
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
    return " · %s %s 기준" % (YDAY if n == 1 else "%d%s" % (n, OLDER), hm)


class RuleTest(unittest.TestCase):

    def test_three_cases(self):
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)      # = 09-22 10:00 KST
        self.assertEqual(head("2026-09-22 07:23", now), " · 07:23 기준")
        self.assertIn(YDAY, head("2026-09-21 07:23", now))
        self.assertIn("3" + OLDER, head("2026-09-19 07:23", now))

    def test_only_the_stale_day_gets_a_day_word(self):
        """신선한 날에는 날짜 말이 없다 — `· 07:23 기준` 뿐이다. 낡은 날에만 **상대 날짜**가 앞에 붙는다."""
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(head("2026-09-22 07:23", now), " · 07:23 기준")
        self.assertEqual(head("2026-09-21 07:23", now), " · 어제 07:23 기준")

    def test_the_same_thing_is_not_said_twice(self):
        """🔴 2026-09-29 에 줄인 그 자리. 절대 날짜와 그 날짜의 뜻을 **같이** 놓지 않는다 —
        그 길이가 제목을 밀어 「견」이 둘째 줄로 내려갔다.

        옛 모양(`· 9/28(월) 03:18 기준 · 어제 자료예요`)이 되살아나면 잡는다."""
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        out = head("2026-09-21 07:23", now)
        self.assertNotIn("자료예요", out)
        self.assertEqual(out.count("기준"), 1)
        self.assertEqual(out.count("·"), 1, "구분점이 둘이면 두 토막으로 말하고 있다")
        # 소스에도 절대 날짜가 안 붙는다 — 옮긴 사본만 고치고 JS 를 안 고치면 조용히 갈린다.
        body = fn("updatedHTML")
        self.assertNotIn("fmtMD", body, "낡음 표시에 절대 날짜를 다시 붙였다")

    def test_two_days_is_not_called_yesterday(self):
        """🔴 `어제` 로 고정하면 **그제인데 어제라고 말한다** — 신선도에서 「나흘·닷새」를 버린 것과 같은 함정."""
        now = dt.datetime(2026, 9, 22, 1, 0, tzinfo=dt.timezone.utc)
        out = head("2026-09-20 07:23", now)
        self.assertEqual(out, " · 2일 전 07:23 기준")
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


class HeadRoomTest(unittest.TestCase):
    """🔴 **낡음 배지가 제목을 밀어내지 않는다** (사용자 2026-09-29: 「오늘의 발견 에서 견이
    아래로 내려갔음」).

    `.fh-top` 은 flex 라 옆 글이 길어지면 **제목이 먼저 줄어든다.** 실측: 「· 어제 자료예요」가
    붙는 순간 제목이 74 → **72px**(자연폭 76)로 눌려 **「견」이 둘째 줄로** 내려갔다(높이 20 → 40).
    4px 이 모자라서 생긴 일이다.

    **이 배지가 있는 날에만 생긴다** — 그래서 3주 넘게 아무도 못 봤다. C-15 를 넣어 배지를
    띄우기 시작한 쪽과 같은 자리이고, 배지를 못 띄우던 시절엔 드러날 수 없었다.
    CH8 이 낸 것이 아니다: 같은 데이터로 CH8 이전 빌드를 나란히 재니 제목이 똑같이 **2줄**이었다.

    줄어들 쪽은 **옆의 작은 글자**다(그쪽은 원래 2줄로 접힌다).
    """

    def test_the_title_never_shrinks(self):
        self.assertIn(".fh-top>b{flex:none;white-space:nowrap}", CSS)

    def test_the_small_text_is_the_one_that_gives_way(self):
        """`min-width:0` 이 없으면 flex 항목은 **자기 내용보다 작아지지 않아** 제목을 다시 민다."""
        self.assertIn(".fh-top>span{min-width:0;text-align:right}", CSS)

    def test_the_two_are_not_glued_together(self):
        """제목이 안 줄어들면 둘이 붙을 수 있다 — 사이를 띄운다."""
        m = re.search(r"\.fh-top\{([^}]*)\}", CSS)
        self.assertIsNotNone(m)
        self.assertIn("gap:", m.group(1))


if __name__ == "__main__":
    unittest.main()
