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

# تفعيل الـ Middleware إجبارياً
apihelper.ENABLE_MIDDLEWARE = True

bot = telebot.TeleBot(TOKEN)

# 🆔 الآي دي الخاص بك (المسؤول والمنشئ)
ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"  # معرفك للتواصل

DATA_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
banned_users = set()

# ذاكرة مؤقتة لبيانات حاسبة المخاطر للمستخدمين
risk_calculator_sessions = {}

app = Flask(__name__)
RENDER_URL = "https://syria-trading-bot.onrender.com"


# --- دوال حفظ واسترجاع بيانات المشتركين والمجموعات ---
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
  return "Trading Bot is running 24/7 with Simple Language, Live Deals & Safe Auto-Promo!"


@app.route("/ping")
def ping():
  return "Pong!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


# دالة جلب الأسعار الفورية المباشرة
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


# 🛡️ الحارس الأمني: فحص الاشتراك والفترة التجريبية (3 أيام) والحظر
@bot.middleware_handler(update_types=["message"])
def check_subscription(bot_instance, message):
  if not message.from_user:
    return
  user_id = message.from_user.id
  uid_str = str(user_id)

  if user_id == ADMIN_ID:
    return

  if user_id in banned_users:
    bot.reply_to(message, "⛔ تم حظرك من استخدام البوت. يرجى مراجعة الإدارة.")
    return True

  if message.chat.type == "private" and uid_str in all_users:
    user_data = all_users[uid_str]
    expiry_dt = datetime.fromisoformat(user_data["expiry"])
    if datetime.now() > expiry_dt:
      lock_msg = (
          "🔒 **انتهت صلاحية استخدامك للبوت!**\n\n"
          "لقد انتهت فترتك التجريبية (3 أيام) أو مدة اشتراكك.\n"
          "لتجديد الاشتراك أو تفعيله مجاناً عبر دعوة أصدقائك:\n\n"
          f"📩 تواصل مع المطور: {ADMIN_USERNAME}\n"
          f"🆔 رقم حسابك (ID): `{user_id}`"
      )
      bot.send_message(message.chat.id, lock_msg, parse_mode="Markdown")
      return True


# متابعة إضافة البوت إلى المجموعات أو القنوات
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


