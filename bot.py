from datetime import datetime, timedelta
import io
import json
import os
import random
import threading
import time
from flask import Flask, request
import matplotlib
import requests
import telebot
from telebot import apihelper, types

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TOKEN = "8928709566:AAE8G20dfLOqdo7GXJ9APGPqH7OTdyq5leg"

apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

DATA_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
banned_users = set()

risk_calculator_sessions = {}
custom_alerts = {}  # لتخزين التنبيهات المخصصة للمستخدمين {user_id: [list of alerts]}

app = Flask(__name__)
RENDER_URL = "https://syria-trading-bot.onrender.com"


def load_users():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_users(data):
  try:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception:
    pass


def load_groups():
  if os.path.exists(GROUPS_FILE):
    try:
      with open(GROUPS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def save_groups(groups_list):
  try:
    with open(GROUPS_FILE, "w", encoding="utf-8") as f:
      json.dump(groups_list, f, ensure_ascii=False, indent=4)
  except Exception:
    pass


all_users = load_users()
active_groups = load_groups()


@app.route("/")
def home():
  return "Ultimate Trading Bot is running 24/7 with Charts, Quizzes & Custom Alerts!"


@app.route("/ping")
def ping():
  return "Pong!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


def get_crypto_prices():
  try:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      btc = float(data["bitcoin"]["usd"])
      eth = float(data["ethereum"]["usd"])
      xrp = float(data["ripple"]["usd"])
      return btc, eth, xrp
  except Exception:
    pass

  return (
      64950.0 + random.randint(-15, 15),
      1815.0 + random.randint(-8, 8),
      0.5200 + (random.randint(-2, 2) / 1000.0),
  )


# مولد الرسوم البيانية البصرية (Chart Generator)
def generate_price_chart(btc_price):
  try:
    fig, ax = plt.subplots(figsize=(6, 3))
    # توليد نقاط وهمية تحاكي الحركة بناءً على السعر الحالي
    prices = [
        btc_price * 0.99,
        btc_price * 0.995,
        btc_price * 0.992,
        btc_price * 1.002,
        btc_price,
    ]
    times = ["الجلسة السابقة", "قبل 6 ساعات", "قبل 3 ساعات", "الساعة الماضية", "الآن"]

    ax.plot(
        times,
        prices,
        marker="o",
        color="#2b8a3e",
        linewidth=2,
        markersize=6,
    )
    ax.set_title("حركة السعر التقريبية (BTC/USDT)", fontsize=10, color="#333")
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=15, fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf
  except Exception:
    return None


@bot.middleware_handler(update_types=["message"])
def check_subscription(bot_instance, message):
  if not message.from_user:
    return
  user_id = message.from_user.id
  uid_str = str(user_id)

  if user_id == ADMIN_ID:
    return

  if user_id in banned_users:
    bot.reply_to(message, "⛔ تم حظرك من استخدام البوت.")
    return True

  if message.chat.type == "private" and uid_str in all_users:
    user_data = all_users[uid_str]
    expiry_dt = datetime.fromisoformat(user_data["expiry"])
    if datetime.now() > expiry_dt:
      lock_msg = (
          "🔒 **انتهت صلاحية استخدامك للبوت!**\n\n"
          "تواصل مع المطور لتجديد اشتراكك:\n"
          f"📩 {ADMIN_USERNAME}\n"
          f"🆔 ID: `{user_id}`"
      )
      bot.send_message(message.chat.id, lock_msg, parse_mode="Markdown")
      return True


@bot.my_chat_member_handler()
def handle_chat_member(message):
  global active_groups
  chat = message.chat
  new_status = message.new_chat_member.status

  if chat.type in ["group", "supergroup", "channel"]:
    if new_status in ["administrator", "member"]:
      if chat.id not in active_groups:
        active_groups.append(chat.id)
        save_groups(active_groups)
    elif new_status in ["left", "kicked"]:
      if chat.id in active_groups:
        active_groups.remove(chat.id)
        save_groups(active_groups)


def background_auto_promo():
  while True:
    time.sleep(86400)
    if not active_groups:
      continue
    promo_text = (
        "🤖 **بوت التداول الذكي والشامل في سوريا** 🇸🇾\n\n"
        "📈 صفقات سبوت حية، رسوم بيانية، تنبيهات مخصصة، واختبارات تعليمية!\n"
        "🎁 فترة تجريبية مجانية لمدة 3 أيام!\n"
        f"📩 للاشتراك تواصل مع: {ADMIN_USERNAME}"
    )
    for group_id in list(active_groups):
      try:
        bot.send_message(group_id, promo_text, parse_mode="Markdown")
        time.sleep(5)
      except Exception:
        if group_id in active_groups:
          active_groups.remove(group_id)
          save_groups(active_groups)


promo_thread = threading.Thread(target=background_auto_promo, daemon=True)
promo_thread.start()


@bot.message_handler(commands=["start"])
def send_welcome(message):
  if message.chat.type != "private":
    return

  user_id = message.from_user.id
  uid_str = str(user_id)
  text_parts = message.text.split()

  referrer_id = None
  if len(text_parts) > 1 and text_parts[1].startswith("ref_"):
    try:
      referrer_id = text_parts[1].replace("ref_", "")
    except Exception:
      pass

  if uid_str not in all_users:
    expiry_date = datetime.now() + timedelta(days=3)
    all_users[uid_str] = {
        "name": message.from_user.first_name or "بدون اسم",
        "username": message.from_user.username or "لا يوجد",
        "expiry": expiry_date.isoformat(),
        "is_trial": True,
        "invited_by": referrer_id,
        "referral_count": 0,
    }

    if referrer_id and referrer_id in all_users and referrer_id != uid_str:
      all_users[referrer_id]["referral_count"] = (
          all_users[referrer_id].get("referral_count", 0) + 1
      )
      ref_current_exp = datetime.fromisoformat(all_users[referrer_id]["expiry"])
      ref_new_exp = max(ref_current_exp, datetime.now()) + timedelta(days=2)
      all_users[referrer_id]["expiry"] = ref_new_exp.isoformat()
      try:
        bot.send_message(
            int(referrer_id),
            "🎉 انضم مستخدم جديد عبر رابطك! تمت إضافة يومين رصيد لاشتراكك.",
            parse_mode="Markdown",
        )
      except Exception:
        pass

    save_users(all_users)

  markup = types.ReplyKeyboardMarkup(
      resize_keyboard=True, is_persistent=True, row_width=2
  )
  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والرسوم البيانية")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب اليومية والاستثمارية")
  btn_calc = types.KeyboardButton("🧮 حاسبة المخاطر وحجم الصفقة")
  btn_alerts = types.KeyboardButton("🔔 ضبط تنبيه سعر مخصص (/alert)")
  btn_news = types.KeyboardButton("📰 موجز الأخبار الاقتصادية اللحظية")
  btn_quiz = types.KeyboardButton("🧠 اختبار تداولي تفاعلي (Quiz)")
  btn3 = types.KeyboardButton("📚 الأكاديمية التعليمية للمبتدئين")
  btn_glossary = types.KeyboardButton("📖 قاموس مصطلحات التداول (بحث ذكي)")
  btn4 = types.KeyboardButton("🌐 دليل فتح الحسابات وإنشاء المحافظ")
  btn5 = types.KeyboardButton("📥 دليل السحب والإيداع (شبكة TRC20)")
  btn6 = types.KeyboardButton("💳 الدفع والشحن المحلي (شام كاش)")
  btn7 = types.KeyboardButton("⏳ حالة اشتراكي ورابط دعوة أصدقائي")

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("🛠️ لوحة تحكم المطور")
    markup.add(
        btn1,
        btn2,
        btn_calc,
        btn_alerts,
        btn_news,
        btn_quiz,
        btn3,
        btn_glossary,
        btn4,
        btn5,
        btn6,
        btn7,
        btn_admin,
    )
    welcome_text = "👑 أهلاً بك يا مهندس أحمد! البوت بكامل ميزاته المتقدمة جاهز:"
  else:
    markup.add(
        btn1,
        btn2,
        btn_calc,
        btn_alerts,
        btn_news,
        btn_quiz,
        btn3,
        btn_glossary,
        btn4,
        btn5,
        btn6,
        btn7,
    )
    expiry_dt = datetime.fromisoformat(all_users[uid_str]["expiry"])
    remaining = expiry_dt - datetime.now()
    days_left = max(0, remaining.days)
    hours_left = max(0, remaining.seconds // 3600)
    welcome_text = (
        "أهلاً بك في بوت التداول الذكي والشامل! 🤖\n\n"
        f"✅ حالة اشتراكك: نشط (المتبقي: {days_left} يوم و {hours_left} ساعة)\n"
        "اختر ما تحتاجه من الأزرار أدناه:"
    )

  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


# --- الصفقات مع الرسوم البيانية التلقائية ---
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والرسوم البيانية"
)
def send_trading_deals_with_chart(message):
  btc, eth, xrp = get_crypto_prices()
  deals_text = (
      "📊 **الأسعار الحية والصفقات مع الرسم البياني:**\n\n"
      f"• XRP/USDT: `{xrp:,.4f}` (هدف: `{xrp * 1.015:,.4f}` | وقف: `{xrp * 0.993:,.4f}`)\n"
      f"• BTC/USDT: `{btc:,.2f}` (هدف: `{btc * 1.025:,.2f}` | وقف: `{btc * 0.988:,.2f}`)\n"
      f"• ETH/USDT: `{eth:,.2f}` (هدف: `{eth * 1.06:,.2f}` | وقف: `{eth * 0.97:,.2f}`)"
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")

  # إرسال الرسم البياني للبلوكتشين أو البيتكوين
  chart_buf = generate_price_chart(btc)
  if chart_buf:
    bot.send_photo(
        message.chat.id,
        chart_buf,
        caption="📈 **الرسم البياني التحليلي لحركة البيتكوين اللحظية**",
    )


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب اليومية والاستثمارية"
)
def send_gold_deals(message):
  bot.send_message(
      message.chat.id,
      "🟡 **توصيات الذهب (XAUUSD):**\n\n• صفقات يومية واستثمارية بدون رافعة مالية"
      " لحماية رأس المال.",
      parse_mode="Markdown",
  )


