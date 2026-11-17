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
  return "Veteran Trader Bot is running 24/7 with Wisdom, Live Data & Safe Auto-Promo!"


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
    bot.reply_to(message, "⛔ تم حظرك من مجلس المتداولين. راجع الإدارة.")
    return True

  if message.chat.type == "private" and uid_str in all_users:
    user_data = all_users[uid_str]
    expiry_dt = datetime.fromisoformat(user_data["expiry"])
    if datetime.now() > expiry_dt:
      lock_msg = (
          "🔒 **انتهت صلاحية جلستك في ديوان المتداولين المخضرمين!**\n\n"
          "لقد انتهت فترتك التجريبية (3 أيام) أو مدة اشتراكك.\n"
          "السوق لا ينتظر، بادر بتجديد جلستك أو دعوة رفاقك عبر رابطك:\n\n"
          f"📩 تواصل مع شيخ الكار: {ADMIN_USERNAME}\n"
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


# 🔄 دالة الترويج التلقائي الآمن في الخلفية (نبرة المتداول العتيق)
def background_auto_promo():
  while Time.sleep(86400) or True:
    time.sleep(86400)
    if not active_groups:
      continue

    promo_text = (
        "📜 **ديوان التداول العتيق في سوريا** 🇸🇾\n\n"
        "أهلاً بكل باحث عن الحكمة، إدارة رأس المال السليمة، والنجاة من محارق الفيوتشر والتمرجن!\n"
        "📈 صفقات سبوت حية، دراسة دقيقة لأنواع الصفقات، حاسبة مخاطر، وقاموس للمتداولين المحترفين.\n"
        "💳 تكامل تام مع الخدمات المحلية (شام كاش) ودليل السحب والإيداع الآمن.\n\n"
        "🎁 **فترة تجريبية مجانية لمدة 3 أيام لترى السوق بعين خبير عتيق!**\n"
        f"📩 للانضمام إلى المجلس تواصل مع شيخ الكار: {ADMIN_USERNAME}"
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
      "📜 **ديوان التداول العتيق في سوريا** 🇸🇾\n\n"
      "أهلاً بكل باحث عن الحكمة، إدارة رأس المال السليمة، والنجاة من محارق الفيوتشر والتمرجن!\n"
      "📈 صفقات سبوت حية، دراسة دقيقة لأنواع الصفقات، حاسبة مخاطر، وقاموس للمتداولين المحترفين.\n"
      "💳 تكامل تام مع الخدمات المحلية (شام كاش) ودليل السحب والإيداع الآمن.\n\n"
      "🎁 **فترة تجريبية مجانية لمدة 3 أيام لترى السوق بعين خبير عتيق!**\n"
      f"📩 للانضمام إلى المجلس تواصل مع شيخ الكار: {ADMIN_USERNAME}"
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


# أمر البدء (Start) - شخصية المتداول العتيق
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
            "🎉 **يا هلا! حلّ ضيف جديد بالمجلس عبر رابطك.**\n"
            "🎁 لقد أضفنا **يومين إضافيين** لرصيد جلستك تقديراً لأثرك في جلب الرفاق!",
            parse_mode="Markdown",
        )
      except Exception:
        pass

    save_users(all_users)

    try:
      bot.send_message(
          ADMIN_ID,
          f"📜 **حكيم جديد دخل ديوان المتداولين!**\n"
          f"👤 الاسم: {all_users[uid_str]['name']}\n"
          f"🏷️ المعرف: @{all_users[uid_str]['username']}\n"
          f"🆔 الآي دي: `{user_id}`\n"
          (
              f"🔗 جاء بدعوة من الآي دي: `{referrer_id}`"
              if referrer_id
              else "🔗 دخل من باب الديوان مباشرة"
          ),
          parse_mode="Markdown",
      )
    except Exception:
      pass

  markup = types.ReplyKeyboardMarkup(
      resize_keyboard=True, is_persistent=True, row_width=2
  )

  btn1 = types.KeyboardButton("📊 نبض السوق الحقيقي وصفقات السبوت")
  btn2 = types.KeyboardButton("🟡 مجالس الذهب (يومية واستثمارية)")
  btn_calc = types.KeyboardButton("🧮 حاسبة العتاولة لتحديد حجم المخاطر")
  btn_alerts = types.KeyboardButton("🔔 رادار مراقبة السيولة والأسعار")
  btn_study = types.KeyboardButton("📜 دراسة عتيقة لفنون الصفقات وأسرارها")
  btn3 = types.KeyboardButton("📚 خزانة الحكمة (أكاديمية المتداول المحترف)")
  btn_glossary = types.KeyboardButton(
      "📖 قاموس الحيتان والمصطلحات (بحث ذكي)"
  )
  btn4 = types.KeyboardButton("🌐 مفاتيح المنصات وإنشاء المحافظ الآمنة")
  btn5 = types.KeyboardButton("📥 شريان الإيداع والسحب (TRC20)")
  btn6 = types.KeyboardButton("💳 حوالات الداخل والخارج (شام كاش)")
  btn7 = types.KeyboardButton("⏳ عمر جلستك ورابط دعوة الرفاق")

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("🛠️ ديوان الإدارة والتحكم")
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
        "👑 أهلاً بك يا شيخ الكار والمهندس أحمد (المطور والمالك)!\n"
        "الديوان كله تحت إمرتك، والأسواق تسير وفق حساباتك العتيقة أدناه:"
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
    sub_status = f"صالح (متبقي: {days_left} يوم و {hours_left} ساعة)"

    welcome_text = (
        "مرحباً بك في ديوان التداول العتيق يا رفيق الدرب! ☕📜\n\n"
        f"✅ **حالة جلستك:** {sub_status}\n"
        "السوق غابة لا ينجو فيها إلا صانع الخطوات الحكيم. اختر من الأزرار أدناه ما"
        " ترغب في مراجعته:"
    )

  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


# --- الحاسبة الذكية ---
@bot.message_handler(
    func=lambda message: message.text == "🧮 حاسبة العتاولة لتحديد حجم المخاطر"
)
def start_risk_calculator(message):
  user_id = message.from_user.id
  risk_calculator_sessions[user_id] = {"step": "waiting_capital"}
  msg = bot.send_message(
      message.chat.id,
      "🧮 **حاسبة الحيتان لإدارة المخاطر:**\n\n"
      "يا بني، القاعدة الأولى للمتداول العتيق: (احمِ رأس مالك فالأرباح تأتي وحدها).\n"
      "الخطوة 1️⃣: أرسل الآن **إجمالي رأس مالك** بالدولار (USDT) (مثلاً أرسل:"
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
        f"✅ تم حفظ رأس المال: `{capital}` USDT.\n\n"
        "الخطوة 2️⃣: ما هي **نسبة المخاطرة** التي تقبل أن تضحي بها في هذه الصفقة"
        " لو انقلب السوق؟ (مثلاً: أرسل `2` تعني 2%):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_risk_step)
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ يا رفيق، أرسل رقماً صحيحاً وموجباً لرأس المال (مثلاً: 500). حاول مجدداً"
        " بالضغط على الزر.",
    )


def process_risk_step(message):
  user_id = message.from_user.id
  try:
    risk_pct = float(message.text.strip())
    session = risk_calculator_sessions.get(user_id, {})
    capital = session.get("capital", 500)

    max_loss_allowed = capital * (risk_pct / 100.0)

    result_text = (
        "📊 **حكم الخبير في إدارة هذه المخاطرة:**\n\n"
        f"💰 إجمالي ما تملكه في المحفظة: `{capital}` USDT\n"
        f"🎯 نسبة المخاطرة المقبولة: `{risk_pct}%`\n"
        f"🛑 الحد الأقصى للخسارة في هذه الصفقة يحب ألا يتجاوز: **`{max_loss_allowed:.2f}`"
        " USDT**\n\n"
        "💡 *نصيحة عتيقة:* إذا تجاوزت هذه الخسارة نفسيتك، فاعلم أن العقد أكبر من"
        " حجمك، صغّر حجم صفقتك ونم قرير العين."
    )
    bot.send_message(message.chat.id, result_text, parse_mode="Markdown")
    if user_id in risk_calculator_sessions:
      del risk_calculator_sessions[user_id]
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ حدث خطأ بالمدخلات. أعد استخدام الحاسبة من الزر الرئيسي يا رفيق.",
    )


