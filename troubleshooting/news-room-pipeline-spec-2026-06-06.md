# 뉴스방 대화형 블로그 파이프라인 — 사양서 (2026-06-06)

> 목적: 뉴스방을 **대화형 블로그 작성 방**으로 구현. 마스터가 뉴스 주제를 던지면 파이프라인이 돌아 워드프레스 임시저장까지.
> 구현·테스트·배포는 **comodo 클로드(서버·레포 접근 가능)**가 수행. 이 문서는 그 사양·코드 가이드.

## 1. 마스터 요구 (확정)
- 뉴스방 = **블로그 글 쓰는 방**이 맞다 (대화 전용 아님).
- **대화형**으로 꾸민다 — 명령 한 방에 침묵 덤프가 아니라, 각 단계를 멘트로 알리고 사용자가 주제·수정 요청하면 반영.
- 수집은 **네이버뉴스 API 우선** (한국뉴스 강함). 지금은 자꾸 **구글 RSS(`google_news_search`)로 빠짐** → 이게 핵심 버그.
- 파이프라인: **코덱스(자료수집) → 데스크(주제 선정) → 미미(글) → 루나(이미지) → 워드프레스 임시저장**.

## 2. 현재 코드 상태 (youngsook_listener.py 기준)
- ✅ `handle_codex_command` — **이미 네이버뉴스 API 사용** (`openapi.naver.com/v1/search/news.json`, `NAVER_CLIENT_ID/SECRET`). 점수화만 하고 미미로 안 넘김.
- ✅ `handle_desk_command` / `handle_keyword_command` — desk.md로 글감/골드키워드 선정. keyword는 데스크→미미까지 자동 체인 있음.
- ✅ `handle_mimi_command(blog_write=True)` — 미미 글 + 루나 이미지(`luna_flow_engine.generate_image`) + 워드프레스 REST 임시저장.
- ❌ 문제 1: `뉴스 [주제]` 트리거(566번 줄) → `handle_mimi_command` 호출인데, **미미 내부 수집이 `google_news_search`**라 네이버를 안 씀.
- ❌ 문제 2: `handle_mimi_command(prefetched_facts=...)` 파라미터가 **선언만 되고 실제로 안 쓰임**(본문에서 google로 재검색). → 코덱스가 모은 네이버 자료를 미미에 못 넘김.

## 3. 고칠 점 (정확히)
1. **네이버 수집 함수 공용화** — `handle_codex_command` 안의 네이버 호출을 `naver_news_search(query)` 공용 함수로 빼서, 뉴스 수집 경로가 전부 이걸 1순위로 쓰게 한다. (없거나 0건이면 구글 RSS→Tavily 폴백)
2. **`handle_mimi_command`가 `prefetched_facts`를 실제로 사용**하도록 수정 — prefetched_facts가 있으면 내부 재검색을 건너뛰고 그 자료로 글을 쓴다.
3. **뉴스방 파이프라인 연결** — `코덱스(naver 수집) → 데스크(주제) → 미미(prefetched_facts로 글 + 루나 + WP)` 를 한 흐름으로. 단계마다 방에 진행 멘트.

### naver_news_search() 참고 코드 (handle_codex_command에서 추출)
```python
import html as _h, re as _re, json, urllib.request, urllib.parse, os

def naver_news_search(query, display=8, sort='date'):
    nid = os.getenv('NAVER_CLIENT_ID'); nsc = os.getenv('NAVER_CLIENT_SECRET')
    if not nid or not nsc:
        return []
    def clean(t):
        return _re.sub(r'<[^>]+>', '', _h.unescape(t or '')).strip()
    try:
        q = urllib.parse.quote(query)
        req = urllib.request.Request(
            f'https://openapi.naver.com/v1/search/news.json?query={q}&display={display}&sort={sort}',
            headers={'X-Naver-Client-Id': nid, 'X-Naver-Client-Secret': nsc})
        with urllib.request.urlopen(req, timeout=10) as r:
            items = json.loads(r.read()).get('items', [])
    except Exception as e:
        print('[naver] error:', e, flush=True); return []
    out = []
    for it in items:
        out.append({
            'title': clean(it.get('title', '')),
            'url': it.get('originallink') or it.get('link', ''),
            'snippet': clean(it.get('description', '')),
            'pubDate': it.get('pubDate', ''),
        })
    return out
```
- 수집 우선순위: `naver_news_search()` → (0건) `google_news_search()` → (0건) `tavily_search()`.

## 4. 대화형 흐름 (뉴스방 전용 리스너 기준)
1. 사용자: 주제 입력 (예: "삼성전자 신제품", 또는 "오늘 뭐 쓸까")
2. 코덱스: `naver_news_search(topic)` → "📊 코덱스 | 네이버뉴스 N건 수집" 멘트
3. 데스크: 헤드라인을 desk.md로 평가 → "🗞️ 데스크 | 오늘은 '○○' 주제 추천" 멘트 (사용자가 다른 주제 말하면 교체)
4. 미미: 선정 주제 + 네이버 자료(prefetched_facts)로 블로그 초안 작성 → 방에 초안 표시
5. 루나: 썸네일 이미지 생성 → 워드프레스 임시저장(featured image 포함) → "📝 임시저장 완료 + 링크" 멘트
6. 사용자가 "고쳐", "다른 주제" 등 말하면 해당 단계만 다시.

## 5. 배포·주의
- **comodo 클로드가 구현**(레포 youngsook_listener 수정 + 뉴스방 리스너). 서버에서 NAVER/WP/루나 키로 실제 테스트.
- 본체 수정이 들어가므로(미미 prefetched_facts·네이버 공용화) **영숙 작업과 충돌 안 나게 순차로**.
- 뉴스 전용 봇(신규) + 뉴스방 chat_id, Irsar_bot에서 뉴스방 제거(이중응답 방지)는 `youngsook-bot-switch-runbook-2026-06-06.md` 0-3 참고.
- 🔒 NAVER_CLIENT_ID/SECRET, WP 키는 서버 .env에만.

기록·보관: 2026-06-06, 코드(Claude Code). 짝 문서: youngsook-bot-switch-runbook-2026-06-06.md.