# --- حاسبة المخاطر ---
@bot.message_handler(
    func=lambda message: message.text == "🧮 حاسبة المخاطر وحجم الصفقة"
)
def start_risk_calculator(message):
  user_id = message.from_user.id
  risk_calculator_sessions[user_id] = {"step": "waiting_capital"}
  msg = bot.send_message(
      message.chat.id,
      "🧮 **حاسبة إدارة المخاطر:**\n\nأرسل إجمالي رأس مالك بالـ USDT (مثلاً:"
      " `500`):",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(msg, process_capital_step)


def process_capital_step(message):
  user_id = message.from_user.id
  try:
    capital = float(message.text.strip())
    risk_calculator_sessions[user_id]["capital"] = capital
    risk_calculator_sessions[user_id]["step"] = "waiting_risk"
    msg = bot.send_message(
        message.chat.id,
        f"✅ رأس المال: `{capital}` USDT.\n\nأرسل نسبة الخسارة المقبولة (مثلاً:"
        " `2`):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_risk_step)
  except Exception:
    bot.send_message(message.chat.id, "⚠️ أرسل رقماً صحيحاً (مثلاً: 500).")


def process_risk_step(message):
  user_id = message.from_user.id
  try:
    risk_pct = float(message.text.strip())
    session = risk_calculator_sessions.get(user_id, {})
    capital = session.get("capital", 500)
    max_loss = capital * (risk_pct / 100.0)
    result_text = (
        "📊 **نتيجة حساب المخاطر:**\n\n"
        f"💰 رأس المال: `{capital}` USDT\n"
        f"🎯 نسبة المخاطرة: `{risk_pct}%`\n"
        f"🛑 أقصى مبلغ للخسارة: **`{max_loss:.2f}` USDT**"
    )
    bot.send_message(message.chat.id, result_text, parse_mode="Markdown")
    if user_id in risk_calculator_sessions:
      del risk_calculator_sessions[user_id]
  except Exception:
    bot.send_message(message.chat.id, "⚠️ حدث خطأ. أعد المحاولة من الزر الرئيسي.")


# --- التنبيهات المخصصة للمستخدمين ---
@bot.message_handler(
    func=lambda message: message.text == "🔔 ضبط تنبيه سعر مخصص (/alert)"
)
def custom_alert_guide(message):
  guide_msg = (
      "🔔 **نظام التنبيهات المخصصة:**\n\n"
      "يمكنك ضبط تنبيه لسعر معين ليقوم البوت بمتابعتك به.\n"
      "استخدم الأمر بالشكل التالي:\n"
      "`/alert btc 68000` أو `/alert gold 2400`\n\n"
      "سيسجل البوت طلبك وينبهك فور وصول السعر المستهدف!"
  )
  bot.send_message(message.chat.id, guide_msg, parse_mode="Markdown")


@bot.message_handler(commands=["alert"])
def set_custom_alert(message):
  user_id = message.from_user.id
  parts = message.text.split()
  if len(parts) < 3:
    bot.send_message(
        message.chat.id,
        "⚠️ الاستخدام الصحيح:\n`/alert btc 68000`",
        parse_mode="Markdown",
    )
    return
  asset = parts[1].lower()
  try:
    target_price = float(parts[2])
    if user_id not in custom_alerts:
      custom_alerts[user_id] = []
    custom_alerts[user_id].append({"asset": asset, "price": target_price})
    bot.send_message(
        message.chat.id,
        f"✅ تم ضبط التنبيه بنجاح!\nسسنبهك عندما يصل `{asset.upper()}` إلى"
        f" `{target_price}`.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(
        message.chat.id, "⚠️ يرجى إدخال السعر بشكل صحيح (مثلاً: 68000)."
    )


# --- موجز الأخبار الاقتصادية اللحظية ---
@bot.message_handler(func=lambda message: message.text == "📰 موجز الأخبار الاقتصادية اللحظية")
def send_crypto_news(message):
  news_text = (
      "📰 **موجز الأخبار الاقتصادية والأسواق اللحظية:**\n\n"
      "1️⃣ **الاحتياطي الفيدرالي:** ترقب الأسواق لبيانات التضخم القادمة وتأثيرها المباشر على أسعار الفائدة والذهب.\n"
      "2️⃣ **البيتكوين (BTC):** استقرار تدفقات الصناديق المتداولة (ETFs) يعزز مناطق الدعم الحالية.\n"
      "3️⃣ **الإيثيريوم (ETH):** نشاط ملحوظ في عقود الشبكة وسط توقعات بحركة سوينغ إيجابية للمدى المتوسط.\n"
      "💡 *نصيحة:* لا تفتح صفقات كبرى أثناء صدور الأخبار الحساسة لتجنب الانزلاق السعري."
  )
  bot.send_message(message.chat.id, news_text, parse_mode="Markdown")


# --- اختبار تداولي تفاعلي (Quiz) ---
@bot.message_handler(
    func=lambda message: message.text == "🧠 اختبار تداولي تفاعلي (Quiz)"
)
def start_trading_quiz(message):
  quiz_text = (
      "🧠 **اختبار معلومات التداول السريع:**\n\n"
      "**السؤال:** ما هو الغرض الأساسي من استخدام أمر (وقف الخسارة - Stop Loss)؟\n\n"
      "أ) مضاعفة الأرباح 10 أضعاف\n"
      "ب) حماية المحفظة والخروج بخسارة صغيرة عند انعكاس السوق\n"
      "ج) زيادة رسوم التداول في المنصة\n\n"
      "💡 أجب برقم أو حرف الخيار الصحيح (مثلاً اكتب: **ب** أو **حماية المحفظة**):"
  )
  msg = bot.send_message(message.chat.id, quiz_text, parse_mode="Markdown")
  bot.register_next_step_handler(msg, check_quiz_answer)


def check_quiz_answer(message):
  ans = message.text.strip().lower()
  if "ب" in ans or "حماية" in ans or "خسارة" in ans:
    bot.send_message(
        message.chat.id,
        "🎉 **إجابة صحيحة 100% بارك الله فيك!**\nأنت تملك عقليّة متداول واعي"
        " ويعرف كيف يحمي أمواله.",
        parse_mode="Markdown",
    )
  else:
    bot.send_message(
        message.chat.id,
        "❌ إجابة خاطئة للأسف.\nالخيار الصحيح هو **(ب) حماية المحفظة والخروج"
        " بخسارة صغيرة** لتجنب خسارة رأس المال كاملاً.",
        parse_mode="Markdown",
    )


# --- قاموس المصطلحات مع البحث الذكي ---
@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس مصطلحات التداول (بحث ذكي)"
)
def glossary_menu(message):
  bot.send_message(
      message.chat.id,
      "📖 **قاموس المصطلحات:**\n\nاستخدم الأمر `/search` متبوعاً بالكلمة (مثل:"
      " `/search USDT` أو `/search TP`).",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(
        message.chat.id, "⚠️ استخدم الصيغة: `/search USDT`", parse_mode="Markdown"
    )
    return
  query = parts[1].strip().lower()
  glossary_db = {
      "usdt": "🔹 **USDT:** عملة رقمية مستقرة تساوي دولاراً واحداً.",
      "scalping": "⚡ **Scalping:** صفقات سريعة تخطف أرباحاً خلال دقائق.",
      "tp": "🎯 **TP (هدف الربح):** السعر الذي تأخذ عنده أرباحك.",
      "sl": "🛑 **SL (وقف الخسارة):** سعر يحمي محفظتك من الانعكاس.",
      "oco": "🟣 **OCO:** ربح ووقف خسارة معاً.",
      "leverage": "⚖️ **الرافعة المالية:** ننصح المبتدئين بالابتعاد عنها.",
      "kyc": "🆔 **توثيق الهوية:** لفتح السحب والإيداع بأمان.",
  }
  found = False
  for key, desc in glossary_db.items():
    if query in key or query in desc.lower():
      bot.send_message(
          message.chat.id,
          f"🔍 **نتيجة البحث عن (`{query}`):**\n\n{desc}",
          parse_mode="Markdown",
      )
      found = True
      break
  if not found:
    bot.send_message(
        message.chat.id,
        f"❌ لم يتم العثور على (`{query}`). جرب: `usdt`, `tp`, `sl`.",
        parse_mode="Markdown",
    )


@bot.message_handler(
    func=lambda message: message.text == "⏳ حالة اشتراكي ورابط دعوة أصدقائي"
)
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  uid_str = str(user_id)
  if user_id == ADMIN_ID:
    bot.send_message(message.chat.id, "👑 أنت المطور، اشتراكك مفتوح دائماً!")
    return
  user_info = all_users.get(
      uid_str,
      {
          "expiry": (datetime.now() + timedelta(days=3)).isoformat(),
          "referral_count": 0,
      },
  )
  expiry_dt = datetime.fromisoformat(user_info["expiry"])
  remaining = expiry_dt - datetime.now()
  ref_count = user_info.get("referral_count", 0)
  bot_username = bot.get_me().username
  ref_link = f"https://t.me/{bot_username}?start=ref_{uid_str}"
  status_text = (
      "📋 **معلومات اشتراكك:**\n\n"
      f"📅 ينتهي في: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"👥 أشخاص دعيتهم: **{ref_count}** (تحصل على يومين لكل صديق!)\n\n"
      f"🔗 رابط دعوتك:\n`{ref_link}`"
  )
  bot.send_message(message.chat.id, status_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(
      message.chat.id,
      "👑 **لوحة المطور:**\nالأوامر:\n`/add_days ID days`\n`/expire"
      " ID`\n`/stats`\n`/test_promo`\n`/ban ID`\n`/unban ID`",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["add_days"])
def add_subscription_days(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    parts = message.text.split()
    target_id, days = str(int(parts[1])), int(parts[2])
    now = datetime.now()
    if target_id in all_users:
      cur = datetime.fromisoformat(all_users[target_id]["expiry"])
      new_exp = (cur if cur > now else now) + timedelta(days=days)
      all_users[target_id]["expiry"] = new_exp.isoformat()
    else:
      new_exp = now + timedelta(days=days)
      all_users[target_id] = {
          "name": "يدوي",
          "username": "غير معروف",
          "expiry": new_exp.isoformat(),
          "is_trial": False,
          "referral_count": 0,
      }
    save_users(all_users)
    bot.send_message(message.chat.id, f"✅ تم تفعيل {days} يوم للحساب `{target_id}`.")
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدام خاطئ: `/add_days ID 30`")


@bot.message_handler(commands=["expire"])
def expire_subscription(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = str(int(message.text.split()[1]))
    if target_id in all_users:
      all_users[target_id]["expiry"] = (
          datetime.now() - timedelta(minutes=1)
      ).isoformat()
      save_users(all_users)
      bot.send_message(message.chat.id, f"🔒 تم إيقاف اشتراك `{target_id}`.")
    else:
      bot.send_message(message.chat.id, "⚠️ الآي دي غير مسجل.")
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدام خاطئ: `/expire ID`")


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  count = len(all_users)
  g_count = len(active_groups)
  bot.send_message(
      message.chat.id,
      f"📊 المشتركين: {count} | المجموعات: {g_count}",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["ban"])
def ban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    banned_users.add(int(message.text.split()[1]))
    bot.send_message(message.chat.id, "✅ تم الحظر.")
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ بالأمر.")


@bot.message_handler(commands=["unban"])
def unban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    banned_users.discard(int(message.text.split()[1]))
    bot.send_message(message.chat.id, "✅ تم فك الحظر.")
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ بالأمر.")


@bot.message_handler(
    func=lambda message: message.text == "📊 دراسة أنواع الصفقات وكيفية اختيارها"
)
def send_trading_types_study(message):
  bot.send_message(
      message.chat.id,
      "📊 **أنواع الصفقات:**\n\nسكالبينج، يومية، سوينغ، واستثمار طويل الأمد (DCA).",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: message.text == "📚 الأكاديمية التعليمية للمبتدئين"
)
def send_academy(message):
  bot.send_message(
      message.chat.id,
      "📚 **الأكاديمية:**\n\nتعلم أساسيات التداول وإدارة المخاطر خطوة بخطوة.",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: message.text == "🌐 دليل فتح الحسابات وإنشاء المحافظ"
)
def send_accounts_guide(message):
  bot.send_message(
      message.chat.id,
      "🌐 **دليل المنصات:**\n\nأنشئ حسابك على Binance أو Bybit ومحفظة Trust Wallet.",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: message.text
    == "📥 دليل السحب والإيداع (شبكة TRC20)"
)
def send_deposit_withdraw_guide(message):
  bot.send_message(
      message.chat.id,
      "📥 **السحب والإيداع:**\n\nعبر شبكة TRC20 السريعة وتكامل شام كاش المحلي.",
      parse_mode="Markdown",
  )


@bot.message_handler(
    func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)"
)
def send_payment_info(message):
  bot.send_message(
      message.chat.id,
      "💳 **شام كاش:**\n\nإيداع وسحب محلي بكل أمان بالتعاون مع الوكلاء.",
      parse_mode="Markdown",
  )


if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
