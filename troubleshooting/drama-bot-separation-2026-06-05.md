# 드라마봇 분리 작업 — 2026-06-05

## 작업 내용
- 드라마방 전용 봇 @irsar_drama_bot 생성 (DRAMA_BOT_TOKEN 발급)
- drama_listener.py 생성 (youngsook_listener.py 기반)
- youngsook_listener.py에서 드라마방 chat_id(-5011456393) 제거

## 봇/방 매핑
| 방 | 봇 | 리스너 |
|---|---|---|
| 봇방/뉴스방 | @Irsar_bot | youngsook_listener.py |
| 드라마방 | @irsar_drama_bot | drama_listener.py |

## 드라마봇 기능
- 모든 메시지 → 코덱스 검색(5건) → 미미 초안 생성
- "블로그 작성해" 키워드 → WP 카테고리 7(드라마영화방)에 임시저장
- "발행 [번호]" 명령 → WP 발행
- 미미 프롬프트: 최소 2500자, H2 5개 이상, 강렬한 훅 포함