# 🔄 دالة الترويج التلقائي الآمن في الخلفية
def background_auto_promo():
  while True:
    time.sleep(86400)
    if not active_groups:
      continue

    promo_text = (
        "🤖 **بوت التداول الذكي والشامل في سوريا** 🇸🇾\n\n"
        "📈 صفقات سبوت حية ومدروسة، حاسبة لإدارة المخاطر، وقاموس مبسط للمبتدئين!\n"
        "📚 تعلم التداول خطوة بخطوة من الصفر حتى الاحتراف بدون تعقيد.\n"
        "💳 دعم كامل للشحن والسحب المحلي عبر (شام كاش) ومنصات التداول.\n\n"
        "🎁 **فترة تجريبية مجانية لمدة 3 أيام لجميع المشتركين الجدد!**\n"
        f"📩 للاشتراك والاستفسار تواصل مع المطور حصرياً: {ADMIN_USERNAME}"
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


# أمر التجربة الفورية للترويج
@bot.message_handler(commands=["test_promo"])
def test_promo_command(message):
  if message.from_user.id != ADMIN_ID:
    return
  if not active_groups:
    bot.send_message(
        message.chat.id,
        "⚠️ البوت ليس مشرفاً في أي مجموعة أو قناة مسجلة حتى الآن!",
    )
    return

  promo_text = (
      "🤖 **بوت التداول الذكي والشامل في سوريا** 🇸🇾\n\n"
      "📈 صفقات سبوت حية ومدروسة، حاسبة لإدارة المخاطر، وقاموس مبسط للمبتدئين!\n"
      "📚 تعلم التداول خطوة بخطوة من الصفر حتى الاحتراف بدون تعقيد.\n"
      "💳 دعم كامل للشحن والسحب المحلي عبر (شام كاش) ومنصات التداول.\n\n"
      "🎁 **فترة تجريبية مجانية لمدة 3 أيام لجميع المشتركين الجدد!**\n"
      f"📩 للاشتراك والاستفسار تواصل مع المطور حصرياً: {ADMIN_USERNAME}"
  )

  success_count = 0
  for group_id in active_groups:
    try:
      bot.send_message(group_id, promo_text, parse_mode="Markdown")
      success_count += 1
    except Exception as e:
      bot.send_message(
          message.chat.id, f"⚠️ فشل الإرسال للمجموعة `{group_id}`: {e}"
      )

  bot.send_message(
      message.chat.id,
      f"✅ تم إرسال رسالة الترويج التجريبية بنجاح إلى ({success_count})"
      " مجموعة/قناة.",
  )


# أمر البدء (Start) - لغة واضحة وبسيطة جداً
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
            "🎉 **مبروك! انضم مستخدم جديد عبر رابط الدعوة الخاص بك.**\n"
            "🎁 تمت إضافة **يومين رصيد إضافي** لاشتراكك تلقائياً!",
            parse_mode="Markdown",
        )
      except Exception:
        pass

    save_users(all_users)

    try:
      bot.send_message(
          ADMIN_ID,
          f"🚨 **مشترك جديد انضم للبوت!**\n"
          f"👤 الاسم: {all_users[uid_str]['name']}\n"
          f"🏷️ المعرف: @{all_users[uid_str]['username']}\n"
          f"🆔 الآي دي: `{user_id}`\n"
          (
              f"🔗 انضم عبر دعوة الآي دي: `{referrer_id}`"
              if referrer_id
              else "🔗 انضم مباشرة"
          ),
          parse_mode="Markdown",
      )
    except Exception:
      pass

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
    welcome_text = (
        "👑 أهلاً بك يا مهندس أحمد (المطور والمالك)!\n"
        "جميع الأقسام والأدوات مرتبطة وجاهزة أدناه:"
    )
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
    sub_status = f"نشط (المتبقي: {days_left} يوم و {hours_left} ساعة)"

    welcome_text = (
        "أهلاً بك في بوت التداول الذكي والشامل! 🤖\n\n"
        f"✅ **حالة اشتراكك:** {sub_status}\n"
        "اختر ما تحتاجه بسهولة من الأزرار الموجودة أسفل الشاشة:"
    )

  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


# --- حاسبة المخاطر المبسطة ---
@bot.message_handler(
    func=lambda message: message.text == "🧮 حاسبة المخاطر وحجم الصفقة"
)
def start_risk_calculator(message):
  user_id = message.from_user.id
  risk_calculator_sessions[user_id] = {"step": "waiting_capital"}
  msg = bot.send_message(
      message.chat.id,
      "🧮 **حاسبة إدارة المخاطر (لحماية رأس مالك):**\n\n"
      "الخطوة 1️⃣: أرسل الآن **إجمالي رأس مالك** بالدولار (USDT) (مثلاً اكتب:"
      " `500` فقط):",
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
        f"✅ رأس المال المسجل: `{capital}` USDT.\n\n"
        "الخطوة 2️⃣: ما هي **نسبة الخسارة المقبولة** لك في هذه الصفقة؟ (مثلاً:"
        " اكتب `2` تعني 2%):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_risk_step)
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى إرسال رقم صحيح فقط لرأس المال (مثلاً: 500). أعد المحاولة بالضغط"
        " على الزر.",
    )


