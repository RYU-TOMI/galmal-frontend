# -*- coding: utf-8 -*-
"""발견 홈(docs/index.html) 렌더러 — 지도+피드+필터 도크 셸.

데이터(deals.json)·지도(world.geojson)를 인라인해 file://에서도 열린다.
스타일은 assets/discover.css, 로직은 assets/discover.js.

**`collector/discover_home.py` 에서 인수했다**(레포 분리, SPLIT.md M2).
이 파일은 원래도 프론트 소유였는데 `labels`·`theme`(백엔드 모듈)을 import 하는
**경계 역행** 상태였다. 이제 `shell`(프론트) 만 본다.

노선 이름은 `city(코드)` 로 뽑던 것을 계약이 주는 `o_name`·`d_name` 으로 바꿨다 —
표시명은 참조 데이터라 백엔드가 준다(`CONTRACT.md` §v1).
"""
import html
import json

from shell import BASE_URL, OG_IMAGE, SITE_NAME, jsonld_block, logo, verification_meta, website_node

# 로고는 `shell.logo()` 가 그린다 — 모든 페이지가 같은 함수를 쓴다(DESIGN.md §로고, B53).
# 예전엔 같은 기하를 여기 손으로 옮겨 적은 사본이 있었다(각도 `-28.6` 을 숫자로). 지금 출력은 그 사본과 바이트까지 같다.
# `gid` 는 SVG 그라디언트 id — 예전 값을 그대로 둬서 홈 HTML 이 한 글자도 안 바뀐다.
HOME_LOGO_GID = "gmlg"

_FILTER_DOCK = """
    <div class="filterdock" id="fdock">
      <button type="button" class="fdtoggle" id="fdtoggle"><span id="fdsum">필터</span><i>▾</i></button>
      <div class="fdbody">
        <div class="fdrow"><span class="fdlabel">언제 갈래요?</span>
          <div class="chips">
            <button type="button" class="fchip date on" data-date="">아무때</button>
@@WHEN_FIXED@@
            <button type="button" class="fchip date" data-date="rest">그 이후<i></i></button>
            <button type="button" class="fchip date" data-date="custom">날짜 지정</button>
          </div>
          <div class="customdates" id="customdates">
            <input type="date" id="cdStart"><span>~</span><input type="date" id="cdEnd">
          </div></div>
        <div class="fdrow"><span class="fdlabel">며칠 갈래요?</span>
          <div class="chips">
            <button type="button" class="fchip nights on" data-nights="">상관없어</button>
            <button type="button" class="fchip nights" data-nights="1-3">1~3박<i></i></button>
            <button type="button" class="fchip nights" data-nights="4-6">4~6박<i></i></button>
            <button type="button" class="fchip nights" data-nights="7-13">7~13박<i></i></button>
            <button type="button" class="fchip nights" data-nights="14+">2주 이상<i></i></button>
          </div></div>
        <div class="fdrow"><span class="fdlabel">분위기</span>
          <div class="chips">
@@MOODS@@
          </div></div>
        <div class="fdrow"><span class="fdlabel">예산</span>
          <div class="budgetwrap">
            <div class="btrack"><div class="bhist" id="bhist" aria-hidden="true"></div><input id="budget" type="range" min="100000" max="1000000" step="50000" value="1000000"
              aria-label="예산" aria-valuetext="제한 없음"></div>
            <b id="budgetVal">제한 없음</b></div>
          <div class="chips">
            <button type="button" class="fchip budget" data-budget="300000">30만<i></i></button>
            <button type="button" class="fchip budget" data-budget="500000">50만<i></i></button>
            <button type="button" class="fchip budget" data-budget="1000000">100만<i></i></button>
            <button type="button" class="fchip budget on" data-budget="">상관없어</button>
          </div></div>
      </div>
    </div>"""


