# -*- coding: utf-8 -*-
"""v1 응답 전부를 **한 번에** 받고, 한 발행분인지 확인한다 (SPLIT.md M5 T6d).

## 왜 필요한가

2026-09-17 신형 크론 첫 실행에서 백엔드의 「새로 발행했다」 신호가 API 배포보다
29초 먼저 와서 **사이트가 어제 데이터로 구워졌다.** 백엔드가 보내는 시점을 고쳤지만
그걸로 다 막히지 않는다 — API 앞에 CDN 캐시(`Cache-Control: max-age=600`)가 있고
**캐시는 파일마다 따로 걸린다.** 이 빌드는 파일 39개를 따로 받으므로 이런 빌드가 가능하다:

    meta.json            오늘
    routes/ICN-FUK.json  어제   ← 다른 엣지, 다른 캐시 시점

**날짜가 섞인 사이트**가 나가고 화면은 멀쩡해 보인다. 아무도 모른다.

## 규칙 (`CONTRACT.md` §공통 규칙)

한 발행의 기준 시각을 G = `meta.generated` 라 할 때:

| 응답 | `generated` |
|---|---|
| `routes/index` · `routes/{code}` | == G |
| `deals` — `meta.preserved` 가 거짓 | == G |
| `deals` — `meta.preserved` 가 참 | **< G** |
| 백엔드 신호의 `client_payload.generated` (있을 때만) | == G |

`preserved` 분기가 있는 이유: 수집이 하한선에 못 미친 날 백엔드는 `deals.json` 을 **새로
쓰지 않는다**(BB1). 어제 데이터에 오늘 도장을 찍지 않기로 했다(2026-08-22). 그래서 그날
`deals` 만 어제 시각을 단다. 처음엔 「39개 전부 같다」로 짰다가 백엔드 반례로 고쳤다 —
그대로 뒀으면 **보존일마다 배포가 통째로 멈췄다.**

⚠️ **알려진 틈**: 보존일에 엣지가 **더 오래된** `deals` 를 줘도 「< G」라 통과한다.
좁은 경우라 받아들였다. 막으려면 `meta` 에 「내보낸 deals 의 generated」를 더해 정확
일치로 바꾼다 — 계약 변경이라 지금은 안 한다.

## 실패 방식

어긋나면 **39개 전부를 다시 받는다**(어긋난 것만 다시 받으면 그 사이 백엔드가 또 발행해
새로운 섞임이 생길 수 있다). 캐시 수명(10분)을 넘길 만큼 기다려도 안 맞으면 **한 파일도
쓰기 전에** 멈춘다 → 배포 안 됨 → 사이트는 직전 배포본으로 남고 잡이 실패한다.
틀린 데이터가 조용히 나가는 것보다 하루 갱신이 밀리고 빨간불이 뜨는 쪽이 낫다.
"""
import sys
import time
from datetime import datetime

from route import fetch


def fetch_all(api):
    """v1 응답 전부를 받는다. 노선은 **`routes/index.json` 에 실린 코드만** 받는다 —
    백엔드는 표본 0 이 된 노선의 옛 파일을 지우지 않으므로 디렉터리를 믿지 않는다."""
    meta = fetch(api, "meta.json")
    index = fetch(api, "routes/index.json")
    deals = fetch(api, "deals.json")
    routes = {r["code"]: fetch(api, "routes/%s.json" % r["code"]) for r in index["routes"]}
    return {"meta": meta, "index": index, "deals": deals, "routes": routes}


def _t(s):
    return datetime.fromisoformat(s)


def problems(snap, expect=None):
    """한 발행분이 아니면 무엇이 어긋났는지 문장 목록을 돌려준다. 맞으면 빈 목록."""
    out = []
    g = snap["meta"]["generated"]

    if expect and expect != g:
        out.append("백엔드가 알린 generated %s 인데 meta 는 %s — 옛 캐시를 받았다" % (expect, g))

    if snap["index"]["generated"] != g:
        out.append("routes/index %s != meta %s" % (snap["index"]["generated"], g))

    stale = sorted(c for c, r in snap["routes"].items() if r["generated"] != g)
    if stale:
        out.append("노선 %d개가 meta(%s)와 다르다: %s%s" % (
            len(stale), g, ", ".join(stale[:5]), " 외" if len(stale) > 5 else ""))

    d = snap["deals"]["generated"]
    if snap["meta"].get("preserved"):
        # 보존일: 어제 파일이 그대로 남는다. 같거나 더 새것이면 계약과 모순이다.
        if not _t(d) < _t(g):
            out.append("preserved=true 인데 deals(%s)가 meta(%s)보다 이전이 아니다" % (d, g))
    elif d != g:
        out.append("deals %s != meta %s (preserved=false)" % (d, g))

    return out


def load(api, expect=None, retries=12, wait=60, check=True, log=print):
    """검증된 스냅숏을 돌려준다. 끝내 안 맞으면 종료코드 1 로 멈춘다."""
    for attempt in range(1, retries + 1):
        snap = fetch_all(api)
        if not check:
            return snap
        bad = problems(snap, expect)
        if not bad:
            if attempt > 1:
                log("스냅숏 일치 — %d번째 시도에서 맞았다" % attempt)
            return snap
        log("⚠️  스냅숏 불일치 (%d/%d):" % (attempt, retries))
        for b in bad:
            log("    - " + b)
        if attempt < retries:
            log("    %d초 뒤 39개를 전부 다시 받는다 (CDN max-age=600)" % wait)
            time.sleep(wait)
    sys.exit("🔴 %d번 받아도 한 발행분이 아니다. 배포하지 않는다 — 사이트는 직전 배포본으로 남는다."
             % retries)
