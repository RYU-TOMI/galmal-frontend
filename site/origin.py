# -*- coding: utf-8 -*-
"""실제 출발 공항(`deals[].oa`)을 **쓰기 전에** 검사한다 — 빌드가 막는 것 다섯째.

헤더 알약은 `서울 출발` 이라고 말하지만 `SEL` 은 **가상 허브**다 — 실제로는 인천이거나 김포다.
김포 딜을 보고 인천으로 갈까 헷갈릴 자리라, 확장 상세에 **진짜 공항**을 적는다(SPEC §CH4).

🔴 **프론트가 만들 수 없는 값이다.** 2026-09-22 에 재 봤을 때 `SEL` 딜 78건 중 공항을 알 수 있는 건
`route` 가 있는 26건뿐이었다(67%는 알 길 없음). 목적지만 보고 짐작하면 **부산 딜에 인천이 붙는다.**
그래서 백엔드가 판정해 계약에 싣고(`36c6f38`·`3ab6067`), 프론트는 **표시만** 한다.

여기서 막는 것 둘:

| 검사 | 틀리면 화면에서 | 왜 조용한가 |
|---|---|---|
| `oa` 가 `vocab.airport_name` 에 없다 | 공항 줄이 **그냥 안 나온다** | 빈 문자열은 예외가 아니다. 새 공항이 열린 날 그 딜만 말없이 빈다 |
| `route` 앞 절반 ≠ `oa` | 한쪽이 거짓말 | 같은 사실이 두 필드에 있다 — **갈리면 어느 쪽이 맞는지 화면으로는 모른다** |

둘째는 백엔드가 생산 쪽에서 이미 잠갔다(같은 값에서 나온다고 테스트로 보장). **그래도 소비 쪽에서 또 잰다** —
기획이 `pax_url` 때와 같은 이유로 권했다. 같은 사실을 두 곳이 각자 확인하면 한쪽이 갈릴 때 시끄러워진다.
(사본을 두 곳에 두는 것과 반대다. 두는 것은 **검사**다.)
"""


def problems(deals, vocab):
    """막아야 할 것들을 사람이 읽을 문장으로. 빈 리스트면 통과.

    **여집합으로 센다** — 「틀린 것만」이 아니라 모든 딜이 판정을 거쳤는지 `summary()` 가 같이 센다.
    """
    names = (vocab or {}).get("airport_name") or {}
    out = []
    if not names:
        return ["`vocab.airport_name` 이 없다 — 공항 이름을 만들 수 없다(손 사본은 두지 않는다)"]
    for d in deals:
        where = d.get("ko", "?")
        oa = d.get("oa")
        if not oa:
            out.append("%s — `oa` 가 없다(계약상 required)" % where)
            continue
        if oa not in names:
            out.append("%s — `oa`=%s 가 `vocab.airport_name` 에 없다(화면에서 공항 줄이 말없이 빈다)"
                       % (where, oa))
        r = d.get("route")
        if r and "-" in r and r.split("-", 1)[0] != oa:
            out.append("%s — `route`=%s 의 앞 절반이 `oa`=%s 와 다르다(한쪽이 거짓말이다)"
                       % (where, r, oa))
    return out


def summary(deals, vocab):
    """`(이름을 얻은 딜, 노선으로도 대조된 딜, 전체)` — 「몇 개를 실제로 쟀나」를 로그에.

    절대값을 기대하지 않는다(딜 수는 매일 바뀐다). **합이 전체와 맞는지**를 본다.
    """
    names = (vocab or {}).get("airport_name") or {}
    named = sum(1 for d in deals if d.get("oa") in names)
    crossed = sum(1 for d in deals if d.get("route") and "-" in d["route"])
    return named, crossed, len(deals)