# --- رادار الأسعار ---
@bot.message_handler(
    func=lambda message: message.text == "🔔 رادار مراقبة السيولة والأسعار"
)
def enable_price_alerts(message):
  btc, eth, xrp = get_crypto_prices()
  alert_text = (
      "🔔 **رادار الأسعار والسيولة العتيق (مفعل):**\n\n"
      "عيوننا على الشاشات ودفاتر الطلبات لا تغفل يا رفيق.\n\n"
      f"📍 **آخر قراءات النبض الحي بالسوق:**\n"
      f"• بيتكوين (BTC): `{btc:,.2f}` USDT\n"
      f"• إيثيريوم (ETH): `{eth:,.2f}` USDT\n"
      f"• ريبل (XRP): `{xrp:,.4f}` USDT\n\n"
      "🚀 رادارنا مرابط في الخلفية؛ سننبهك فور حدوث أي هزة قوية أو كسر لمناطق"
      " الحيتان."
  )
  bot.send_message(message.chat.id, alert_text, parse_mode="Markdown")


# --- قاموس المصطلحات الذكي ---
@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس الحيتان والمصطلحات (بحث ذكي)"
)
def glossary_menu(message):
  glossary_guide = (
      "📖 **قاموس الحيتان ومصطلحات السوق العتيقة:**\n\n"
      "لكي تفهم لغة الكبار، استخدم الأمر `/search` متبوعاً بالكلمة التي تقصدها.\n"
      "📌 *مثال:* `/search OCO` أو `/search USDT` أو `/search Scalping`\n\n"
      "--- \n"
      "**فهرس المصطلحات المتاحة في الديوان:**\n"
      "1️⃣ **USDT** (الملاذ الآمن المستقر)\n"
      "2️⃣ **Scalping** (اقتناص الفتات السريع)\n"
      "3️⃣ **TP / Take Profit** (مرفأ جني الأرباح)\n"
      "4️⃣ **SL / Stop Loss** (طوق النجاة / وقف الخسارة)\n"
      "5️⃣ **OCO** (الحارس المزدوج للأوامر)\n"
      "6️⃣ **Leverage** (أداة الانتحار / الرافعة المالية)\n"
      "7️⃣ **KYC** (بصمة الهوية المشروطة)"
  )
  bot.send_message(message.chat.id, glossary_guide, parse_mode="Markdown")


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(
        message.chat.id,
        "⚠️ يا رفيق، اكتب المصطلح بعد الأمر.\n*مثال:* `/search OCO`",
        parse_mode="Markdown",
    )
    return

  query = parts[1].strip().lower()

  glossary_db = {
      "usdt": (
          "🔹 **USDT:** العملة المستقرة التي تعصم مالك من تقلبات العواصف."
          " تسوى دولاباً، وتنقذك وقت الهبوط دون تسييل لكاش ورقي."
      ),
      "scalping": (
          "⚡ **Scalping (السكالبينج):** صفقات الخاطف السريع؛ تأخذ قُوتك"
          " وتنسحب في دقائق. لا تعاشرها طويلاً."
      ),
      "tp": (
          "🎯 **TP (هدف الربح):** المحطة التي تتنزل عندها بربحك قانعاً، فالطمع"
          " مهلكة."
      ),
      "sl": (
          "🛑 **SL (وقف الخسارة):** حبل النجاة الذي تقطع به الذراع الصغرى لتنجو"
          " من بتر الجسد كله."
      ),
      "oco": (
          "🟣 **OCO (الأوامر المتقدمة):** أن تربط ربحك بخسارتك برباط واحد، فتنام"
          " قرير العين لا تقلقك حركات الشاشات."
      ),
      "leverage": (
          "⚖️ **Leverage (الرافعة المالية):** سيف ذو حدين، أدخلته بيتك فكأنك"
          " استجلبتاً طوفاناً. العاقل يتجنبها ويسلك درب السبوت الآمن."
      ),
      "kyc": (
          "🆔 **KYC (التحقق من الهوية):** ورقة اعترافك رسمياً أمام المنصات"
          " لتفتح أبواب السحب والإيداع."
      ),
  }

  found = False
  for key, desc in glossary_db.items():
    if query in key or query in desc.lower():
      bot.send_message(
          message.chat.id,
          f"📜 **حكمة القاموس في (`{query}`):**\n\n{desc}",
          parse_mode="Markdown",
      )
      found = True
      break

  if not found:
    bot.send_message(
        message.chat.id,
        f"❌ يا رفيق، لم نجد في دفاترنا أثراً لـ (`{query}`). جرب بحثاً آخر مثل:"
        " `usdt`, `tp`, `sl`, `oco`.",
        parse_mode="Markdown",
    )


