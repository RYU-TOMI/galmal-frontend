# -*- coding: utf-8 -*-
"""어휘를 키로 쓰는 프론트 전용 매핑이 어휘를 다 덮는가 — 빠지면 빌드 실패 (CONTRACT §5).

`discover.js` 에는 어휘를 키로 한 **프론트 전용 매핑**이 둘 있다. 색·지도 단계는 디자인이라
계약에 없어야 맞다 — 그래서 `/v1/vocab.json` 으로 받아 없앨 수가 없다. 대신 **빠지면 조용히
폴백한다**:

| 매핑 | 빠지면 | 여기서 막는 것 |
|---|---|---|
| `TAG_GRAD` | `grad()` 가 기본 색으로 폴백 | `tags.top` 전부가 키에 있다 + **이번 딜이 전부 색을 얻는다** |
| `HAUL2STAGE` | `|| "far"` 로 폴백 — 근거리가 「아주 멀리」에 뜬다 | `haul` 전부가 키에 있다 |

## `TAG_GRAD` — 왜 「대표 태그 전부」 + 「실제 딜 전부」 둘을 보나

`grad(tags)` 는 딜의 태그를 **순서대로** 보다가 색상표에 있는 **첫 태그**의 색을 쓴다. 하위 태그
18개 중 색이 있는 건 일부다(2026-09-19 실측 5/18) — 나머지는 건너뛰고 대표 태그에서 색을 받는다.
그래서 「대표 6개가 전부 색을 가진다」면 폴백이 없다 — **단, 모든 딜이 대표 태그를 하나 이상 가질 때만.**
그 전제는 백엔드 계약 검증기가 지키지만, 여기서 **이번 스냅숏의 실제 딜로도** 확인한다.
전제가 깨지면 구조 검사는 통과하고 실데이터 검사만 걸린다.

2026-09-19 실측: 딜 137건 · 대표 태그 없는 딜 0 · 폴백 0 · 색 출처 대표 104 / 하위 33.

## JS 를 정규식으로 읽는다

두 매핑은 JS 객체 리터럴이다. 파이썬이 읽으려면 정규식밖에 없다. 그래서 **못 찾으면 통과가 아니라
실패**로 둔다 — 누가 이름을 바꿔 정규식이 빈손으로 돌아오면 「빠진 게 없다」로 읽히면 안 된다.
지역 표시 순서 목록은 프론트에 **없다**(2026-09-19 확인) — 생기면 여기에 더한다.
"""
import re


def _keys(js_text, name, key_re):
    m = re.search(r"var %s = \{(.*?)\};" % re.escape(name), js_text, re.S)
    if not m:
        return None
    return re.findall(key_re, m.group(1))


def problems(js_text, vocab, deals):
    out = []

    grad = _keys(js_text, "TAG_GRAD", r'"([^"]+)"\s*:\s*"linear-gradient')
    if not grad:
        out.append("discover.js 에서 TAG_GRAD 를 못 읽었다 — 검사를 할 수 없으면 통과가 아니라 실패다")
    else:
        miss = [t for t in vocab["tags"]["top"] if t not in grad]
        if miss:
            out.append("TAG_GRAD 에 대표 태그 %s 의 색이 없다 — 그 태그만 가진 목적지는 기본 색으로 폴백한다"
                       % miss)
        fall = [d.get("ko", "?") for d in deals if not any(t in grad for t in d.get("tags", []))]
        if fall:
            out.append("딜 %d건이 색을 못 얻는다(기본 색 폴백): %s%s"
                       % (len(fall), ", ".join(fall[:5]), " 외" if len(fall) > 5 else ""))

    haul = _keys(js_text, "HAUL2STAGE", r'(\w+)\s*:\s*"')
    if not haul:
        out.append("discover.js 에서 HAUL2STAGE 를 못 읽었다 — 검사를 할 수 없으면 통과가 아니라 실패다")
    else:
        miss = [h for h in vocab["haul"] if h not in haul]
        if miss:
            out.append("HAUL2STAGE 에 haul %s 이 없다 — 그 목적지는 「아주 멀리」로 폴백한다" % miss)

    return out
