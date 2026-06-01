# 2026-06-01 — irsar_news 뉴스방 "작동 완료" + 디버깅 교훈

> 결과: `irsar_news` 방에서 **`뉴스 [주제]` → 미미 초안 → 워드프레스 임시저장**까지 전 파이프라인 작동 확인.
> 이 문서는 그 과정에서 막혔던 4가지 + 해결을 남겨, 드라마·영화방 추가 시 한 번에 가게 하기 위함.

## ✅ 최종 작동 구조
1. 방에서 `뉴스 삼성전자` 전송
2. `telegram_listener.py`의 `process_message`가 `startswith('뉴스')`로 잡음
3. `handle_mimi_command(f"미미야 {topic}", token, chat_id)` 호출 → 미미가 초안 작성
4. 미미가 그 방으로 답장 + 워드프레스 임시저장 자동

## 🧩 막혔던 4가지와 해결 (다음에 그대로 재사용)

### 1) GitHub 푸시 인증 — `.env`에 토큰 줄 중복
- 증상: `git push` → `Invalid username or token`.
- 원인: `.env`에 `GITHUB_TOKEN=` 줄이 2개 → 추출 시 두 토큰이 공백으로 붙어 깨짐.
- 해결: 중복 줄 제거(한 줄만), 푸시는 `https://x-access-token:<TOKEN>@github.com/<owner>/<repo>.git` 형식.
- 교훈: 토큰이 화면/채팅에 노출되면 즉시 재발급(classic, `repo` 스코프 하나면 모든 레포 read/write).

### 2) 봇이 그룹 메시지를 못 읽음 — Group Privacy
- 증상: 방에 "뉴스 …" 보내도 로그에 `메시지 처리 중`이 안 뜸. 봇·코드·문법은 정상.
- 진단: `getMe` → `"can_read_all_group_messages": false`.
- 해결: BotFather `/setprivacy` → 봇 → Disable → 봇을 방에서 내보냈다 다시 초대해야 적용. (관리자 지정도 가능)
- 확인: `getMe`가 `true`면 OK.
- 교훈: 코드 봇(`@Irsar_bot`) 기준으로 프라이버시 Disable/관리자. 영숙봇 아닙니다.

### 3) 봇 코드가 "마스터 개인 채팅"만 허용 — chat_id 필터
- 증상: 프라이버시 꺼도 그룹 무시. 개인채팅은 처리, 그룹은 안 됨.
- 원인: 메인 루프 `if str(sender_id) != str(chat_id): ... continue` — 허용된 한 곳 외 차단.
- 해결(2곳):
  - 허용 추가: `if str(sender_id) != str(chat_id) and str(sender_id) not in {"-5012814805"}:`
  - 답장을 메시지 온 방으로: 호출을 `process_message(token, sender_id, ...)`. (def 시그니처는 손대지 말 것)
- 교훈: 새 방 추가 = 그 방 chat_id를 위 세트에 추가.

### 4) 미미가 "뉴스를 못 찾음" — 검색어 형식
- 증상: 미미가 `최근 뉴스를 못 찾았어요`.
- 원인: 긴 지시문 전체를 검색어로 넘김. `handle_mimi_command`는 주제로 뉴스 검색 후 작성.
- 해결: `handle_mimi_command(f"미미야 {topic}", token, chat_id)` — 깔끔한 주제만.
- 참고: 미미는 No Fabrication상, 주제가 모호하면 팩트를 되묻는다. 구체적 주제+팩트를 주면 바로 초안.

## 🆕 새 방(드라마·영화 등) 추가 체크리스트 (현실 반영판)
1. 텔레그램에서 방 생성 → `@Irsar_bot` 초대 (프라이버시 이미 Disable이라 재초대 불필요)
2. 서버 `getUpdates`로 새 방 chat_id(`-숫자`) 확보
3. 코드 2곳:
   - 허용 세트에 새 chat_id 추가: `{"-5012814805", "-새번호"}`
   - 새 트리거 블록 추가(예: `startswith('드라마')`) → `handle_mimi_command(f"미미야 {topic}", token, chat_id)`
     - 삽입 위치: `msg_strip = message_text.strip()` 바로 다음(최상단)
4. `python3 -m py_compile` 문법 검사 → 봇 안전 재시작(감시자1/리스너1)
5. 새 방에서 트리거 테스트
- 연예방 가드레일: 공개된 사실만, 루머·사생활·명예훼손 금지, 스포일러 경고 후.

## 파일 백업 흔적(서버)
- `telegram_listener.py.bak_news` / `.bak_room` / `.bak_query`