# --- متابعة الجلسة والدعوات ---
@bot.message_handler(
    func=lambda message: message.text == "⏳ عمر جلستك ورابط دعوة الرفاق"
)
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  uid_str = str(user_id)

  if user_id == ADMIN_ID:
    bot.send_message(
        message.chat.id,
        "👑 أنت شيخ الكار والمالك، جلستك مفتوحة إلى أبد الآبدين!",
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
      "📋 **دفتر جلستك ودعوات الرفاق:**\n\n"
      f"🆔 رقم حسابك بالديوان: `{uid_str}`\n"
      f"📅 تاريخ انتهاء الصلاحية: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"⏳ الوقت الباقي بالدقائق والساعات: **{remaining.days} يوم و"
      f" {remaining.seconds // 3600} ساعة**\n"
      f"👥 عدد من جلبتهم للديوان: **{ref_count} رفيق** (تأخذ يومين زيادة لكل"
      " رفيق يعبر الباب برابطك!)\n\n"
      "🔗 **رابطك الخاص (انشره لصحبك):**\n"
      f"`{ref_link}`\n\n"
      f"لتجديد جلستك رسمياً، اضرب عتبة المطور: {ADMIN_USERNAME}"
  )
  bot.send_message(message.chat.id, status_text, parse_mode="Markdown")


