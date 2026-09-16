# galmal-frontend

[galmal.kr](https://galmal.kr) 의 **화면**. 한국 출발 항공권 특가를 지도에서 고르는 발견 서비스.

데이터는 여기 없다. 백엔드(`galmal-backend`)가 발행하는 **v1 API** 를 **빌드 타임에** 받아
정적 HTML 로 굽는다 — 브라우저가 아니라 GitHub Actions 가 받는다. 그래서 방문자는
아무것도 요청하지 않고, CORS·로딩 상태·재시도가 전부 없다.

```
galmal-backend  수집·판정 → v1/*.json 발행
        │
        └─ repository_dispatch ─▶  이 저장소: 받아서 굽고 Pages 로 배포
```

## 구조

| | |
|---|---|
| `site/` | 빌드. `build.py`(진입점) · `home.py`(발견 홈) · `route.py`(노선 36장) · `shell.py`(`<head>`·CSS) · `charts.py` · `fmt.py` · `seo.py` |
| `public/` | **그대로 서빙되는 파일.** `assets/`(`discover.js|css` · d3 · OG 이미지) · `data/world.geojson` |
| `fixtures/` | v1 응답 **사본**. 네트워크 없이 빌드하려고 둔다. **손으로 고치지 않는다** — `capture.py` 로 받아 적는다 |

## 로컬에서 굽기

```bash
python site/build.py --api fixtures/v1 --out dist     # 네트워크 없이
python site/build.py --api https://galmal.kr/v1 --out dist
```

표준 라이브러리만 쓴다. 설치할 것이 없다 — Node·npm 도 안 쓴다.

## 규칙 둘

- **`site/build.py` 는 `public/` 을 산출물 폴더에 복사한다.** JS·CSS 는 빌드 산출물이 아니라
  그냥 파일이라, 안 깔리면 **HTML 은 멀쩡한데 화면만 백지**가 된다. HTML 비교로는 안 잡힌다 —
  없는 파일의 404 는 HTML 에 안 나타난다. 그래서 배포 전에 파일 존재를 따로 점검한다.
- **`build.json`** 에 「어느 시점 데이터로 구웠나」(`api_generated`)를 적어 같이 배포한다.
  백엔드가 그 값과 API 의 `generated` 가 **같은지** 본다 — 배포가 조용히 멈추면 그걸로 잡힌다.

## 이력

2026-08~09 의 작업 이력은 [`promo-ticket-site`](https://github.com/RYU-TOMI/promo-ticket-site)
(→ `galmal-plan`) 에 있다. 이 저장소는 레포 분리(2026-09-16) 시점부터 시작한다.
