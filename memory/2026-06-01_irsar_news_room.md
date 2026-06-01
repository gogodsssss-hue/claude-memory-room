# 2026-06-01 — irsar_news 뉴스방 개설 + 다중 방 확장 계획

## 상황
- 새 텔레그램 방 **`irsar_news`** 개설(뉴스 전용).
- 향후 **연예인 드라마·영화방**을 추가로 개설할 계획.
- 이전 작업에서 긴 설치 코드 붙여넣기(paste) 깨짐 문제가 있었음 → 전달 방식 재검토.

## 결정/정리
- 봇은 하나(@Irsar_bot, .env의 TELEGRAM_BOT_TOKEN 주인)로 모든 방을 돌린다. 방 구분은 **트리거 단어**로만.
- 방 추가 = (1) 코드 봇 초대 (2) chat_id .env 저장 (3) 트리거 라우팅 (4) 명령 온 방으로 회신. → 런북: troubleshooting/multi-room-setup.md.
- 연예(드라마·영화)방은 미미 팩트 원칙 위에 **루머·사생활·명예훼손 가드레일** 추가.
- paste 깨짐 회피: 설치 코드는 비공개 레포 git pull 또는 공개 가능한 스니펫만 raw URL curl. 토큰/키/chat_id는 공개 레포 금지.

## 다음 할 일 (서버 작업 시)
1. irsar_news에 @Irsar_bot 초대 + Group Privacy off(또는 관리자) — 코드 봇 기준.
2. getUpdates로 irsar_news chat_id(-100…) 확보 → .env의 NEWS_ROOM_CHAT_ID.
3. telegram_listener.py에 "뉴스 [주제]" 트리거 라우팅 확인/추가 → 미미 호출 → WP 임시저장.
4. 검증: 감시자 1 / 리스너 1, 새 방에서 트리거 보내 그 방으로 회신 확인.
5. (이후) 드라마/영화방은 같은 4단계 반복, 트리거만 드라마/영화로.