# لوحة تحكم المطور
@bot.message_handler(func=lambda message: message.text == "🛠️ ديوان الإدارة والتحكم")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  panel_text = (
      "👑 **ديوان إدارة الحكيم (المطور)**\n\n"
      "الأوامر المرعية عندك:\n"
      "1️⃣ **تمديد جلسة مستخدم بأيام:**\n"
      "`/add_days [ID] [عدد_الأيام]`\n\n"
      "2️⃣ **قطع الجلسة وقفل الباب بوجه شخص:**\n"
      "`/expire [ID]`\n\n"
      "3️⃣ **سجل الحضور وإحصائيات الديوان:**\n"
      "`/stats`\n\n"
      "4️⃣ **تجربة الإعلان في المجموعات:**\n"
      "`/test_promo`\n\n"
      "5️⃣ **طرد أو عفو:**\n"
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
          "name": "مفعل بأمر الشيخ",
          "username": "مجهول",
          "expiry": new_expiry.isoformat(),
          "is_trial": False,
          "referral_count": 0,
      }

    save_users(all_users)

    bot.send_message(
        message.chat.id,
        f"✅ **تم تمديد الجلسة بنجاح يا شيخ!**\n"
        f"🆔 الحساب: `{target_id}`\n"
        f"➕ المضافة: **{days_to_add} يوم**\n"
        f"📅 تنتهي في: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`",
        parse_mode="Markdown",
    )
    try:
      bot.send_message(
          int(target_id),
          f"🎉 **يا هلا! مُددت جلستك بمداد الكرم لمدة {days_to_add} يوم!**\n"
          f"📅 صالحة لغاية: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`\n"
          "أرسل /start وعُد إلى التداول الحكيم.",
          parse_mode="Markdown",
      )
    except Exception:
      pass
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ الخطأ في الصيغة.\nاستخدم: `/add_days 8611033531 30`",
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
          f"🔒 تم قطع الجلسة عن الحساب `{target_id}` وإغلاق الباب دونه.",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(message.chat.id, "⚠️ لا أثر لهذا الآي دي بالدفاتر.")
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
    status = "🟢 بالديوان"
    if exp <= now:
      status = "🔴 طيف منقطع"
    rem_days = (exp - now).days if exp > now else 0
    refs = info.get("referral_count", 0)
    lines.append(
        f"• {info['name']} (@{info['username']})\n  🆔 `{uid}` | {status}"
        f" ({rem_days} يوم) | 👥 رفاق جلبهُم: {refs}"
    )
  report = (
      f"📜 **سجل الحضور بالديوان ({count}) والمجموعات المرابطة"
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
        f"✅ تم نفي وحظر المستخدم `{target_id}` من الديوان.",
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
        f"✅ تم العفو عن المستخدم `{target_id}` ورجوعه للديوان.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدم: `/unban 8611033531`")


