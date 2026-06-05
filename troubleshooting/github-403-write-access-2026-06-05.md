# 런북: 클로드가 GitHub에 못 올림 (403 쓰기 권한)

> 클로드(Claude Code)가 커밋은 되는데 **push/쓰기에서 403**이 날 때.
> 이건 거의 항상 **권한 설치 문제**다. 해킹·우회로 푸는 게 아니라 "권한을 연다".

## 증상

- `git push` → `remote: Permission to OWNER/REPO.git denied. 403`
- GitHub API(MCP) 쓰기 → `403 Resource not accessible by integration`
- 반면 **읽기·클론은 멀쩡히 됨** (이게 핵심 단서)

## 원인

클로드 GitHub 앱이 **"승인(Authorized/OAuth)"만 되고 "설치(Installed)"가 안 된 상태.**

| 구분 | 권한 | 결과 |
| --- | --- | --- |
| 승인됨 (OAuth) | 신원 확인 + 계정이 볼 수 있는 repo **읽기** | 클론·읽기 OK |
| 설치됨 (Installed) | 특정 repo에 **읽기+쓰기(Contents write)** | 이게 없으면 push 403 |

즉 "읽기는 되는데 쓰기만 막힘"은 거의 100% **앱 미설치**가 범인이다.

## 진단 (3분)

1. `https://github.com/settings/installations` → **"GitHub 앱 설치됨"** 탭
   - 여기 **Claude 가 없으면** → 미설치 확정
2. **"GitHub 앱 승인됨"** 탭
   - 여기 **Claude(소유자 anthropics) 가 있으면** → 승인만 된 상태 (읽기만 가능)
3. 클로드 앱 상세 페이지에 `"어떤 계정에도 설치되어 있지 않습니다"` 문구가 보이면 확정

## 해결

`https://github.com/apps/claude/installations/new` 접속 →
1. 설치할 계정 선택 (본인 계정)
2. 저장소 범위:
   - `저장소만 선택` → 해당 repo 추가 (**권장: 최소 권한**)
   - 또는 `모든 저장소` (편의 우선, 미래 repo 자동 포함)
3. 권한 화면에 **"코드 … 읽기 및 쓰기 권한"** 확인 → `설치 및 인증`

설치 직후 push 즉시 됨. 세션 재시작 불필요.

## 검증 (보고 ≠ 보관)

푸시했다고 끝이 아니다. 원격에 실제로 올라갔는지 눈으로 본다.

```bash
git fetch origin <branch>
git rev-parse HEAD                       # 로컬
git rev-parse origin/<branch>            # 원격 — 둘이 같아야 함
git show origin/<branch>:<파일> | head   # 원격 파일 내용 직접 확인
```

세 가지(로컬 커밋 / 해시 일치 / 원격 파일 내용)가 다 맞아야 "보관 완료".

## 교훈

- **읽기 OK + 쓰기 403 = 앱 설치 문제.** 토큰·서명·폴더 구조부터 의심하지 말 것.
- **403은 권한이다.** 자격증명(401)이 아니다. 뚫는 게 아니라 소유자가 연다.
- **로컬 커밋은 보관이 아니다.** 임시 컨테이너는 세션 종료 시 사라진다. push·검증까지 해야 보관.
- 권한이 막혀 한쪽이 다른 쪽 몫을 **대리로 써주면 "보고-실제 불일치"가 생긴다.** 각자 자기 손으로 보관하라.

---
기록: 2026-06-05, 클로드(코드)
