# -*- coding: utf-8 -*-
"""사진과 출처 표시 — PH8 (SPEC §CH2 사진 · 위키미디어 CC).

🔴 **이 파일이 지키는 것은 화면이 아니라 법적 의무다.** 사진은 전부 위키미디어 커먼즈에서
왔고 CC BY·BY-SA 가 대부분이다 — **표시 없이 쓰면 위반**이다. 그래서 막는 것은
「사진이 예쁘게 나오나」가 아니라 **「표시 없는 사진이 나가는가」**다.

여집합으로 **양방향**을 센다(`PLAN.md` 함정 11 — 남은 것만 보는 검사는 없는 것을 못 본다):
파일만 있으면 표시 없이 나가고, 행만 있으면 **없는 사진의 저작자를 밝힌다.**

사진이 **없는 목적지는 정상**이다(실측: 헬싱키·이시가키). 막지 않고 센다 —
실패로 걸면 백엔드가 목적지를 하나 늘린 날 사이트가 안 나간다.
"""
import ast
import io
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "site"))

import photos  # noqa: E402

PHOTO_DIR = os.path.join(ROOT, "public", "assets", "photos")
SRC = io.open(os.path.join(ROOT, "site", "photos.py"), encoding="utf-8").read()
BUILD = io.open(os.path.join(ROOT, "site", "build.py"), encoding="utf-8").read()


def row(**kw):
    base = {"city": "가고시마", "en": "Kagoshima", "title": "File:x.jpg", "author": "Hirase",
            "license": "CC BY-SA 3.0", "license_url": "https://creativecommons.org/licenses/by-sa/3.0",
            "page": "https://commons.wikimedia.org/wiki/File:x.jpg"}
    base.update(kw)
    return base


def credits(**rows):
    return {"photos": rows}


BOTH = {"", "-s"}


class GateTest(unittest.TestCase):
    """막아야 할 것을 정말 막나 — 하나씩 깨뜨려 본다."""

    def test_a_correct_set_passes(self):
        self.assertEqual(photos.problems(credits(KOJ=row()), {"KOJ": set(BOTH)}), [])

    def test_a_photo_without_a_credit_row_is_caught(self):
        """🔴 이 파일의 본체. 표시 없이 나가는 것이 **라이선스 위반**이다."""
        bad = photos.problems(credits(KOJ=row()), {"KOJ": set(BOTH), "HND": set(BOTH)})
        self.assertTrue(any("HND" in b and "CC 위반" in b for b in bad), bad)

    def test_a_credit_row_without_a_photo_is_caught(self):
        """없는 사진의 저작자를 밝히는 것도 **거짓 표시**다."""
        bad = photos.problems(credits(KOJ=row(), HND=row()), {"KOJ": set(BOTH)})
        self.assertTrue(any("HND" in b for b in bad), bad)

    def test_a_missing_size_is_caught(self):
        for have, word in ((set(["-s"]), "큰 사진"), (set([""]), "작은 썸네일")):
            bad = photos.problems(credits(KOJ=row()), {"KOJ": have})
            self.assertTrue(any(word in b for b in bad), (have, bad))

    def test_an_empty_attribution_field_is_caught(self):
        """빈 문자열은 예외가 아니다 — 표시가 **말없이 빈다**(`origin.py` 와 같은 이유)."""
        for k in ("author", "license", "license_url", "page", "title", "city"):
            bad = photos.problems(credits(KOJ=row(**{k: ""})), {"KOJ": set(BOTH)})
            self.assertTrue(any(("`%s`" % k) in b for b in bad), (k, bad))
        bad = photos.problems(credits(KOJ=row(author="   ")), {"KOJ": set(BOTH)})
        self.assertTrue(bad, "공백만 있는 저작자도 빈 것이다")

    def test_a_license_url_must_be_a_link(self):
        bad = photos.problems(credits(KOJ=row(license_url="by-sa/3.0")), {"KOJ": set(BOTH)})
        self.assertTrue(any("링크가 아니다" in b for b in bad), bad)

    def test_photos_without_any_credits_file_are_caught(self):
        bad = photos.problems({}, {"KOJ": set(BOTH)})
        self.assertTrue(any("credits.json" in b for b in bad), bad)

    def test_no_photos_at_all_is_not_a_failure(self):
        """사진을 아직 안 넣은 상태로도 빌드는 돌아야 한다 — 사진은 장식이다."""
        self.assertEqual(photos.problems({}, {}), [])


