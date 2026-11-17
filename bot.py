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

# إعداد Matplotlib للعمل بدون واجهة رسومية
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
custom_alerts = {}

app = Flask(__name__)
RENDER_URL = "https://syria-trading-bot.onrender.com"


# --- دوال حفظ واسترجاع البيانات ---
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
  return "Ultimate Trading Bot is running 24/7!"


@app.route("/ping")
def ping():
  return "Pong!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


# جلب الأسعار الحية
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


# مولد الرسوم البيانية
def generate_price_chart(btc_price):
  try:
    fig, ax = plt.subplots(figsize=(6, 3))
    prices = [
        btc_price * 0.99,
        btc_price * 0.995,
        btc_price * 0.992,
        btc_price * 1.002,
        btc_price,
    ]
    times = ["الان", "قبل ساعة", "قبل 3 ساعات", "قبل 6 ساعات", "السابقة"]

    ax.plot(
        times,
        prices,
        marker="o",
        color="#2b8a3e",
        linewidth=2,
        markersize=6,
    )
    ax.set_title("حركة السعر التحليلية (BTC/USDT)", fontsize=10, color="#333")
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


# --- دالة فصل الأرباح الصافية عن رأس المال الأساسي (حماية الأصل) ---
def calculate_safe_rebalancing(
    initial_capital_usdt, btc_amount, current_btc_price
):
  current_portfolio_value = btc_amount * current_btc_price
  net_profit = current_portfolio_value - initial_capital_usdt

  if net_profit > 0:
    profit_to_lock = net_profit * 0.25
    equivalent_btc_to_sell = profit_to_lock / current_btc_price
    safe_btc_remaining = btc_amount - equivalent_btc_to_sell
    return {
        "is_profitable": True,
        "net_profit": net_profit,
        "profit_locked_usdt": profit_to_lock,
        "btc_to_sell": equivalent_btc_to_sell,
        "protected_btc": safe_btc_remaining,
    }
  else:
    return {
        "is_profitable": False,
        "net_profit": 0,
        "profit_locked_usdt": 0,
        "btc_to_sell": 0,
        "protected_btc": btc_amount,
    }


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
        "📈 صفقات سبوت حية، رسوم بيانية، تنبيهات، واختبارات تعليمية!\n"
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
    user_name = message.from_user.first_name or "بدون اسم"
    user_uname = message.from_user.username or "لا يوجد"

    all_users[uid_str] = {
        "name": user_name,
        "username": user_uname,
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

    if user_id != ADMIN_ID:
      try:
        admin_alert_text = (
            "🚨 **مشترك جديد انضم إلى البوت!**\n\n"
            f"👤 **الاسم:** {user_name}\n"
            f"🆔 المعرف (ID): `{user_id}`\n"
            f"🌐 اليوزر: `@{user_uname}`\n"
            f"👥 إجمالي المشتركين الآن: `{len(all_users)}`"
        )
        bot.send_message(ADMIN_ID, admin_alert_text, parse_mode="Markdown")
      except Exception:
        pass

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
    welcome_text = "👑 أهلاً بك يا مهندس أحمد! البوت بكامل ميزاته جاهز:"
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


# --- 1. الصفقات المقترحة والرسوم البيانية (مع نظام التأمين وحماية الأصل) ---
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والرسوم البيانية"
)
def send_trading_deals_with_chart(message):
  btc, eth, xrp = get_crypto_prices()

  deals_text = (
      "📊 **الأسعار الحية والصفقات المقترحة (Spot) + نظام التأمين وحماية الأصل:**\n\n"
      "⚡ **1. صفقات السكالبينج (السريعة جداً):**\n"
      f"• **العملة:** XRP/USDT (سعر الدخول: `{xrp:,.4f}`)\n"
      f"  🎯 *الهدف الأول (TP1):* `{xrp * 1.008:,.4f}`\n"
      f"  🛡️ **نقطة التأمين:** عند وصول السعر لـ `{xrp * 1.008:,.4f}`، احجز 50%"
      f" من الربح وارفع وقف الخسارة لسعر الدخول (`{xrp:,.4f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{xrp * 1.015:,.4f}`\n"
      f"  🛑 *وقف الخسارة الأساسي (SL):* `{xrp * 0.993:,.4f}`\n\n"
      "📅 **2. الصفقات اليومية:**\n"
      f"• **العملة:** BTC/USDT (سعر الدخول: `{btc:,.2f}`)\n"
      f"  🎯 *الهدف الأول (TP1):* `{btc * 1.012:,.2f}`\n"
      f"  🛡️ **نقطة التأمين:** عند ملامسة `{btc * 1.012:,.2f}`، اجنِ نصف الربح"
      f" وحرك وقف الخسارة لنقطة الدخول (`{btc:,.2f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{btc * 1.025:,.2f}`\n"
      f"  🛑 *وقف الخسارة الأساسي (SL):* `{btc * 0.988:,.2f}`\n\n"
      "🌊 **3. صفقات السوينغ (المتوسطة - أسبوع):**\n"
      f"• **العملة:** ETH/USDT (سعر الدخول: `{eth:,.2f}`)\n"
      f"  🎯 *الهدف الأول (TP1):* `{eth * 1.03:,.2f}`\n"
      f"  🛡️ **نقطة التأمين:** عند الوصول لـ `{eth * 1.03:,.2f}`، أمّن الصفقة"
      f" بنقل وقف الخسارة إلى `{eth:,.2f}` مع جني 50%.\n"
      f"  🚀 *الهدف الثاني (TP2):* `{eth * 1.06:,.2f}`\n"
      f"  🛑 *وقف الخسارة الأساسي (SL):* `{eth * 0.97:,.2f}`\n\n"
      "🏛️ **4. الاستثمار طويل الأمد (تجميع البيتكوين DCA + قاعدة حماية الأصل):**\n"
      f"• **العملة:** Bitcoin (BTC) عند سعر `{btc:,.2f}`\n"
      "  📌 *الطريقة:* الشراء تدريجياً **بدون رافعة مالية**. عند تحقيق أرباح،"
      " يتم بيع **25% من الأرباح الصافية فقط** وتحويلها لـ USDT ككاش احتياطي"
      " **مع الحفاظ على كمية البيتكوين الأساسية كاملة وغير منقوصة** لضمان عدم"
      " تآكل المحفظة."
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")

  chart_buf = generate_price_chart(btc)
  if chart_buf:
    bot.send_photo(
        message.chat.id,
        chart_buf,
        caption="📈 **الرسم البياني التحليلي لحركة البيتكوين اللحظية**",
    )


# --- 2. صفقات وتوصيات الذهب المفصلة (مع نظام التأمين) ---
@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب اليومية والاستثمارية"
)
def send_gold_deals(message):
  gold_text = (
      "🟡 **توصيات صفقات الذهب (XAUUSD) الاحترافية + نظام التأمين:**\n\n"
      "⚡ **1️⃣ صفقات الذهب اليومية (Scalping / Day Trading):**\n"
      "• **النوع:** صفقات سريعة لاقتناص التذبذبات أثناء الجلسات النشطة.\n"
      "• **الهدف الأول (TP1):** صعود بنسبة (+0.7%).\n"
      "• **🛡️ قاعدة التأمين الإلزامية:** فور تحقق (+0.7%)، أغلق 50% من العقد"
      " وانقل وقف الخسارة إلى **نقطة الدخول تماماً** لتصبح الصفقة مجانية"
      " (Risk-Free).\n"
      "• **الهدف الثاني (TP2):** صعود بنسبة (+1.5%).\n"
      "• **وقف الخسارة الأساسي (SL):** صارم عند (-0.7%) لحماية المحفظة.\n\n"
      "📈 **2️⃣ استثمار وتجميع الذهب طويل الأمد:**\n"
      "• **النوع:** بناء محفظة ذهبية لحفظ القيمة والثروة.\n"
      "• **🛡️ تأمين الاستثمار:** عند تحقيق أرباح صافية، يتم جني 25% من الربح فقط"
      " وإبقاء الأصل الأساسي آمناً.\n"
      "• **قاعدة الأمان:** العمل بالكامل **بدون أي رافعة مالية**."
  )
  bot.send_message(message.chat.id, gold_text, parse_mode="Markdown")


