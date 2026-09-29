# -*- coding: utf-8 -*-
"""🔴 **테스트가 배포를 막는가** — B48 (2026-09-28).

2026-09-28 까지 `deploy.yml` 과 `test.yml` 은 같은 push 에서 **따로** 돌았다.
그래서 **단위 테스트가 빨개도 사이트는 그대로 나갔다.**

빌드가 막는 것을 다섯이나 세워 두고도(스냅숏 · 어휘 매핑 · 인원 링크 · 출발 공항 · 칩),
정작 **그 코드를 지키는 테스트는 문지기가 아니었다.** 게이트를 아무리 쌓아도 게이트를
지키는 사람이 문 밖에 서 있으면 소용이 없다.

여기서 잠그는 것 셋:
  ① `build` 가 `test` 를 `needs` 한다 — 빨간 채로는 한 파일도 안 나간다
  ② 테스트 단계가 **한 벌만** 있다 — `deploy.yml` 에 복사하지 않는다.
     복사하면 한쪽만 자라고, 하필 **검사하는 쪽**이 갈리면 그게 제일 조용하다.
  ③ 야간 크론(`repository_dispatch`)에도 걸린다 — 사람이 push 할 때만 막으면 반쪽이다.

⚠️ **YAML 파서를 쓰지 않는다.** CI 는 `setup-python` 만 하고 아무것도 설치하지 않는다
(`CLAUDE.md` 「표준 라이브러리만」). PyYAML 을 import 하면 **이 파일만 CI 에서 터진다** —
문지기를 지키는 검사가 문지기를 막는 꼴이다. 그래서 문자열로 본다.
"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows")


def _read(name):
    with io.open(os.path.join(WF, name), encoding="utf-8") as f:
        return f.read()


DEPLOY = _read("deploy.yml")
TEST = _read("test.yml")

# 주석을 걷어낸 몸통 — **왜 그렇게 했나는 주석에 남겨야** 다음 사람이 되돌리지 않는다.
DEPLOY_CODE = re.sub(r"(?m)^\s*#.*$", "", DEPLOY)
TEST_CODE = re.sub(r"(?m)^\s*#.*$", "", TEST)


class GateTest(unittest.TestCase):

    def test_build_waits_for_tests(self):
        """🔴 이 파일의 본체. `build` 가 `test` 를 기다린다."""
        self.assertIn("  test:\n    uses: ./.github/workflows/test.yml", DEPLOY_CODE)
        self.assertRegex(DEPLOY_CODE, r"  build:\n    needs: test\n")

    def test_the_whole_chain_holds(self):
        """`test → build → deploy`. 가운데가 빠지면 굽기만 하고 안 올리거나, 안 굽고 올린다."""
        self.assertRegex(DEPLOY_CODE, r"  deploy:\n    needs: build\n")
        order = [DEPLOY_CODE.index(x) for x in ("  test:", "  build:", "  deploy:")]
        self.assertEqual(order, sorted(order))

    def test_test_workflow_can_be_called(self):
        self.assertIn("workflow_call:", TEST_CODE)

    def test_the_test_command_lives_in_exactly_one_place(self):
        """🔒 **복사하지 않는다.** 두 벌이면 한쪽만 자라고, 검사하는 쪽이 갈리면 제일 조용하다."""
        self.assertEqual(TEST_CODE.count("unittest discover"), 1)
        self.assertEqual(DEPLOY_CODE.count("unittest discover"), 0,
                         "deploy.yml 에 테스트 단계가 복사됐다")

    def test_main_runs_once_but_branches_run_too(self):
        """`main` 은 한 번만, 브랜치는 돈다.

        `main` 에서 `push` 로도 따로 돌면 **어느 쪽이 배포를 막았는지**가 흐려진다 —
        배포가 같은 push 에서 부르기 때문이다.

        🔴 그런데 B48 에서 `push` 를 **통째로** 뺐더니 구멍이 생겼다: 「챕터 1개 = 브랜치 1개 = PR」
        (2026-09-28 공통 규칙)에서는 **PR 을 열기 전까지 브랜치 push 에 아무 CI 도 안 돈다** —
        태스크를 커밋할 때마다 초록불을 봐야 하는데 못 본다. `branches-ignore: [main]` 이 둘 다 만족한다.
        """
        on = TEST_CODE.split("jobs:")[0]
        self.assertIn("push:", on)
        self.assertIn("branches-ignore: [main]", on)
        self.assertIn("pull_request:", on)     # PR 에서도 돈다

    def test_the_nightly_cron_is_gated_too(self):
        """야간 크론이 문지기를 비켜 가면 **사람이 안 보는 시간에만** 깨진 코드가 나간다."""
        on = DEPLOY_CODE.split("jobs:")[0]
        self.assertIn("repository_dispatch:", on)
        self.assertIn("api-updated", on)
        # 트리거별로 job 을 가르지 않는다 — 가르는 순간 어느 길엔 문지기가 없다.
        self.assertNotIn("if:", DEPLOY_CODE.split("  build:")[1].split("  deploy:")[0])

    def test_reason_is_kept_in_the_comments(self):
        """되돌리려는 사람이 **왜 이렇게 됐는지**를 먼저 읽게 한다 — 규칙만 남기면 다시 풀린다."""
        self.assertIn("B48", DEPLOY)
        self.assertIn("따로", TEST)


if __name__ == "__main__":
    unittest.main()
