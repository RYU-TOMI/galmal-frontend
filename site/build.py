# -*- coding: utf-8 -*-
"""갈래말래 화면 빌드 — v1 응답을 받아 정적 HTML 을 굽는다.

    python site/build.py --api fixtures/v1          # 로컬 사본으로 (네트워크 없이)
    python site/build.py --api https://api.galmal.kr/v1
    python site/build.py --api fixtures/v1 --out /tmp/out --only ICN-FUK

**분리 후 프론트 저장소의 유일한 진입점이다.** 지금은 `collector/build_site.py` 와
나란히 존재하고 크론은 아직 옛 것을 부른다 — 스위치는 M3 다.

## 이게 「API 를 쓰는 프론트」인가

아니다. **빌드 타임에** 한 번 받아서 HTML 에 박아 넣는다(SSG). 방문자 브라우저는
아무것도 요청하지 않는다. 그래서 CORS·로딩 상태·재시도·레이트리밋이 전부 없다.
`--api` 가 URL 이든 폴더든 같은 일을 하는 것도 그래서다.

바뀌는 건 **경계**다 — 프론트가 sqlite 를 직접 열던 것이 계약을 읽는 것으로 바뀐다.
나중에 백엔드가 자체 서버가 되면 **이 인자에 넣는 문자열만 바뀐다.**
"""
import argparse
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import coverage  # noqa: E402
import home   # noqa: E402
import snapshot  # noqa: E402
import route  # noqa: E402  (위 sys.path 설정 뒤여야 한다)
import seo    # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="v1 응답에서 화면을 굽는다")
    ap.add_argument("--api", required=True,
                    help="v1 base — URL(https://api.galmal.kr/v1) 또는 폴더(fixtures/v1)")
    ap.add_argument("--out", default="docs",
                    help="산출물 폴더 (기본 docs)")
    ap.add_argument("--only", default=None,
                    help="노선 코드 하나만 굽는다 (예: ICN-FUK). 대조할 때 쓴다")
    ap.add_argument("--public", default="public",
                    help="그대로 서빙될 정적 파일 트리(assets/ · data/). 산출물 폴더에 통째로 복사한다")
    ap.add_argument("--world", default="public/data/world.geojson",
                    help="지도 윤곽. 정적 자산이라 API 가 아니라 파일이다 — d3 와 같은 부류로, "
                         "커밋 2회짜리이고 크론이 만들지 않는다")
    ap.add_argument("--expect-generated", default="",
                    help="백엔드 신호가 알려준 generated. 받은 meta 와 다르면 옛 캐시다. "
                         "비우면 이 대조만 건너뛴다(섞임 검사는 그대로 한다)")
    ap.add_argument("--retries", type=int, default=12, help="스냅숏이 안 맞을 때 다시 받는 횟수")
    ap.add_argument("--wait", type=int, default=60, help="재시도 간격(초). CDN max-age=600")
    a = ap.parse_args()

    # 🔴 **다 받고, 한 발행분인지 확인한 다음에야 한 파일이라도 쓴다** (snapshot.py 참고).
    # 예전엔 정적 자산을 먼저 깔고 API 를 받아서, 받다가 실패하면 자산만 있고 HTML 은
    # 없는 반쪽 폴더가 남았다. 이제 실패는 산출물 폴더를 건드리기 전에 난다.
    snap = snapshot.load(a.api, expect=a.expect_generated or None,
                         retries=a.retries, wait=a.wait)
    meta, index = snap["meta"], snap["index"]
    print("스냅숏 generated=%s · preserved=%s · 노선 %d" % (
        meta["generated"], meta.get("preserved"), len(snap["routes"])))

    # 🔴 **어휘를 키로 쓰는 매핑이 어휘를 다 덮는지** — 빠지면 조용히 폴백하므로 쓰기 전에 막는다
    # (site/coverage.py · CONTRACT §5). 새 태그·새 haul 이 생기면 여기서 빌드가 멈춘다.
    js_path = os.path.join(a.public, "assets", "discover.js")
    with open(js_path, encoding="utf-8") as f:
        bad = coverage.problems(f.read(), snap["vocab"], snap["deals"]["deals"])
    if bad:
        for b in bad:
            print("  🔴 " + b)
        sys.exit("어휘를 덮지 못하는 매핑이 있다 — 배포하지 않는다")

    # 🔴 **정적 자산을 먼저 깐다.** 빌드가 만드는 건 HTML·XML 뿐이고
    # `discover.js|css`·d3·지도 윤곽은 **산출물이 아니라 그냥 파일**이다.
    # 안 깔면 HTML 은 완벽한데 **화면만 백지**가 되고, HTML diff 로는 절대 안 잡힌다 —
    # 없는 파일의 404 는 HTML 에 안 나타난다. 그래서 확인에 브라우저 콘솔이 들어간다.
    # (M2 에서 실제로 겪었고 SPLIT.md M4 의 함정으로 박아둔 자리다.)
    if os.path.isdir(a.public):
        shutil.copytree(a.public, a.out, dirs_exist_ok=True)
        print("정적 자산 → %s" % a.out)
    else:
        sys.exit("정적 자산 폴더가 없다: %s" % a.public)

    pages = route.build_all(snap)
    if a.only:
        want = a.only + ".html"
        pages = {k: v for k, v in pages.items() if k == want}
        if not pages:
            sys.exit("노선 %s 이 응답에 없다" % a.only)

    dst = os.path.join(a.out, "routes")
    os.makedirs(dst, exist_ok=True)
    for name, html_text in pages.items():
        with open(os.path.join(dst, name), "w", encoding="utf-8", newline="") as f:
            f.write(html_text)
    print("노선 페이지 %d장 → %s" % (len(pages), dst))

    # sitemap 은 전체 목록이라 `--only` 로 일부만 구웠으면 만들지 않는다 —
    # 반쪽짜리 sitemap 을 내보내는 것이 안 내보내는 것보다 나쁘다.
    if a.only:
        print("--only 라 sitemap·robots 는 건너뛴다")
        return
    os.makedirs(a.out, exist_ok=True)

    # 발견 홈. deals 와 지도 윤곽을 HTML 에 인라인하므로 file:// 로도 열린다
    # (fetch() 는 file:// 에서 막힌다).
    payload = snap["deals"]
    with open(a.world, encoding="utf-8") as f:
        world = f.read()
    page = home.render_home(payload, home.inline_deals(payload), world, index, snap["vocab"])
    # 🔴 `discover.js` 가 어휘 목록을 **이 칩에서 읽으므로** 칩이 계약과 다르면 내보내지 않는다.
    bad = home.chip_problems(page, snap["vocab"])
    if bad:
        for b in bad:
            print("  🔴 " + b)
        sys.exit("홈의 어휘 칩이 /v1/vocab.json 과 다르다 — 배포하지 않는다")
    with open(os.path.join(a.out, "index.html"), "w", encoding="utf-8", newline="") as f:
        f.write(page)
    print("  index.html")

    for name, text in seo.build_all(index, route.machine_date(meta["generated"])).items():
        with open(os.path.join(a.out, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print("  %s" % name)

    # 🔴 **배포가 멈춘 걸 누가 알아채나** (SPLIT.md R1c · M4 T5b).
    # 저장소가 갈리면 백엔드 API 는 매일 신선한데 프론트 배포만 몇 주째 죽어 있을 수 있다
    # (PAT 만료 등). 그때 백엔드 점검은 자기 API 만 보고 **초록불**이다.
    # 그래서 「어느 시점 데이터로 구웠나」를 사이트에 같이 내보낸다. 백엔드가
    # 사이트의 `api_generated` 와 API 의 `generated` 가 **같은지** 본다 — 절대값이 아니라 일치다.
    # `meta.generated` 를 **가공 없이 그대로** 복사한다(문자열 비교다).
    build_info = {"api_generated": meta["generated"],
                  "built": datetime.now().astimezone().isoformat(timespec="seconds")}
    with open(os.path.join(a.out, "build.json"), "w", encoding="utf-8", newline="") as f:
        json.dump(build_info, f, ensure_ascii=False)
    print("  build.json  (api_generated=%s)" % meta["generated"])


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    main()