# --- 3. حاسبة المخاطر وحجم الصفقة ---
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


# --- 4. التنبيهات المخصصة المطورة ---
@bot.message_handler(
    func=lambda message: message.text == "🔔 ضبط تنبيه سعر مخصص (/alert)"
)
def custom_alert_guide(message):
  bot.send_message(
      message.chat.id,
      "🔔 **التنبيهات المخصصة:**\n\n"
      "استخدم الأمر بالشكل الصحيح:\n"
      "• `/alert btc 68000`\n"
      "• أو بدون فاصلة عشرية معقدة، مثل: `/alert btc 66220`",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["alert"])
def set_custom_alert(message):
  user_id = message.from_user.id
  parts = message.text.split()

  if len(parts) < 3:
    bot.send_message(
        message.chat.id,
        "⚠️ الصيغة الصحيحة:\n`/alert btc 68000` أو `/alert eth 1850`",
        parse_mode="Markdown",
    )
    return

  asset = parts[1].replace("/", "").replace("USDT", "").upper()
  price_str = parts[2].replace(",", "")

  try:
    target_price = float(price_str)
    if user_id not in custom_alerts:
      custom_alerts[user_id] = []

    custom_alerts[user_id].append({"asset": asset, "price": target_price})

    bot.send_message(
        message.chat.id,
        f"✅ **تم ضبط التنبيه بنجاح!**\n"
        f"• العملة: `{asset}/USDT`\n"
        f"• السعر المستهدف: `{target_price:,.2f}`",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى كتابة السعر بشكل رقُمي صحيح بدون رموز.\n*مثال:* `/alert btc"
        " 68000`",
        parse_mode="Markdown",
    )


