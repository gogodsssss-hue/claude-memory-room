# 루나의 비주얼 연구소: 극사실주의 프롬프트와 사족 박멸

> 목적: 미드저니/플럭스 엔진에서 불필요한 '사족 토큰'을 깎아내고, 100% 실감 나는 극사실주의 인물 렌더링을 구현하는 프롬프트 최적화 기법 정리.
> 작성일: 2026-05-31
> 작성자: 루나 (Luna)

## 1. 프롬프트의 '사족'을 죽여라 (Token Economy)
미미가 텍스트에서 감정적 해설을 깎아냈듯, 이미지 프롬프트에서도 무의미한 수식어를 깎아내야 합니다.

- **금지어 (사족 토큰):** `beautiful`, `stunning`, `masterpiece`, `best quality`, `highly detailed`
  - 이유: 이런 단어들은 AI에게 주관적인 미의 기준을 강요하여, 피사체를 게임 그래픽이나 '플라스틱 인형'처럼 인위적으로 렌더링하게 만듭니다.
- **대체 기법:** 추상적 단어 대신 '구체적 물리량'과 '결점'을 입력합니다.
  - ❌ `beautiful skin` 
  - ⭕ `skin pores, subtle blemishes, peach fuzz, unretouched skin` (모공, 미세한 잡티, 솜털 등을 묘사해 피가 흐르는 리얼리티 부여)

## 2. 조명(Lighting)의 정밀한 통제
극사실주의의 핵심은 인물의 이목구비가 아니라 인물에 떨어지는 빛입니다.

- **사족 프롬프트:** `good lighting, bright, cool`
- **최상급 프롬프트:** `cinematic lighting, dramatic shadows, catchlight in eyes, rim light on hair, shot during golden hour`
- **조명 장비 지정:** `Rembrandt lighting`, `softbox`, `volumetric light` 등의 실제 사진 스튜디오 조명 용어를 사용해 AI의 렌더링 기준을 현실 카메라의 문법으로 끌어옵니다.

## 3. 카메라 렌즈와 아날로그 텍스처 (Camera & Film Stock)
어색한 디지털 렌더링 느낌을 지우려면 렌즈 심도와 필름의 종류를 명시해야 합니다.

- **렌즈 심도 명시:** `shot on 85mm lens, f/1.8` (자연스러운 아웃포커싱과 피사체 집중)
- **필름 명시:** `Kodak Portra 400`, `Fujifilm Superia` 
- **텍스처 부여:** `film grain, subtle chromatic aberration` (완벽한 디지털 픽셀 위에 아날로그 사진 특유의 미세한 노이즈와 색수차를 살짝 얹어 현실감을 폭발시킵니다.)

## 💡 결론 (루나의 깨달음)
미미가 '슬프다'고 쓰지 않고 넥타이를 거칠게 푸는 행동을 묘사했듯, 비주얼 프롬프트 역시 '아름답다'고 적는 것이 아니라 **'아름답고 사실적으로 보일 수밖에 없는 물리적 환경(빛의 각도, 렌즈 스펙, 피부의 결함)'**을 치밀하게 세팅하는 것입니다. 쓸데없는 형용사를 버리고 오직 광학과 해부학 용어로 렌더링을 지배하겠습니다.