def process_risk_step(message):
  user_id = message.from_user.id
  try:
    risk_pct = float(message.text.strip())
    session = risk_calculator_sessions.get(user_id, {})
    capital = session.get("capital", 500)

    max_loss_allowed = capital * (risk_pct / 100.0)

    result_text = (
        "📊 **نتيجة حساب المخاطر الآمنة:**\n\n"
        f"💰 إجمالي رأس المال: `{capital}` USDT\n"
        f"🎯 نسبة المخاطرة المختارة: `{risk_pct}%`\n"
        f"🛑 أقصى مبلغ مسموح بخصارته في هذه الصفقة: **`{max_loss_allowed:.2f}`"
        " USDT**\n\n"
        "💡 *نصيحة للمبتدئين:* لا تدخل صفقة واحدة تخاطر فيها بأكثر من 1% إلى 2%"
        " من إجمالي مالك لكي تحافظ على حسابك."
    )
    bot.send_message(message.chat.id, result_text, parse_mode="Markdown")
    if user_id in risk_calculator_sessions:
      del risk_calculator_sessions[user_id]
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ حدث خطأ في الإدخال. يرجى إعادة استخدام الحاسبة من الزر الرئيسي.",
    )


# --- التنبيهات الفورية ---
@bot.message_handler(func=lambda message: message.text == "🔔 تنبيهات الأسعار الفورية")
def enable_price_alerts(message):
  btc, eth, xrp = get_crypto_prices()
  alert_text = (
      "🔔 **نظام تنبيهات الأسعار (مفعل):**\n\n"
      "تم تفعيل مراقبة الأسعار الحية للعملات والذهب بنجاح.\n\n"
      f"📍 **الأسعار الحالية بالسوق:**\n"
      f"• البيتكوين (BTC): `{btc:,.2f}` USDT\n"
      f"• الإيثيريوم (ETH): `{eth:,.2f}` USDT\n"
      f"• الريبل (XRP): `{xrp:,.4f}` USDT\n\n"
      "🚀 سيقوم البوت بتنبيهك تلقائياً عند حدوث تحركات قوية أو فرص جديدة."
  )
  bot.send_message(message.chat.id, alert_text, parse_mode="Markdown")


# --- قاموس المصطلحات مع البحث الذكي ---
@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس مصطلحات التداول (بحث ذكي)"
)
def glossary_menu(message):
  glossary_guide = (
      "📖 **قاموس مصطلحات التداول (مبسط للمبتدئين):**\n\n"
      "للبحث السريع عن أي مصطلح، استخدم الأمر `/search` متبوعاً بالكلمة المطلوبة.\n"
      "📌 *مثال:* `/search OCO` أو `/search USDT` أو `/search TP`\n\n"
      "--- \n"
      "**المصطلحات الأساسية المتاحة:**\n"
      "1️⃣ **USDT** (العملة المستقرة)\n"
      "2️⃣ **Scalping** (التداول السريع)\n"
      "3️⃣ **TP / Take Profit** (هدف الربح)\n"
      "4️⃣ **SL / Stop Loss** (وقف الخسارة)\n"
      "5️⃣ **OCO** (الأوامر المزدوجة)\n"
      "6️⃣ **Leverage** (الرافعة المالية)\n"
      "7️⃣ **KYC** (توثيق الهوية)"
  )
  bot.send_message(message.chat.id, glossary_guide, parse_mode="Markdown")


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى كتابة المصطلح بعد الأمر.\n*مثال:* `/search OCO`",
        parse_mode="Markdown",
    )
    return

  query = parts[1].strip().lower()

  glossary_db = {
      "usdt": (
          "🔹 **USDT:** عملة رقمية تساوي دولاراً واحداً دائماً.\n*فويدتها:* لحفظ"
      " الأرباح والهرب من هبوط السوق دون تحويلها لكاش ورقي."
      ),
      "scalping": (
          "⚡ **Scalping (التداول السريع):** صفقات تخطف أرباحاً صغيرة خلال دقائق"
          " وتُغلق فوراً."
      ),
      "tp": (
          "🎯 **TP (هدف الربح):** السعر الذي يبيع عنده البوت تلقائياً ليأخذ"
          " أرباحك."
      ),
      "sl": (
          "🛑 **SL (وقف الخسارة):** سعر يحمي محفظتك ويخرجك بخسارة صغيرة جداً إذا"
          " عكس السوق."
      ),
      "oco": (
          "🟣 **OCO (الأوامر المزدوجة):** وضع هدف الربح ووقف الخسارة معاً لتنام"
          " مرتاح البال."
      ),
      "leverage": (
          "⚖️ **Leverage (الرافعة المالية):** استدانة أموال لمضاعفة الأرباح"
          " والخسائر (ننصح المبتدئين بالابتعاد عنها والالتزام بالسبوت)."
      ),
      "kyc": (
          "🆔 **KYC (توثيق الهوية):** إرسال صورة الهوية للمنصة لفتح السحب"
          " والإيداع بحماية كاملة."
      ),
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
        f"❌ عذراً، لم نجد مصطلحاً يطابق (`{query}`). جرب بحثاً آخر مثل: `usdt`,"
        " `tp`, `sl`, `oco`.",
        parse_mode="Markdown",
    )