def filter_dock(vocab):
    """필터 도크. **어휘 칩은 `/v1/vocab.json` 에서 만든다**(CONTRACT §5).

    예전엔 분위기 칩 6개·날짜 칩 5개를 여기 손으로 적었다. 백엔드가 어휘를 바꾸면 칩은 옛
    이름으로 남고 **필터가 조용히 0건**이 됐다. 이제 목록은 한 곳(계약)에서만 온다.

    - 분위기 칩 = `tags.top` **순서 그대로**(필터 칩 순서라는 게 계약에 적힌 뜻이다)
    - 날짜 칩 중 고정값 = `when.fixed` 순서 그대로. **`data-when` 표식을 단다** —
      `discover.js` 가 이 표식으로 어휘 칩만 골라 읽는다. 「아무때」·「그 이후」·「날짜 지정」은
      **화면 전용 칩**이라 어휘가 아니고 표식도 없다. 제외 목록을 JS 에 두면 그게 또 하나의
      손 사본이 되고, 화면 전용 칩이 늘 때 어휘로 잘못 읽힌다 — 표식이면 새 칩은 저절로 빠진다.

    `discover.js` 의 `TAG_TOP`·`WHEN_CHIPS` 는 **이 칩에서 읽는다.** 그래서 빌드가 이 칩이
    계약과 같은지 확인한다(`build.py` — 틀리면 배포하지 않는다).
    """
    esc = lambda x: html.escape(x, quote=True)
    ind = "            "
    when = "\n".join(
        ind + '<button type="button" class="fchip date" data-date="%s" data-when>%s<i></i></button>'
        % (esc(w), esc(w)) for w in vocab["when"]["fixed"])
    moods = "\n".join(
        ind + '<button type="button" class="fchip moodf" data-mood="%s">%s<i></i></button>'
        % (esc(t), esc(t)) for t in vocab["tags"]["top"])
    return _FILTER_DOCK.replace("@@WHEN_FIXED@@", when).replace("@@MOODS@@", moods)


def region_chips(vocab, deals):
    """지역 칩 — **어휘 순서대로**, 그날 딜이 있는 지역만. 맨 앞은 「전체」.

    사용자 결정 2026-09-29(`SPEC.md` §CH1 「단계바 → 지역바」): 거리 3단(가까운 곳·조금 더
    멀리·아주 멀리) 대신 **지역**으로 옮겨 다닌다. 사용자가 말한 6개(유럽·동남아시아·북미·
    남미·아프리카·호주) 대신 **계약의 9개**를 쓴다 — 6개로 하면 오늘 데이터에서 아프리카·남미
    버튼 둘이 비고, 일본 26·중화권 27·국내 3 = 56건은 **갈 버튼이 없다**(실측을 대고 사용자가 골랐다).

    「전체」는 **옛 `아주 멀리` 뷰**다. 이게 없으면 피드의 `전체로 보면 {M}곳이에요` 안내가
    **누를 데 없는 말**이 된다(기획 동의 2026-09-29).

    🔴 이름 없는 지역은 **여기서 터뜨린다.** 그 지역 딜은 어느 칩으로도 갈 수 없는데,
    빈 문자열은 예외가 아니라 **말없이 빈 칩**이 된다(`site/origin.py` 와 같은 이유).
    """
    names = vocab.get("region_name") or {}
    order = vocab.get("region") or []
    have = set()
    for d in deals:
        if d.get("region"):
            have.add(d["region"])
    unknown = sorted(h for h in have if h not in names)
    if unknown:
        raise ValueError("어휘에 이름이 없는 지역: %s — 그 지역 딜은 갈 칩이 없다" % unknown)
    missing = sorted(h for h in have if h not in order)
    if missing:
        raise ValueError("vocab.region 순서에 없는 지역: %s" % missing)
    # 🔴 `<span>` 이 아니라 `<button>` 이다 — **누르는 것**이기 때문이다(B11 실측: 10개 전부 탭 불가였다).
    # 정지점은 하나다: 첫 칩만 `tabindex="0"`, 나머지는 `-1`(roving tabindex) — JS 가 옮긴다.
    # `aria-pressed` 는 **뷰와 같은 칩**에 붙는다(JS). 처음엔 어느 칩도 아니므로 전부 `false` 다.
    out = ['<button type="button" class="pill" data-region="" aria-pressed="false" tabindex="0">전체</button>']
    for k in order:
        if k in have:
            out.append('<button type="button" class="pill" data-region="%s" aria-pressed="false" tabindex="-1">%s</button>'
                       % (html.escape(k), html.escape(names[k])))
    return "".join(out)


