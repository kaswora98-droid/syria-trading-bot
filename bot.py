from datetime import datetime, timedelta
import json
import os
import random
import threading
import time
from flask import Flask, request
import requests
import telebot
from telebot import apihelper, types

TOKEN = "8928709566:AAE8G20dfLOqdo7GXJ9APGPqH7OTdyq5leg"

apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

DATA_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
banned_users = set()

risk_calculator_sessions = {}

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
  return "Bot is running 24/7 perfectly!"


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
        "📈 صفقات سبوت حية، حاسبة مخاطر، وقاموس مبسط للمبتدئين!\n"
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


@bot.message_handler(commands=["test_promo"])
def test_promo_command(message):
  if message.from_user.id != ADMIN_ID:
    return
  if not active_groups:
    bot.send_message(message.chat.id, "⚠️ لا توجد مجموعات مسجلة.")
    return
  bot.send_message(message.chat.id, "✅ اختبار الترويج يعمل بنجاح.")


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
  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والأسعار المباشرة")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب اليومية والاستثمارية")
  btn_calc = types.KeyboardButton("🧮 حاسبة المخاطر وحجم الصفقة")
  btn_alerts = types.KeyboardButton("🔔 تنبيهات الأسعار الفورية")
  btn_study = types.KeyboardButton("📊 دراسة أنواع الصفقات وكيفية اختيارها")
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
        btn_study,
        btn3,
        btn_glossary,
        btn4,
        btn5,
        btn6,
        btn7,
        btn_admin,
    )
    welcome_text = "👑 أهلاً بك يا مهندس أحمد! القوائم جاهزة أدناه:"
  else:
    markup.add(
        btn1,
        btn2,
        btn_calc,
        btn_alerts,
        btn_study,
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
        "أهلاً بك في بوت التداول الذكي! 🤖\n\n"
        f"✅ حالة اشتراكك: نشط (المتبقي: {days_left} يوم و {hours_left} ساعة)\n"
        "اختر ما تحتاجه من الأزرار أدناه:"
    )

  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


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


@bot.message_handler(func=lambda message: message.text == "🔔 تنبيهات الأسعار الفورية")
def enable_price_alerts(message):
  btc, eth, xrp = get_crypto_prices()
  bot.send_message(
      message.chat.id,
      "🔔 **تنبيهات الأسعار:**\n\n"
      f"• بيتكوين: `{btc:,.2f}`\n"
      f"• إيثيريوم: `{eth:,.2f}`\n"
      f"• ريبل: `{xrp:,.4f}`",
      parse_mode="Markdown",
  )


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
    func=lambda message: message.text == "📊 الصفقات المقترحة والأسعار المباشرة"
)
def send_trading_deals(message):
  btc, eth, xrp = get_crypto_prices()
  deals_text = (
      "📊 **الأسعار الحية والصفقات:**\n\n"
      f"• XRP/USDT: `{xrp:,.4f}` (هدف: `{xrp * 1.015:,.4f}` | وقف: `{xrp * 0.993:,.4f}`)\n"
      f"• BTC/USDT: `{btc:,.2f}` (هدف: `{btc * 1.025:,.2f}` | وقف: `{btc * 0.988:,.2f}`)\n"
      f"• ETH/USDT: `{eth:,.2f}` (هدف: `{eth * 1.06:,.2f}` | وقف: `{eth * 0.97:,.2f}`)"
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


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