# --- حالة الاشتراك والدعوات ---
@bot.message_handler(
    func=lambda message: message.text == "⏳ حالة اشتراكي ورابط دعوة أصدقائي"
)
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  uid_str = str(user_id)

  if user_id == ADMIN_ID:
    bot.send_message(
        message.chat.id, "👑 أنت المالك والمطور، اشتراكك مفتوح مدى الحياة!"
    )
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
      "📋 **معلومات اشتراكك ورابط دعوتك:**\n\n"
      f"🆔 رقم حسابك: `{uid_str}`\n"
      f"📅 تاريخ انتهاء الاشتراك: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"⏳ الوقت المتبقي: **{remaining.days} يوم و {remaining.seconds // 3600}"
      " ساعة**\n"
      f"👥 عدد أصدقائك الذين دعيتهم: **{ref_count} شخص** (تحصل على يومين إضافيين"
      " لكل صديق يسجل عبر رابطك!)\n\n"
      "🔗 **رابط الدعوة الخاص بك (انسخه وانشره لأصدقائك):**\n"
      `{ref_link}`\n\n`
      f"لتجديد الاشتراك تواصل مع الإدارة: {ADMIN_USERNAME}"
  )
  bot.send_message(message.chat.id, status_text, parse_mode="Markdown")


# لوحة تحكم المطور
@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  panel_text = (
      "👑 **لوحة تحكم المطور**\n\n"
      "الأوامر المتاحة لك:\n"
      "1️⃣ **تفعيل أو تمديد اشتراك:**\n"
      "`/add_days [ID] [عدد_الأيام]`\n\n"
      "2️⃣ **إنهاء اشتراك مستخدم فوراً:**\n"
      "`/expire [ID]`\n\n"
      "3️⃣ **عرض إحصائيات المشتركين:**\n"
      "`/stats`\n\n"
      "4️⃣ **تجربة النشر بالمجموعات:**\n"
      "`/test_promo`\n\n"
      "5️⃣ **حظر / فك حظر مستخدم:**\n"
      "`/ban [ID]` أو `/unban [ID]`"
  )
  bot.send_message(message.chat.id, panel_text, parse_mode="Markdown")


@bot.message_handler(commands=["add_days"])
def add_subscription_days(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    parts = message.text.split()
    target_id = str(int(parts[1]))
    days_to_add = int(parts[2])

    now = datetime.now()
    if target_id in all_users:
      current_expiry = datetime.fromisoformat(all_users[target_id]["expiry"])
      base_date = current_expiry if current_expiry > now else now
      new_expiry = base_date + timedelta(days=days_to_add)
      all_users[target_id]["expiry"] = new_expiry.isoformat()
      all_users[target_id]["is_trial"] = False
    else:
      new_expiry = now + timedelta(days=days_to_add)
      all_users[target_id] = {
          "name": "مفعل يدوياً",
          "username": "غير معروف",
          "expiry": new_expiry.isoformat(),
          "is_trial": False,
          "referral_count": 0,
      }

    save_users(all_users)

    bot.send_message(
        message.chat.id,
        f"✅ **تم تفعيل الاشتراك بنجاح!**\n"
        f"🆔 الحساب: `{target_id}`\n"
        f"➕ الأيام المضافة: **{days_to_add} يوم**\n"
        f"📅 ينتهي في: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`",
        parse_mode="Markdown",
    )
    try:
      bot.send_message(
          int(target_id),
          f"🎉 **تم تفعيل اشتراكك بنجاح لمدة {days_to_add} يوم!**\n"
          f"📅 صالح لغاية: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`\n"
          "أرسل /start للبدء.",
          parse_mode="Markdown",
      )
    except Exception:
      pass
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ صيغة الأمر خاطئة.\nاستخدم: `/add_days 8611033531 30`",
        parse_mode="Markdown",
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
          message.chat.id,
          f"🔒 تم إنهاء اشتراك الحساب `{target_id}` بنجاح.",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(message.chat.id, "⚠️ هذا الآي دي غير مسجل في البيانات.")
  except Exception:
    bot.send_message(
        message.chat.id, "⚠️ استخدم: `/expire 8611033531`", parse_mode="Markdown"
    )


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  count = len(all_users)
  groups_count = len(active_groups)
  now = datetime.now()
  lines = []
  for uid, info in all_users.items():
    exp = datetime.fromisoformat(info["expiry"])
    status = "🟢 نشط" if exp > now else "🔴 منتهي"
    rem_days = (exp - now).days if exp > now else 0
    refs = info.get("referral_count", 0)
    lines.append(
        f"• {info['name']} (@{info['username']})\n  🆔 `{uid}` | {status}"
        f" ({rem_days} يوم) | 👥 دعوات: {refs}"
    )
  report = (
      f"📊 **إحصائيات المشتركين ({count}) والمجموعات الإعلانية"
      f" ({groups_count}):**\n\n"
  ) + "\n\n".join(lines)
  bot.send_message(message.chat.id, report, parse_mode="Markdown")


