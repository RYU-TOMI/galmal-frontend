# -*- coding: utf-8 -*-
"""sitemap.xml · robots.txt — 검색엔진에 무엇이 있는지 알린다.

**`collector/build_site.py:build_seo()` 에서 인수했다**(레포 분리, SPLIT.md M2).
P1(백엔드는 마크업을 만들지 않는다)과 P2(사이트 주소를 아는 건 프론트뿐) 둘 다 걸린다 —
sitemap 은 처음부터 끝까지 우리 도메인의 URL 목록이다.

`lastmod` 는 **크롤러가 읽는 기계용 날짜**다. 현행은 `timeutil.today_utc()`(빌드 시각)를
썼고, 여기서는 `meta.generated` 의 날짜를 쓴다 — 페이지가 주장하는 신선도와 같은 값이어야
하기 때문이다. 노선 페이지의 `dateModified` 와 **같은 출처**를 쓰는 것이 요점이다.
둘이 갈리면 한쪽만 고쳐지고, 그건 이 프로젝트가 이미 겪은 실패다(`SPEC.md` IA-3).
"""
from route import thin
from shell import BASE_URL

SITEMAP_HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n' \
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'


def sitemap(index, lastmod, routes):
    """홈 + 노선 페이지. 순서는 `routes/index.json` 그대로 — 현행이 `route_index` 순서였다.

    🔴 **표본이 얇은 노선(수집 14일 미만)은 싣지 않는다**(DECISIONS.md 2026-09-20 (7)). 페이지는 **그대로 굽는다** —
    접근도 되고 「다른 노선 보기」 링크도 남는다. 빼는 것은 검색엔진에 **먼저 내미는 것**뿐이다.
    새 노선의 첫날 페이지는 차트가 전부 비어 있다. 거짓 주장은 없지만, 노선 페이지의 존재 이유가 검색 유입이라
    빈 페이지로 먼저 색인되면 그 모습이 다음 크롤까지 남는다 — 가장 나쁜 첫인상을 우리가 직접 제출하는 셈이다.
    `routes` 는 `{code: 노선 응답}`. 목록에 있는데 응답이 없는 노선은 얇은 것으로 친다(구워지지도 않는다).
    """
    urls = [(f"{BASE_URL}/", "daily", "1.0")]
    urls += [(f'{BASE_URL}/routes/{r["code"]}.html', "daily", "0.8")
             for r in index["routes"] if not thin(routes.get(r["code"]) or {})]
    entries = "\n".join(
        f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod>"
        f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>"
        for loc, freq, pri in urls)
    return SITEMAP_HEAD + entries + "\n</urlset>\n"


def robots():
    return f"User-agent: *\nAllow: /\n\nSitemap: {BASE_URL}/sitemap.xml\n"


def build_all(index, lastmod, routes):
    """{파일명: 내용}. 파일 쓰기는 `build.py` 가 한다."""
    return {"sitemap.xml": sitemap(index, lastmod, routes), "robots.txt": robots()}