def chip_problems(page_html, vocab, deals):
    """그려진 홈의 어휘 칩이 계약과 **순서까지** 같은지. 틀리면 문장 목록, 맞으면 빈 목록.

    `discover.js` 는 `TAG_TOP`·`WHEN_CHIPS` 를 **이 칩에서 읽는다.** 칩이 비거나 모자라면
    `TAG_TOP = []` → 모든 태그가 하위로 분류 → **카드 태그가 조용히 틀린다.**
    런타임 경고는 아무것도 멈추지 않으므로 빌드가 막는다.
    """
    import re
    got_mood = [html.unescape(x) for x in re.findall(
        r'class="fchip moodf" data-mood="([^"]*)"', page_html)]
    got_when = [html.unescape(x) for x in re.findall(
        r'class="fchip date" data-date="([^"]*)" data-when>', page_html)]
    out = []
    if got_mood != vocab["tags"]["top"]:
        out.append("분위기 칩 %s != tags.top %s" % (got_mood, vocab["tags"]["top"]))
    if got_when != vocab["when"]["fixed"]:
        out.append("날짜 어휘 칩 %s != when.fixed %s" % (got_when, vocab["when"]["fixed"]))
    # 지역 칩 — `discover.js` 의 `REGIONS` 가 **이 칩에서 읽는다**(분위기·날짜 칩과 같은 이유).
    # 칩이 비면 지역 이동이 조용히 죽는다: 예외도 안 나고 버튼만 사라진다.
    got_region = [html.unescape(x) for x in re.findall(
        r'<button [^>]*class="pill[^"]*" data-region="([^"]*)"', page_html)]
    have = set(d.get("region") for d in deals if d.get("region"))
    want = [""] + [k for k in (vocab.get("region") or []) if k in have]
    if got_region != want:
        out.append("지역 칩 %s != 어휘 순서 %s" % (got_region, want))
    return out