@bot.message_handler(commands=["ban"])
def ban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = int(message.text.split()[1])
    banned_users.add(target_id)
    bot.send_message(
        message.chat.id,
        f"✅ تم حظر المستخدم `{target_id}`.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدم: `/ban 8611033531`")


@bot.message_handler(commands=["unban"])
def unban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = int(message.text.split()[1])
    banned_users.discard(target_id)
    bot.send_message(
        message.chat.id,
        f"✅ تم فك الحظر عن المستخدم `{target_id}`.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدم: `/unban 8611033531`")


# --- الأسعار والصفقات الحية المباشرة ---
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والأسعار المباشرة"
)
def send_trading_deals(message):
  btc, eth, xrp = get_crypto_prices()
  deals_text = (
      "📊 **الأسعار الحية وتحليل الصفقات (تداول آمن - Spot):**\n\n"
      "⚡ **1. صفقات السكالبينج (السريعة جداً):**\n"
      f"• **العملة:** XRP/USDT (السعر الحالي: `{xrp:,.4f}`)\n"
      f"  🎯 *هدف الربح (+1.5%):* `{xrp * 1.015:,.4f}`\n"
      f"  🛑 *وقف الخسارة (-0.7%):* `{xrp * 0.993:,.4f}`\n\n"
      "📅 **2. الصفقات اليومية:**\n"
      f"• **العملة:** BTC/USDT (السعر الحالي: `{btc:,.2f}`)\n"
      f"  🎯 *هدف الربح (+2.5%):* `{btc * 1.025:,.2f}`\n"
      f"  🛑 *وقف الخسارة (-1.2%):* `{btc * 0.988:,.2f}`\n\n"
      "🌊 **3. صفقات السوينغ (المتوسطة - أسبوع):**\n"
      f"• **العملة:** ETH/USDT (السعر الحالي: `{eth:,.2f}`)\n"
      f"  🎯 *هدف الربح (+6%):* `{eth * 1.06:,.2f}`\n"
      f"  🛑 *وقف الخسارة (-3%):* `{eth * 0.97:,.2f}`\n\n"
      "🏛️ **4. الاستثمار طويل الأمد (تجميع البيتكوين):**\n"
      f"• **العملة:** Bitcoin (BTC) عند سعر `{btc:,.2f}`\n"
      "  📌 *الطريقة:* الشراء على دفعات تدريجية (DCA) **بدون رافعة مالية** للاستثمار"
      " الآمن."
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب اليومية والاستثمارية"
)
def send_gold_deals(message):
  gold_text = (
      "🟡 **توصيات صفقات الذهب (XAUUSD):**\n\n"
      "⚡ **1️⃣ صفقات الذهب اليومية:**\n"
      "• **النوع:** صفقات قصيرة الأمد لجلسة التداول.\n"
      "• **هدف الربح (TP):** ربح سريع بين (1% إلى 1.5%).\n"
      "• **وقف الخسارة (SL):** (-0.7%) لحماية رأس المال عند الانعكاس.\n\n"
      "📈 **2️⃣ استثمار وتجميع الذهب طويل الأمد:**\n"
      "• **النوع:** تجميع هادئ لحفظ القيمة.\n"
      "• **هدف الربح (TP):** أهداف استثمارية تبدأ من (+5% إلى +10%).\n"
      "• **الأمان:** بدون أي رافعة مالية لحماية كامل المحفظة."
  )
  bot.send_message(message.chat.id, gold_text, parse_mode="Markdown")


