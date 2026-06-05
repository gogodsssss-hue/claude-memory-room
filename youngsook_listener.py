#!/usr/bin/env python3
"""Telegram Listener — secretary_telegram_listener.

영숙(Secretary)이 텔레그램 메시지를 실시간으로 모니터링하여 대표님의 지시를 접수하고,
인터넷 검색, 핫뉴스/이슈/실시간 트렌드 추적, 구글 캘린더 조회를 연동하여 실시간 보고를 전송합니다.
Gemini API와 연동하여 영숙의 품격 있고 완벽한 페르소나(경어체, 두괄식, Next Action 제시)를 100% 구현합니다.
"""
import os
import json
import time
import datetime
import urllib.request
import urllib.parse
import re
import sys
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Ensure stdout uses UTF-8 to prevent Windows console encoding errors
if sys.platform.startswith('win'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "telegram_private.json")
SETUP_CONFIG_PATH = os.path.join(HERE, "telegram_setup.json")
PERSONA_PATH = os.path.abspath(os.path.join(HERE, "..", "prompt.md"))
BRAIN_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
ENV_PATH = os.path.join(BRAIN_ROOT, ".env")

try:
    sys.path.append(HERE)
    import google_calendar_helper
except ImportError:
    google_calendar_helper = None

try:
    juppang_path = os.path.abspath(os.path.join(HERE, "..", "..", "..", "agents", "stock_expert", "skills"))
    sys.path.append(juppang_path)
    import juppang_analyzer
except ImportError:
    juppang_analyzer = None

SECURITY_ATTEMPT_LOG = {}
SECURITY_NOTIFY_LOG = {}

def mask_sender_id(sender_id) -> str:
    """sender_id를 ***마지막4자리 형태로 마스킹"""
    s = str(sender_id)
    if len(s) > 4:
        return "***" + s[-4:]
    return "***" + s

def log_security_event(sender_id, chat_type, count) -> None:
    """_company/logs/security_access.log에 메타데이터만 append"""
    log_dir = os.path.join(BRAIN_ROOT, "_company", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "security_access.log")
    
    masked_id = mask_sender_id(sender_id)
    now_str = datetime.datetime.now().astimezone().isoformat()
    
    log_entry = json.dumps({
        "time": now_str,
        "sender_id": masked_id,
        "chat_type": chat_type,
        "count": count,
        "action": "blocked"
    })
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Log writing failed: {e}")

def increment_attempt_counter(sender_id) -> int:
    """sender_id별 시도 카운터 증가. 1시간 전 기록 자동 만료. 현재 카운트 반환."""
    now = time.time()
    one_hour_ago = now - 3600
    
    if sender_id not in SECURITY_ATTEMPT_LOG:
        SECURITY_ATTEMPT_LOG[sender_id] = []
        
    SECURITY_ATTEMPT_LOG[sender_id] = [t for t in SECURITY_ATTEMPT_LOG[sender_id] if t > one_hour_ago]
    SECURITY_ATTEMPT_LOG[sender_id].append(now)
    
    return len(SECURITY_ATTEMPT_LOG[sender_id])

def notify_master_security_alert(sender_id, count, chat_type, token, chat_id) -> None:
    """마스터에게 보안 경보 sendMessage. 1시간에 동일 sender_id당 1회 제한."""
    now = time.time()
    one_hour_ago = now - 3600
    
    last_notify = SECURITY_NOTIFY_LOG.get(sender_id, 0)
    if last_notify > one_hour_ago:
        return
        
    SECURITY_NOTIFY_LOG[sender_id] = now
    
    masked_id = mask_sender_id(sender_id)
    alert_msg = (
        "🔒 **보안 경보**\n"
        "외부 접근 반복 시도 감지\n"
        f"- sender_id: {masked_id}\n"
        f"- chat_type: {chat_type}\n"
        f"- 최근 1시간 시도 횟수: {count}"
    )
    send_telegram_message(token, chat_id, alert_msg)

def load_config():
    load_dotenv(dotenv_path=ENV_PATH)
    for path in (CONFIG_PATH, SETUP_CONFIG_PATH):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if cfg.get("TELEGRAM_BOT_TOKEN") and cfg.get("TELEGRAM_CHAT_ID"):
                    print(f"[*] Telegram config loaded: {os.path.basename(path)}")
                    return cfg
            except Exception as e:
                print(f"[!] Telegram config load failed ({path}): {e}")

    cfg = {
        "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
    }
    if cfg["TELEGRAM_BOT_TOKEN"] and cfg["TELEGRAM_CHAT_ID"]:
        print("[*] Telegram config loaded from .env")
        return cfg

    print("❌ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 설정을 찾을 수 없습니다.")
    sys.exit(1)

def load_gemini_api_key():
    load_dotenv(dotenv_path=ENV_PATH)
    return os.getenv("GEMINI_API_KEY_3") or os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")

def load_openai_api_key():
    load_dotenv(dotenv_path=ENV_PATH)
    return os.getenv("OPENAI_API_KEY")

