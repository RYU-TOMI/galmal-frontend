# -*- coding: utf-8 -*-
"""사진을 받아 굽는다 — **오프라인 도구다. 빌드가 부르지 않는다.**

🔴 **`site/` 나 `tests/` 에서 이 파일을 import 하지 않는다.** Pillow 가 필요한데 CI 는
`setup-python` 만 하고 아무것도 설치하지 않는다 — import 하는 순간 **CI 만 죽는다**
(`tests/test_gate.py` 가 같은 이유로 PyYAML 을 금지한다). 빌드가 보는 것은 이 도구가
**써 놓은 결과물**(`public/assets/photos/`)뿐이고, 판단은 파일 이름과 `credits.json` 으로 한다.

들어오는 것: `../galmal-plan/design/photos.json` (기획 소유 · 위키미디어에서 고른 77곳)
나가는 것:   `public/assets/photos/`
    {코드}-s.webp   160x160   작은 썸네일(피드 62px)
    {코드}.webp     800x533   히어로 썸네일 · 호버 카드 · 확장 상세
    credits.json    코드별 저작자·제목·라이선스·원본 링크

**왜 코드별로 파일을 쓰나(도시별이 아니라)**: 딜은 `d`(목적지 코드)로 온다. 도시 하나에 코드가
여럿인 곳이 있어(도쿄 NRT/HND 처럼) 도시별로 두면 **코드→도시 표**를 어딘가에 손으로 둬야 한다.
이 저장소는 손 사본으로 다섯 번 사고를 냈다. 같은 사진을 코드 수만큼 쓰는 낭비(7장)를 택한다.

**왜 `credits.json` 을 이 저장소에 쓰나**: CI 에는 형제 저장소가 없다. 빌드가 `/credits.html` 을
만들려면 표시 정보가 **이 저장소 안에** 있어야 한다. 사진과 같은 폴더에 둬서 둘이 갈리지 않게 한다.

⚠️ **위키미디어는 설명 있는 User-Agent 없이 요청하면 403 이다**(실측). 캐시를 쓰고 1초씩 쉰다.

    python tools/photos.py                       # 없는 것만 굽는다
    python tools/photos.py --force               # 전부 다시
    python tools/photos.py --only KOJ,HND        # 그 코드만
"""
import argparse
import io
import json
import os
import sys
import tempfile
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "..", "galmal-plan", "design", "photos.json")
OUT = os.path.join(ROOT, "public", "assets", "photos")
# 🔴 내려받은 원본은 **저장소 밖**에 둔다. 처음엔 `<repo>/.photocache` 에 뒀는데 이 저장소엔
# `.gitignore` 가 없어서 `git status` 에 그대로 떴다 — 커밋될 수 있는 자리에 임시 파일을 두지 않는다.
# 같은 사진을 코드 둘이 쓰면 한 번만 받는 것도 여기서 산다(실측: 84코드 중 8번 재사용).
CACHE = os.path.join(tempfile.gettempdir(), "galmal-photocache")

# 🔴 사진 자리를 **재서** 정한 값이다(2026-09-30 실측). 자리는 전부 **옆으로 긴 띠**다:
#   피드 작은 썸네일 62x62      → 3배 186   (아이폰 Pro 가 3배다)
#   히어로 썸네일   320x104     → 2배 640x208
#   데스크톱 상세   340x92      → 2배 680x184
#   모바일 시트     430x130     → 2배 860x260   ← 가장 큰 요구. 모바일에서 카드는 **전폭 시트**다
# `cover` 는 「둘 다 덮을 때까지」 키우므로 **900x340 하나로 셋 다** 덮인다.
#
# ⚠️ 처음엔 800x533 으로 잡았는데 **모바일 시트를 못 덮는다**(860x260 에 1.07배 부족).
# 세로는 남고 가로는 모자랐다 — 자리의 **비율**을 안 보고 「큰 값」만 골라서 그랬다.
# 실측(세 장 평균, q78): 900x340 63.9KB(오차 3.13) vs 800x533 79.8KB(2.97) —
# **덜 쓰고 더 맞는다.** 잘려 나갈 세로 픽셀을 굽고 있었다.
#
# 작은 쪽을 따로 두는 이유: 첫 화면에 작은 썸네일이 25장 깔린다(B71 — 첫 화면 무게).
# 큰 것만 쓰면 62px 자리에 63.9KB 를 25장 받는다.
SIZES = [("-s", 200, 200), ("", 900, 340)]
QUALITY = 78
UA = ("galmal.kr photo fetch/1.0 (https://galmal.kr; "
      "https://github.com/RYU-TOMI/galmal-frontend) python-urllib")


def fetch(url, cache_path, pause):
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        return open(cache_path, "rb").read(), True
    req = urllib.request.Request(url)
    req.add_header("User-Agent", UA)          # 🔴 없으면 403
    raw = urllib.request.urlopen(req, timeout=40).read()
    with open(cache_path, "wb") as f:
        f.write(raw)
    time.sleep(pause)                          # 남의 서버다 — 몰아치지 않는다
    return raw, False


