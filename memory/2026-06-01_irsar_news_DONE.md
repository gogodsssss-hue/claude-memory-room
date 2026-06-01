# 2026-06-01 — irsar_news & irsar_drama 텔레그램 방 "작동 완료" 및 최종 디버깅 교훈

## 1. 작동 확인 완료 사항
- `irsar_news`, `irsar_drama` 방에서 `뉴스/영화/드라마/신작 [주제]` 명령어 전송 시, 봇이 정상적으로 이를 포착하여 미미(Mimi)에게 초안 작성을 지시합니다.
- 미미가 작성한 초안이 해당 그룹방으로 즉시 회신되며, 동시에 워드프레스(WP) 임시저장이 자동으로 수행됨을 확인했습니다.
- 백로그(큐)에 쌓여있던 메시지들이 정상적으로 소화되며, Gemini API 503 오류 발생 시 OpenAI(gpt-4o-mini)로 폴백(Fallback) 되는 것까지 완벽 작동을 확인했습니다.

## 2. 막혔던 5대 원인과 해결책 (★가장 치명적인 5번 주의)

### ① GitHub 푸시 인증 오류 (토큰 중복)
- **증상:** `git push` 시 `Invalid username or token` 오류 발생.
- **원인:** `.env` 파일에 `GITHUB_TOKEN=` 줄이 2개 중복 등록되어 인증이 깨짐.
- **해결:** 중복 줄을 하나로 병합하여 해결.

### ② 봇 Group Privacy 권한 문제
- **증상:** 봇이 그룹방의 일반 메시지를 전혀 읽지 못함.
- **원인:** BotFather에서 `@Irsar_bot`(실행 봇)의 `can_read_all_group_messages`가 비활성화됨.
- **해결:** BotFather에서 프라이버시를 Disable로 설정 후, 봇을 방에서 내보냈다가 다시 초대. (또는 봇을 방의 '관리자'로 승급시켜 강제로 권한 갱신)

### ③ 메인 루프 `chat_id` 필터 차단
- **증상:** 개인 채팅은 응답하지만 그룹 방 메시지는 무시됨.
- **원인:** 보안 필터(`if str(sender_id) != str(chat_id):`)로 인해 마스터 개인 채팅 외의 모든 발신자가 차단됨.
- **해결:** 메인 루프 허용 세트에 `irsar_news`와 `irsar_drama`의 그룹 chat_id를 추가하고, `process_message` 호출 시 `chat_id` 대신 `sender_id`를 넘겨주어 응답이 발신 방으로 가도록 조치함.

### ④ 미미 검색어 형식 오류
- **증상:** 미미가 `최근 뉴스를 못 찾았어요`라고 답변함.
- **원인:** 너무 긴 프롬프트 지시문 전체가 검색어로 넘어감.
- **해결:** 트리거에서 깔끔한 주제(`미미야 {topic}`)만 전달하도록 로직 수정. (모호한 팩트는 미미가 No Fabrication 원칙에 따라 확인을 요청함)

### ⑤ [치명적] config override 찌꺼기 파일 문제 (무응답 원인)
- **증상:** 코드는 멀쩡하고 관리자 승급도 했는데 `config loaded` 이후 아무 반응이 없음.
- **원인:** 스크립트의 `load_config()` 로직이 `.env`보다 `telegram_setup.json`을 우선적으로 읽음. 이로 인해 서버에 남아있던 예전 테스트용 찌꺼기 파일이 로드되면서, 코드가 `@Irsar_bot`이 아닌 엉뚱한 봇(영숙봇 등)의 토큰으로 기동됨.
- **해결:** 서버에서 찌꺼기 설정 파일 삭제.
  ```bash
  cd ~/comodo-ingong/_company/_agents/secretary/tools/
  rm -f telegram_setup.json telegram_private.json
  ```
  이후 재기동 시 `[*] Telegram config loaded from .env`가 뜨면서 정상 작동.

## 3. cron 및 봇 재시작 주의 사항
- 봇의 백그라운드 구동 시 중복 인스턴스가 돌면서 409 Conflict(crash-loop)가 발생하는 현상을 주의해야 합니다.
- 문제 해결 후에는 `bot_watchdog`을 제외하고 **단일 가드(1줄 + `@reboot`)**로만 재무장하여 구동해야 합니다.

## 4. 새 방(예: 영화/드라마 방) 추가 절차 요약
1. 텔레그램 방 생성 후 **`@Irsar_bot` 초대 및 '관리자' 권한 부여**.
2. 서버에서 `getUpdates`를 통해 새 방의 `chat_id`(-숫자 형태) 확보.
3. `telegram_listener.py` 메인 루프 허용 세트에 새 `chat_id` 추가.
4. `process_message` 최상단에 새 트리거(예: `startswith('드라마')`) 추가 및 `handle_mimi_command` 연결.
5. 서버에 `telegram_setup.json` 같은 **찌꺼기 파일이 없는지 확인**.
6. `python3 -m py_compile`로 문법 검사 후, 기존 프로세스(`pkill -f telegram_listener.py`)를 죽이고 봇 안전 재시작.