def load_persona():
    if os.path.exists(PERSONA_PATH):
        try:
            with open(PERSONA_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    return "당신은 이르사르 제국의 수석 행정 비서인 영숙(Youngsook)입니다. 대표님(마스터)께 극도의 품격과 신뢰가 묻어나는 비즈니스 경어체를 사용하여 두괄식 보고와 다음 실행 단계(Next Action)를 제시해야 합니다."

def load_juppang_persona():
    jp_path = os.path.abspath(os.path.join(HERE, "..", "..", "..", "agents", "stock_expert", "prompt.md"))
    if os.path.exists(jp_path):
        try:
            with open(jp_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    return "당신은 시장의 모든 정보를 흡수하여 확정적이고 명쾌한 조언을 제공하는 마이더스 손 주식 전략가 주빵이입니다."

def load_claude_persona():
    c_path = os.path.join(BRAIN_ROOT, "CLAUDE.md")
    if os.path.exists(c_path):
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    return "당신은 클로드(Claude)입니다."

def load_codex_persona():
    c_path = os.path.join(BRAIN_ROOT, ".claude", "agents", "codex.md")
    if os.path.exists(c_path):
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    return "당신은 코덱스(Codex)입니다."

def load_irsar_persona():
    c_path = os.path.join(BRAIN_ROOT, ".claude", "agents", "irsar.md")
    if os.path.exists(c_path):
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    return "당신은 이르사르(Irsar)입니다."

def load_kodari_persona():
    c_path = os.path.join(BRAIN_ROOT, ".claude", "agents", "kodari.md")
    if os.path.exists(c_path):
        try:
            with open(c_path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            pass
    return "당신은 코다리(Kodari)입니다."

def save_last_update_id(update_id):
    state_path = os.path.join(HERE, "telegram_state.json")
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"last_update_id": update_id}, f)

def get_last_update_id():
    state_path = os.path.join(HERE, "telegram_state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f).get("last_update_id", 0)
        except:
            pass
    return 0

def _send_single_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.loads(res.read().decode('utf-8'))
    except Exception as e:
        print(f"[!] 메시지 전송 실패: {e}")
        return None

import re

def clean_telegram_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("**", "")
    text = text.replace("###", "")
    text = text.replace("---", "")
    text = re.sub(r'^\s*\*\s+', '- ', text, flags=re.MULTILINE)
    return text

def send_telegram_message(token, chat_id, text, add_timestamp=False):
    if not text:
        return None

    text = clean_telegram_text(text)
    if add_timestamp:
        kst = datetime.timezone(datetime.timedelta(hours=9))
        ts = datetime.datetime.now(kst).strftime("%Y년 %m월 %d일 %H시 %M분")
        text = f"[기준 시각: {ts} KST]\n\n{text}"

    max_len = 3500
    if len(text) <= max_len:
        return _send_single_telegram_message(token, chat_id, text)
        
    chunks = []
    current_text = text
    while len(current_text) > max_len:
        split_idx = current_text.rfind('\n', 0, max_len)
        if split_idx == -1:
            split_idx = max_len
        chunks.append(current_text[:split_idx])
        current_text = current_text[split_idx:].lstrip('\n')
        
    if current_text:
        chunks.append(current_text)
        
    total = len(chunks)
    last_res = None
    for i, chunk in enumerate(chunks, 1):
        prefix = f"[{i}/{total}]\n"
        last_res = _send_single_telegram_message(token, chat_id, prefix + chunk)
    return last_res

def call_gemini(system_instruction, user_prompt, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key.strip()}"
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {
                "parts": [{"text": user_prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": 8192
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            resp_data = json.loads(res.read().decode('utf-8'))
            return resp_data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[!] Gemini API 호출 에러: {e}")
        return None

def call_openai(system_instruction, user_prompt, api_key):
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            data = json.loads(res.read().decode('utf-8'))
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[!] OpenAI 폴백 호출 실패: {e}")
        return None

def call_agent_model(system_instruction, user_prompt, gemini_key, openai_key):
    load_dotenv(dotenv_path=ENV_PATH)
    gkeys = []
    for _n in ("GEMINI_API_KEY_3", "GEMINI_API_KEY_2", "GEMINI_API_KEY",
               "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"):
        _v = os.getenv(_n)
        if _v and _v not in gkeys:
            gkeys.append(_v)
    for _i, _gk in enumerate(gkeys, 1):
        report = call_gemini(system_instruction, user_prompt, _gk)
        if report:
            return report
        print(f"[*] Gemini key{_i} limit/fail -> next free key", flush=True)
    print("[!] all free Gemini keys exhausted - retry later", flush=True)
    return None

def resolve_google_news_url(rss_url):
    """Google News RSS URL → 실제 기사 URL 변환"""
    if not rss_url or 'news.google.com' not in rss_url:
        return rss_url
    try:
        from googlenewsdecoder import new_decoderv1
        result = new_decoderv1(rss_url)
        if result.get('status') and result.get('decoded_url'):
            return result['decoded_url']
    except Exception:
        pass
    return rss_url

def extract_search_keywords(query, oai_key):
    """자연어 쿼리 → 검색 키워드 2-3개 추출"""
    if len(query) <= 12:
        return query
    import json, urllib.request
    try:
        data = json.dumps({
            'model': 'gpt-4o-mini', 'max_tokens': 20,
            'messages': [
                {'role': 'system', 'content': '인물명/회사명/기술명 고유명사 2개만 추출. 동사형용사 제외. 공백 구분 출력. 다른 말 금지.'},
                {'role': 'user', 'content': query}
            ]
        }).encode()
        req = urllib.request.Request(
            'https://api.openai.com/v1/chat/completions', data=data,
            headers={'Authorization': f'Bearer {oai_key}', 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=10) as r:
            result = json.loads(r.read())['choices'][0]['message']['content'].strip()
            return result if result else query
    except:
        return query


_FLUFF = ('대학', '유학생', '기부', '동아리', '축제', '장학', '캠퍼스', '총장',
          '입학', '졸업', '봉사', '위촉', '임명', '동문', '학생회', '제빵', '양갱')

def hot_market_news(max_total=10):
    sections = [
        ("https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=ko&gl=KR&ceid=KR:ko", 3),
        ("https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko", 3),
        ("https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko", 2),
    ]
    merged, seen = [], set()
    for u, take in sections:
        cnt = 0
        try:
            rq = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(rq, timeout=15) as rp:
                rt = ET.fromstring(rp.read())
            for it in rt.findall('.//item'):
                if cnt >= take:
                    break
                ti = it.findtext('title', '')
                ln = it.findtext('link', '')
                if not ti or not ln or any(b in ti for b in _FLUFF) or ln in seen:
                    continue
                seen.add(ln); cnt += 1
                merged.append({"title": ti, "url": resolve_google_news_url(ln),
                               "snippet": "발행일시: " + it.findtext('pubDate', '')})
        except Exception as e:
            print("[hot_market_news] feed fail:", e, flush=True)
    for r in google_news_search('부동산 정책')[:2]:
        k = r.get('url') or r.get('title')
        if k and k not in seen:
            seen.add(k); merged.append(r)
    return merged[:max_total]


def google_news_search(query):
    encoded_query = urllib.parse.quote(query + " when:2d")  # 최근 2일만
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            import email.utils
            cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)
            collected = []
            for item in root.findall('.//item'):
                title = item.findtext('title', default='제목 없음')
                if any(b in title for b in _FLUFF):
                    continue
                rawlink = item.findtext('link', default='')
                pubDate = item.findtext('pubDate', default='')
                if not rawlink:
                    continue
                dt = None
                if pubDate:
                    try:
                        dt = email.utils.parsedate_to_datetime(pubDate)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=datetime.timezone.utc)
                    except Exception:
                        dt = None
                if dt is not None and dt < cutoff:
                    continue
                collected.append({"title": title, "rawlink": rawlink, "pubDate": pubDate, "_dt": dt})
            _min = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
            collected.sort(key=lambda x: x["_dt"] or _min, reverse=True)
            results = []
            for c in collected[:5]:
                results.append({
                    "title": c["title"],
                    "url": resolve_google_news_url(c["rawlink"]),
                    "snippet": f"발행일시: {c['pubDate']}"
                })
            return results
    except Exception as e:
        print(f"[!] 구글 뉴스 RSS 파싱 에러: {e}")
        return []

def tavily_search(query, api_key):
    url = "https://api.tavily.com/search"
    headers = {"Content-Type": "application/json"}
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_answer": False,
        "include_images": False,
        "max_results": 5
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        results = []
        for res in data.get("results", []):
            results.append({
                "title": res.get("title", ""),
                "url": res.get("url", ""),
                "snippet": res.get("content", "")
            })
        return results
    except Exception as e:
        print(f"[!] Tavily 검색 에러: {e}")
        return []

def get_recent_history():
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    conv_file = os.path.join(BRAIN_ROOT, "_company", "00_Raw", "conversations", f"{today}.md")
    if not os.path.exists(conv_file):
        return "최근 대화 기록이 없습니다."
    try:
        with open(conv_file, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content) > 3000:
                return "..." + content[-3000:]
            return content
    except Exception as e:
        return ""

def log_to_conversation(message_text, reply_text=""):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    conv_dir = os.path.join(BRAIN_ROOT, "_company", "00_Raw", "conversations")
    os.makedirs(conv_dir, exist_ok=True)
    conv_file = os.path.join(conv_dir, f"{today}.md")
    
    log_entry = f"\n\n## [{timestamp}] 👤 **사용자 (Telegram)**\n\n{message_text}\n"
    if reply_text:
        log_entry += f"\n### [{timestamp}] 📱 **비서 영숙**\n\n{reply_text}\n"
    
    try:
        if not os.path.exists(conv_file):
            with open(conv_file, "w", encoding="utf-8") as f:
                f.write(f"# 📜 {today} 회사 대화록\n\n_모든 명령·분배·산출물·대화가 시간순으로 누적됩니다. 두뇌가 자동 인덱싱·동기화합니다._\n")
        
        with open(conv_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
        print(f"[+] 텔레그램 지시사항 전사 대화록에 기록 완료: {conv_file}")
        return True
    except Exception as e:
        print(f"[!] 전사 대화록 기록 실패: {e}")
        return False

def process_message(token, chat_id, message_text, gemini_key, openai_key, persona):
    # === 주빵 호출 정규화: 주빵/주빵아/주빵이 (붙이든 띄든) -> "주빵 [종목]" ===
    _m = message_text.strip()
    if _m.startswith('주빵') and '감시' not in _m:
        _rest = re.sub(r'^주빵(?:[아이]\s+|\s+)?', '', _m).strip()
        if _rest:
            message_text = '주빵 ' + _rest

    # 0.05 키워드 발굴 - 최우선
    if message_text.strip().startswith('키워드') or message_text.strip().startswith('/keyword'):
        _m = message_text.strip()
        _q = (_m[8:] if _m.startswith('/keyword') else _m[3:]).strip()
        handle_keyword_command(_q, token, chat_id)
        return
    # 0.1 데스크 (글감 선별) - 최우선 분기
    if message_text.strip().startswith('데스크') or message_text.strip().startswith('/desk'):
        _m = message_text.strip()
        _q = (_m[5:] if _m.startswith('/desk') else _m[3:]).strip()
        handle_desk_command(_q, token, chat_id)
        return
    print(f"[*] 메시지 처리 중: {message_text}")
    load_dotenv(dotenv_path=ENV_PATH)
    
    # 0. Check for Claude and Codex commands
    msg_strip = message_text.strip()
    for _kw in ('영화', '드라마', '신작'):
        if message_text.strip().startswith(_kw):
            topic = message_text.strip()[len(_kw):].strip()
            if not topic:
                send_telegram_message(token, chat_id, f'🎬 사용법: {_kw} [제목]\n예) {_kw} 오징어게임 시즌3')
                return
            handle_mimi_command(f'미미야 {topic}', token, chat_id)
            return
    # === 뉴스방: "뉴스 [주제]" -> 미미 뉴스 초안 ===
    if message_text.strip().startswith('뉴스'):
        topic = message_text.strip()[2:].strip()
        if not topic:
            send_telegram_message(token, chat_id, '📰 사용법: 뉴스 [주제]\n예) 뉴스 삼성전자 신제품 출시')
            return
        handle_mimi_command(f"미미야 {topic}", token, chat_id)
        return
    
    is_codex_request = False
    codex_prefix = ""
    for kw in ["/codex", "코덱스,", "코덱스 ", "코덱스\n", "코덱스!"]:
        if msg_strip.startswith(kw) or msg_strip == "코덱스":
            is_codex_request = True
            codex_prefix = kw if msg_strip.startswith(kw) else "코덱스"
            break
            
    is_claude_request = False
    claude_prefix = ""
    for kw in ["/claude", "클로드,", "클로드 ", "클로드\n", "클로드!"]:
        if msg_strip.startswith(kw) or msg_strip == "클로드":
            is_claude_request = True
            claude_prefix = kw if msg_strip.startswith(kw) else "클로드"
            break

    is_irsar_request = False
    irsar_prefix = ""
    for kw in ["/irsar", "이르사르,", "이르사르 ", "이르사르\n", "이르사르!"]:
        if msg_strip.startswith(kw) or msg_strip == "이르사르":
            is_irsar_request = True
            irsar_prefix = kw if msg_strip.startswith(kw) else "이르사르"
            break

    is_kodari_request = False
    kodari_prefix = ""
    for kw in ["/kodari", "코다리,", "코다리 ", "코다리\n", "코다리!"]:
        if msg_strip.startswith(kw) or msg_strip == "코다리":
            is_kodari_request = True
            kodari_prefix = kw if msg_strip.startswith(kw) else "코다리"
            break

    if is_irsar_request:
        query = msg_strip[len(irsar_prefix):].strip() if msg_strip.startswith(irsar_prefix) else ""
        i_persona = load_irsar_persona()
        recent_history = get_recent_history()
        prompt = f"[최근 대화 컨텍스트 (기억용)]\n{recent_history}\n\n" \
                 f"마스터의 지시:\n{query}\n\n" \
                 f"당신의 정본 페르소나(IRSAR)에 완벽히 빙의하여 판단/정리/라우팅을 수행하십시오.\n" \
                 f"텔레그램 환경이므로 본체 호출이 아님을 명시하기 위해, 반드시 응답을 '마스터, [Gemini/Irsar Persona]입니다.'로 시작하십시오."
                 
        send_telegram_message(token, chat_id, f"👑 *[Gemini/Irsar Persona]*\n\n명령을 접수했습니다. 판단 및 정리를 시작합니다...")
        
        report = call_agent_model(i_persona, prompt, gemini_key, openai_key)
        send_telegram_message(token, chat_id, report)
        log_to_conversation(message_text, report)
        return

    if is_kodari_request:
        query = msg_strip[len(kodari_prefix):].strip() if msg_strip.startswith(kodari_prefix) else ""
        k_persona = load_kodari_persona()
        recent_history = get_recent_history()
        
        if "응급복구 승인" in query:
            prompt = f"[최근 대화 컨텍스트 (기억용)]\n{recent_history}\n\n" \
                     f"마스터의 지시:\n{query}\n\n" \
                     f"당신의 정본 페르소나(KODARI)에 빙의하여 응급복구 안내 모드를 가동하십시오.\n" \
                     f"주의: 텔레그램 내의 당신은 서버 명령을 직접 실행할 권한이 전혀 없는 '진단/복구 안내 전용' 에이전트입니다. " \
                     f"절대 자신이 직접 실행했다고 말하지 마십시오. 마스터가 직접 SSH에서 실행할 명령어를 제시하고 결과를 기다리십시오.\n" \
                     f"반드시 응답을 '마스터, [Gemini/Kodari Persona]입니다.'로 시작하십시오."
            send_telegram_message(token, chat_id, f"🛠️ *[Gemini/Kodari Persona]*\n\n응급복구 승인 확인. 복구 진단 모드를 가동합니다...")
        else:
            prompt = f"[최근 대화 컨텍스트 (기억용)]\n{recent_history}\n\n" \
                     f"마스터의 지시:\n{query}\n\n" \
                     f"당신의 정본 페르소나(KODARI)에 빙의하십시오.\n" \
                     f"주의: 텔레그램 내의 당신은 서버 명령을 직접 실행할 권한이 전혀 없는 '진단/복구 안내 전용' 에이전트입니다. " \
                     f"절대 자신이 서버에서 직접 실행했다고 말하거나 자동 실행을 시도하지 마십시오. 진단, 명령어 안내, 로그 해석, 복구 순서 제시만 수행하십시오.\n" \
                     f"반드시 응답을 '마스터, [Gemini/Kodari Persona]입니다.'로 시작하십시오."
            send_telegram_message(token, chat_id, f"🛠️ *[Gemini/Kodari Persona]*\n\n명령을 접수했습니다. 진단 및 분석을 시작합니다...")
            
        report = call_agent_model(k_persona, prompt, gemini_key, openai_key)
        send_telegram_message(token, chat_id, report)
        log_to_conversation(message_text, report)
        return

    if is_claude_request:
        query = msg_strip[len(claude_prefix):].strip() if msg_strip.startswith(claude_prefix) else ""
        c_persona = load_claude_persona()
        recent_history = get_recent_history()
        prompt = f"[최근 대화 컨텍스트 (기억용)]\n{recent_history}\n\n" \
                 f"마스터의 지시:\n{query}\n\n" \
                 f"당신의 정본 페르소나(CLAUDE)에 완벽히 빙의하여 대본 및 본문을 확장/작성하십시오.\n" \
                 f"주의: 사용자가 짧은 글을 요청한 경우 '정직 보고 5단계' 형식을 절대 붙이지 마십시오.\n" \
                 f"주의: 텔레그램 API 대리자이므로 본문 내에서 '마스터, 클로드입니다'라고 말하지 마십시오.\n" \
                 f"반드시 '마스터, [Gemini/Claude Persona]입니다.'로만 시작하십시오."
                 
        send_telegram_message(token, chat_id, f"📝 *[Gemini/Claude Persona]*\n\n명령을 접수했습니다. 본문 작성을 시작합니다...")
        
        report = call_agent_model(c_persona, prompt, gemini_key, openai_key)
        if not report:
            send_telegram_message(token, chat_id, "⚠️ [Gemini/Claude Persona] 최종 응답 생성 실패: API 통신 오류.")
            return
            
        send_telegram_message(token, chat_id, report)
        log_to_conversation(message_text, report)
        return
        
    if is_codex_request:
        query = msg_strip[len(codex_prefix):].strip() if msg_strip.startswith(codex_prefix) else ""
        
        if not query or any(kw in query for kw in ["핫이슈", "뉴스", "트랜드", "트렌드", "이슈"]):
            query = "최신 비즈니스 및 IT 핵심 기술 트렌드"
            
        send_telegram_message(token, chat_id, f"📊 *[수석 정보 수집관 코덱스]*\n\n코덱스 | '{query}' 뉴스 검색 중...")
        
        # 1. Scrape web results (Google News 1st, Tavily 2nd)
        search_context = ""
        search_query = extract_search_keywords(query, openai_key)
        if search_query != query:
            send_telegram_message(token, chat_id, f'🔑 키워드: {search_query}')
        res = google_news_search(search_query)
        if res:
            send_telegram_message(token, chat_id, "🔍 *[수석 정보 수집관 코덱스]*\n\n코덱스 | 구글뉴스RSS 수집 완료")
            for idx, r in enumerate(res[:6], 1):
                search_context += f"출처 {idx}: [{r['title']}] ({r['url']})\n내용 요약: {r['snippet']}\n\n"
        else:
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                send_telegram_message(token, chat_id, "🔍 *[수석 정보 수집관 코덱스]*\n\n코덱스 | Tavily 백업망 가동")
                res = tavily_search(search_query, tavily_key)
                if res:
                    for idx, r in enumerate(res[:6], 1):
                        search_context += f"출처 {idx}: [{r['title']}] ({r['url']})\n내용 요약: {r['snippet']}\n\n"
        
        if not search_context:
            send_telegram_message(token, chat_id, "⚠️ 검색 데이터 수집 실패: 해당 주제의 뉴스가 존재하지 않습니다. 할루시네이션(가짜 정보) 방지를 위해 조사를 즉각 중단합니다.")
            return
            
        # 2. Assemble prompt for Codex
        recent_history = get_recent_history()
        codex_prompt = f"[최근 대화 컨텍스트 (기억용)]\n{recent_history}\n\n" \
                       f"마스터께서 다음 주제에 대한 정밀 조사 및 뼈대 설계를 명령하셨습니다.\n" \
                       f"조사 주제: {query}\n\n" \
                       f"수집된 실시간 교차 검증용 원본 데이터:\n{search_context}\n" \
                       f"당신의 [Fact-Check Rules]를 엄격히 적용해 검증 상태를 분류하십시오.\n" \
                       f"반드시 '마스터, 코덱스입니다.'로 시작하는 마크다운 뼈대와 다음 지시를 작성해 보고하십시오. 감성이나 사설은 배제하십시오."
                       
        codex_actual_persona = load_codex_persona()
        report = call_agent_model(codex_actual_persona, codex_prompt, gemini_key, openai_key)
        
        if not report:
            send_telegram_message(token, chat_id, "⚠️ [수석 정보 수집관 코덱스] 코덱스 오류 — API 통신 실패")
            return
            
        approvals_dir = os.path.join(BRAIN_ROOT, "_company", "approvals")
        os.makedirs(approvals_dir, exist_ok=True)
        safe_query = re.sub(r'[\\/*?:"<>|]', "", query).replace(" ", "_")[:30]
        approval_file = os.path.join(approvals_dir, f"[대기상태]_{safe_query}.md")
        try:
            with open(approval_file, "w", encoding="utf-8") as f:
                f.write(report)
        except Exception as e:
            pass
                
        send_telegram_message(token, chat_id, report)
        log_to_conversation(message_text, report)
        return

    # 0.4 Market Monitor (Watchlist) Commands
    if "감시" in message_text and "주빵" in message_text:
        msg_clean = message_text.replace("주빵아", "").replace("주빵이", "").replace("주빵", "").strip()
        
        # Calculate absolute path for watchlist.csv
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            watchlist_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "..", "_company", "agents", "stock_expert", "watchlist.csv"))
        except NameError:
            watchlist_path = os.path.abspath(os.path.join(os.getcwd(), "_company", "agents", "stock_expert", "watchlist.csv"))
            
        import csv
        
        if "목록 보여줘" in msg_clean or "목록" in msg_clean:
            if not os.path.exists(watchlist_path):
                send_telegram_message(token, chat_id, "🥊 [주빵이] 마스터, 현재 등록된 감시 종목이 없습니다.")
                return
            
            lines = []
            with open(watchlist_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lines.append(f"- {row.get('name', 'UNKNOWN')} ({row.get('ticker', '')})")
            
            if lines:
                msg = "🥊 [주빵이] 마스터, 현재 감시 중인 종목 목록입니다:\n" + "\n".join(lines)
            else:
                msg = "🥊 [주빵이] 마스터, 현재 등록된 감시 종목이 없습니다."
            send_telegram_message(token, chat_id, msg)
            return
            
        elif "중지" in msg_clean or "해제" in msg_clean or "삭제" in msg_clean:
            target_name = msg_clean.replace("감시", "").replace("중지", "").replace("해제", "").replace("삭제", "").strip()
            if not target_name:
                send_telegram_message(token, chat_id, "🥊 [주빵이] 마스터, 감시를 중지할 종목명을 입력해 주십시오.")
                return
                
            if not os.path.exists(watchlist_path):
                send_telegram_message(token, chat_id, "🥊 [주빵이] 마스터, 감시 목록이 비어있습니다.")
                return
                
            tmp_path = watchlist_path + ".tmp"
            found = False
            with open(watchlist_path, "r", encoding="utf-8") as fin, open(tmp_path, "w", encoding="utf-8", newline="") as fout:
                reader = csv.DictReader(fin)
                writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
                writer.writeheader()
                for row in reader:
                    if row.get("name") == target_name:
                        found = True
                    else:
                        writer.writerow(row)
            
            if found:
                os.replace(tmp_path, watchlist_path)
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, '{target_name}' 감시를 중지했습니다.")
            else:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, '{target_name}' 종목은 감시 목록에 없습니다.")
            return
            
        elif "감시해" in msg_clean or "등록" in msg_clean or "추가" in msg_clean:
            parts = msg_clean.replace("감시해", "").replace("감시", "").replace("등록", "").replace("추가", "").strip().split()
            if len(parts) < 2:
                send_telegram_message(token, chat_id, "🥊 [주빵이] 마스터, 티커를 함께 입력해 주십시오. (예: 주빵아 서울반도체 046890.KQ 감시해)")
                return
                
            target_name = parts[0]
            target_ticker = parts[1]
            
            fieldnames = ["name", "ticker", "market", "alert_pct", "news_watch"]
            is_duplicate = False
            
            if os.path.exists(watchlist_path):
                with open(watchlist_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames:
                        fieldnames = reader.fieldnames
                    for row in reader:
                        if row.get("name") == target_name or row.get("ticker") == target_ticker:
                            is_duplicate = True
                            break
            
            if is_duplicate:
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, '{target_name}'({target_ticker}) 종목은 이미 감시 목록에 있습니다.")
                return
                
            tmp_path = watchlist_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8", newline="") as fout:
                writer = csv.DictWriter(fout, fieldnames=fieldnames)
                writer.writeheader()
                if os.path.exists(watchlist_path):
                    with open(watchlist_path, "r", encoding="utf-8") as fin:
                        reader = csv.DictReader(fin)
                        for row in reader:
                            writer.writerow(row)
                
                writer.writerow({
                    "name": target_name,
                    "ticker": target_ticker,
                    "market": "KOREA",
                    "alert_pct": "3",
                    "news_watch": "true"
                })
            
            os.replace(tmp_path, watchlist_path)
            send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, '{target_name}'({target_ticker}) 감시를 시작합니다.")
            return

    # 0.4.5 Check for standalone watchlist stock name (Watchlist Routing Guard)
    msg_clean_for_stock = message_text.strip()
    if " " not in msg_clean_for_stock:
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            watchlist_path_guard = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "..", "_company", "agents", "stock_expert", "watchlist.csv"))
        except NameError:
            watchlist_path_guard = os.path.abspath(os.path.join(os.getcwd(), "_company", "agents", "stock_expert", "watchlist.csv"))
            
        if os.path.exists(watchlist_path_guard):
            import csv
            is_watchlist_stock = False
            with open(watchlist_path_guard, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("name") == msg_clean_for_stock:
                        is_watchlist_stock = True
                        break
            
            if is_watchlist_stock:
                print(f"[watchlist-router] {msg_clean_for_stock} -> 주빵 분석 라우팅", flush=True)
                message_text = f"주빵아 {msg_clean_for_stock} 분석해"

    # 0.2 코덱스 명령어
    if message_text.strip().startswith('/codex') or message_text.strip().startswith('코덱스'):
        msg = message_text.strip()
        query = (msg[6:] if msg.startswith('/codex') else msg[3:]).strip() or '코스피 코스닥'
        handle_codex_command(query, token, chat_id)
        return

    # 0.3 미미 (글쓰기)
    if message_text.strip().startswith('미미'):
        q=message_text.strip()
        q=(q[3:] if q.startswith('미미야') else q[2:]).strip()
        if not q:
            send_telegram_message(token, chat_id, '✍️ 미미: 팩트를 같이 주세요. 예) 미미야 [내용]'); return
        handle_mimi_command(q, token, chat_id); return

    # 0.2 코덱스 명령어
    if message_text.strip().startswith('/codex'):
        query = message_text.strip()[7:].strip() or '코스피 코스닥'
        handle_codex_command(query, token, chat_id)
        return

    # 0.3 공시 전용: 종목명 + 공시 -> 임원/주요주주 변동 상세 해석
    if juppang_analyzer and '공시' in message_text and hasattr(juppang_analyzer, 'interpret_insider_disclosures'):
        _q = message_text.replace('공시','').replace('알려줘','').replace('보여줘','').replace('주빵아','').replace('주빵','').strip()
        _ci = juppang_analyzer.extract_intent(_q)
        _tk = _ci.get('ticker')
        _nm = _ci.get('matched_name') or _q
        if _tk:
            import os as _osc
            _dk = _osc.getenv('DART_API_KEY','')
            _ak = _osc.getenv('ANTHROPIC_API_KEY','')
            _rtk = _tk.replace('.KS','').replace('.KQ','')
            _cc = juppang_analyzer.CORP_CODE_MAP.get(_rtk,'')
            send_telegram_message(token, chat_id, f"\U0001F4D1 [주빵이] '{_nm}' 임원/주요주주 공시 변동 분석 중입니다...")
            _res = juppang_analyzer.interpret_insider_disclosures(_cc, _nm, _dk, _ak)
            send_telegram_message(token, chat_id, _res)
            return

    # 0.4 Auto-trigger: 종목명만 말해도 주빵이 자동 분석
    if juppang_analyzer and '주빵' not in message_text:
        _quick = juppang_analyzer.extract_intent(message_text)
        if _quick.get('route_type') in ('stock_only', 'stock_and_market') and _quick.get('ticker'):
            message_text = '주빵아 ' + message_text + ' 분석해'

    # 0.5 Check for Juppang command
    juppang_keywords = ["주빵", "주식", "분석해", "시세"]
    if any(kw in message_text for kw in juppang_keywords) and "주빵" in message_text:
        if juppang_analyzer:
            # 쿼리 정리
            query_clean = message_text.replace("주빵아", "").replace("주빵이", "").replace("주빵", "").strip()
            if not query_clean:
                send_telegram_message(token, chat_id, "🥊 [주빵이] 마스터, 분석할 종목명이나 시황을 말씀해 주십시오. (예: 주빵아 엔비디아 분석해)")
                return
                
            # 결정론적 라우터 호출
            intent = juppang_analyzer.extract_intent(query_clean)
            route_type = intent.get("route_type", "unknown")
            ticker_val = intent.get("ticker")
            extracted_name = intent.get("matched_name")
            is_ambiguous = intent.get("is_ambiguous")
            ambiguous_candidates = intent.get("ambiguous_candidates", [])
            has_market = intent.get("has_market_context")
            
            if is_ambiguous:
                candidates_str = ", ".join(ambiguous_candidates)
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, '{extracted_name}'에 해당하는 종목이 여러 개 발견되었습니다. ({candidates_str}) 정확한 종목명을 지정해 주십시오.")
                return
                
            if route_type == "unknown" or (not ticker_val and not has_market):
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, 종목명이나 시황 키워드를 식별하지 못했습니다. 사전(stock_master.csv)에 등록된 종목인지 확인해 주십시오.")
                return
                
            math_report = ""
            search_query_news = ""
            search_query_tavily = ""
            query_for_prompt = ""
            
            stock_data_injected = False
            market_data_injected = False
            stock_source = "UNKNOWN"
            kis_used = False
            fallback_used = False
            
            if route_type == "stock_and_market":
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, '{extracted_name}'({ticker_val}) 종목 실시간 데이터와 미장/한국장 시황을 종합 분석 중입니다. 잠시만 대기하십시오...")
                search_query_news = f"{extracted_name} 주가 OR {query_clean} 시황"
                search_query_tavily = f"{extracted_name} 및 시장 동향 원인 최신"
                query_for_prompt = f"'{extracted_name}({ticker_val})' 종목 분석 및 전반적 시황 브리핑"
                
                stock_res = juppang_analyzer.analyze_stock(ticker_val)
                stock_data = stock_res["report"]
                stock_source = stock_res.get("source", "UNKNOWN")
                kis_used = stock_res.get("kis_used", False)
                fallback_used = stock_res.get("fallback_used", False)
                dart_count = stock_res.get("dart_count", 0)
                
                us_data = juppang_analyzer.analyze_stock("^IXIC")["report"]
                kr_data = juppang_analyzer.analyze_stock("^KS11")["report"]
                
                math_report = f"■ [개별 종목 데이터]\n{stock_data}\n\n■ [미국장(나스닥) 데이터]\n{us_data}\n\n■ [한국장(코스피) 데이터]\n{kr_data}"
                stock_data_injected = True
                market_data_injected = True
                # DART해석 + 뉴스 + 최종판단
                if False:  # 훈수 OFF (비용 절감)
                    import os as _osj
                    _ak = _osj.getenv('ANTHROPIC_API_KEY', '')
                    _dk = _osj.getenv('DART_API_KEY', '')
                    _ni = _osj.getenv('NAVER_CLIENT_ID', '')
                    _ns = _osj.getenv('NAVER_CLIENT_SECRET', '')
                    _rtk = ticker_val.replace('.KS','').replace('.KQ','')
                    _cc = juppang_analyzer.CORP_CODE_MAP.get(_rtk, '')
                    _news = juppang_analyzer.get_naver_news(extracted_name, _ni, _ns) if _ni else []
                    _di = ""
                    _jd = juppang_analyzer.get_juppang_final_judgment(extracted_name, stock_data, _di, _news, _ak, openai_key)
                    send_telegram_message(token, chat_id, _jd)
                
            elif route_type == "stock_only":
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, '{extracted_name}'({ticker_val}) 종목의 실시간 데이터와 뉴스를 집중 분석 중입니다. 잠시만 대기하십시오...")
                search_query_news = f"{extracted_name} 특징주 OR {extracted_name} 주가"
                search_query_tavily = f"{extracted_name} 주가 급등락 악재 호재 원인 최신"
                query_for_prompt = f"'{extracted_name}({ticker_val})' 종목 분석"
                
                stock_res = juppang_analyzer.analyze_stock(ticker_val)
                stock_data = stock_res["report"]
                stock_source = stock_res.get("source", "UNKNOWN")
                kis_used = stock_res.get("kis_used", False)
                fallback_used = stock_res.get("fallback_used", False)
                dart_count = stock_res.get("dart_count", 0)
                
                math_report = f"■ [개별 종목 데이터]\n{stock_data}"
                stock_data_injected = True
                

                # DART해석 + 뉴스 + 최종판단 (stock_only)
                if False:  # 훈수 OFF (비용 절감)
                    import os as _osj2
                    _ak = _osj2.getenv('ANTHROPIC_API_KEY', '')
                    _dk = _osj2.getenv('DART_API_KEY', '')
                    _ni = _osj2.getenv('NAVER_CLIENT_ID', '')
                    _ns = _osj2.getenv('NAVER_CLIENT_SECRET', '')
                    _rtk = ticker_val.replace('.KS','').replace('.KQ','')
                    _cc = juppang_analyzer.CORP_CODE_MAP.get(_rtk, '')
                    _news = juppang_analyzer.get_naver_news(extracted_name, _ni, _ns) if _ni else []
                    _di = ""
                    _jd = juppang_analyzer.get_juppang_final_judgment(extracted_name, stock_data, _di, _news, _ak, openai_key)
                    send_telegram_message(token, chat_id, _jd)

            elif route_type == "market_only":
                send_telegram_message(token, chat_id, f"🥊 [주빵이] 마스터, 요청하신 시황에 대한 미국장/한국장 동향을 종합 분석 중입니다. 잠시만 대기하십시오...")
                search_query_news = f"{query_clean} 증시 시황 특징주"
                search_query_tavily = f"{query_clean} 시장 동향 원인 최신"
                query_for_prompt = f"'{query_clean}' 시장 동향 분석"
                
                us_data = juppang_analyzer.analyze_stock("^IXIC")["report"]
                kr_data = juppang_analyzer.analyze_stock("^KS11")["report"]
                math_report = f"■ [미국장(나스닥) 데이터]\n{us_data}\n\n■ [한국장(코스피) 데이터]\n{kr_data}"
                market_data_injected = True
            
            news_context = ""
            market_sources_count = 0
            news_titles = []
            news_urls = []
            
            # 1. Google News RSS for breaking news
            g_news = google_news_search(search_query_news)
            if g_news:
                news_context += "■ 구글 뉴스 실시간 특징주/이슈:\n"
                for idx, r in enumerate(g_news[:3], 1):
                    news_context += f"- [{r['title']}] ({r['url']})\n"
                    market_sources_count += 1
                    news_titles.append(r['title'])
                    news_urls.append(r['url'])
                news_context += "\n"

            # 2. Tavily Search for deep reasons
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                res = tavily_search(search_query_tavily, tavily_key)
                if res:
                    news_context += "■ Tavily 딥서치 원인/이슈 분석:\n"
                    for idx, r in enumerate(res[:3], 1):
                        news_context += f"뉴스 {idx}: [{r['title']}] ({r['url']})\n내용: {r['snippet']}\n\n"
                        market_sources_count += 1
                        news_titles.append(r['title'])
                        news_urls.append(r['url'])
            
            if not news_context:
                news_context = "수집된 뉴스 데이터가 없습니다. 원인 분석 시 '관련 뉴스 URL 미확인 → 구체 원인 미확인'으로 출력하십시오."

            # 라우팅 로그 기록 (LLM 주입 직전)
            log_dir = os.path.join(BRAIN_ROOT, "_company", "logs")
            os.makedirs(log_dir, exist_ok=True)
            routing_log_path = os.path.join(log_dir, "juppang_routing.log")
            try:
                with open(routing_log_path, "a", encoding="utf-8") as f:
                    log_data = {
                        "time": datetime.datetime.now().isoformat(),
                        "query": query_clean,
                        "route_type": route_type,
                        "matched_name": extracted_name,
                        "ticker": ticker_val,
                        "market_context": has_market,
                        "stock_data_injected": stock_data_injected,
                        "market_data_injected": market_data_injected,
                        "market_sources_count": market_sources_count,
                        "news_sources_count": len(news_urls),
                        "news_titles": news_titles,
                        "news_urls": news_urls,
                        "news_used_for_reasoning": len(news_urls) > 0,
                        "stock_data_source": stock_source,
                        "kis_used": kis_used,
                        "fallback_used": fallback_used,
                        "price_ok": stock_data_injected,
                        "market_ok": market_data_injected,
                        "news_count": len(news_urls),
                        "disclosure_count": dart_count if 'dart_count' in locals() else 0
                    }
                    f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
            except:
                pass

            time_header = juppang_analyzer.build_time_header()
            
            jp_persona = (
                load_juppang_persona()
                + f"\n\n[중요] 현재 시각은 주입된 {time_header} 값만 사용합니다. "
                "분석과 표현은 이 시각을 기준으로 삼고, 임의로 '09시 30분' 같은 예시/추정 시각을 생성하지 마십시오."
            )
            prompt = f"마스터가 {query_for_prompt}을 지시하셨습니다.\n\n" \
                     f"{time_header}\n\n" \
                     f"[1. 파이썬 기반 수학적 팩트 (현재가/등락률 포함)]\n{math_report}\n\n" \
                     f"[2. 최신 글로벌 뉴스 및 주가 변동 원인 데이터]\n{news_context}\n\n" \
                     f"당신의 완벽한 페르소나에 빙의하여 위 데이터를 종합 분석하십시오.\n" \
                     f"**[핵심 지시사항]**\n" \
                     f"1. 최상단에 반드시 {time_header}을 있는 그대로 표기하십시오.\n" \
                     f"2. 불필요한 감탄사나 추임새 없이, 5단계 구조(종목 상태, 직접 원인, 시장 원인, 연결 판단, 다음 확인 포인트)에 맞춰 핵심만 요약하십시오.\n" \
                     f"3. 뉴스는 반드시 위 [2. 최신 글로벌 뉴스] 목록에 제공된 기사만 인용하십시오. 절대 목록에 없는 뉴스를 상상하거나 가짜 URL을 생성하지 마십시오.\n" \
                     f"4. 직접 원인과 시장 원인 항목은 다음 형식을 엄격히 따르십시오:\n" \
                     f"   - 기사 제목\n" \
                     f"     출처: 언론사명\n" \
                     f"     URL: https://...\n" \
                     f"   만약 [2. 최신 글로벌 뉴스]에 해당 종목/시장에 대한 뉴스 URL이 없다면, 임의로 원인을 단정하지 말고 무조건 '관련 뉴스 URL 미확인 → 구체 원인 미확인'이라고만 기재하십시오.\n" \
                     f"5. 매수/매도/진입/보유 등 투자 방향 지시 및 임의의 확률 생성을 절대 금지하며, 오직 객관적 리스크 관점에서 서술하십시오.\n" \
                     f"6. KIS가 제공한 현재가, 등락률, 거래량은 절대 변경하지 말고 그대로 인용하십시오.\n" \
                     f"7. KIS_FAILED일 경우 현재가, 등락률, 거래량을 생성하지 마십시오.\n" \
                     f"8. '예시' 수치를 쓰지 마십시오.\n" \
                     f"9. 현재 시각은 주입된 KST 기준 시각만 사용하십시오.\n" \
                     f"10. 뉴스 URL이 없으면 원인을 단정하지 마십시오.\n" \
                     f"11. [1. 파이썬 기반 수학적 팩트] 안에 '📈 시장 지수' 섹션이 있으면 반드시 '시장 지수' 항목으로 KOSPI/KOSDAQ/NASDAQ/SOX/USD-KRW 수치를 그대로 출력하십시오.\n11-2. [1. 파이썬 기반 수학적 팩트] 안에 '공시:' 섹션이 존재하면 반드시 분석 결과에 공시 항목을 포함하십시오. dart.fss.or.kr URL은 그대로 인용하십시오.\n12. 단순히 주가 변동 수치(예: OO원 내림, OO원 마감)만 보도하는 기사는 직접 원인/시장 원인 근거로 사용 금지입니다. 해당 기사는 인용하지 마십시오.\n반드시 '마스터, 근거 기반 시장 분석관 주빵이입니다.'로 시작하십시오.\n" \
                     f"가장 마지막 줄에는 반드시 '본 분석은 투자 권유가 아니라 참고용 시장 분석입니다.'를 포함하십시오."
                     
            forbidden_words = ["확실하다", "무조건", "완벽한 기회", "매수하라", "매도하라", "즉시 진입"]
            final_report = None
            
            for attempt in range(2):
                report_cand = call_agent_model(jp_persona, prompt, gemini_key, openai_key)
                if not report_cand:
                    break
                    
                has_forbidden = False
                for word in forbidden_words:
                    if word in report_cand:
                        has_forbidden = True
                        break
                        
                if not has_forbidden:
                    final_report = report_cand
                    break
                    
                print(f"[!] 금지어 감지. 재시도 진행 중... (시도 {attempt+1})")
                
            if not final_report:
                final_report = "⚠️ 시장 요약 생성 중 금지어(매수/매도/확정적 표현)가 감지되어 출력을 차단했습니다. 객관적 지표를 다시 확인해 주십시오.\n\n" + math_report
                
            # 시세 출처 명시적 Append (중복 방지)
            append_text = ""
            if stock_source == "KIS":
                append_text = "\n\n시세 출처: 한국투자증권 API"
            elif stock_source == "KIS_FAILED":
                append_text = "\n\n시세 출처: KIS 조회 실패 (통신 또는 연동 오류)"
            elif stock_source == "YFINANCE":
                append_text = "\n\n시세 출처: Yahoo Finance"
                
            if append_text and "시세 출처:" not in final_report:
                final_report += append_text
                
            send_telegram_message(token, chat_id, final_report)
            log_to_conversation(message_text, final_report)
        else:
            send_telegram_message(token, chat_id, "⚠️ [주빵이 시스템 오류] juppang_analyzer 모듈을 불러올 수 없습니다.")
        return

    # 1. Check for Calendar command
    calendar_keywords = ["일정", "캘린더", "달력", "스케줄", "schedule", "calendar", "약속"]
    is_calendar_request = any(kw in message_text for kw in calendar_keywords)
    if is_calendar_request:
        if google_calendar_helper:
            send_telegram_message(token, chat_id, "📅 대표님, 연동된 구글 캘린더에서 실시간 일정을 조회하는 중입니다...")
            res = google_calendar_helper.get_today_events()
            if res["status"] == "success":
                events = res.get("events", [])
                recent_history = get_recent_history()
                prompt = f"[최근 대화 컨텍스트 (기억용)]\n{recent_history}\n\n" \
                         f"대표님께서 오늘 일정을 요청하셨습니다. 데이터:\n{json.dumps(events, ensure_ascii=False)}\n\n" \
                         f"대표님의 인지 부하를 줄이는 초프리미엄 캘린더 일정 브리핑을 영숙의 품격 있고 단정된 정식 비즈니스 어조로 작성하십시오."
                report = call_agent_model(persona, prompt, gemini_key, openai_key)
                send_telegram_message(token, chat_id, report)
                log_to_conversation(message_text, report)
            else:
                send_telegram_message(token, chat_id, res["message"])
        return

    # 2. Check for Search / Hot News command
    search_intent_keywords = ["검색", "찾아", "인터넷", "구글", "뉴스", "핫뉴스", "트렌드", "이슈", "실시간", "기사", "보도"]
    is_search_request = any(kw in message_text for kw in search_intent_keywords) or message_text.startswith("/")
    
    if is_search_request:
        query = message_text
        strip_suffixes = ["검색해줘", "검색해", "검색", "찾아줘", "찾아", "알려줘", "알려", "해줘"]
        for suffix in strip_suffixes:
            if query.endswith(suffix):
                query = query[:-len(suffix)].strip()
        query = query.strip().strip("/").strip()
        
        if not query:
            send_telegram_message(token, chat_id, "대표님, 검색하고 싶으신 구체적인 키워드를 말씀해 주십시오.")
            return
            
        is_news = any(kw in message_text for kw in ["뉴스", "핫뉴스", "기사", "보도"])
        prompt_prefix = "📰 코덱스 | 뉴스 검색 중..." if is_news else f"⚙️ 코덱스 | '{query}' 조사 중..."
        send_telegram_message(token, chat_id, prompt_prefix)
        
        search_context = ""
        
        import re as _re
        _GEN = {'핫뉴스','핫뉴스로','뉴스','뉴스로','속보','이슈','트렌드','실시간','오늘뉴스'}
        _bare = _re.sub(r'(오늘|지금|현재|요즘|최근|한국|국내|실시간|핫|속보|뉴스|기사|보도|이슈|트렌드|자)', '', query).strip()
        _is_generic = is_news and (query.replace(' ', '') in _GEN or _bare == '')
        search_query = '한국 경제 증시 금리 부동산 정책 환율' if _is_generic else query
        # If it's a news request, strictly use Google News RSS first
        if is_news:
            res = hot_market_news() if _is_generic else google_news_search(search_query)
            if res:
                for idx, r in enumerate(res[:5], 1):
                    search_context += f"기사 {idx}: [{r['title']}] ({r['url']})\n발행정보: {r['snippet']}\n\n"
        
        # If not news or if Google News returned 0, try Tavily
        if not search_context:
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                res = tavily_search(query, tavily_key)
                if res:
                    for idx, r in enumerate(res[:5], 1):
                        search_context += f"출처 {idx}: [{r['title']}] ({r['url']})\n내용: {r['snippet']}\n\n"
                    
        kst = datetime.timezone(datetime.timedelta(hours=9))
        current_kst = datetime.datetime.now(kst).strftime("%Y년 %m월 %d일 %H시 %M분 KST")
        anti_hallucination = "검색 결과나 데이터가 비어있으면 [주요 뉴스 요약] 같은 플레이스홀더를 채우지 말고 '실시간 검색 결과를 가져오지 못했습니다. 백엔드 점검이 필요합니다.'로 응답하라."
        search_report_rules = (
            f"기준 시각은 {current_kst}입니다. 사용자가 '29일'처럼 월/연도 없이 말하면 기준 시각의 월/연도를 적용했다고 명시하십시오.\n"
            "검색 결과는 반드시 출처 유형별로 구분하십시오: 언론 보도 / 정부 공식자료 / 선거 일정 / 기타.\n"
            "정부 공식자료라고 쓰려면 수집 데이터의 제목이나 URL에서 정부기관·공식 보도자료임이 확인되어야 합니다. 확인되지 않으면 '언론 보도'로만 표기하십시오.\n"
            "서로 다른 주제는 하나의 정책처럼 묶지 말고 '동일 날짜의 별개 이슈'로 분리하십시오.\n"
            "'핵심 의사결정', '최우선 의사결정', '정부가 시행한다' 같은 단정적 표현은 근거가 있을 때만 쓰십시오.\n"
            "검색 결과에 없는 날짜, 시행 내용, 수치, 출처를 만들지 마십시오.\n"
            "마지막에 '공식자료 추가 확인 필요' 여부를 한 줄로 표시하십시오."
        )
        
        # If both failed or returned 0 results, we STOP to prevent hallucination
        if not search_context:
            # We can rely on Gemini's built-in Google Search grounding instead!
            prompt = f"대표님께서 인터넷 실시간 조사를 지시하셨습니다.\n검색 주제: {query}\n" \
                     f"수집 데이터가 제공되지 않았으므로 기사·정부 발표·날짜를 생성하지 마십시오.\n" \
                     f"지침:\n{anti_hallucination}\n{search_report_rules}"
            report = call_agent_model(persona, prompt, gemini_key, openai_key)
        else:
            prompt = f"대표님께서 인터넷 조사를 지시하셨습니다.\n검색 주제: {query}\n" \
                     f"실시간 수집 데이터:\n{search_context}\n\n" \
                     f"위 데이터를 바탕으로 영숙의 말투(정중한 비즈니스체, 두괄식 요약)로 보고서를 작성하십시오.\n" \
                     f"절대 [링크1](#) 같은 가짜 플레이스홀더를 쓰지 말고, 수집 데이터에 있는 실제 출처 URL을 포함하십시오.\n" \
                     f"지침:\n{anti_hallucination}\n{search_report_rules}"
            report = call_agent_model(persona, prompt, gemini_key, openai_key)
            
        send_telegram_message(token, chat_id, report, add_timestamp=True)
        log_to_conversation(message_text, report)
        return

    # 3. General Conversation
    recent_history = get_recent_history()
    prompt = f"[최근 대화 컨텍스트 (기억용)]\n{recent_history}\n\n" \
             f"대표님께서 다음과 같이 말씀하셨습니다: \"{message_text}\"\n" \
             f"영숙의 페르소나 매뉴얼에 따르되, 확인되지 않은 날짜, 수치, 시행 내용, 출처를 만들지 마십시오.\n" \
             f"실제 출처 URL, KIS API, Google News 결과가 프롬프트에 제공되지 않은 경우 '실시간 조회'라고 말하지 마십시오.\n" \
             f"출처 없는 분석은 반드시 '(일반 분석 · 실시간 출처 없음)'이라고 구분하십시오.\n" \
             f"질문 대상이 불명확하면 답을 단정하지 말고 필요한 확인 질문만 하십시오.\n" \
             f"예시 날짜를 임의로 만들지 마십시오. 2023년, 2024년, 2025년 같은 구체 연도 예시를 절대 쓰지 마십시오.\n" \
             f"날짜가 불명확하면 '원하시는 연도와 월을 알려주십시오'라고만 말하고 예시 날짜를 붙이지 마십시오.\n" \
             f"'[구체적인 시행 내용 기재 필요]', '[출처 입력]', '[날짜 입력]' 같은 내부 템플릿 문구를 절대 출력하지 마십시오."
    reply = call_agent_model(persona, prompt, gemini_key, openai_key)
    if not reply:
        reply = f"대표님, 지시하신 사항을 확인하였습니다."
                
    send_telegram_message(token, chat_id, reply, add_timestamp=True)
    log_to_conversation(message_text, reply)

def main():
    print("==================================================")
    print("📱 영숙 텔레그램 리스너 기동 (Google News RSS & Tavily 적용)")
    print("==================================================")
    
    cfg = load_config()
    token = cfg.get("TELEGRAM_BOT_TOKEN")
    chat_id = cfg.get("TELEGRAM_CHAT_ID")
    gemini_key = load_gemini_api_key()
    openai_key = load_openai_api_key()
    persona = load_persona()
    
    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID 설정이 누락되었습니다.")
        sys.exit(1)
        
    startup_msg = "📡 수석 비서 영숙 가동 완료"
    send_telegram_message(token, chat_id, startup_msg)
    
    last_update_id = get_last_update_id()
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=30"
            if last_update_id > 0:
                url += f"&offset={last_update_id + 1}"
                
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=35) as res:
                data = json.loads(res.read().decode('utf-8'))
                results = data.get("result", [])
                
                for update in results:
                    update_id = update.get("update_id")
                    last_update_id = max(last_update_id, update_id)
                    save_last_update_id(last_update_id)
                    
                    message = update.get("message")
                    if not message:
                        continue
                    if message.get("from", {}).get("is_bot", False):
                        continue
                        
                    sender_id = message.get("chat", {}).get("id")
                    print("[DEBUG chat_id] 수신 chat_id=" + str(sender_id) + " text=" + (message.get("text") or "")[:20], flush=True)
                    if str(sender_id) != str(chat_id) and str(sender_id) not in {"-5012814805"}:
                        chat_type = message.get("chat", {}).get("type", "unknown")
                        count = increment_attempt_counter(sender_id)
                        log_security_event(sender_id, chat_type, count)
                        if count >= 5:
                            notify_master_security_alert(sender_id, count, chat_type, token, chat_id)
                        continue
                        
                    message_text = message.get("text")
                    if not message_text:
                        continue
                        
                    try:
                        import room_pipeline as _rp
                        _handled = _rp.room_dispatch(token, sender_id, message_text, gemini_key, openai_key, persona)
                    except Exception as _rpe:
                        _handled = False
                        print('[room_pipeline] error:', _rpe, flush=True)
                    if not _handled:
                        process_message(token, sender_id, message_text, gemini_key, openai_key, persona)
                    
        except KeyboardInterrupt:
            break
        except Exception as e:
            import traceback; traceback.print_exc()
            time.sleep(5)



def handle_keyword_command(query, token, chat_id):
    import urllib.request, urllib.parse, json
    if not query:
        send_telegram_message(token, chat_id, '🔑 키워드: 주제를 같이 주세요. 예) 키워드 삼성전자 실적'); return
    def _naver(q):
        url = 'https://ac.search.naver.com/nx/ac?q=' + urllib.parse.quote(q) + '&st=100&r_format=json&r_enc=UTF-8&q_enc=UTF-8&frm=nv'
        rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.naver.com/'})
        with urllib.request.urlopen(rq, timeout=10) as r:
            d = json.loads(r.read().decode('utf-8'))
        out = []
        for grp in d.get('items', []):
            for it in grp:
                if isinstance(it, list) and it and isinstance(it[0], str):
                    out.append(it[0].strip())
        return out
    def _google(q):
        url = 'http://suggestqueries.google.com/complete/search?client=firefox&hl=ko&q=' + urllib.parse.quote(q)
        rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(rq, timeout=10) as r:
            d = json.loads(r.read().decode('utf-8'))
        return [s for s in d[1] if isinstance(s, str)] if len(d) > 1 else []
    src_name = '네이버'
    try:
        cands = _naver(query)
    except Exception:
        cands = []
    if not cands:
        try:
            cands = _google(query); src_name = '구글'
        except Exception:
            cands = []
    seen = set(); uniq = []
    for c in cands:
        if c and c not in seen:
            seen.add(c); uniq.append(c)
    if not uniq:
        send_telegram_message(token, chat_id, "🔑 '" + query + "' 자동완성 결과 없음. 주제를 바꿔보세요."); return
    lines = ["🔑 황금 키워드 후보 (" + src_name + " 실검색어) - '" + query + "'", '-'*20]
    for i, k in enumerate(uniq[:15], 1):
        lines.append(str(i) + ". " + k)
    lines.append("")
    send_telegram_message(token, chat_id, chr(10).join(lines))
    # === 발굴 -> 데스크(골드키워드) -> 미미(작성) 자동 연결 ===
    import re as _re
    try:
        _full = open('/home/master/comodo-ingong/.claude/agents/desk.md', encoding='utf-8').read()
        _gi = _full.find('[골드키워드 선택 규칙]')
        desk_rule = _full[_gi:] if _gi != -1 else _full
    except Exception:
        desk_rule = '후보 키워드 중 1개를 "골드키워드: [키워드]" 형식으로 골라라.'
    send_telegram_message(token, chat_id, '🗞️ 데스크가 골드키워드 고르는 중...')
    try:
        desk_out = (call_agent_model(desk_rule, '후보:' + chr(10) + chr(10).join(uniq[:15]), load_gemini_api_key(), load_openai_api_key()) or '').strip()
    except Exception as e:
        send_telegram_message(token, chat_id, '데스크 오류: ' + str(e)); return
    _m = _re.search(r'골드키워드\s*[:：]\s*(.+)', desk_out)
    gold = _m.group(1).strip() if _m else (uniq[0] if uniq else '')
    for _sep in [' (', ' —', ' - ', ' |']:
        if _sep in gold:
            gold = gold.split(_sep)[0].strip()
    gold = gold.strip('[]').strip()
    if not gold:
        send_telegram_message(token, chat_id, '데스크가 키워드를 못 골랐습니다.'); return
    send_telegram_message(token, chat_id, '✅ 데스크 선택: ' + gold + (chr(10) + desk_out if desk_out else ''))
    handle_mimi_command(gold + ' 뉴스', token, chat_id)


def handle_desk_command(query, token, chat_id):
    if not query:
        send_telegram_message(token, chat_id, '🗞️ 데스크: 헤드라인 목록을 같이 주세요. 예) 데스크 [뉴스 제목들]'); return
    try:
        desk_md = open('/home/master/comodo-ingong/.claude/agents/desk.md', encoding='utf-8').read()
    except Exception:
        desk_md = '너는 한국 뉴스 사이트 편집장이다. 헤드라인에서 글로 쓸 글감을 강추/신중/제외로 분류하라. 연예 먼저, 잡동사니(운세·날씨·지역행사) 컷.'
    send_telegram_message(token, chat_id, '🗞️ 데스크 | 글감 고르는 중...')
    try:
        out = (call_agent_model(desk_md, query, load_gemini_api_key(), load_openai_api_key()) or '').strip()
    except Exception as e:
        send_telegram_message(token, chat_id, f'데스크 오류: {e}'); return
    if not out:
        send_telegram_message(token, chat_id, '📭 데스크: 결과가 비었습니다. 잠시 후 재시도.'); return
    body = '🗞️ 데스크 글감 선별\n' + '-'*20 + '\n' + out
    for _i in range(0, len(body), 3500):
        send_telegram_message(token, chat_id, body[_i:_i+3500])


def handle_codex_command(query, token, chat_id):
    import html as _h, re as _re, json, urllib.request, urllib.parse
    nid = os.getenv('NAVER_CLIENT_ID')
    nsc = os.getenv('NAVER_CLIENT_SECRET')
    oai = os.getenv('OPENAI_API_KEY')
    def clean(t):
        return _re.sub(r'<[^>]+>', '', _h.unescape(t or '')).strip()
    sys_msg = (
        '한국주식 전문 뉴스 분석관. JSON만 응답:'
        'score(1-10),direction(긍정/부정/중립),stocks([종목]),summary(50자),reason(영향근거).'
        'score기준:9-10=실적/M&A,7-8=목표가/규제,5-6=업황,1-4=무관.'
        '시장:코스피최고치,AI반도체,HBM4,젠슨황방한,삼성전자노조'
    )
    try:
        q = urllib.parse.quote(query)
        req = urllib.request.Request(
            f'https://openapi.naver.com/v1/search/news.json?query={q}&display=5&sort=date',
            headers={'X-Naver-Client-Id': nid, 'X-Naver-Client-Secret': nsc})
        with urllib.request.urlopen(req, timeout=10) as r:
            items = json.loads(r.read()).get('items', [])
    except Exception as e:
        send_telegram_message(token, chat_id, f'코덱스 오류: {e}'); return
    if not items:
        send_telegram_message(token, chat_id, f"📭 '{query}' 뉴스 없음"); return
    results = []
    for item in items[:5]:
        title = clean(item.get('title', ''))
        desc  = clean(item.get('description', ''))
        link  = item.get('originallink') or item.get('link', '')
        try:
            data = json.dumps({
                'model': 'gpt-4o-mini', 'max_tokens': 150,
                'messages': [
                    {'role': 'system', 'content': sys_msg},
                    {'role': 'user',   'content': f'제목:{title}\n요약:{desc}'}
                ]
            }).encode()
            req2 = urllib.request.Request(
                'https://api.openai.com/v1/chat/completions', data=data,
                headers={'Authorization': f'Bearer {oai}', 'Content-Type': 'application/json'})
            with urllib.request.urlopen(req2, timeout=15) as r:
                raw = json.loads(r.read())['choices'][0]['message']['content']
                res = json.loads(_re.sub(r'```json|```', '', raw).strip())
            if int(res.get('score', 0)) >= 6:
                d      = res.get('direction', '중립')
                icon   = '📈' if d == '긍정' else '📉' if d == '부정' else '📊'
                stks   = ' '.join(res.get('stocks', []))
                score  = res.get('score', '?')
                reason = res.get('reason', '')
                msg    = f'📰 [{score}/10] {icon} {d}' + (f' | {stks}' if stks else '')
                msg   += f'\n{res.get("summary", title)}'
                if reason: msg += f'\n💡 {reason}'
                msg   += f'\n🔗 {link}'
                results.append(msg)
        except:
            pass
    if results:
        send_telegram_message(token, chat_id,
            f"📰 코덱스 뉴스 — '{query}'\n{'─'*20}\n" + '\n\n'.join(results[:3]))
    else:
        send_telegram_message(token, chat_id, f"📭 '{query}' — 관련 뉴스 없음")




def handle_drama_command(query, token, chat_id, blog_write=False):
    """드라마방 전용: 코덱스 정보수집 → 미미 작성 파이프라인"""
    load_dotenv(dotenv_path=ENV_PATH)
    gemini_key = load_gemini_api_key()
    openai_key = load_openai_api_key()

    send_telegram_message(token, chat_id, f"🎬 코덱스 | \'{query}\' 드라마/영화 정보 수집 중...")

    search_query = extract_search_keywords(query + " 드라마 영화", openai_key)
    res = google_news_search(search_query)
    if not res:
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            res = tavily_search(search_query, tavily_key)
    if not res:
        send_telegram_message(token, chat_id, f"📭 \'{query}\' 관련 정보를 찾지 못했어요."); return

    facts = "\n".join("- " + r["title"] + " (" + r.get("snippet","")[:80] + ")" for r in res[:8])
    send_telegram_message(token, chat_id, f"✅ 코덱스 | {len(res[:8])}건 수집 완료 → 미미에게 전달")

    handle_mimi_command(f"드라마 {query}", token, chat_id, blog_write=blog_write, prefetched_facts=facts)

def handle_mimi_command(query, token, chat_id, blog_write=False, prefetched_facts=None):
    import json, re, urllib.request
    key = os.getenv('ANTHROPIC_API_KEY')
    if any(k in query for k in ['드라마', '영화', '신작', '시즌', '출연', '배우', '줄거리', '리뷰']):
        topic = re.sub(r'^미미야?\s*', '', query).strip()
        items = google_news_search(topic + ' 드라마 영화')
        if not items:
            send_telegram_message(token, chat_id, f"📭 미미: '{topic}' 관련 정보를 찾지 못했어요."); return
        facts = '\n'.join(f"- {it['title']} ({it.get('snippet', '')})" for it in items)
        if blog_write:
            user_content = (f'아래는 수집된 실제 뉴스/정보다. 이 팩트만 근거로 드라마/영화 블로그 포스팅을 작성하라.\n'
                            f'조건: ①최소 1000자 이상 ②H2 소제목 4개 이상 ③도입(APB훅)-작품소개-관전포인트-기대이유-마무리 구성 ④없는 정보는 [확인 필요]\n\n'
                            f'[정보]\n{facts}\n\n[주제] {topic}')
        else:
            user_content = (f'아래는 수집된 실제 뉴스/정보다. 이 내용만 근거로 답해라. 없는 내용은 [확인 필요]로 표시.\n\n'
                            f'[정보]\n{facts}\n\n[요청] {topic}에 대해 알려줘')
    elif any(k in query for k in ['뉴스', '핫뉴스', '기사', '보도', '이슈', '트렌드', '속보']):
        topic = re.sub(r'(블로그|글|기사|내용|으로|로|관련)?\s*(써\s?줘|써|작성\w*|정리\w*|만들어\s?줘|해\s?줘|부탁\w*)\s*$', '', query)
        topic = re.sub(r'^(오늘|지금|요즘|최근)\s*', '', topic).strip()
        if topic in ('', '핫뉴스', '핫뉴스로', '뉴스', '뉴스로', '이슈', '트렌드', '실시간'):
            topic = '속보'
        items = google_news_search(topic)
        if not items:
            send_telegram_message(token, chat_id, f"📭 미미: '{topic}' 최근 뉴스를 못 찾았어요. 주제를 더 구체적으로 주세요."); return
        facts = '\n'.join(f"- {it['title']} ({it.get('snippet', '')})" for it in items)
        user_content = ('아래는 오늘 수집된 실제 뉴스 헤드라인이다. 이 사실만 근거로 글을 써라. '
                        '헤드라인에 없는 구체 수치/세부는 지어내지 말고 [확인 필요]로 표시한다.\n\n'
                        f'[뉴스 헤드라인]\n{facts}\n\n[요청] {query}')
    else:
        user_content = f'[팩트]\n{query}'
    sys_msg = ('너는 한국어 글쓰기 담당 "미미"다. 주어진 팩트만 근거로 쓴다. '
               '없는 수치/날짜/인용/출처는 만들지 않고, 빠지면 [확인 필요]로 표시한다. 제목 + 본문으로 출력.')
    try:
        _pt=open('/home/master/comodo-ingong/personas/mimi_persona.md',encoding='utf-8').read()
        _c=_pt.find('## 3.')
        _pt=(_pt[:_c] if _c!=-1 else _pt).strip()
        if _pt: sys_msg=_pt
    except Exception: pass
    try:
        draft = (call_agent_model(sys_msg, user_content, load_gemini_api_key(), load_openai_api_key()) or '').strip()
    except Exception as e:
        send_telegram_message(token, chat_id, f'미미 오류: {e}'); return
    if not draft:
        send_telegram_message(token, chat_id, '📭 미미: 작성된 글이 없습니다'); return
    body = '✍️ 미미 초안 (클로드)\n' + '─'*20 + '\n' + draft
    for i in range(0, len(body), 3500):
        send_telegram_message(token, chat_id, body[i:i+3500])
    # === 워드프레스 임시저장(draft) ===
    if not blog_write:
        return
    try:
        import base64 as _b64
        _raw = draft.split('\n')
        _title = '미미 초안'; _bs = 0
        for _i2, _l in enumerate(_raw):
            if _l.strip().startswith('#'):
                _s = _l.strip().lstrip('#').strip()
                if _s and re.sub('[^\uAC00-\uD7A3a-zA-Z0-9\s]','',_s).strip():
                    _title = _s; _bs = _i2 + 1; break
        if _title == '미미 초안':
            _title = (call_agent_model('다음 블로그 글의 제목을 20자 이내 한국어로 한 줄만 출력하라.', draft[:500], load_gemini_api_key(), load_openai_api_key()) or '미미 초안').strip().split('\n')[0][:60]
        _rest = '\n'.join(_raw[_bs:]).strip()
        _paras = [p.strip() for p in _rest.split('\n\n') if p.strip()]
        _html = ''.join('<p>' + p.replace('\n', '<br>') + '</p>' for p in _paras)
        if not _html:
            _html = '<p>' + _rest.replace('\n', '<br>') + '</p>'
        _wp_url = os.getenv('WP_URL'); _wp_user = os.getenv('WP_USERNAME'); _wp_pw = os.getenv('WP_APP_PASSWORD')
        _auth = _b64.b64encode(f'{_wp_user}:{_wp_pw}'.encode()).decode()
        _fm = None
        try:
            import sys as _sys2, time as _tm2
            _root2 = '/home/master/comodo-ingong'
            if _root2 not in _sys2.path:
                _sys2.path.insert(0, _root2)
            from luna_flow_engine import generate_image as _gen
            _ipsys = 'Convert the Korean topic into ONE concise English image prompt for a clean photorealistic editorial blog thumbnail. No text, no letters, no logos in the image. Output only the prompt.'
            _iprompt = (call_agent_model(_ipsys, query, load_gemini_api_key(), load_openai_api_key()) or '').strip() or query
            _imgpath = '/tmp/luna_' + str(int(_tm2.time())) + '.png'
            _gen(_iprompt, _imgpath, '16:9')
            with open(_imgpath, 'rb') as _imf:
                _imgbytes = _imf.read()
            _mreq = urllib.request.Request(_wp_url + '/wp-json/wp/v2/media', data=_imgbytes, headers={'Authorization': 'Basic ' + _auth, 'Content-Type': 'image/png', 'Content-Disposition': 'attachment; filename=\"thumb.png\"'})
            with urllib.request.urlopen(_mreq, timeout=90) as _mr:
                _mres = json.loads(_mr.read())
            _fm = _mres.get('id')
            _murl = _mres.get('source_url', '')
            if _murl:
                _html = '<figure><img src=\"' + _murl + '\" alt=\"' + _title + '\"/></figure>' + _html
        except Exception as _ie:
            send_telegram_message(token, chat_id, '⚠️ 루나 이미지 실패(글은 계속 저장): ' + str(_ie))
        _post = {'title': _title, 'content': _html, 'status': 'draft'}
        if _fm:
            _post['featured_media'] = _fm
        _pd = json.dumps(_post).encode()
        _wreq = urllib.request.Request(_wp_url + '/wp-json/wp/v2/posts', data=_pd,
            headers={'Authorization': 'Basic ' + _auth, 'Content-Type': 'application/json'})
        with urllib.request.urlopen(_wreq, timeout=20) as _wr:
            _wres = json.loads(_wr.read())
        _link = _wres.get('link', '')
        send_telegram_message(token, chat_id, '📝 워드프레스 임시저장 완료\n제목: ' + _title + '\n' + _link)
    except Exception as _e:
        send_telegram_message(token, chat_id, '⚠️ 워드프레스 임시저장 실패: ' + str(_e))

if __name__ == "__main__":
    main()
