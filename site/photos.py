# -*- coding: utf-8 -*-
"""사진과 출처 표시를 **쓰기 전에** 대조한다 — 빌드가 막는 것 일곱째.

사진은 전부 위키미디어 커먼즈에서 왔고 **CC 라이선스**다(BY-SA 42+14+4+1 · BY 6+3+2+2 · CC0 3).
CC BY·BY-SA 는 **표시가 법적 의무**다 — 저작자·제목·라이선스·출처를 밝히지 않고 쓰면 위반이다.
그래서 이 게이트가 막는 것은 「화면이 예쁜가」가 아니라 **「표시 없는 사진이 나가는가」**다.

🔴 **여집합으로 양방향을 센다.** 남은 것만 보는 검사는 없는 것을 못 본다(`PLAN.md` 함정 11):

| 어긋남 | 무슨 일이 되나 |
|---|---|
| 사진 파일은 있는데 `credits.json` 에 행이 없다 | **표시 없이 나간다 — 라이선스 위반** |
| 행은 있는데 파일이 없다 | `/credits.html` 이 **없는 사진의 저작자를 밝힌다**(거짓 표시) |
| 두 크기 중 하나가 없다 | 그 자리만 조용히 그라디언트로 떨어진다 |
| 저작자·라이선스·링크가 빈 문자열 | 표시가 **말없이 빈다** — 빈 문자열은 예외가 아니다(`origin.py` 와 같은 이유) |

⚠️ **Pillow 를 쓰지 않는다.** 사진을 굽는 건 `tools/photos.py`(오프라인)이고 여기서는
**파일 이름과 `credits.json`** 만 본다. CI 는 아무것도 설치하지 않으므로 이미지 라이브러리를
import 하면 **이 검사가 CI 를 죽인다** — 문지기가 문을 막는 꼴이다(`tests/test_gate.py` 와 같은 이유).

사진이 **없는 목적지는 정상**이다(2026-09-30 실측: 헬싱키·이시가키 둘). 그 카드는 그라디언트로
남는다 — 그래서 「모든 목적지에 사진이 있나」는 **막지 않고 세어서 로그에만** 적는다.
없는 것을 실패로 걸면 백엔드가 목적지를 하나 늘린 날 **사이트가 안 나간다.**
"""
import io
import json
import os

NEED = ("author", "license", "license_url", "page", "title", "city")
SMALL = "-s"


def _codes_on_disk(photo_dir):
    """`{코드}.webp`·`{코드}-s.webp` → `{코드: 가진 크기들}`. 파일 이름만 본다."""
    got = {}
    if not os.path.isdir(photo_dir):
        return got
    for f in sorted(os.listdir(photo_dir)):
        if not f.endswith(".webp"):
            continue
        stem = f[:-len(".webp")]
        if stem.endswith(SMALL):
            got.setdefault(stem[:-len(SMALL)], set()).add(SMALL)
        else:
            got.setdefault(stem, set()).add("")
    return got


def load(photo_dir):
    """`(credits dict, 코드→가진 크기들)`. `credits.json` 이 없으면 `({}, …)` — 사진 없는 빌드도 돈다."""
    p = os.path.join(photo_dir, "credits.json")
    if not os.path.exists(p):
        return {}, _codes_on_disk(photo_dir)
    with io.open(p, encoding="utf-8") as f:
        return json.load(f), _codes_on_disk(photo_dir)


def problems(credits, on_disk):
    """막아야 할 것들을 사람이 읽을 문장으로. 빈 리스트면 통과."""
    out = []
    rows = (credits or {}).get("photos") or {}
    if not rows and not on_disk:
        return out                      # 사진을 아직 안 넣은 상태 — 그 자체는 잘못이 아니다
    if on_disk and not rows:
        return ["사진 %d개가 있는데 `credits.json` 이 없다 — 표시 없이 나간다(CC 위반)" % len(on_disk)]
    for code in sorted(on_disk):
        if code not in rows:
            out.append("%s.webp 가 있는데 `credits.json` 에 행이 없다 — **표시 없이 나간다**(CC 위반)" % code)
    for code in sorted(rows):
        sizes = on_disk.get(code)
        if not sizes:
            out.append("`credits.json` 에 %s 행이 있는데 사진 파일이 없다 — 없는 사진의 저작자를 밝히게 된다" % code)
            continue
        for sfx, what in ((SMALL, "작은 썸네일"), ("", "큰 사진")):
            if sfx not in sizes:
                out.append("%s — %s(%s%s.webp)가 없다 — 그 자리만 조용히 그라디언트로 떨어진다"
                           % (code, what, code, sfx))
        row = rows[code]
        for k in NEED:
            if not (row.get(k) or "").strip():
                out.append("%s — 표시에 쓸 `%s` 가 비었다(표시가 말없이 빈다)" % (code, k))
        u = row.get("license_url") or ""
        if u and not u.startswith("http"):
            out.append("%s — `license_url` 이 링크가 아니다: %r" % (code, u))
    return out


def summary(credits, on_disk, dest_codes):
    """`(사진 있는 목적지, 전체 목적지, 사진 코드 수, 안 쓰이는 사진 코드)` — 로그용.

    절대값을 기대하지 않는다. **여집합**(사진 없는 목적지)을 같이 돌려주는 게 요점이다.
    """
    rows = (credits or {}).get("photos") or {}
    have = set(rows) & set(on_disk)
    dests = set(dest_codes or ())
    return len(dests & have), len(dests), len(have), sorted(have - dests)


def missing(credits, on_disk, dest_codes):
    """사진이 없는 목적지 코드 — **막지 않고 센다.** 그 카드는 그라디언트로 남는다."""
    rows = (credits or {}).get("photos") or {}
    have = set(rows) & set(on_disk)
    return sorted(set(dest_codes or ()) - have)