class MissingTest(unittest.TestCase):
    """사진 없는 목적지는 **세지만 막지 않는다.**"""

    def test_a_destination_without_a_photo_is_not_a_problem(self):
        c, d = credits(KOJ=row()), {"KOJ": set(BOTH)}
        self.assertEqual(photos.problems(c, d), [])
        self.assertEqual(photos.missing(c, d, ["KOJ", "HEL"]), ["HEL"])

    def test_summary_counts_both_sides(self):
        c, d = credits(KOJ=row(), HND=row()), {"KOJ": set(BOTH), "HND": set(BOTH)}
        have, allc, codes, unused = photos.summary(c, d, ["KOJ", "HEL"])
        self.assertEqual((have, allc, codes, unused), (1, 2, 2, ["HND"]))


class NoPillowTest(unittest.TestCase):
    """⚠️ CI 는 아무것도 설치하지 않는다 — 이미지 라이브러리를 import 하면 **문지기가 문을 막는다.**"""

    def test_the_gate_never_imports_an_image_library(self):
        """⚠️ **자를 두 번 고쳤다.** ① `assertNotIn("Pillow", SRC)` → docstring 의 「Pillow 를 쓰지
        않는다」에 걸렸다 ② 「`import` 로 시작하는 줄」 → 같은 docstring 의 「**import** 하면 이 검사가
        CI 를 죽인다」가 줄 맨 앞에 와서 코드로 잡혔다. **산문이 코드처럼 생긴 것**이다.
        이제 `ast` 로 **진짜 import 문**을 읽는다 — 문자열로 코드를 재지 않는다."""
        tree = ast.parse(SRC)
        names = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        self.assertTrue(names, "import 를 하나도 못 찾았다 — 검사를 할 수 없으면 실패다")
        for n in names:
            self.assertNotIn("PIL", n, "게이트가 이미지 라이브러리를 import 한다: %s" % n)
        self.assertEqual(sorted(names), ["io", "json", "os"],
                         "게이트는 표준 라이브러리 셋만 쓴다 — CI 는 아무것도 설치하지 않는다")

    def test_the_offline_tool_is_not_imported_by_the_build(self):
        """`tools/photos.py` 는 오프라인 도구다. 빌드가 부르면 CI 가 죽는다."""
        self.assertNotIn("tools", BUILD.split("def main")[0])
        self.assertNotIn("from tools", BUILD)

    def test_the_build_runs_the_gate_and_stops_on_failure(self):
        self.assertIn("photolib.problems(credits, on_disk)", BUILD)
        self.assertIn("사진과 출처 표시가 어긋난다 — 배포하지 않는다", BUILD)
        # 사진 없는 목적지로는 멈추지 않는다 — 세기만 한다
        seg = BUILD.split("photolib.missing")[1][:400]
        self.assertNotIn("sys.exit", seg)


class RealSetTest(unittest.TestCase):
    """실데이터 — 지금 저장소에 있는 사진 전부가 표시를 갖고 있나."""

    def setUp(self):
        self.c, self.d = photos.load(PHOTO_DIR)

    def test_the_real_set_passes_the_gate(self):
        self.assertEqual(photos.problems(self.c, self.d), [])

    def test_every_photo_on_disk_has_a_credit(self):
        rows = self.c.get("photos") or {}
        self.assertTrue(rows, "credits.json 이 비었다 — 검사를 할 수 없으면 통과가 아니라 실패다")
        self.assertEqual(sorted(set(self.d) - set(rows)), [])
        self.assertEqual(sorted(set(rows) - set(self.d)), [])

    def test_every_licence_is_a_creative_commons_one(self):
        """위키미디어에서 골랐어도 **모든 파일이 CC 는 아니다**(공정이용·상표 등이 섞인다).
        전부 CC 인지 실제로 센다 — 아니면 그 사진은 이 방식으로 쓸 수 없다."""
        for code, r in (self.c.get("photos") or {}).items():
            self.assertRegex(r["license"], r"^(CC BY(-SA)? \d(\.\d)?( \w+)?|CC0)",
                             "%s 의 라이선스가 CC 가 아니다: %s" % (code, r["license"]))
            # 🔴 **https 를 요구한다.** 기획 원본에 `http://` 가 7건 있어 도구가 스킴만 올린다 —
            # 우리가 내보내는 페이지에 http 링크를 섞지 않는다. 호스트·경로는 그대로다.
            self.assertTrue(r["license_url"].startswith("https://creativecommons.org/"),
                            "%s 의 라이선스 링크가 https://creativecommons.org 가 아니다: %s"
                            % (code, r["license_url"]))
            self.assertTrue(r["page"].startswith("https://commons.wikimedia.org/"),
                            "%s 의 출처가 커먼즈가 아니다" % code)

    def test_the_spec_version_is_recorded(self):
        """어느 발행분에서 왔는지 남긴다 — 사진이 바뀐 날 무엇이 바뀌었는지 댈 수 있어야 한다."""
        self.assertTrue(self.c.get("spec_generated"))
        self.assertTrue(self.c.get("source"))


if __name__ == "__main__":
    unittest.main()
