# 텔레그램 봇(comodo-ingong) 무응답 트러블슈팅 런북

> 대상: ~/comodo-ingong / _company/_agents/secretary/tools/telegram_listener.py
> 목적: 봇 무응답이 또 생겼을 때 처음부터 헤매지 않고 빠르게 원인을 좁히기 위한 기록.
> 최초 작성: 2026-05-31

## 0. 30초 요약 (TL;DR)
무응답 원인은 거의 항상 셋 중 하나:
1) 리스너 중복 실행 → 409 충돌 + LLM 키 429 조기 소진
2) 특정 분기 코드의 예외가 메인 루프 `except Exception: time.sleep(5)`에 조용히 삼켜짐
3) LLM 키 한도/장애 (폴백 살아있으면 보통 응답은 나옴)
핵심: 보내기/받기/시세/뉴스/LLM 중 어디서 끊겼는지 단계별로 자른다. 예외 삼키기를 풀어 에러를 드러내는 게 가장 빠르다.

## 1. 2026-05-31 사건 기록
증상: "주빵아 OO 분석해" 무응답("분석 중" 안내조차 없음). 코덱스/일반 메시지는 정상.
진짜 원인: 중복으로 들어간 2번째 코덱스 블록(773~781줄)에서 변수명을 message로 오타. 실제 변수명은 message_text.
 - 코덱스는 위에서 일찍 return → 이 줄 안 옴(정상)
 - 주빵이 등은 이 줄 통과 시 NameError: name 'message' is not defined
 - 메인 루프 except가 조용히 삼킴 → 무응답
수정: 해당 4곳 message -> message_text (단 res["message"] 같은 딕셔너리 키는 건드리지 말 것)
곁다리: 감시자(run_bot_forever) 다중 누적 → 리스너 5개 → Gemini 5배 호출 → 429 / cron 이중 감시(가드+bot_watchdog) 충돌 / .env 22·24줄 한글 메모로 dotenv 파싱 경고(키 로드엔 무해)

## 2. 표준 진단 플레이북
STEP 1 프로세스 상태:
  pgrep -f run_bot_forever.sh | wc -l   # 1이어야
  pgrep -f telegram_listener.py | wc -l # 1이어야
STEP 2 완전 정리 후 단일 재기동(감시자 먼저 kill):
  pkill -9 -f run_bot_forever.sh; pkill -9 -f telegram_listener.py; sleep 2
  TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d'=' -f2)
  curl -s "https://api.telegram.org/bot${TOKEN}/getUpdates?offset=-1" >/dev/null
  nohup bash run_bot_forever.sh >/dev/null 2>&1 &
  sleep 5; pgrep -f run_bot_forever.sh | wc -l; pgrep -f telegram_listener.py | wc -l
STEP 3 봇 신원/전송 테스트:
  curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
  curl -s "https://api.telegram.org/bot${TOKEN}/sendMessage" -d "chat_id=<CHAT>" -d "text=[진단] 전송 테스트"
STEP 4 예외 가시화 + foreground (가장 강력):
  crontab -l | grep -v -E "run_bot_forever|bot_watchdog" | crontab -   # 자동부활 잠시 끄기
  pkill -9 -f run_bot_forever.sh; pkill -9 -f telegram_listener.py; sleep 2
  PYTHONPATH="$PWD/vendor" python3 -u -X utf8 _company/_agents/secretary/tools/telegram_listener.py
  → 문제 메시지 보내고 화면 확인: Traceback=코드에러 / Segfault·Killed=네이티브크래시 / 멈춤=무한대기
STEP 5 멈춘 지점 덤프(py-spy): Ctrl+Z 후
  PID=$(pgrep -f telegram_listener.py | head -1)
  pip install py-spy --break-system-packages -q
  $(command -v py-spy || echo ~/.local/bin/py-spy) dump --pid $PID; kill -9 $PID
  ※ 덤프가 main getUpdates(폴링)를 가리키면 멈춤이 아니라 정상 idle → STEP 4로.
STEP 6 모듈/키 격리 테스트:
  timeout 45 python3 -c "import sys;sys.path.insert(0,'vendor');sys.path.insert(0,'_company/agents/stock_expert/skills');import juppang_analyzer as j;print(j.extract_intent('삼성전자 분석해'));print(str(j.analyze_stock('005930.KS').get('report',''))[:200])"
STEP 7 복구 후 cron 재무장(가드 1줄 + @reboot, bot_watchdog 제외)

## 3. 알려진 취약점
1) 메인 루프 except가 에러를 출력 없이 삼킴 → traceback.print_exc() 추가 권장
2) run_bot_forever 수동 실행분 누적 → 항상 STEP 2로 재기동
3) cron 이중 감시(가드+bot_watchdog) → 가드 1줄 + @reboot만 유지
4) .env 한글 메모줄(22·24) → # 주석, 덮어쓰는 주체 점검
5) process_message 내 단독 message는 전부 message_text 여야 함

## 4. 핵심 파일/위치
- 리스너: _company/_agents/secretary/tools/telegram_listener.py (main 폴링 루프 / process_message)
- 종목분석 모듈: _company/agents/stock_expert/skills/juppang_analyzer.py (extract_intent, analyze_stock)
- LLM: call_agent_model -> call_gemini(timeout60) -> 폴백 call_openai(timeout20)
- 감시자: run_bot_forever.sh(무한 재시작), bot_watchdog.sh(하트비트 정체 시 kill)
- 로그: _company/logs/listener.log, listener_supervisor.log