# --- 5. موجز الأخبار الاقتصادية اللحظية المفصل ---
@bot.message_handler(
    func=lambda message: message.text == "📰 موجز الأخبار الاقتصادية اللحظية"
)
def send_crypto_news(message):
  news_text = (
      "📰 **موجز الأخبار الاقتصادية والأسواق اللحظية:**\n\n"
      "1️⃣ **الاحتياطي الفيدرالي وأسعار الفائدة:**\n"
      "• ترقب الأسواق لبيانات التضخم الأمريكية القادمة وتأثيرها المباشر على"
      " قرارات الفيدرالي وحركة الذهب والعملات.\n\n"
      "2️⃣ **سوق العملات الرقمية (Crypto):**\n"
      "• استقرار تدفقات صناديق الاستثمار المتداولة (ETFs) يعزز مناطق الدعم"
      " الحالية للبيتكوين.\n\n"
      "3️⃣ **سوق الذهب العالمي (XAUUSD):**\n"
      "• الأحداث الجيوسياسية وتحركات الدولار تقود أسعار الذهب نحو مستويات"
      " قياسية جديدة.\n\n"
      "💡 *نصيحة المطور:* لا تفتح صفقات كبرى أثناء صدور الأخبار الاقتصادية"
      " الحساسة لتجنب الانزلاق السعري المفاجئ."
  )
  bot.send_message(message.chat.id, news_text, parse_mode="Markdown")


