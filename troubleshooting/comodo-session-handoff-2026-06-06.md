# comodo-ingong 세션 인계문 (영숙방 비서 영숙 자동실행 등록)

> 이 문서는 **`comodo-ingong` 레포에서 새로 연 클로드 작업창**에 그대로 붙여넣어, 영숙방(비서 영숙) 리스너를 자동 실행에 등록시키기 위한 인계문이다.
> 진단·설계 전문은 공개 메모리룸의 `troubleshooting/youngsook-bot-switch-runbook-2026-06-06.md` 에 있다 (raw URL로 읽기 가능).

## 배경 한 줄
영숙방(@irir4r_secretary_bot)에서 비서 영숙이 주식·대화를 답하게 하려고 전용 리스너 `secretary_listener.py`를 만들었으나, **서버 자동실행 목록에 없어서 안 켜진다**(무응답). 이걸 자동실행에 등록하면 끝.

## comodo 세션 클로드에게 시킬 일 (복붙용)

```
영숙방(비서 영숙, @irir4r_secretary_bot) 전용 리스너를 자동 실행에 등록해줘.

1. youngsook_listener.py 와 같은 폴더에 secretary_listener.py 를 추가한다.
   - 이 파일은 youngsook_listener.py를 import해서 재사용하는 얇은 래퍼다.
   - 비서 영숙 토큰 + 영숙방 chat_id 만 보고, 상태파일(secretary_telegram_state.json)을 따로 쓰며,
     영숙방 외 메시지는 무시한다. "무조건 답하기" 안전장치 포함.
   - 전체 코드는 공개 메모리룸 런북 또는 마스터가 텔레그램으로 받은 파일과 동일.
     (참고 raw: github.com/gogodsssss-hue/claude-memory-room → troubleshooting/youngsook-bot-switch-runbook-2026-06-06.md)
2. 서버 자동 실행 스크립트(run_bot_forever.sh / pm2 / systemd 등 현재 youngsook_listener·drama_listener를
   띄우는 그 설정)를 찾아서, secretary_listener.py 도 같은 방식으로 백그라운드 상시 실행되도록 한 줄 추가한다.
   (드라마봇 분리했을 때와 동일 패턴)
3. secretary_private.json 을 만들되 토큰·chat_id 는 빈칸/플레이스홀더로 두고 .gitignore 에 추가한다.
   (실제 토큰·chat_id 는 마스터가 서버에서 직접 채운다. git에 올리지 말 것.)
4. py_compile로 문법 확인 후 커밋·푸시. 서버가 자동 pull/재기동하도록.
5. 본체 youngsook_listener.py 는 수정하지 말 것 (Irsar_bot·뉴스방 보존).
```

## 마스터가 직접 할 것 (서버에서, 토큰은 비밀)
- `secretary_private.json` 의 빈칸에 비서 영숙 봇 토큰 + 영숙방 chat_id 채우기.
- 비서 영숙 봇을 영숙방에 **관리자**로 (Group Privacy는 이미 OFF).
- 영숙방에서 Irsar_bot 내보내기(혼란 방지).
- 자동 재기동 후 영숙방에 `안녕` → 답하면 성공. 안 되면 콘솔 `[DEBUG chat_id] 수신 chat_id=` 값 확인.

## 확인 포인트 (comodo 세션에서)
- [ ] 현재 자동실행 설정 파일 위치·종류 파악(run_bot_forever.sh? pm2? systemd?).
- [ ] secretary_listener.py 가 거기 등록됐는지.
- [ ] juppang_analyzer 모듈 경로 정상 로드(기동 로그).
- [ ] 영숙방 chat_id 가 secretary 설정과 일치.

기록·보관: 2026-06-06, 코드(Claude Code). 짝 문서: `troubleshooting/youngsook-bot-switch-runbook-2026-06-06.md`.