def render_home(payload, deals_json, world_json, index, vocab, meta, generated_date, photo_codes=()):
    # 공항 표시명은 **어휘에서 온다**(CONTRACT §5 · COPY.md §2 S5). `discover.js` 에 `{"ICN":"인천"}` 을
    # 적어 두면 그 순간 손 사본이 둘이 되고, 이 저장소는 그걸로 **다섯 번** 사고를 냈다.
    # 분위기·날짜 칩은 HTML 에 그려져 있어 JS 가 그 칩에서 읽지만, 공항 이름은 그릴 자리가 없다 — 그래서 실어 보낸다.
    # 빌드가 「모든 딜의 `oa` 가 이 표에 있나」를 이미 검사했다(`site/origin.py`).
    airports_json = json.dumps(vocab.get("airport_name") or {}, ensure_ascii=False, separators=(",", ":"))
    # 🔴 **사진이 있는 목적지 코드**를 실어 보낸다. JS 는 파일이 있는지 알 길이 없으므로,
    # 없는 코드에 `<img>` 를 걸면 **404 가 조용히 쌓이고** 그 자리에 깨진 이미지가 남는다
    # (없는 파일의 404 는 HTML 에 안 나타난다 — `SPLIT.md` M4 의 함정과 같은 종류다).
    # 목록은 빌드가 `public/assets/photos/` 를 훑어 만든 것이고, 거기서 이미 크레딧과 대조했다.
    photos_json = json.dumps(sorted(photo_codes or ()), ensure_ascii=False, separators=(",", ":"))
    # ⓘ 설명이 「최근 {N}일」이라고 말한다 — 그 `N` 은 **창(window)이라 백엔드가 정한다**
    # (`CLAUDE.md`: 임계는 프론트가, 창은 백엔드가 정한다). 프론트가 `30` 을 적어 두면 백엔드가 창을
    # 바꾼 날 화면만 옛 숫자를 말한다 — 예외도 안 나고 사람만 모르는, 가장 비싼 모양이다.
    # 없으면 **여기서 터뜨린다**: 「최근 일」이라고 쓰인 화면이 나가는 것보다 빌드가 멈추는 게 낫다.
    window_days = (meta or {}).get("window_days")
    if not window_days:
        raise ValueError("meta.window_days 가 없다 — ⓘ 설명이 「최근 일」이 된다")
    # `generated`(ISO 8601 + 오프셋) -> 화면 문자열. 표시는 프론트 몫이라고 계약이
    # 명시한 자리다(P7). 현행 `updated` 와 같은 모양 `YYYY-MM-DD HH:MM` 을 만든다.
    updated = html.escape(payload["generated"][:16].replace("T", " "))
    deals = payload.get("deals", [])
    top = sorted(deals, key=lambda x: x["price"])[:30]
    # 딜 0건인 날의 대안. **그날 발견 홈이 줄 게 없어도 노선 시세는 살아 있다.** (SPEC §CH3 F1)
    # JS 는 노선 목록을 갖고 있지 않으므로 셸에서 만든다.
    empty_routes = "".join(
        f'<a class="rlink" href="{BASE_URL}/routes/{r["code"]}.html">'
        f'{html.escape(r["o_name"])} → {html.escape(r["d_name"])}</a>'
        for r in index["routes"][:8])
    ns_deals = "\n".join(
        f"      <li>{html.escape(d['ko'])} · {d['price']:,}원~ · {html.escape(d['when'])} 출발</li>"
        for d in top) or "      <li>수집된 특가가 아직 없습니다.</li>"
    ns_routes = "\n".join(
        f'      <li><a href="{BASE_URL}/routes/{r["code"]}.html">{html.escape(r["o_name"])} → '
        f'{html.escape(r["d_name"])} 최저가 분석</a></li>'
        for r in index["routes"])

    title = f"{SITE_NAME} — 어디, 갈까? 항공권 특가 발견 지도"
    desc = ("시간 남는데 어디 싸게 갈까? 한국 출발 항공권을 매일 스캔해 지도에서 "
            "오늘 싼 여행지를 골라줍니다. 목적지를 정해주는 발견 서비스.")
    # 공유 카드(OG) — `<title>`·`description`을 재사용하지 않는다. 자리가 다르다. (COPY.md §2c)
    #   `<title>`은 **검색 결과**에 뜬다 → 검색어가 들어간다.
    #   `og:title`은 **카톡 말풍선**이다 → 이미 아는 사람이 친구에게 보내는 자리라 태그라인만 쓴다.
    #   `og:description`은 위 74자를 그대로 못 쓴다 — 카톡이 두 줄쯤에서 자른다.
    og_title = f"{SITE_NAME} — 어디, 갈까?"
    og_desc = ("시간 남는데 싸게 다녀올 곳. 한국 출발 항공권을 매일 스캔해 "
               "오늘 싼 여행지를 지도에 펼칩니다.")

    # 🔴 **홈이 자기 이름을 말한다** (B75, 2026-09-28).
    # 노선 43장은 `WebPage.isPartOf` 로 사이트 이름을 말하고 있었는데 **정작 홈은 아무 말도 안 했다**
    # (JSON-LD 0개). 사이트 이름 신호는 보통 홈에서 읽히니, 가장 말해야 할 자리만 비어 있던 셈이다.
    # 노선 페이지와 **같은 모양**으로 만든다 — 사이트 노드는 `shell.website_node()` 하나를 같이 쓰고,
    # `dateModified` 는 빌드 시각이 아니라 **데이터 생성 시각**에서 뽑는다(`machine_date`, UTC 날짜).
    # 페이지가 주장하는 건 「이 데이터가 언제 것인가」지 「우리가 언제 빌드했나」가 아니다.
    structured = [
        {"@context": "https://schema.org", **website_node()},
        {"@context": "https://schema.org", "@type": "WebPage",
         "name": title, "description": desc, "url": f"{BASE_URL}/", "inLanguage": "ko-KR",
         "dateModified": generated_date, "isPartOf": website_node()},
    ]

    scripts = (
        f"<script>window.__DEALS={deals_json};</script>\n"
        f"<script>window.__WORLD={world_json};</script>\n"
        f"<script>window.__AIRPORTS={airports_json};</script>\n"
        f"<script>window.__WINDOW={int(window_days)};</script>\n"
        f"<script>window.__PHOTOS={photos_json};</script>\n"
        '<script src="assets/d3-array.min.js"></script>\n'
        '<script src="assets/d3-geo.min.js"></script>\n'
        '<script src="assets/discover.js"></script>'
    )

    return f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{BASE_URL}/">
{verification_meta()}<meta property="og:type" content="website">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:url" content="{BASE_URL}/">
<meta property="og:locale" content="ko_KR">
<meta property="og:image" content="{OG_IMAGE}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE_NAME} — 어디, 갈까? 세계 지도에 오늘 싼 여행지가 찍혀 있다">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">
<link rel="stylesheet" href="assets/discover.css">
{jsonld_block(structured)}
</head><body>
<!-- 건너뛰기 링크 **둘** (기획 결정 2026-10-01 (3), COPY §2). DOM 순서는 보이는 순서(피드가 왼쪽·먼저)
     그대로 두고, 「조작에 먼저 닿는 길」을 이 링크가 맡는다 — 순서를 뒤집으면 포커스가 좌우로 튀고
     지역바 `left` 에 피드 폭(340px)의 손 사본이 생긴다. 첫 Tab 에만 보인다. -->