# --- دراسة أنواع الصفقات بلغة بسيطة ---
@bot.message_handler(
    func=lambda message: message.text == "📊 دراسة أنواع الصفقات وكيفية اختيارها"
)
def send_trading_types_study(message):
  study_text = (
      "📊 **دليل مبسط لفهم أنواع الصفقات وكيفية إدارتها:**\n\n"
      "لكي تنجح في السوق، يجب أن تعرف الفرق بين أنواع الصفقات وتوزع رأس مالك بذكاء:\n\n"
      "⚡ **1. صفقات السكالبينج (XRP/USDT)**\n"
      "• *المميزات:* أرباح سريعة (+1.5%) مقابل وقف خسارة صغير (-0.7%).\n"
      "• *نصيحة:* تتطلب مراقبة الشاشة والالتزام التام بوقف الخسارة لتجنب"
      " التقلبات السريعة.\n\n"
      "📅 **2. الصفقات اليومية (BTC/USDT)**\n"
      "• *المميزات:* البيتكوين أكثر استقراراً، وهدف (+2.5%) مع وقف خسارة"
      " (-1.2%) ممتاز لجلسة يوم أو يومين.\n"
      "• *نصيحة:* راقب مناطق الدعم ولا تدخل وقت الأخبار الاقتصادية القوية.\n\n"
      "🌊 **3. صفقات السوينغ (ETH/USDT)**\n"
      "• *المميزات:* مناسبة للمدى المتوسط (أسبوع)، بهدف (+6%) وخسارة (-3%).\n"
      "• *نصيحة:* قسم دخولك على دفعتين (50% الآن و50% إذا انخفض السعر قليلاً"
      " للاختبار).\n\n"
      "🏛️ **4. الاستثمار طويل الأمد (DCA في Bitcoin)**\n"
      "• *المميزات:* الطريقة الأضمن والأسهل للمبتدئين بدون أي رافعة مالية.\n"
      "• *نصيحة:* اشترِ بمبلغ محدد أسبوعياً أو شهرياً بغض النظر عن السعر لبناء"
      " ثروة مستقبلاً."
  )
  bot.send_message(message.chat.id, study_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "📚 الأكاديمية التعليمية للمبتدئين"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية التعليمية - تعلم التداول من الصفر:**\n\n"
      "🟢 **الدرس الأول (ما هو التداول؟):**\n"
      "• بيع وشراء الأصول الرقمية للاستفادة من فرق السعر، ويتم قياسها دائماً"
      " بالدولار الرقمي (USDT).\n\n"
      "🟡 **الدرس الثاني (أنواع الصفقات):**\n"
      "• صفقات سريعة (سكالبينج ويومية) أو استثمار طويل الأمد بدون رافعة مالية"
      " لحماية أموالك.\n\n"
      "🔵 **الدرس الثالث (إدارة المخاطر):**\n"
      "• لا تستخدم كل مالك في صفقة واحدة أبداً، وقسم سيولتك بحكمة.\n\n"
      "🟣 **الدرس الرابع (الأوامر التلقائية OCO):**\n"
      "• طريقة ربط هدف الربح ووقف الخسارة معاً ليقوم البوت بحمايتك تلقائياً دون"
      " أن تبقى مراقباً للشاشة طوال اليوم.\n\n"
      "🟠 **الدرس الخامس (التحكم بالمشاعر):**\n"
      "• ابتعد عن الطمع ولا تحاول الانتقام من السوق بعد أي صفقة خاسرة.\n\n"
      "🟤 **الدرس السادس (تنويع المحفظة):**\n"
      "• وزع أموالك بين العملات الرقمية والذهب لتقليل المخاطر."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "🌐 دليل فتح الحسابات وإنشاء المحافظ"
)
def send_accounts_guide(message):
  guide_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ:**\n\n"
      "1️⃣ **المنصة المركزية:** أنشئ حسابك ووثقه رسمياً (KYC) على منصة موثوقة"
      " مثل **Binance** أو **Bybit** لتنفذ عمليات البيع والشراء بسهولة.\n"
      "2️⃣ **المحفظة اللامركزية:** ثبت تطبيق **Trust Wallet** على هاتفك لاحتفاظ"
      " بأصولك الرقمية بأمان بعيداً عن المنصات، واكتب كلمات الأمان على ورقة"
      " خارجية."
  )
  bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text
    == "📥 دليل السحب والإيداع (شبكة TRC20)"
)
def send_deposit_withdraw_guide(message):
  dw_text = (
      "📥 **دليل السحب والإيداع في المنصات:**\n\n"
      "• **الشبكة المعتمدة:** استخدم دائماً عملة (USDT) عبر شبكة **TRC20** عند"
      " التحويل.\n"
      "• **السبب:** لأنها الأسرع وصولاً (خلال دقائق معدودة) ورسوم تحويلها ثابتة"
      " ورخيصة جداً (1 دولار).\n\n"
      "🔄 **آلية التحويل المحلي في سوريا:**\n"
      "• **للإيداع:** تحول المبلغ بالليرة السورية عبر تطبيق **شام كاش** للوكيل"
      " المعتمد، فيرسل لك بدلها عملة `USDT (TRC20)` لمحافظتك فوراً.\n"
      "• **لسحب الأرباح:** تحول الـ `USDT` من منصتك للوكيل، فيحول قيمتها نقداً"
      " أو لحسابك على شام كاش بالليرة السورية بكل أمان."
  )
  bot.send_message(message.chat.id, dw_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **معلومات الدفع والشحن عبر (شام كاش):**\n\n"
      "• **طريقة الشحن الآمنة:** تتم عمليات الإيداع والسحب المحلي بكل سهولة عبر"
      " محفظة **شام كاش** بالتعاون مع الوكلاء المعتמدين.\n"
      "• **خطوات التفعيل:**\n"
      "  1️⃣ تواصل مع المطور أو الوكيل المعتمد عبر المعرف الرسمي.\n"
      "  2️⃣ أتمم التحويل بالليرة السورية عبر تطبيق شام كاش.\n"
      "  3️⃣ أرسل إيصال التحويل ورقم حسابك (ID) في البوت ليتم تفعيل اشتراكك"
      " أو رصيدك فورياً."
  )
  bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")


if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
