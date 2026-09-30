# -*- coding: utf-8 -*-
"""`/credits.html` — 사진 출처 표시. **법적 의무를 지키는 페이지다.**

사진은 전부 위키미디어 커먼즈에서 왔고 대부분 **CC BY 또는 CC BY-SA** 다.
그 라이선스는 다음을 밝히라고 요구한다 — 흔히 **TASL** 로 줄여 부른다:

| | 무엇 | 어디서 오나 |
|---|---|---|
| **T**itle | 사진 제목 | `credits.json` 의 `title`(커먼즈 파일명) |
| **A**uthor | 저작자 | `author` |
| **S**ource | 원본이 있는 곳 | `page`(커먼즈 파일 페이지) |
| **L**icense | 라이선스 이름 + **링크** | `license` · `license_url` |

여기에 하나 더 — **「고쳤는지」를 밝힌다.** CC BY 4.0·BY-SA 4.0 은 「수정했으면 그렇다고
표시하라」를 명문으로 요구한다(3.0 이하도 관행상 밝힌다). 우리는 **크기를 줄이고 잘라내고
webp 로 바꿨다** — 그 사실을 페이지 머리에 한 번, 표 아래에 한 번 적는다.

🔴 **CC0 도 표에 적는다.** 표시 의무가 없지만, 빼면 「왜 이 사진만 없나」를 나중에 아무도 모른다.
라이선스 칸에 `CC0` 이라고 그대로 적어 의무가 없다는 것까지 보이게 한다.

⚠️ **나는 법률 판단을 하지 않는다.** 이 페이지는 커먼즈 재사용자들이 쓰는 표준 형태
(TASL + 수정 고지)를 따른 것이고, BY-SA 의 ShareAlike 가 크기 변경에도 걸리는지 같은
해석은 사용자가 봐야 한다. 그래서 **사진마다 원본 라이선스와 링크를 그대로** 실어,
어느 해석에서도 「어떤 라이선스의 무엇을 썼는지」가 페이지에 남게 한다.

정렬은 **도시 이름(한국어)** 순이다 — 사람이 찾는 순서다. 코드 순으로 두면
같은 도시가 떨어져 앉는다(도쿄 NRT·TYO).
"""
import html

import shell

# 🔴 칸 이름은 **여기 한 벌**이다. `<thead>` 와 모바일 라벨(`data-label`)이 같은 값을 쓴다 —
# 두 벌이면 한쪽만 바뀐다(이 저장소가 손 사본으로 다섯 번 겪은 그것이다).
COLS = ("도시", "사진", "저작자", "라이선스")

TITLE = "사진 출처"
# 🔴 **문구는 `COPY.md` §8 이 정본이다**(2026-09-29 확정). 여기 적힌 것은 **그 문자열의 사본**이고,
# `tests/test_photos.py` 가 기획 파일과 **한 글자까지** 대조한다 — 갈리면 빨개진다.
#
# ⚠️ PH8 을 만들 때 나는 §8 을 **읽지 않고** 내 문장을 썼다. 머리말·`사진 준비중` 배지·`alt` 셋이
# 스펙과 갈린 채 배포됐다. 문구는 기획 소관인데 「없을 것」이라 짐작하고 지어낸 것이 원인이다.
# **소관이 남에게 있는 것은 찾아보고 시작한다.**
#
# 🔴 마지막 문장이 **ShareAlike 대응**이다 — BY-SA 사진을 줄여 쓴 사본도 같은 라이선스로
# 내놓는다고 밝힌다. 「크기 변경이 각색인가」의 해석과 무관하게 안전한 쪽이다(SPEC §CH3 보강).
LEAD = ("이 사이트의 목적지 사진은 위키미디어 공용의 자유 라이선스 사진입니다. "
        "원본·작가·라이선스는 아래와 같습니다. "
        "CC BY-SA 사진의 줄인 사본도 같은 라이선스로 제공됩니다.")
DESC = "갈래말래가 쓰는 도시 사진의 저작자·라이선스·원본 링크. 사진은 위키미디어 커먼즈에서 왔습니다."


def _rows(photos):
    """`{코드: 행}` → 도시별로 묶은 목록. 같은 사진을 여러 코드가 쓰면 **한 줄**로 합친다.

    합치는 기준은 **원본 페이지**다(같은 사진이면 같은 페이지). 코드마다 한 줄씩 내면
    도쿄가 두 번 나와 「사진이 두 장인가」로 읽힌다 — 실제로는 한 장이다.
    """
    by = {}
    for code, r in photos.items():
        key = (r.get("city") or "", r.get("page") or "")
        by.setdefault(key, {"row": r, "codes": []})["codes"].append(code)
    out = []
    for (city, _), v in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        v["codes"].sort()
        out.append((city, v["row"], v["codes"]))
    return out


def render(credits, contact):
    """`credits.json` 을 읽어 표를 그린다. 빈 값이 있으면 `site/photos.py` 가 이미 빌드를 멈췄다."""
    photos = (credits or {}).get("photos") or {}
    rows = _rows(photos)
    e = html.escape
    tr = []
    for city, r, codes in rows:
        tr.append(
            "      <tr>"
            f'<th scope="row">{e(city)}'
            f'<span class="cr-codes">{e(" ".join(codes))}</span></th>'
            f'<td data-label="{COLS[1]}">'
            f'<a href="{e(r["page"])}" rel="noopener nofollow" target="_blank">{e(r["title"])}</a></td>'
            f'<td data-label="{COLS[2]}">{e(r["author"])}</td>'
            f'<td data-label="{COLS[3]}">'
            f'<a href="{e(r["license_url"])}" rel="license noopener nofollow" target="_blank">'
            f'{e(r["license"])}</a></td>'
            "</tr>")
    body = f"""  {shell.logo("cr")}
  <h1>{TITLE}</h1>
  <p class="cr-lead">{LEAD}</p>
  <p class="cr-lead">🔧 <b>원본을 고쳤습니다.</b> 화면에 맞추려고 <b>크기를 줄이고 가장자리를 잘라냈으며
    webp 형식으로 바꿨습니다.</b> 내용을 더하거나 바꾸지는 않았습니다.
    원본은 각 줄의 제목 링크에서 볼 수 있습니다.</p>
  <table class="credits">
    <thead><tr>{"".join('<th scope="col">%s</th>' % c for c in COLS)}</tr></thead>
    <tbody>
{chr(10).join(tr)}
    </tbody>
  </table>
  <p class="cr-note">· 사진 {len(rows)}장 · 목적지 코드 {len(photos)}개.
    같은 사진을 쓰는 코드는 한 줄에 함께 적었습니다.</p>
  <p class="cr-note">· <b>CC0</b> 로 표시된 사진은 표시 의무가 없지만 같은 기준으로 적었습니다.</p>
  <p class="cr-note">· 사진이 아직 없는 목적지는 카드에 색만 들어갑니다.</p>
  <p class="cr-back"><a href="/">← 갈래말래로 돌아가기</a></p>"""
    return shell.page(TITLE + " · " + shell.SITE_NAME, DESC, "/credits.html", body, contact=contact)
