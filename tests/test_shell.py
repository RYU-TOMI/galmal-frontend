# -*- coding: utf-8 -*-
"""셸 — 모든 페이지가 **같은 옷**을 입는가 (DESIGN.md §컬러·§로고, 2026-09-20 B53).

홈과 노선 페이지가 서로 다른 옷을 입고 있었다:

  | | 홈 | 노선 페이지 |
  |---|---|---|
  | OS 가 다크일 때 | 밝음 | **어두움** — `shell.py` 에만 `@media (prefers-color-scheme: dark)` |
  | 로고 | 코랄 `말래` + 비행운 SVG | 청록 `말래` + ✈️ 이모지(`.brand`) |

둘 다 레포 분리 전 `theme.py` 의 유물이었고, 아무것도 안 깨지니 아무도 몰랐다 — OS 가 다크인 사람만
홈에서 노선으로 넘어가며 다른 사이트를 봤다. 여기서 지키는 것:

  1. **다크 색표가 다시 생기지 않는다** — 다크는 지도·핀·사진까지 사이트 전체를 한 번에 켤 때 한다.
     한 페이지만 켜면 같은 일이 다시 난다. 그날이 오면 이 테스트를 **같이** 고친다(둘 다 켜졌는지 보도록).
  2. **두 페이지의 로고가 `shell.logo()` 의 출력이다** — 손 사본·이모지로 대신하지 않는다.
"""
import io
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import home   # noqa: E402
import route  # noqa: E402
import shell  # noqa: E402

DISCOVER_CSS = io.open(os.path.join(ROOT, "public", "assets", "discover.css"), encoding="utf-8").read()

VOCAB = {"tags": {"top": ["해변"], "sub": {}}, "when": {"fixed": ["이번 달"], "patterns": []},
         "region_name": {"JP": "일본"}}
INDEX = {"routes": [{"code": "ICN-FUK", "o_name": "인천", "d_name": "후쿠오카"}]}
META = {"subscribe": {"address": "a@example.com", "subject_subscribe": "구독신청",
                      "subject_unsubscribe": "구독취소", "route_token": "{code}"}}
ROUTE = {"code": "ICN-FUK", "o_name": "인천", "d_name": "후쿠오카", "region": "JP",
         "summary": {"cheapest": 132536, "median": 306708, "n": 1784},
         "months": [], "weekdays": [], "airlines": [], "trend": []}


def _home():
    payload = {"generated": "2026-09-19T16:04:43+09:00", "origins": {}, "deals": []}
    return home.render_home(payload, home.inline_deals(payload), "{}", INDEX, VOCAB)


def _route():
    return route.render(ROUTE, INDEX, META, "2026-09-19", VOCAB["region_name"])[1]


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def dark_problems(*sheets):
    """스타일시트 어디에도 다크 분기가 없어야 한다. 있으면 문장 목록."""
    out = []
    for name, css in sheets:
        if re.search(r"prefers-color-scheme\s*:\s*dark", _strip_comments(css)):
            out.append("%s 에 `prefers-color-scheme: dark` 가 있다 — 한 페이지만 다크가 되면 홈↔노선이 다른 사이트가 된다" % name)
    return out


def _logo_inner(page_html):
    """페이지에서 `.gm-logo` 요소의 **안쪽**을 꺼낸다. 그라디언트 id 는 페이지마다 달라도 된다(충돌 방지용)."""
    m = re.search(r'<(a|span) class="gm-logo"[^>]*>(.*?</svg>)</\1>', page_html, re.S)
    return re.sub(r'id="\w+"|url\(#\w+\)', "ID", m.group(2)) if m else None


class OneLookTest(unittest.TestCase):

    def test_no_dark_branch_anywhere(self):
        self.assertEqual(dark_problems(("shell.CSS", shell.CSS), ("discover.css", DISCOVER_CSS)), [])

    def test_dark_branch_creeping_back_is_caught(self):
        """탐침 — 2026-09-20 까지 `shell.py` 에 실제로 있던 모양."""
        old = shell.CSS + "\n@media (prefers-color-scheme: dark) { :root { --bg:#0F2A29; } }"
        self.assertTrue(dark_problems(("shell.CSS", old)))
        self.assertTrue(dark_problems(("discover.css", DISCOVER_CSS + "@media(prefers-color-scheme:dark){body{background:#000}}")))

    def test_comment_mentioning_dark_is_not_a_branch(self):
        """주석에 그 말이 있는 것은 분기가 아니다 — 왜 없는지 적어 둔 주석에 걸리면 안 된다."""
        self.assertEqual(dark_problems(("x", "/* prefers-color-scheme: dark 는 쓰지 않는다 */ body{color:#000}")), [])

    def test_route_pages_declare_light(self):
        """명시하지 않으면 OS 가 다크일 때 폼 컨트롤·스크롤바가 다크로 간다."""
        self.assertRegex(_strip_comments(shell.CSS), r"color-scheme\s*:\s*light")


class OneLogoTest(unittest.TestCase):

    def test_both_pages_use_shell_logo(self):
        want = _logo_inner(shell.logo())
        self.assertIsNotNone(want)
        self.assertEqual(_logo_inner(_home()), want, "홈 로고가 shell.logo() 출력이 아니다")
        self.assertEqual(_logo_inner(_route()), want, "노선 페이지 로고가 shell.logo() 출력이 아니다")

    def test_route_logo_links_home(self):
        self.assertIn('<a class="gm-logo" href="%s/"' % shell.BASE_URL, _route())

    def test_no_emoji_or_text_wordmark(self):
        """탐침 — 예전 노선 페이지 머리(`.brand` + ✈️)가 돌아오면 잡힌다."""
        page = _route()
        self.assertNotIn("✈️", page)
        self.assertNotIn('class="brand"', page)
        old = page.replace(shell.logo(gid="gmr", href=shell.BASE_URL + "/"),
                           '<a class="brand" href="%s/">갈래<em>말래</em> ✈️</a>' % shell.BASE_URL)
        self.assertNotEqual(old, page, "탐침이 아무것도 안 바꿨다 — 로고 호출 모양이 달라졌으면 탐침을 고친다")
        self.assertIsNone(_logo_inner(old))

    def test_gradient_ids_do_not_collide_meaningfully(self):
        """한 페이지에 로고는 하나 — 같은 id 가 두 번 나오면 비행운 그라디언트가 엉뚱한 정의를 집는다."""
        for page in (_home(), _route()):
            ids = re.findall(r'<linearGradient id="(\w+)"', page)
            self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