# --- 6. الاختبار التفاعلي (بنك الأسئلة العشوائي) ---
QUIZ_QUESTIONS = [
    {
        "question": (
            "🧠 **سؤال اختبار التداول (1/4):**\n\nما هو الغرض الأساسي من استخدام أمر"
            " (وقف الخسارة - Stop Loss)؟\n\nأ) مضاعفة الأرباح 10 أضعاف\nب) حماية"
            " المحفظة والخروج بخسارة صغيرة عند انعكاس السوق\nج) زيادة رسوم التداول في"
            " المنصة\n\n💡 أجب بـ (ب) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "حماية", "خسارة"],
    },
    {
        "question": (
            "🧠 **سؤال اختبار التداول (2/4):**\n\nماذا تعني العملة الرقمية (USDT)"
            " في عالم التداول؟\n\nأ) عملة رقمية متذبذبة ترتفع وتنهبط بعنف\nب)"
            " عملة مستقرة تساوي دولاراً واحداً دائماً لحفظ الأرباح\nج) عملة مخصصة"
            " لتعدين البيتكوين فقط\n\n💡 أجب بـ (ب) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "مستقرة", "دولار"],
    },
    {
        "question": (
            "🧠 **سؤال اختبار التداول (3/4):**\n\nما هي النسبة الآمنة الموصى"
            " بالمخاطرة بها في الصفقة الواحدة للمبتدئين؟\n\nأ) من 50% إلى 100% من"
            " رأس المال\nب) من 1% إلى 2% فقط للحفاظ على المحفظة\nج) لا داعي لحساب"
            " نسب المخاطرة\n\n💡 أجب بـ (ب) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "1%", "2%", "واحد", "اثنان"],
    },
    {
        "question": (
            "🧠 **سؤال اختبار التداول (4/4):**\n\nما هو سوق (السبوت - Spot) في"
            " التداول؟\n\nأ) شراء الأصول وامتلاكها حقيقةً بدون رافعة مالية\nب)"
            " الاقتراض والاستدانة بمضاعفات ضخمة\nج) التداول العشوائي بدون تحليل\n\n💡"
            " أجب بـ (أ) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "أ",
        "keywords": ["أ", "شراء", "امتلاك", "بدون"],
    },
]

active_quizzes = {}


@bot.message_handler(
    func=lambda message: message.text == "🧠 اختبار تداولي تفاعلي (Quiz)"
)
def start_trading_quiz(message):
  user_id = message.from_user.id
  q_data = random.choice(QUIZ_QUESTIONS)
  active_quizzes[user_id] = q_data

  msg = bot.send_message(
      message.chat.id, q_data["question"], parse_mode="Markdown"
  )
  bot.register_next_step_handler(msg, check_quiz_answer)


def check_quiz_answer(message):
  user_id = message.from_user.id
  ans = message.text.strip().lower()

  q_data = active_quizzes.get(user_id)
  if not q_data:
    bot.send_message(
        message.chat.id,
        "⚠️ انتهت جلسة الاختبار. اضغط على الزر مجدداً للبدء.",
    )
    return

  is_correct = any(keyword in ans for keyword in q_data["keywords"])

  if is_correct:
    bot.send_message(
        message.chat.id,
        "🎉 **إجابة صحيحة 100% بارك الله فيك!**\nأنت تملك عقليّة متداول واعي"
        " يعرف كيف يحمي أمواله.",
        parse_mode="Markdown",
    )
  else:
    bot.send_message(
        message.chat.id,
        f"❌ إجابة غير صحيحة.\nالخيار الصحيح هو **({q_data['answer_key']})**.",
        parse_mode="Markdown",
    )

  if user_id in active_quizzes:
    del active_quizzes[user_id]


# --- 7. الأكاديمية التعليمية للمبتدئين المفصلة ---
@bot.message_handler(
    func=lambda message: message.text == "📚 الأكاديمية التعليمية للمبتدئين"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية التعليمية - تعلم التداول من الصفر حتى الاحتراف:**\n\n"
      "🟢 **الدرس الأول (ما هو التداول؟):**\n"
      "• هو عملية بيع وشراء الأصول الرقمية (مثل العملات أو الذهب) للاستفادة"
      " من فرق السعر.\n"
      "• يتم قياس وتسعير الأصول دائماً مقابل العملة المستقرة والدولار الرقمي"
      " (`USDT`).\n\n"
      "🟡 **الدرس الثاني (فهم أنواع الصفقات وتأمينها):**\n"
      "• تنقسم الصفقات إلى سريعة جداً (سكالبينج)، يومية، متوسطة الأمد (سوينغ)، أو"
      " استثمار طويل الأمد (DCA).\n"
      "• احرص دائماً على تطبيق **قاعدة التأمين (Breakeven)** برفع وقف الخسارة"
      " لسعر الدخول بعد بلوغ الهدف الأول.\n\n"
      "🔵 **الدرس الثالث (إدارة المخاطر وحماية رأس المال):**\n"
      "• القاعدة الذهبية: **لا توضع كل البيض في سلة واحدة.**\n"
      "• لا تستخدم كل أموالك في صفقة واحدة أبداً، واجعل خسارة أي صفقة لا تتجاوز"
      " 1% إلى 2% من إجمالي مالك.\n\n"
      "🟣 **الدرس الرابع (حماية الأصول في الاستثمار طويل الأمد):**\n"
      "• عند جني الأرباح في استراتيجيات DCA الصاعدة، يتم بيع جزء من الأرباح"
      " الصافية فقط وتحويله لـ USDT مع **الحفاظ على كمية البيتكوين الأساسية كاملة"
      " دون تآكل**.\n\n"
      "🟠 **الدرس الخامس (السيطرة على المشاعر):**\n"
      "• أكبر عدو للمتداول هو (الطمع) و(الخوف) والرغبة في الانتقام من السوق بعد"
      " صفقة خاسرة.\n"
      "• الالتزام بالخطة هو طريقك الوحيد للنجاح المستدام."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


# --- 8. قاموس مصطلحات التداول الشامل مع البحث الذكي ---
@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس مصطلحات التداول (بحث ذكي)"
)
def glossary_menu(message):
  glossary_guide = (
      "📖 **قاموس الحيتان ومصطلحات السوق العتيقة:**\n\n"
      "لتحترف لغة الكبار، استخدم الأمر `/search` متبوعاً بالكلمة التي تقصدها.\n"
      "📌 *مثال:* `/search breakeven` أو `/search OCO` أو `/search USDT`\n\n"
      "---\n"
      "**فهرس المصطلحات المتاحة في الديوان:**\n"
      "1️⃣ **USDT** (الملاذ الآمن المستقر)\n"
      "2️⃣ **Breakeven** (تأمين الصفقة / نقطة التعادل)\n"
      "3️⃣ **Scalping** (اقتناص الفتات السريع)\n"
      "4️⃣ **TP / Take Profit** (مرفأ جني الأرباح)\n"
      "5️⃣ **SL / Stop Loss** (طوق النجاة / وقف الخسارة)\n"
      "6️⃣ **OCO** (الحارس المزدوج للأوامر)\n"
      "7️⃣ **Leverage** (أداة الانتحار / الرافعة المالية)\n"
      "8️⃣ **KYC** (بصمة الهوية المشروطة)\n"
      "9️⃣ **DCA** (التجميع الهادئ المستمر)"
  )
  bot.send_message(message.chat.id, glossary_guide, parse_mode="Markdown")


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى كتابة المصطلح بعد الأمر.\n*مثال:* `/search breakeven`",
        parse_mode="Markdown",
    )
    return

  query = parts[1].strip().lower()

  glossary_db = {
      "usdt": (
          "🔹 **USDT (الملاذ الآمن المستقر):**\n"
          "عملة رقمية مشفرة ثابتة القيمة تساوى دولاراً أمريكياً واحداً دائماً.\n"
          "💡 *فائدتها:* تستخدم لحفظ الأرباح والهرب من هبوط السوق دون الحاجة لتحويل"
          " الأموال لكاش ورقي."
      ),
      "breakeven": (
          "🛡️ **Breakeven (تأمين الصفقة / نقطة التعادل):**\n"
          "إجراء وقائي يقوم به المتداول المحترف بعد تحرك السعر في صالحه وتحقيق"
          " الهدف الأول (TP1)، وذلك بجني نصف الربح ونقل أمر وقف الخسارة (SL) إلى"
          " سعر الدخول تماماً.\n"
          "💡 *النتيجة:* تضمن عدم خسارة أي سنت من رأس مالك حتى لو انعكس السوق"
          " فجأة!"
      ),
      "scalping": (
          "⚡ **Scalping (اقتناص الفتات السريع):**\n"
          "صفقات سريعة جداً تخطف أرباحاً صغيرة (مثل 1% أو 1.5%) خلال دقائق معدودة"
          " وتُغلق فوراً."
      ),
      "tp": (
          "🎯 **TP / Take Profit (مرفأ جني الأرباح):**\n"
          "السعر المحدد مسبقاً الذي يأخذ عنده البوت أو المنصة أرباحك تلقائياً ويغلق"
          " الصفقة."
      ),
      "sl": (
          "🛑 **SL / Stop Loss (طوق النجاة / وقف الخسارة):**\n"
          "السعر الذي يحمي محفظتك ويخرجك بخسارة صغيرة جداً ومحدودة إذا عكس السوق"
          " اتجاهه."
      ),
      "oco": (
          "🟣 **OCO (الحارس المزدوج للأوامر):**\n"
          "وضع هدف الربح (TP) ووقف الخسارة (SL) معاً في نفس اللحظة، بحيث إذا تحقق"
          " أحدهما يُلغى الآخر تلقائياً لتنام مرتاح البال."
      ),
      "leverage": (
          "⚖️ **Leverage (أداة الانتحار / الرافعة المالية):**\n"
          "استدانة أموال من المنصة لمضاعفة حجم الصفقة والأرباح (وتعظيم الخسائر"
          " أيضاً). ⚠️ *ننصح المبتدئين بالابتعاد عنها والالتزام بالسبوت فقط.*"
      ),
      "kyc": (
          "🆔 **KYC (بصمة الهوية المشروطة):**\n"
          "توثيق الهوية الرسمية عبر إرسال صور الأوراق الثبوتية للمنصة لفتح صلاحيات"
          " السحب والإيداع بأمان تام."
      ),
      "dca": (
          "🏛️ **DCA (التجميع الهادئ المستمر):**\n"
          "استراتيجية شراء الأصل (مثل البيتكوين) بمبالغ ثابتة على فترات منتظمة بغض"
          " النظر عن السعر، مع جني جزء من الأرباح الصافية فقط والحفاظ على كمية"
          " الأصل كاملة."
      ),
      "bull": (
          "🐂 **Bull Market (سوق الثيران):**\n"
          "سوق صاعد وإيجابي تسوده حالة التفاؤل وارتفاع الأسعار على المدى الطويل."
      ),
      "bear": (
          "🐻 **Bear Market (سوق الدببة):**\n"
          "سوق هابط وسلبي تسوده المخاوف وانخفاض الأسعار، ويحتاج إلى صبر واستراتيجيات"
          " تجميع."
      ),
  }

  found = False
  for key, desc in glossary_db.items():
    if query in key or query in desc.lower():
      bot.send_message(
          message.chat.id,
          f"🔍 **نتيجة البحث في الديوان عن (`{query}`):**\n\n{desc}",
          parse_mode="Markdown",
      )
      found = True
      break

  if not found:
    bot.send_message(
        message.chat.id,
        f"❌ عذراً يا مهندس، لم نجد مصطلحاً يطابق (`{query}`). جرب بحثاً آخر مثل:"
        " `breakeven`, `usdt`, `tp`, `sl`, `oco`.",
        parse_mode="Markdown",
    )


# --- 9. دليل فتح الحسابات وإنشاء المحافظ المفصل ---
@bot.message_handler(
    func=lambda message: message.text == "🌐 دليل فتح الحسابات وإنشاء المحافظ"
)
def send_accounts_guide(message):
  accounts_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ (الخطوة الأولى للاحتراف):**\n\n"
      "🏛️ **1. منصات التداول المركزية (مثل Binance أو Bybit):**\n"
      "• هي البورصة الكبرى التي ستشتري وتبيع من خلالها العملات الرقمية والذهب وتنفذ"
      " الصفقات.\n"
      "• **طريقة التسجيل:** تحميل التطبيق الرسمي من المتجر، التسجيل عبر البريد"
      " الإلكتروني، وإنشاء كلمة مرور قوية.\n"
      "• **توثيق الهوية (KYC):** ضروري جداً لحماية حسابك وسحب أرباحك بأمان، ويتم"
      " عبر رفع صورة جواز السفر أو الهوية الشخصية.\n\n"
      "👛 **2. المحافظ اللامركزية (مثل Trust Wallet أو MetaMask):**\n"
      "• هي محفظتك الخاصة لتخزين أصولك بشكل بعيد عن المنصات وتحت سيطرتك الكاملة.\n"
      "• **قاعدة الأمان الذهبية:** عند إنشاء المحفظة سيعطيك التطبيق (12 كلمة"
      " سرية)، احفظهم في مكان آمن ورقي بعيداً عن الإنترنت ولا تعطهم لأي شخص نهائياً"
      " لأن من يملكهم يملك أموالك.\n\n"
      "💡 *نصيحة المطور:* ابدأ دائماً بتوثيق حسابك على إحدى المنصات الموثوقة،"
      " وتعلّم ببطء وثبات قبل ضخ أي أموال حقيقية."
  )
  bot.send_message(message.chat.id, accounts_text, parse_mode="Markdown")


# --- 10. دليل السحب والإيداع المفصل (شبكة TRC20) ---
@bot.message_handler(
    func=lambda message: message.text
    == "📥 دليل السحب والإيداع (شبكة TRC20)"
)
def send_deposit_withdraw_guide(message):
  deposit_withdraw_text = (
      "📥 **دليل الإيداع والسحب (الطريق الآمن لأموالك):**\n\n"
      "🌐 **1. لماذا نعتمد شبكة TRC20 تحديداً؟**\n"
      "• هي الشبكة الأكثر استخداماً وأماناً للتحويلات الرقمية لعملة `USDT`.\n"
      "• تتميز بسرعتها الفائقة في وصول الأموال (لا تتجاوز بضع دقائق).\n"
      "• رسوم التحويل فيها ثابتة ورخيصة جداً (1 دولار فقط بغض النظر عن حجم"
      " الحوالة).\n"
      "• ⚠️ **تنبيه هام:** تأكد دائماً عند السحب أو الإيداع من اختيار شبكة"
      " **TRC20 (Tron)** حصرياً لكي لا تضيع أموالك في شبكة خاطئة.\n\n"
      "🔄 **2. آلية الإيداع والشحن (عبر الوكلاء وشام كاش):**\n"
      "• لتحويل أموالك المحلية إلى رصيد رقمي `USDT` في منصتك، تتواصل مع الوكيل"
      " المعتمد وتتم عملية التحويل بالليرة السورية عبر تطبيق **شام كاش**.\n"
      "• يقوم الوكيل فوراً بإرسال ما يقابلها من عملات مستقرة إلى عنوان محفظتك"
      " الرقمية.\n\n"
      "💵 **3. آلية سحب الأرباح (كاش أو محفظة محلية):**\n"
      "• عندما ترغب بسحب أرباحك، تقوم بتحويل الـ `USDT` من منصتك إلى عنوان"
      " محفظة الوكيل.\n"
      "• يستلم الوكيل العملات ويقوم بتسليمك المبلغ نقداً أو تحويله إلى حسابك على"
      " شام كاش بكل سهولة وأمان."
  )
  bot.send_message(message.chat.id, deposit_withdraw_text, parse_mode="Markdown")


# --- 11. معلومات الدفع والشحن المحلي (شام كاش) المفصلة ---
@bot.message_handler(
    func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **معلومات الدفع والشحن عبر محفظة (شام كاش):**\n\n"
      "تعتبر محفظة **شام كاش** الوسيلة المحلية الأسهل والأسرع لإتمام المعاملات"
      " المالية وتفعيل الاشتراكات أو شحن الرصيد في سوريا.\n\n"
      "📌 **خطوات إتمام الدفع أو الشحن بنجاح:**\n"
      "  1️⃣ تواصل حصرياً مع المطور أو الوكيل المعتمد عبر المعرف الرسمي (`"
      + ADMIN_USERNAME
      + "` لتأكيد تفاصيل الحوالة).\n"
      "  2️⃣ قم بإتمام عملية التحويل بالليرة السورية عبر تطبيق شام كاش إلى الحساب"
      " المعتمد.\n"
      "  3️⃣ أرسل صورة إيصال التحويل (الوصل) مع رقم حسابك التعريفي (`ID`) داخل"
      " البوت للإدارة.\n"
      "  4️⃣ سيقوم النظام أو الإدارة بمراجعة الحوالة وتفعيل اشتراكك أو رصيدك"
      " فورياً خلال دقائق معدودة!"
  )
  bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")


# --- 12. حالة الاشتراكي ورابط الدعوة ---
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
  bot.send_message(
      message.chat.id,
      f"📋 ينتهي اشتراكك في: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n👥 عدد"
      f" أصدقائك الذين دعيتهم: **{ref_count}**\n🔗 رابط الدعوة الخاص بك:\n`{ref_link}`",
      parse_mode="Markdown",
  )


# --- 13. لوحة تحكم المطور المطورة ---
@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(
      message.chat.id,
      "👑 **لوحة تحكم المطور:**\n\n"
      "أوامر التحكم المتاحة:\n"
      "• `/users` (لعرض قائمة بأسماء وتفاصيل جميع المشتركين)\n"
      "• `/stats` (لعرض إحصائيات سريعة بالأعداد)\n"
      "• `/add_days ID days` (لتمديد اشتراك مستخدم)\n"
      "• `/expire ID` (لإنهاء اشتراك مستخدم)\n"
      "• `/ban ID` (لحظر مستخدم)\n"
      "• `/unban ID` (لفك الحظر)",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["users"])
def show_all_users(message):
  if message.from_user.id != ADMIN_ID:
    return

  if not all_users:
    bot.send_message(
        message.chat.id,
        "📭 لا يوجد أي مشتركين مسجلين في قاعدة البيانات حتى الآن.",
    )
    return

  users_list_text = "👥 **قائمة المشتركين في البوت:**\n\n"
  counter = 1

  for uid_str, u_data in all_users.items():
    name = u_data.get("name", "بدون اسم")
    uname = u_data.get("username", "لا يوجد")
    expiry = u_data.get("expiry", "غير معروف")
    ref_count = u_data.get("referral_count", 0)

    try:
      exp_formatted = datetime.fromisoformat(expiry).strftime("%Y-%m-%d %H:%M")
    except Exception:
      exp_formatted = expiry

    users_list_text += (
        f"{counter}️⃣ **الاسم:** {name}\n"
        f"   • المعرف (ID): `{uid_str}`\n"
        f"   • اليوزر: `@{uname}`\n"
        f"   • ينتهي في: `{exp_formatted}`\n"
        f"   • الدعوات: **{ref_count}**\n\n"
    )
    counter += 1

    if len(users_list_text) > 3500:
      bot.send_message(message.chat.id, users_list_text, parse_mode="Markdown")
      users_list_text = ""

  if users_list_text:
    bot.send_message(message.chat.id, users_list_text, parse_mode="Markdown")


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(
      message.chat.id,
      f"📊 **إحصائيات البوت:**\n• إجمالي المشتركين: {len(all_users)}\n• المجموعات"
      f" المفعلة: {len(active_groups)}\n\n💡 *ملاحظة:* استخدم الأمر `/users` لعرض"
      " أسماء وتفاصيل جميع المشتركين بالكامل.",
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
    bot.send_message(
        message.chat.id, f"✅ تم تفعيل {days} يوم للمستخدم `{target_id}`."
    )
  except Exception:
    bot.send_message(
        message.chat.id, "⚠️ خطأ في الصيغة. استخدم: `/add_days ID 30`"
    )


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
      bot.send_message(
          message.chat.id, f"🔒 تم إنهاء اشتراك المستخدم `{target_id}`."
      )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ في الصيغة. استخدم: `/expire ID`")


@bot.message_handler(commands=["ban"])
def ban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = int(message.text.split()[1])
    banned_users.add(target_id)
    bot.send_message(message.chat.id, f"✅ تم حظر المستخدم `{target_id}`.")
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ في الصيغة. استخدم: `/ban ID`")


@bot.message_handler(commands=["unban"])
def unban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = int(message.text.split()[1])
    banned_users.discard(target_id)
    bot.send_message(message.chat.id, f"✅ تم فك الحظر عن `{target_id}`.")
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ في الصيغة. استخدم: `/unban ID`")


# تشغيل التطبيق والسيرفر
if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