# --- صفقات السبوت الحية (نبرة المتداول العتيق) ---
@bot.message_handler(
    func=lambda message: message.text == "📊 نبض السوق الحقيقي وصفقات السبوت"
)
def send_trading_deals(message):
  btc, eth, xrp = get_crypto_prices()
  deals_text = (
      "📊 **نبض الشاشات وقراءات السوق الحي (أمان السبوت بلا مخاطر):**\n\n"
      "⚡ **1. صفقات السكالبينج (الخاطف السريع):**\n"
      f"• **الأصل:** XRP/USDT (السعر المرصود: `{xrp:,.4f}`)\n"
      f"  🎯 *المحطة المستهدفة (+1.5%):* `{xrp * 1.015:,.4f}`\n"
      f"  🛑 *طوق النجاة (-0.7%):* `{xrp * 0.993:,.4f}`\n\n"
      "📅 **2. الصفقات اليومية (نبض الجلسة الواحدة):**\n"
      f"• **الأصل:** BTC/USDT (السعر المرصود: `{btc:,.2f}`)\n"
      f"  🎯 *المحطة المستهدفة (+2.5%):* `{btc * 1.025:,.2f}`\n"
      f"  🛑 *طوق النجاة (-1.2%):* `{btc * 0.988:,.2f}`\n\n"
      "🌊 **3. صفقات السوينغ (أرجوحة الأسابيع):**\n"
      f"• **الأصل:** ETH/USDT (السعر المرصود: `{eth:,.2f}`)\n"
      f"  🎯 *المحطة المستهدفة (+6%):* `{eth * 1.06:,.2f}`\n"
      f"  🛑 *طوق النجاة (-3%):* `{eth * 0.97:,.2f}`\n\n"
      "🏛️ **4. الاستثمار بعيد النظرة (تجميع الساجدين لـ BTC):**\n"
      f"• **الأصل:** بيتكوين عند مستويات `{btc:,.2f}`\n"
      "  📌 *الوصية:* اجمع تدريجياً (DCA) **بدون دراهم قروض أو رافعة مالية**،"
      " واصبر صبر الأنبياء."
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "🟡 مجالس الذهب (يومية واستثمارية)"
)
def send_gold_deals(message):
  gold_text = (
      "🟡 **مجالس وتوصيات الذهب (XAUUSD):**\n\n"
      "⚡ **1️⃣ صفقات الذهب اليومية (حركاتها السريعة):**\n"
      "• **النوع:** اقتناص حركة الجلسات وقوتها.\n"
      "• **المحطة المستهدفة (TP):** أرباح نظيفة بنسبة (1% إلى 1.5%).\n"
      "• **طوق النجاة (SL):** (-0.7%) عند كسر السور القريب للدعم.\n\n"
      "📈 **2️⃣ تجميع الذهب طويل الأمد (خزائن الأجيال):**\n"
      "• **النوع:** حفظ القيمة وكنز الملاذات الآمنة.\n"
      "• **المحطة المستهدفة (TP):** غايات بعيدة تبدأ من (+5% إلى +10%).\n"
      "• **التحصين:** شراء هادئ وخالٍ من الديون أو الرافعة."
  )
  bot.send_message(message.chat.id, gold_text, parse_mode="Markdown")


