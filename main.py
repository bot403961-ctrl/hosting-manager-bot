import telebot, requests, os, json, re

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
BH_KEY = os.environ.get("BH_KEY", "")
LARP_KEY = os.environ.get("LARP_KEY", "")
DEP_ID = os.environ.get("DEP_ID", "")

BASE = "https://bot-hosting.net/api/v1"
H = {"Authorization": f"Bearer {BH_KEY}", "Content-Type": "application/json"}

bot = telebot.TeleBot(BOT_TOKEN)

# ─── AI يفهم الطلب ويحدد العملية ───
def ai_plan(text):
    prompt = f"""أنت مدير سيرفرات Bot-Hosting. المستخدم قال: "{text}"

حدد العملية المطلوبة:
- list: عرض كل السيرفرات
- status: حالة سيرفر
- logs: سجلات
- resources: موارد (CPU/RAM)
- start: تشغيل
- stop: إيقاف
- restart: إعادة تشغيل
- chat: رد عادي

رد بـ JSON فقط:
{{"action": "list|status|logs|resources|start|stop|restart|chat"}}
"""
    try:
        r = requests.post("https://larprouter.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {LARP_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 150}, timeout=30)
        d = r.json()
        c = d["choices"][0]["message"].get("content") or d["choices"][0]["message"].get("reasoning_content", "")
        m = re.search(r'\{.*\}', c, re.DOTALL)
        if m: return json.loads(m.group()).get("action", "chat")
    except: pass
    return "chat"

# ─── عمليات Bot-Hosting ───
def get_servers():
    r = requests.get(f"{BASE}/deployments", headers=H, timeout=15)
    return r.json().get("deployments", [])

def get_resources(dep_id):
    r = requests.get(f"{BASE}/deployments/{dep_id}/resources", headers=H, timeout=15)
    return r.json()

def get_logs(dep_id):
    r = requests.get(f"{BASE}/deployments/{dep_id}/logs?size=30", headers=H, timeout=15)
    return r.json().get("lines", [])

def power(dep_id, action):
    return requests.post(f"{BASE}/deployments/{dep_id}/power", headers=H, json={"action": action}, timeout=15).status_code == 200

def ai_chat(text):
    try:
        r = requests.post("https://larprouter.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {LARP_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": text}], "max_tokens": 2000}, timeout=45)
        d = r.json()
        return d["choices"][0]["message"].get("content") or d["choices"][0]["message"].get("reasoning_content", "")
    except Exception as e:
        return f"❌ {e}"

# ─── الرد ───
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def handle(msg):
    bot.send_chat_action(msg.chat.id, 'typing')
    action = ai_plan(msg.text)

    try:
        if action == "list":
            servers = get_servers()
            reply = "🖥 <b>سيرفراتك:</b>\n\n"
            for s in servers:
                reply += f"• <b>{s.get('name')}</b>\n  الحالة: {s.get('state')}\n  ID: <code>{s.get('id')}</code>\n  الرابط: {s.get('domains',{}).get('url','-')}\n\n"
            bot.reply_to(msg, reply, parse_mode="HTML")

        elif action == "status":
            servers = get_servers()
            if servers:
                s = servers[0]
                bot.reply_to(msg, f"📊 <b>{s.get('name')}</b>\nالحالة: {s.get('state')}\nRuntime: {s.get('runtime')}\nالملف: {s.get('entryFile')}")

        elif action == "resources":
            res = get_resources(DEP_ID)
            cpu = res.get("cpu", {}).get("usedPercent", 0)
            ram = res.get("memory", {}).get("usedBytes", 0) / 1024 / 1024
            bot.reply_to(msg, f"📊 <b>الموارد:</b>\nCPU: {cpu}%\nRAM: {ram:.1f} MB\nالحالة: {res.get('state')}")

        elif action == "logs":
            logs = get_logs(DEP_ID)
            bot.reply_to(msg, f"<pre>{chr(10).join(logs[-20:])}</pre>", parse_mode="HTML")

        elif action == "start":
            power(DEP_ID, "start")
            bot.reply_to(msg, "▶️ تم إرسال أمر التشغيل")

        elif action == "stop":
            power(DEP_ID, "stop")
            bot.reply_to(msg, "⏹ تم إرسال أمر الإيقاف")

        elif action == "restart":
            power(DEP_ID, "restart")
            bot.reply_to(msg, "🔄 تم إرسال أمر إعادة التشغيل")

        else:
            bot.reply_to(msg, ai_chat(msg.text))

    except Exception as e:
        bot.reply_to(msg, f"❌ خطأ: {e}")

print("🤖 TAKER Hosting Manager شغال")
bot.infinity_polling()