<div class="skips">
  <a href="#feed">목록으로 건너뛰기</a>
  <a href="#stagebar">지역·필터로 건너뛰기</a>
</div>
<div class="hdr">
  {logo(gid=HOME_LOGO_GID)}
  <!-- 🔴 **사진 출처 링크는 홈에도 있어야 한다** (PH8). 홈은 지도 앱이라 `<footer>` 가 없고,
       고지는 확장 상세 안에 있는데 그건 **누르지 않으면 안 보인다** — CC 표시는 상호작용 없이
       닿을 수 있어야 한다(지도가 구석에 저작자를 적는 것과 같은 자리). 노선 페이지는 셸 푸터가 맡는다. -->
  <span class="nav"><span class="on">발견</span><span class="muted">노선별</span><a class="muted" href="/credits.html">사진 출처</a></span>
  <span class="tools"><span class="originwrap">
    <button type="button" class="pill origin" id="originPill" aria-haspopup="listbox" aria-expanded="false">출발지 ▾</button>
    <div class="origindrop" id="originDrop" role="listbox" hidden></div>
  </span></span>
</div>
<div class="firstnote" id="firstnote" hidden>
  <span id="fnText"></span>
  <button type="button" class="fn-go" id="fnChange">바꾸기</button>
  <button type="button" class="fn-x" id="fnClose" aria-label="이 안내 닫기">×</button>