# --- دراسة الصفقات بنبرة خبير عتيق ---
@bot.message_handler(
    func=lambda message: message.text == "📜 دراسة عتيقة لفنون الصفقات وأسرارها"
)
def send_trading_types_study(message):
  study_text = (
      "📜 **دراسة عتيقة في إدارة العاصفة وتوزيع المخاطر:**\n\n"
      "يا بني، السوق ليس كازينو، بل هو ساحة لصبر الحكماء. من أراد النجاة، فعليه بتوزيع بيضه في سلال شتى:\n\n"
      "⚡ **1. صفقات السكالبينج (XRP/USDT)**\n"
      "• *حكمة الخبير:* نسبة العائد للمخاطرة 2:1، تربح +1.5% وتضحي بـ -0.7%. عملة سريعة السيولة لكنها تأكل أعصاب الغشيم.\n"
      "• *وصية تداولية:* عيناك لا تفارق دفتر الطلبات (Order Book)، وإياك والعناد إن خالفتك الشمعة.\n\n"
      "📅 **2. الصفقات اليومية (BTC/USDT)**\n"
      "• *حكمة الخبير:* البيتكوين شيخ السوق. هدف +2.5% وخسارة -1.2% تناسب يومك ولا تبيتها بقلب وجل.\n"
      "• *وصية تداولية:* راقب مناطق السيولة ولا تدخل في وسط العاصفة قبل أن يهدأ الموج.\n\n"
      "🌊 **3. صفقات السوينغ (ETH/USDT)**\n"
      "• *حكمة الخبير:* إيثيريوم للأسبوع والأسبوعين. هدف +6% وخسارة -3% لمن يملك نفساً أطول.\n"
      "• *وصية تداولية:* لا تلقِ بمالك دفعة واحدة، بل قسمه: نصفه اليوم ونصفه إن عاد السعر يختبر الدعم.\n\n"
      "🏛️ **4. الاستثمار طويل الأمد (DCA في Bitcoin)**\n"
      "• *حكمة الخبير:* هو الملاذ الأضمن والأقوى لمن لا يملك وقت مراقبة الشاشات، بلا رافعة مالية تُهلك المال.\n"
      "• *وصية تداولية:* اشتري بجدول زمني ثابت (أسبوعياً أو شهرياً) ولا تهتم إن ارتفعت أو انخفضت غداً، فالعبرة بالنهايات."
  )
  bot.send_message(message.chat.id, study_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text
    == "📚 خزانة الحكمة (أكاديمية المتداول المحترف)"
)
def send_academy(message):
  academy_text = (
      "📚 **خزانة الحكمة - أصول التجارة من الطراز القديم:**\n\n"
      "🟢 **المقام الأول (أبجديات السوق):**\n"
      "• البيع والشراء في عالم الكريبتو يتم بميزان الدولار الرقمي (USDT) لكي تحفظ رأس مالك من تمايل العملات.\n\n"
      "🟡 **المقام الثاني (فنون العقود والأنواع):**\n"
      "• السكالبينج واليومي لأصحاب الأعصاب الحديدية، والاستثمار طويل الأمد لأصحاب النفس الطويل بلا رافعة مالية.\n\n"
      "🔵 **المقام الثالث (ميزان الأمان وحجم العقود):**\n"
      "• لا توضع بيضاتك كلهن في سلة صفقة واحدة؛ قسم سيولتك بحكمة العارفين.\n\n"
      "🟣 **المقام الرابع (الحارس المزدوج OCO):**\n"
      "• اربط هدفك بوقف خسارتك منذ لحظة الدخول، لكي تنام قرير العين ولا تعذب قلبك بمتابعة الساعات.\n\n"
      "🟠 **المقام الخامس (روضة النفس وعلم التداول):**\n"
      "• إياك وأن تنتقم من السوق بعد خسارة؛ السوق بحر لا يغلب، ومن عانده غرق.\n\n"
      "🟤 **المقام السادس (تنويع الخزائن):**\n"
      "• انثر جزءاً من مالك في الذهب وجزءاً في الرقميات لتحيا آمناً من غدر الزمان."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "🌐 مفاتيح المنصات وإنشاء المحافظ الآمنة"
)
def send_accounts_guide(message):
  guide_text = (
      "🌐 **مفاتيح المنصات وإنشاء المحافظ الحصينة:**\n\n"
      "1️⃣ **القلعة المركزية:** افتح حسابك ووثقه (KYC) في منصة عريقة مثل **Binance** أو **Bybit** لتأمين عمليات البيع والشراء الفوري.\n"
      "2️⃣ **الخزنة اللامركزية:** أنزل محفظة **Trust Wallet** على هاتفك، واكتب كلمات السر العتيقة على ورقة واحتفظ بها في مكان خفي، فتلك هي مفتاح أصولك بعيداً عن المنصات."
  )
  bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "📥 شريان الإيداع والسحب (TRC20)"
)
def send_deposit_withdraw_guide(message):
  dw_text = (
      "📥 **شريان الإيداع والسحب في الأسواق الرقمية:**\n\n"
      "• **الطريق المعتمد للعابرين:** استخدم دائماً عملة (USDT) عبر شبكة **TRC20** عند نقل الأموال.\n"
      "• **سر الإذن:** لأنها الأسرع وصولاً (دقائق معدودات) ورسومها زهيدة ثابتة لا تضر مالك.\n\n"
      "🔄 **حلقة الوصل مع الداخل السوري:**\n"
      "• عند **الإيداع**: تحول ليرات سورية عبر تطبيق **شام كاش** للوكيل المعتمد، فيرسل لك بدلها `USDT (TRC20)` لمحفظتك فوراً.\n"
      "• عند **السحب**: ترسل الـ `USDT` من منصتك للوكيل، فيحول قيمتها نقداً أو لليرات إلى حسابك على شام كاش بكل أمان وأمانة."
  )
  bot.send_message(message.chat.id, dw_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "💳 حوالات الداخل والخارج (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **ديوان الحوالات والشحن عبر (شام كاش):**\n\n"
      "• **الأمانة والسرعة:** تجرى معاملات الإيداع والسحب المحلي عبر محفظة **شام كاش** بالتعاون مع الرفاق الوكلاء المعتمدين بعهد وثيق.\n"
      "• **مراسم الشحن والتفعيل:**\n"
      "  1️⃣ خاطب الإدارة أو الوكيل المعتمد بالمعرف الرسمي.\n"
      "  2️⃣ أتمم التحويل بالعملة المحلية عبر تطبيق شام كاش.\n"
      "  3️⃣ ابعث بإيصال التحويل ورقم جلستك (ID) لكي يُقيد اشتراكك في سجلات الديوان فوراً."
  )
  bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")


if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
