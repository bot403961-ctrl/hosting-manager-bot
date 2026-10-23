import telebot, requests, os, json, re

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
BH_KEY = os.environ.get("BH_KEY", "bhk_1d653a038dd2121f736f5ccb4e82f2bdab6ae44c69470c78")
LARP_KEY = os.environ.get("LARP_KEY", "lrsk-acf60d3e0feed025330bd904ed6347c5282b82cd9f1f83af3bed724b94874c22")
DEP_ID = "7dbbcba4-13ad-4307-9292-f5bef4f43078"

BASE = "https://bot-hosting.net/api/v1"
H = {"Authorization": f"Bearer {BH_KEY}", "Content-Type": "application/json"}

bot = telebot.TeleBot(BOT_TOKEN)

def ai_plan(text):
    prompt = f'مدير سيرفر Bot-Hosting. الطلب: "{text}"\n\nرد بـ JSON فقط:\n{{"action": "list|status|logs|resources|files|read|write|delete|start|stop|restart|chat", "path": "", "content": ""}}'
    try:
        r = requests.post("https://larprouter.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {LARP_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}, timeout=30)
        d = r.json()
        content = d["choices"][0]["message"].get("content") or d["choices"][0]["message"].get("reasoning_content", "")
        m = re.search(r'\{.*\}', content, re.DOTALL)
        if m: return json.loads(m.group())
    except: pass
    return {"action": "chat"}

def get_state():
    return requests.get(f"{BASE}/deployments/{DEP_ID}/resources", headers=H, timeout=15).json()

def get_logs():
    return requests.get(f"{BASE}/deployments/{DEP_ID}/logs?size=30", headers=H, timeout=15).json().get("lines", [])

def power(a):
    return requests.post(f"{BASE}/deployments/{DEP_ID}/power", headers=H, json={"action": a}, timeout=15).status_code == 200

def ai_chat(text):
    try:
        r = requests.post("https://larprouter.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {LARP_KEY}", "Content-Type": "application/json"},
            json={"model": "deepseek-v4.1-flash", "messages": [{"role": "user", "content": text}], "max_tokens": 2000}, timeout=45)
        d = r.json()
        return d["choices"][0]["message"].get("content") or d["choices"][0]["message"].get("reasoning_content", "")
    except Exception as e:
        return f"❌ {e}"

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def handle(msg):
    bot.send_chat_action(msg.chat.id, 'typing')
    plan = ai_plan(msg.text)
    a = plan.get("action", "chat")
    try:
        if a == "status":
            s = get_state()
            bot.reply_to(msg, f"📊 {s.get('state')}\nCPU: {s.get('cpu',{}).get('usedPercent',0)}%\nRAM: {s.get('memory',{}).get('usedBytes',0)/1024/1024:.1f}MB")
        elif a == "logs":
            bot.reply_to(msg, f"<pre>{chr(10).join(get_logs()[-20:])}</pre>", parse_mode="HTML")
        elif a in ["start", "stop", "restart"]:
            power(a)
            bot.reply_to(msg, {"start": "▶️ تشغيل", "stop": "⏹ إيقاف", "restart": "🔄 إعادة"}[a])
        else:
            bot.reply_to(msg, ai_chat(msg.text))
    except Exception as e:
        bot.reply_to(msg, f"❌ {e}")

print("🤖 مدير Bot-Hosting شغال")
bot.infinity_polling()