# 🔴 **라이선스 링크의 스킴만 올린다**(`http://creativecommons.org` → `https://`).
# 기획의 원본에 `http://` 가 7건 있다(CJU·DOH·HAN·IST·KMQ·NRT·TYO — 전부 creativecommons.org).
# 우리가 **내보내는 페이지**에 http 링크가 섞이면 브라우저가 경고하거나 사용자가 못 미더워한다.
# 같은 문서를 가리키고 CC 자신이 http→https 로 넘긴다 — 호스트도 경로도 건드리지 않고 **스킴만** 바꾼다.
# 원본은 기획 소유라 고치지 않고 알린다(2026-09-30 통지).
def https_cc(url):
    u = (url or "").strip()
    if u.startswith("http://creativecommons.org/"):
        return "https://" + u[len("http://"):]
    return u


def cover(im, tw, th):
    """비율을 지키고 **넘치는 쪽을 잘라** 목표 크기를 채운다(CSS `background-size:cover` 와 같은 규칙).
    늘리지 않는다 — 원본 thumb 이 960 폭이라 두 크기 모두 축소만 한다."""
    src = im.convert("RGB")
    sr, dr = src.width / float(src.height), tw / float(th)
    if sr > dr:
        nw, nh = int(round(src.height * dr)), src.height
    else:
        nw, nh = src.width, int(round(src.width / dr))
    box = ((src.width - nw) // 2, (src.height - nh) // 2,
           (src.width + nw) // 2, (src.height + nh) // 2)
    from PIL import Image
    return src.resize((tw, th), Image.LANCZOS, box=box)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=SPEC)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--quality", type=int, default=QUALITY)
    ap.add_argument("--pause", type=float, default=1.0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    try:
        from PIL import Image, features
    except ImportError:
        sys.exit("Pillow 가 없다 — 이 도구만 필요하다(빌드·CI 에는 필요 없다): pip install pillow")
    if not features.check("webp"):
        sys.exit("Pillow 에 webp 지원이 없다")

    with io.open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    cities = spec["cities"]
    only = set(x.strip() for x in a.only.split(",") if x.strip())
    for d in (a.out, a.cache):
        if not os.path.isdir(d):
            os.makedirs(d)

    credits, made, skipped, reused, total = {}, 0, 0, 0, 0
    codes = [(c, ko) for ko, v in sorted(cities.items()) for c in v["codes"]]
    for i, (code, ko) in enumerate(sorted(codes)):
        v = cities[ko]
        ch = v["chosen"]
        credits[code] = {
            "city": ko, "en": v.get("en", ""),
            "title": ch["title"], "author": ch["author"],
            "license": ch["license"], "license_url": https_cc(ch["license_url"]),
            "page": ch["page"],
        }
        if only and code not in only:
            continue
        paths = [os.path.join(a.out, code + sfx + ".webp") for sfx, _, _ in SIZES]
        if not a.force and all(os.path.exists(p) and os.path.getsize(p) > 0 for p in paths):
            skipped += 1
            total += sum(os.path.getsize(p) for p in paths)
            continue
        # 캐시 이름은 **도시 기준**이다 — 코드 둘이 같은 사진을 쓰면 한 번만 받는다.
        cpath = os.path.join(a.cache, ko.replace("/", "_") + ".bin")
        raw, was_cached = fetch(ch["thumb"], cpath, a.pause)
        reused += 1 if was_cached else 0
        im = Image.open(io.BytesIO(raw))
        for (sfx, w, h), p in zip(SIZES, paths):
            cover(im, w, h).save(p, "WEBP", quality=a.quality, method=6)
            total += os.path.getsize(p)
        made += 1
        sys.stdout.write("\r  %d/%d %s (%s)      " % (i + 1, len(codes), code, ko))
        sys.stdout.flush()

    with io.open(os.path.join(a.out, "credits.json"), "w", encoding="utf-8", newline="") as f:
        json.dump({"source": spec.get("source", ""),
                   "spec_generated": spec.get("generated", ""),
                   "spec_confirmed": spec.get("confirmed", ""),
                   "sizes": [{"suffix": s, "w": w, "h": h} for s, w, h in SIZES],
                   "quality": a.quality,
                   "photos": credits}, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    print("\r도시 %d · 코드 %d · 구운 코드 %d · 건너뜀 %d · 캐시 재사용 %d"
          % (len(cities), len(codes), made, skipped, reused))
    # 🔴 합계는 **디스크에 있는 것**을 센다. 만든 것만 세면 `--only` 로 돌릴 때 「0.0 MB」라고
    # 거짓말을 한다(실제로 그랬다) — 세고 말하거나 모른다고 한다.
    disk = [f for f in os.listdir(a.out) if f.endswith(".webp")]
    onlyk = " (이번에 만든 것 %d 파일)" % (made * len(SIZES)) if only else ""
    print("사진 %d 파일 · %.2f MB%s · credits.json %d행"
          % (len(disk), sum(os.path.getsize(os.path.join(a.out, f)) for f in disk) / 1048576.0,
             onlyk, len(credits)))


if __name__ == "__main__":
    main()