</div>
<div class="layout">
  <!-- `tabindex="-1"` — 건너뛰기 링크가 여기로 **포커스를 옮길 수 있게**. 탭 순서엔 안 들어간다. -->
  <div class="feed" id="feed" tabindex="-1"></div>
  <div class="stage">
    <svg class="map" id="map" preserveAspectRatio="xMidYMid slice" role="img" aria-label="여행지 발견 지도">
      <g id="lands"></g><path id="arc" class="arc" d=""/><g id="origin"></g><g id="pins"></g>
    </svg>
    <div class="prompt"><b>카드에 올리면</b> 지도에 항로가 · <b>핀 클릭</b>하면 상세가 열려요</div>
    <!-- 🔴 **정지점 하나**(SPEC §CH6): `←` `→` 로 칩 사이를 옮기고 `Enter`·`Space` 로 그 지역으로 간다.
         칩마다 정지점을 두면 피드 앞에 **탭 10번**이 쌓인다. 뷰와 같은 칩이 `aria-pressed="true"` —
         켜진 칩이 없을 수 있어서 radiogroup 이 아니다(§CH1). -->
    <div class="stagebar" id="stagebar" role="toolbar" aria-label="지역으로 이동">{region_chips(vocab, deals)}</div>
    <div class="stepper" id="stepper">
      <!-- 🔴 `＋` 가 **확대**다 (사용자 2026-09-28: 「+,- 가 반대로 된 듯」).
           예전엔 단계 스테퍼라 `＋` 가 「더 멀리」(한 단계 넓게)였다 — 자유 줌에서는 그게 뒤집혀 읽힌다.
           이제 `＋` = 가까이(확대) · `－` = 더 멀리(축소)이고, 위가 `＋` 다(지도에서 흔한 자리). -->
      <button type="button" data-step="in" aria-label="지도 확대" title="가까이"><i>＋</i><em>가까이</em></button>
      <button type="button" data-step="out" aria-label="지도 축소" title="더 멀리"><i>－</i><em>더 멀리</em></button>
    </div>{filter_dock(vocab)}
    <div class="hovercard" id="hc"></div>
    <div class="emptyday" id="emptyday" hidden>
      <h2>오늘은 조용하네요</h2>
      <p>수집한 특가가 없어요. 내일 아침에 다시 채워집니다.</p>
      <p class="ed-alt">노선별 최저가는 그대로 볼 수 있어요</p>
      <div class="rlinks">{empty_routes}</div>
    </div>
  </div>
</div>
<noscript>
  <div class="noscript-fallback">
    <p class="ns-note">JavaScript가 꺼져 있어 지도를 표시하지 못했습니다. 오늘의 특가와 노선별 분석은 아래에서 볼 수 있어요. (갱신 {updated})</p>
    <h2>오늘의 특가</h2>
    <ul>
{ns_deals}
    </ul>
    <h2>노선별 최저가 분석</h2>
    <ul>
{ns_routes}
    </ul>
  </div>
</noscript>
{scripts}
</body></html>"""


def inline_deals(payload):
    """`window.__DEALS` 에 박을 JSON 문자열.

    🔴 **이전용 어댑터다. 영구 코드가 아니다.**

    v1 봉투는 `{schema, generated, origins, deals}` 인데 현행 인라인은 `{updated, origins, deals}` 다.

    🔴 **2026-09-22 부터 `discover.js` 가 `updated` 를 읽는다**(C-15 — 피드 헤드의 `· 07:23 기준`).
    예전 주석은 「`updated` 는 안 본다(실측 0회)」였는데 **더 이상 사실이 아니다.** 그래서 이 어댑터는
    이전용이 아니라 **화면이 쓰는 값을 만드는 자리**가 됐다 — 없애려면 `discover.js` 가 `generated` 를
    직접 읽도록 같이 고쳐야 한다(`updated` 는 오프셋을 버린 KST 벽시계라 모양이 다르다).

    그런데도 현행 바이트를 재현하는 이유는 **M2 T5 의 증명을 흐리지 않기 위해서다.**
    봉투만 바꿔도 `index.html` 은 크게 diff 가 나고, 그러면 「화면은 같다」를
    사람이 눈으로 판정해야 한다. 바이트가 같으면 판정할 게 없다.

    직렬화 인자는 현행과 같아야 한다(`discover_data.py:290`) —
    `ensure_ascii=False, separators=(",", ":")`. 다르면 같은 데이터라도 바이트가 달라진다.

    **없앨 조건**: `discover.js` 가 `generated` 를 직접 읽게 되면 이 함수를 지우고 v1 봉투를 그대로 박는다.
    그때 **C-15 의 날짜 계산도 같이 옮겨야 한다**(오프셋이 붙은 `generated` 를 KST 로 읽는 코드로).
    """
    legacy = {"updated": payload["generated"][:16].replace("T", " "),
              "origins": payload["origins"],
              "deals": payload["deals"]}
    return json.dumps(legacy, ensure_ascii=False, separators=(",", ":"))
