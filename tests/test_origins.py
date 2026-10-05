# -*- coding: utf-8 -*-
"""산출물이 **어디서 무엇을 받아 오는가** — 허용목록 (CH11, 기획 요청 2026-10-05).

`SESSIONS.md` 「기술 스택(고정)」은 **런타임 CDN 의존 0(폰트 제외)** 이라고 적어 뒀다.
적어 둔 것과 나가는 것이 같은지 **세는 곳이 없었다.** 지도는 `d3-geo` 를 벤더링해 두었는데,
어느 날 누가 `<script src="https://cdn…/d3.js">` 한 줄을 넣으면 **화면은 멀쩡하고**
의존만 늘어난다. 그게 이 프로젝트가 제일 비싸다고 적어 둔 형태다 — 조용히 통과하는 것.

🔴 **이 파일이 허용목록의 정본이다.** `SESSIONS.md` 에는 「검사가 있다」만 적는다 —
목록을 두 곳에 두면 한쪽만 자란다(레포 분리 첫날 `CONTRACT.md` 사본이 갈린 그 일).

실측(2026-10-05, 픽스처 빌드 · 텍스트 파일 57개):
  받아 오는 외부 출처 = **`cdn.jsdelivr.net` 하나**(Pretendard 글꼴 49 + preconnect 48)
  가리키는 외부 출처 = `commons.wikimedia.org` 77 · `creativecommons.org` 77 (사진 출처 표기)
  나머지는 전부 자기 자신(`galmal.kr`)이거나 상대 경로다.

**받아 오는 것과 가리키는 것을 가른다.** `<a href>` 는 사용자가 누를 때 **그쪽으로 가는** 것이지
우리 페이지가 받아 오는 게 아니다. 제휴 링크는 API 가 주므로 목록으로 묶을 수도 없다.
묶는 건 `src`·`<link>`·`url()`·`@import`·`fetch()` — **방문자가 페이지를 열면 자동으로 받는 것**이다.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 🔴 허용목록 — 이 둘만. 늘릴 땐 왜 벤더링할 수 없는지를 여기 적는다.
FONT_HOST = "cdn.jsdelivr.net"
FONT_PATH = "/gh/orioncactus/pretendard@"     # 버전까지 박힌다 — `@latest` 는 내용이 바뀐다
SELF = "galmal.kr"
ALLOWED_FETCH_HOSTS = {FONT_HOST, SELF}

# 🔴 **주석에만 적힌 주소.** 여집합 세기가 찾아 준 것이다 — 두 양동이(받아 온다 / 가리킨다)로는
# 안 잡혔다. 벤더링한 d3 파일 첫 줄의 저작권 머리말인데, **그게 바로 안 받아 온다는 증거**다.
# 지우면 저작권 표시가 사라지므로 지우지 않고, 「주석 안에만 있다」를 검사로 못 박는다.
COMMENT_ONLY = {"d3js.org": "벤더링한 d3-array·d3-geo 의 저작권 머리말(`// https://d3js.org/…`)"}

TEXT = (".html", ".css", ".js", ".json", ".xml", ".txt", ".svg", ".webmanifest")

# 페이지를 열면 **자동으로 받는** 자리들. `<a href>` 는 여기 없다 — 그건 가리키는 것이다.
FETCHERS = re.compile(
    r'\b(?:src|srcset|poster|data-src)\s*=\s*["\']([^"\']+)'
    r'|<link\b([^>]*)>'
    r'|url\(\s*["\']?([^"\')]+)'
    r'|@import\s+["\']([^"\']+)'
    r'|\bfetch\(\s*["\']([^"\']+)')
HOST = re.compile(r'^(?:https?:)?//([^/"\'\s]+)')
# `rel` 이 이 값이면 받아 오지 않는다 — 메타데이터다.
META_REL = ("canonical", "alternate", "me", "author", "license", "prev", "next")

_dist = None


def setUpModule():
    """픽스처로 한 번 굽는다 — 재는 대상은 소스가 아니라 **나가는 것**이다."""
    global _dist
    _dist = tempfile.mkdtemp(prefix="galmal-origins-")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "site", "build.py"),
                        "--api", os.path.join(ROOT, "fixtures", "v1"), "--out", _dist],
                       capture_output=True, cwd=ROOT)
    assert r.returncode == 0, (r.stdout + r.stderr).decode("utf-8", "replace")[-800:]


def tearDownModule():
    shutil.rmtree(_dist, ignore_errors=True)


def files():
    for root, _, fs in os.walk(_dist):
        for f in sorted(fs):
            if f.lower().endswith(TEXT):
                p = os.path.join(root, f)
                with io.open(p, encoding="utf-8", errors="replace") as fh:
                    yield os.path.relpath(p, _dist).replace("\\", "/"), fh.read()


def fetched():
    """(파일, 호스트, 원문) — 페이지가 자동으로 받아 오는 절대 주소 전부."""
    out = []
    for name, s in files():
        for m in FETCHERS.finditer(s):
            link_attrs = m.group(2)
            if link_attrs is not None:
                rel = re.search(r'\brel\s*=\s*["\']([^"\']+)', link_attrs)
                if rel and rel.group(1).strip().lower() in META_REL:
                    continue
                href = re.search(r'\bhref\s*=\s*["\']([^"\']+)', link_attrs)
                if not href:
                    continue
                u = href.group(1)
            else:
                u = next(g for g in (m.group(1), m.group(3), m.group(4), m.group(5)) if g)
            h = HOST.match(u.strip())
            if h:
                out.append((name, h.group(1), u.strip()))
    return out


class FetchedOriginsTest(unittest.TestCase):

    def test_nothing_outside_the_list(self):
        """🔴 **이 챕터가 세우는 문지기다.** 새 외부 출처가 들어오면 여기서 멈춘다."""
        hosts = sorted(set(h for _, h, _ in fetched()))
        self.assertEqual(set(hosts) - ALLOWED_FETCH_HOSTS, set(),
                         "허용목록에 없는 출처에서 받아 온다: %s" % hosts)

    def test_the_only_outside_host_is_the_font(self):
        """「폰트 제외」가 **폰트만**인지 — 글꼴 CDN 은 아무 패키지나 내준다."""
        outside = sorted(set(h for _, h, _ in fetched() if h != SELF))
        self.assertEqual(outside, [FONT_HOST])
        for name, h, u in fetched():
            if h == FONT_HOST:
                self.assertTrue(FONT_PATH in u or u.rstrip("/").endswith(FONT_HOST),
                                "%s 에서 글꼴 아닌 것을 받는다: %s" % (name, u))

    def test_the_font_version_is_pinned(self):
        """`@latest` 면 같은 주소가 **다른 내용**을 준다 — 글꼴이 바뀌는 날 아무도 모른다."""
        urls = [u for _, h, u in fetched() if h == FONT_HOST and FONT_PATH in u]
        self.assertTrue(urls, "글꼴을 안 받고 있다")
        for u in urls:
            v = u.split(FONT_PATH, 1)[1].split("/")[0]
            self.assertRegex(v, r"^v\d+\.\d+\.\d+$", "버전이 안 박혔다: " + u)

    def test_no_script_comes_from_outside(self):
        """`d3-geo` 는 벤더링한다 — 스크립트는 **한 줄도** 밖에서 받지 않는다."""
        bad = []
        for name, s in files():
            for m in re.finditer(r'<script\b[^>]*?\bsrc\s*=\s*["\']([^"\']+)', s):
                if HOST.match(m.group(1).strip()) and SELF not in m.group(1):
                    bad.append((name, m.group(1)))
        self.assertEqual(bad, [])

    def test_no_image_comes_from_outside(self):
        """사진은 우리가 굽는다 — 핫링크면 그쪽이 지우는 날 카드가 빈다."""
        bad = []
        for name, s in files():
            for m in re.finditer(r'<img\b[^>]*?\bsrc\s*=\s*["\']([^"\']+)', s):
                if HOST.match(m.group(1).strip()) and SELF not in m.group(1):
                    bad.append((name, m.group(1)))
        self.assertEqual(bad, [])

    def test_every_absolute_url_is_classified(self):
        """🔴 **여집합으로 센다.** 산출물의 절대 주소를 전부 모아 「받아 오는 것」과
        「가리키는 것」으로 가르고, **어느 쪽도 아닌 것이 0** 인지 본다.
        남은 것만 보는 검사는 **없는 것을 못 본다**(`PLAN.md` 함정 11)."""
        all_hosts, link_hosts = set(), set()
        host_in_text = re.compile(r'(?:https?:)?//([a-z0-9.\-]+\.[a-z]{2,})', re.I)
        for name, s in files():
            for m in host_in_text.finditer(s):
                all_hosts.add(m.group(1).lower())
            for m in re.finditer(r'<a\b[^>]*?\bhref\s*=\s*["\'](?:https?:)?//([^/"\'\s]+)', s):
                link_hosts.add(m.group(1).lower())
            for m in re.finditer(r'"(?:https?:)?//([a-z0-9.\-]+\.[a-z]{2,})[^"]*"', s, re.I):
                link_hosts.add(m.group(1).lower())
        fetch_hosts = set(h.lower() for _, h, _ in fetched())
        unclassified = all_hosts - link_hosts - fetch_hosts - ALLOWED_FETCH_HOSTS - set(COMMENT_ONLY)
        self.assertEqual(unclassified, set(), "분류되지 않은 출처: %s" % sorted(unclassified))
        self.assertGreater(len(all_hosts), 1, "주소를 하나도 못 찾았다 — 자가 고장났다")
        # 자가 도는지 — 세 양동이 중 하나라도 비면 분류가 아니라 통과 도장이 된다
        self.assertTrue(fetch_hosts and link_hosts and set(COMMENT_ONLY) <= all_hosts)

    def test_the_commented_hosts_are_only_in_comments(self):
        """🔴 주석 허용은 **주석까지만**이다. 같은 호스트가 `src=` 로 올라오면 잡는다."""
        for host in COMMENT_ONLY:
            self.assertNotIn(host, [h for _, h, _ in fetched()], host + " 를 실제로 받아 온다")
            places = []
            for name, s in files():
                for ln in s.split("\n"):
                    if host in ln:
                        places.append((name, ln.strip()))
            self.assertTrue(places, host + " 가 산출물에 없다 — 목록이 낡았다")
            for name, ln in places:
                self.assertTrue(ln.startswith("//") or ln.startswith("/*") or ln.startswith("*"),
                                "주석 밖에서 나타난다: %s · %s" % (name, ln[:80]))


class LinkedOriginsTest(unittest.TestCase):
    """가리키는 출처는 **묶지 않는다** — 제휴 링크는 API 가 준다. 대신 **세어서 적어 둔다.**"""

    def test_credit_links_go_to_the_source_and_the_licence(self):
        """사진 출처 표기는 두 곳을 가리켜야 쓸모가 있다 — 원본과 라이선스 전문."""
        hosts = set()
        for name, s in files():
            if not name.endswith("credits.html"):
                continue
            for m in re.finditer(r'<a\b[^>]*?\bhref\s*=\s*["\']https?://([^/"\']+)', s):
                hosts.add(m.group(1))
        self.assertIn("commons.wikimedia.org", hosts)
        self.assertIn("creativecommons.org", hosts)

    def test_outgoing_links_say_they_are_outgoing(self):
        """밖으로 나가는 링크엔 `rel` 이 붙어야 한다 — 제휴 고지는 `COPY` 소관이고,
        여기선 **빠진 것이 0** 인지만 본다."""
        bad = []
        for name, s in files():
            for m in re.finditer(r'<a\b([^>]*?\bhref\s*=\s*["\']https?://[^"\']+["\'][^>]*)>', s):
                attrs = m.group(1)
                if SELF in attrs:
                    continue
                if "rel=" not in attrs:
                    bad.append((name, attrs[:90]))
        self.assertEqual(bad, [], "rel 없는 외부 링크: %s" % bad[:3])


if __name__ == "__main__":
    unittest.main()
