import telebot, requests, os, json, re

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
BH_KEY = os.environ.get("BH_KEY", "")
LARP_KEY = os.environ.get("LARP_KEY", "")
DEP_ID = os.environ.get("DEP_ID", "")

BASE = "https://bot-hosting.net/api/v1"
H = {"Authorization": f"Bearer {BH_KEY}", "Content-Type": "application/json"}

bot = telebot.TeleBot(BOT_TOKEN)

# ─── AI Agent: يخطط وينفذ ───
def ai_plan(text):
    """AI يفهم الطلب ويحدد الخطوات"""
    prompt = f"""أنت TAKER — مدير سيرفرات Bot-Hosting ذكي.
المستخدم قال: "{text}"

حدد العملية من:
- list_servers: عرض السيرفرات
- server_info: معلومات سيرفر
- resources: موارد (CPU/RAM)
- logs: السجلات
- start / stop / restart: تشغيل/إيقاف/إعادة
- list_files: عرض الملفات
- read_file: قراءة ملف (يحتاج path)
- write_file: كتابة ملف (يحتاج path, content)
- delete_file: حذف ملف (يحتاج path)
- chat: رد عادي

رد بـ JSON فقط:
{{"action": "...", "path": "...", "content": "..."}}
"""
    try:
        r = requests.post("https://larprouter.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {LARP_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300}, timeout=30)
        d = r.json()
        c = d["choices"][0]["message"].get("content") or d["choices"][0]["message"].get("reasoning_content", "")
        m = re.search(r'\{.*\}', c, re.DOTALL)
        if m: return json.loads(m.group())
    except Exception as e:
        print(f"⚠️ AI: {e}")
    return {"action": "chat"}

# ─── Bot-Hosting API ───
def get_servers():
    try:
        r = requests.get(f"{BASE}/deployments", headers=H, timeout=15)
        return r.json().get("deployments", [])
    except: return []

def get_resources(dep_id):
    try:
        r = requests.get(f"{BASE}/deployments/{dep_id}/resources", headers=H, timeout=15)
        return r.json()
    except: return {}

def get_logs(dep_id):
    try:
        r = requests.get(f"{BASE}/deployments/{dep_id}/logs?size=30", headers=H, timeout=15)
        return r.json().get("lines", [])
    except: return []

def power(dep_id, action):
    try:
        return requests.post(f"{BASE}/deployments/{dep_id}/power", headers=H, json={"action": action}, timeout=15).status_code == 200
    except: return False

def list_files(dep_id, path="/"):
    try:
        r = requests.get(f"{BASE}/deployments/{dep_id}/files?path={path}", headers=H, timeout=15)
        return r.json()
    except: return {}

def read_file(dep_id, path):
    try:
        r = requests.get(f"{BASE}/deployments/{dep_id}/files/content?path={path}", headers=H, timeout=15)
        return r.json()
    except: return {}

def write_file(dep_id, path, content):
    try:
        return requests.put(f"{BASE}/deployments/{dep_id}/files/content", headers=H,
                            json={"path": path, "content": content}, timeout=15).status_code
    except: return 0

def delete_file(dep_id, path):
    try:
        return requests.delete(f"{BASE}/deployments/{dep_id}/files?path={path}", headers=H, timeout=15).status_code
    except: return 0

def ai_chat(text):
    try:
        r = requests.post("https://larprouter.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {LARP_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": text}], "max_tokens": 2000}, timeout=45)
        d = r.json()
        return d["choices"][0]["message"].get("content") or d["choices"][0]["message"].get("reasoning_content", "")
    except Exception as e:
        return f"❌ {e}"

# ─── المعالج ───
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def handle(msg):
    bot.send_chat_action(msg.chat.id, 'typing')
    plan = ai_plan(msg.text)
    action = plan.get("action", "chat")
    path = plan.get("path", "")
    content = plan.get("content", "")

    print(f"🎯 Action: {action} | Path: {path}")

    try:
        if action == "list_servers":
            servers = get_servers()
            if not servers:
                return bot.reply_to(msg, "📭 مفيش سيرفرات")
            reply = "🖥 <b>سيرفراتك:</b>\n\n"
            for s in servers:
                reply += f"• <b>{s.get('name')}</b>\n  الحالة: {s.get('state')}\n  Runtime: {s.get('runtime')}\n  ID: <code>{s.get('id')}</code>\n  الرابط: {s.get('domains',{}).get('url','-')}\n\n"
            bot.reply_to(msg, reply, parse_mode="HTML")

        elif action == "resources":
            res = get_resources(DEP_ID)
            cpu = res.get("cpu", {}).get("usedPercent", 0)
            ram = res.get("memory", {}).get("usedBytes", 0) / 1024 / 1024
            bot.reply_to(msg, f"📊 <b>موارد السيرفر</b>\n\nCPU: {cpu}%\nRAM: {ram:.1f} MB\nالحالة: {res.get('state')}")

        elif action == "logs":
            logs = get_logs(DEP_ID)
            bot.reply_to(msg, f"📜 <b>آخر السجلات:</b>\n<pre>{chr(10).join(logs[-20:])}</pre>", parse_mode="HTML")

        elif action == "start":
            power(DEP_ID, "start")
            bot.reply_to(msg, "▶️ تم إرسال أمر التشغيل")

        elif action == "stop":
            power(DEP_ID, "stop")
            bot.reply_to(msg, "⏹ تم إرسال أمر الإيقاف")

        elif action == "restart":
            power(DEP_ID, "restart")
            bot.reply_to(msg, "🔄 تم إرسال أمر إعادة التشغيل")

        elif action == "list_files":
            files = list_files(DEP_ID, path or "/")
            bot.reply_to(msg, f"📁 <pre>{json.dumps(files, indent=2, ensure_ascii=False)[:3500]}</pre>", parse_mode="HTML")

        elif action == "read_file":
            if not path:
                return bot.reply_to(msg, "❌ محتاج مسار الملف")
            c = read_file(DEP_ID, path)
            bot.reply_to(msg, f"📄 <pre>{json.dumps(c, indent=2, ensure_ascii=False)[:3500]}</pre>", parse_mode="HTML")

        elif action == "write_file":
            if not path:
                return bot.reply_to(msg, "❌ محتاج مسار الملف")
            code = write_file(DEP_ID, path, content)
            bot.reply_to(msg, f"✅ تم الحفظ (كود: {code})")

        elif action == "delete_file":
            if not path:
                return bot.reply_to(msg, "❌ محتاج مسار الملف")
            code = delete_file(DEP_ID, path)
            bot.reply_to(msg, f"🗑 تم الحذف (كود: {code})")

        else:
            bot.reply_to(msg, ai_chat(msg.text))

    except Exception as e:
        bot.reply_to(msg, f"❌ خطأ: {e}")

print("🤖 TAKER Hosting Agent شغال")
bot.infinity_polling()
