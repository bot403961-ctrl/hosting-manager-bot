import telebot, requests, os, json

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
BH_KEY = os.environ.get("BH_KEY", "")
LARP_KEY = os.environ.get("LARP_KEY", "")
DEP_ID = os.environ.get("DEP_ID", "")

BASE = "https://bot-hosting.net/api/v1"
H = {"Authorization": f"Bearer {BH_KEY}", "Content-Type": "application/json"}

bot = telebot.TeleBot(BOT_TOKEN)

# ─── Bot-Hosting API ───
def get_servers():
    try:
        r = requests.get(f"{BASE}/deployments", headers=H, timeout=15)
        return r.json().get("deployments", [])
    except Exception as e:
        return {"error": str(e)}

def get_resources(dep_id):
    try:
        r = requests.get(f"{BASE}/deployments/{dep_id}/resources", headers=H, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

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
    except Exception as e:
        return {"error": str(e)}

def read_file(dep_id, path):
    try:
        r = requests.get(f"{BASE}/deployments/{dep_id}/files/content?path={path}", headers=H, timeout=15)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

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
    text = msg.text.strip()
    low = text.lower()
    bot.send_chat_action(msg.chat.id, 'typing')

    try:
        # 1. السيرفرات
        if any(k in low for k in ["سيرفر", "servers", "الخوادم"]):
            servers = get_servers()
            if isinstance(servers, dict) and "error" in servers:
                return bot.reply_to(msg, f"❌ {servers['error']}")
            if not servers:
                return bot.reply_to(msg, "📭 مفيش سيرفرات")
            reply = "🖥 <b>سيرفراتك:</b>\n\n"
            for s in servers:
                reply += f"• <b>{s.get('name')}</b>\n  الحالة: {s.get('state')}\n  Runtime: {s.get('runtime')}\n  ID: <code>{s.get('id')}</code>\n\n"
            return bot.reply_to(msg, reply, parse_mode="HTML")

        # 2. الموارد
        if any(k in low for k in ["موارد", "cpu", "ram", "resources"]):
            res = get_resources(DEP_ID)
            cpu = res.get("cpu", {}).get("usedPercent", 0)
            ram = res.get("memory", {}).get("usedBytes", 0) / 1024 / 1024
            return bot.reply_to(msg, f"📊 <b>الموارد:</b>\nCPU: {cpu}%\nRAM: {ram:.1f} MB\nالحالة: {res.get('state')}")

        # 3. السجلات
        if any(k in low for k in ["سجلات", "لوج", "logs"]):
            logs = get_logs(DEP_ID)
            return bot.reply_to(msg, f"📜 <pre>{chr(10).join(logs[-20:])}</pre>", parse_mode="HTML")

        # 4. تشغيل
        if any(k in low for k in ["شغل", "start", "تشغيل"]):
            power(DEP_ID, "start")
            return bot.reply_to(msg, "▶️ تم إرسال أمر التشغيل")

        # 5. إيقاف
        if any(k in low for k in ["اوقف", "وقف", "stop"]):
            power(DEP_ID, "stop")
            return bot.reply_to(msg, "⏹ تم إرسال أمر الإيقاف")

        # 6. إعادة تشغيل
        if any(k in low for k in ["ريستارت", "restart", "أعد"]):
            power(DEP_ID, "restart")
            return bot.reply_to(msg, "🔄 تم إرسال أمر إعادة التشغيل")

        # 7. الملفات
        if any(k in low for k in ["ملفات", "files", "ملف"]):
            files = list_files(DEP_ID, "/")
            return bot.reply_to(msg, f"📁 <pre>{json.dumps(files, indent=2, ensure_ascii=False)[:3500]}</pre>", parse_mode="HTML")

        # 8. أي حاجة تانية → AI
        bot.reply_to(msg, ai_chat(text))

    except Exception as e:
        bot.reply_to(msg, f"❌ خطأ: {e}")

print("🤖 TAKER Hosting Manager شغال")
bot.infinity_polling()
