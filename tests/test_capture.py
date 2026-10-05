# -*- coding: utf-8 -*-
"""capture — 받다 실패해도 **옛 사본을 깨지 않는다** (B52-②, CH11 T2).

`fixtures/capture.py` 는 받아 적는 도구다. 받기 **전에** `fixtures/v1/` 을 비우고 있었다 —
노선이 47개라 30번째에서 네트워크가 끊기면 **픽스처가 반쪽으로 남았다.**

「git 으로 복구는 된다」가 이 항목을 오래 미뤄 둔 이유였는데, 그게 틀린 위안이다:
복구해야 하는 걸 **아는 사람만** 복구한다. 반쪽 픽스처로 빌드하면 스냅숏 검사가 잡아 주지만,
잡아 주는 건 「한 발행분이 아니다」라는 말이고 **왜 파일이 없어졌는지는 아무도 안 알려 준다.**

실측(대조군, 2026-10-05): 샌드박스에 픽스처를 복사해 4번째에서 끊기게 했을 때
  옛 순서 → 51개가 **4개로** 줄었다(해시 바뀜)
  고친 순서 → 51개 그대로(해시 동일)

그래서 여기서 재는 것은 「순서가 이렇게 쓰여 있다」가 아니라 **실패시킨 뒤 폴더가 그대로인가**다.
"""
import hashlib
import importlib.util
import io
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "fixtures", "v1")

# `capture.main()` 은 `HERE` 옆에서 `site/` 를 찾는다. 샌드박스로 `HERE` 를 돌려놓고 쓰므로
# 진짜 `site/` 를 미리 길에 넣는다 — 테스트가 만든 사정이지 도구의 문제가 아니다.
sys.path.insert(0, os.path.join(ROOT, "site"))


def load_capture():
    """매번 새 모듈로 읽는다 — `HERE`·`OUT` 을 샌드박스로 돌려놓고 쓰므로 공유하면 샌다."""
    spec = importlib.util.spec_from_file_location(
        "capture_under_test", os.path.join(ROOT, "fixtures", "capture.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def fingerprint(d):
    """파일 수 + 내용 해시. 「파일이 그대로인가」를 이름까지 포함해 한 값으로 본다."""
    h = hashlib.sha256()
    n = 0
    for root, _, fs in sorted(os.walk(d)):
        for f in sorted(fs):
            p = os.path.join(root, f)
            h.update(os.path.relpath(p, d).replace("\\", "/").encode("utf-8"))
            with open(p, "rb") as fh:
                h.update(fh.read())
            n += 1
    return n, h.hexdigest()


class FailedCaptureTest(unittest.TestCase):

    def setUp(self):
        self.sand = tempfile.mkdtemp(prefix="galmal-capture-")
        shutil.copytree(FIX, os.path.join(self.sand, "v1"))
        self.cap = load_capture()
        self.cap.HERE = self.sand
        self.cap.OUT = os.path.join(self.sand, "v1")
        self.before = fingerprint(self.sand)
        self.assertGreater(self.before[0], 40, "샌드박스에 픽스처가 복사됐나")

    def tearDown(self):
        shutil.rmtree(self.sand, ignore_errors=True)

    def _run(self, gen):
        """`main()` 의 받기+쓰기 부분을 실제 모듈 코드로 돌린다."""
        cap, argv = self.cap, sys.argv
        sys.argv = ["capture.py", "https://example.invalid/v1"]
        cap._from_url = lambda src: gen()
        try:
            cap.main()
        except (IOError, OSError, SystemExit) as e:
            return e
        finally:
            sys.argv = argv
        return None

    def _partial(self):
        """4개를 주고 끊긴다 — 노선 43개를 받기 전이다."""
        for p in ("meta.json", "deals.json", "vocab.json", "routes/index.json"):
            with open(os.path.join(FIX, *p.split("/")), "rb") as f:
                yield "v1/" + p, f.read()
        raise IOError("받는 중 끊겼다 (테스트가 일부러 끊는다)")

    def test_a_broken_fetch_changes_nothing(self):
        """🔴 **이 챕터의 요지다** — 실패가 사본을 건드리지 않는다."""
        err = self._run(self._partial)
        self.assertIsInstance(err, IOError)
        self.assertEqual(fingerprint(self.sand), self.before,
                         "받다 실패했는데 픽스처가 바뀌었다")

    def test_the_old_order_really_did_break_it(self):
        """대조군 — 예전 순서를 그대로 재현하면 **깨진다.** 안 깨지면 위 테스트가 아무것도 안 지킨다."""
        shutil.rmtree(self.cap.OUT, ignore_errors=True)       # 예전 코드: 먼저 비웠다
        try:
            for rel, blob in self._partial():
                dst = os.path.join(self.cap.HERE, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f:
                    f.write(blob)
        except IOError:
            pass
        after = fingerprint(self.sand)
        self.assertNotEqual(after, self.before)
        self.assertEqual(after[0], 4, "4개만 남는다 — 노선이 통째로 사라진다")

    def test_a_good_fetch_still_replaces_the_old_copy(self):
        """🔴 **비우는 일 자체는 그대로 해야 한다.** 백엔드는 표본 0 이 된 노선의 옛 파일을
        지우지 않으므로, 덮어쓰기만 하면 지금 index 에 없는 노선이 섞여 남는다."""
        ghost = os.path.join(self.cap.OUT, "routes", "ICN-ZZZ.json")
        with io.open(ghost, "w", encoding="utf-8") as f:
            f.write('{"generated":"1999-01-01T00:00:00+09:00","code":"ICN-ZZZ"}')
        self.assertTrue(os.path.exists(ghost))

        def whole():
            for root, _, fs in os.walk(FIX):
                for f in sorted(fs):
                    p = os.path.join(root, f)
                    rel = "v1/" + os.path.relpath(p, FIX).replace("\\", "/")
                    with open(p, "rb") as fh:
                        yield rel, fh.read()
        err = self._run(whole)
        self.assertIsNone(err, "정상 수신인데 멈췄다: %r" % (err,))
        self.assertFalse(os.path.exists(ghost), "index 에 없는 옛 노선이 남았다")
        self.assertEqual(fingerprint(self.sand), self.before, "받아 적은 결과가 원본과 달라졌다")


if __name__ == "__main__":
    unittest.main()
