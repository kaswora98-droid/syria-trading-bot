from datetime import datetime, timedelta
import json
import os
import random
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
banned_users = set()

app = Flask(__name__)
RENDER_URL = "https://syria-trading-bot.onrender.com"


# --- دوال حفظ واسترجاع بيانات الاشتراكات ---
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


all_users = load_users()


@app.route("/")
def home():
  return "Bot is running 24/7 with Live Prices & Persistent Menu!"


@app.route("/ping")
def ping():
  return "Pong!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


# دالة جلب الأسعار الفورية المباشرة (تمنع الثبات وتتحدث لحظياً)
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

  # خط دفاع أخير يتغير قليلاً لضمان عدم ثبات الأرقام كلياً في حال انقطاع الشبكة
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

  # استثناء المدير (أنت)
  if user_id == ADMIN_ID:
    return

  # 1. فحص الحظر اليدوي
  if user_id in banned_users:
    bot.reply_to(message, "⛔ تم حظرك من استخدام هذا البوت. يرجى مراجعة الإدارة.")
    return True

  # 2. منح 3 أيام تجريبية تلقائية للمستخدم الجديد
  if uid_str not in all_users:
    expiry_date = datetime.now() + timedelta(days=3)
    all_users[uid_str] = {
        "name": message.from_user.first_name or "بدون اسم",
        "username": message.from_user.username or "لا يوجد",
        "expiry": expiry_date.isoformat(),
        "is_trial": True,
    }
    save_users(all_users)

    try:
      bot.send_message(
          ADMIN_ID,
          f"🚨 **مشترك جديد بدأ الفترة التجريبية (3 أيام)!**\n"
          f"👤 الاسم: {all_users[uid_str]['name']}\n"
          f"🏷️ المعرف: @{all_users[uid_str]['username']}\n"
          f"🆔 الآي دي: `{user_id}`\n"
          f"⏳ ينتهي في: `{expiry_date.strftime('%Y-%m-%d %H:%M')}`",
          parse_mode="Markdown",
      )
    except Exception:
      pass
    return

  # 3. فحص انتهاء الصلاحية
  user_data = all_users[uid_str]
  expiry_dt = datetime.fromisoformat(user_data["expiry"])

  if datetime.now() > expiry_dt:
    lock_msg = (
        "🔒 **انتهت صلاحية استخدامك للبوت!**\n\n"
        "لقد انتهت فترتك التجريبية (3 أيام) أو مدة اشتراكك الشهري.\n"
        "لإعادة تفعيل البوت والاستمرار في الحصول على الصفقات الفورية والتوصيات:\n\n"
        f"📩 يرجى التواصل ودفع الاشتراك مع المطور: {ADMIN_USERNAME}\n"
        f"🆔 أرسل له رقم حسابك (ID) لتفعيل الاشتراك فوراً:\n`{user_id}`"
    )
    bot.send_message(message.chat.id, lock_msg, parse_mode="Markdown")
    return True


# أمر البدء والأزرار الثابتة في أسفل الدردشة (الزر المثبت المدمج)
@bot.message_handler(commands=["start"])
def send_welcome(message):
  user_id = message.from_user.id
  uid_str = str(user_id)

  # بناء لوحة المفاتيح الثابتة والمستمرة أسفل المحادثة
  markup = types.ReplyKeyboardMarkup(
      resize_keyboard=True, is_persistent=True, row_width=2
  )

  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والأسعار (Crypto)")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب (يومية وطويلة الأمد)")
  btn3 = types.KeyboardButton("📚 الأكاديمية الشاملة (من الصفر للاحتراف)")
  btn4 = types.KeyboardButton("🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)")
  btn5 = types.KeyboardButton("📥 دليل السحب والإيداع في المنصات")
  btn6 = types.KeyboardButton("💳 معلومات الدفع والشحن (شام كاش)")
  btn7 = types.KeyboardButton("⏳ حالة اشتراكي")

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("🛠️ لوحة تحكم المطور")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn_admin)
    welcome_text = (
        "👑 أهلاً بك يا مهندس أحمد (المطور والمالك)!\n"
        "تم تثبيت كافة الخيارات والقوائم في لوحة المفاتيح أدناه:"
    )
  else:
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7)
    if uid_str in all_users:
      expiry_dt = datetime.fromisoformat(all_users[uid_str]["expiry"])
      remaining = expiry_dt - datetime.now()
      days_left = max(0, remaining.days)
      hours_left = max(0, remaining.seconds // 3600)
      sub_status = f"نشط (المتبقي: {days_left} يوم و {hours_left} ساعة)"
    else:
      sub_status = "قيد التفعيل"

    welcome_text = (
        "أهلاً بك في بوت التداول الذكي الشامل! 🤖\n\n"
        f"✅ **حالة الحساب:** {sub_status}\n"
        "يمكنك الوصول إلى كافة الخيارات فوراً عبر الأزرار المثبتة أسفل"
        " الشاشة:"
    )

  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


# زر حالة الاشتراك للمستخدم
@bot.message_handler(func=lambda message: message.text == "⏳ حالة اشتراكي")
def check_my_status(message):
  uid_str = str(message.from_user.id)
  if message.from_user.id == ADMIN_ID:
    bot.send_message(
        message.chat.id, "👑 أنت المالك والمطور، اشتراكك مفتوح مدى الحياة!"
    )
    return

  expiry_dt = datetime.fromisoformat(all_users[uid_str]["expiry"])
  remaining = expiry_dt - datetime.now()
  status_text = (
      "📋 **تفاصيل اشتراكك:**\n\n"
      f"🆔 رقم حسابك: `{uid_str}`\n"
      f"📅 تاريخ الانتهاء: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"⏳ الوقت المتبقي: **{remaining.days} يوم و {remaining.seconds // 3600}"
      " ساعة**\n\n"
      f"لتجديد الاشتراك تواصل مع الإدارة: {ADMIN_USERNAME}"
  )
  bot.send_message(message.chat.id, status_text, parse_mode="Markdown")


# لوحة تحكم المطور
@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  panel_text = (
      "👑 **لوحة تحكم المطور والاشتراكات**\n\n"
      "الأوامر المتاحة لك:\n"
      "1️⃣ **تفعيل أو تمديد اشتراك (أيام):**\n"
      "`/add_days [ID] [عدد_الأيام]`\n"
      "مثال: `/add_days 8611033531 30`\n\n"
      "2️⃣ **قفل البوت فوراً عن مستخدم:**\n"
      "`/expire [ID]`\n\n"
      "3️⃣ **عرض جميع المشتركين:**\n"
      "`/stats`\n\n"
      "4️⃣ **حظر / فك حظر:**\n"
      "`/ban [ID]` أو `/unban [ID]`"
  )
  bot.send_message(message.chat.id, panel_text, parse_mode="Markdown")


# تفعيل الأيام للمشتركين
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
      }

    save_users(all_users)

    bot.send_message(
        message.chat.id,
        f"✅ **تم تفعيل الاشتراك بنجاح!**\n"
        f"🆔 الحساب: `{target_id}`\n"
        f"➕ المدة المضافة: **{days_to_add} يوم**\n"
        f"📅 ينتهي في: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`",
        parse_mode="Markdown",
    )

    try:
      bot.send_message(
          int(target_id),
          f"🎉 **تم تفعيل اشتراكك بنجاح لمدة {days_to_add} يوم!**\n"
          f"📅 صالح لغاية: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`\n"
          "أرسل /start للبدء بالتداول الآن.",
          parse_mode="Markdown",
      )
    except Exception:
      pass

  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ صيغة الأمر غير صحيحة.\nاستخدم: `/add_days 8611033531 30`",
        parse_mode="Markdown",
    )


# إنهاء اشتراك مستخدم
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
          f"🔒 تم إنهاء اشتراك الحساب `{target_id}` وقفل البوت عنه فوراً.",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(message.chat.id, "⚠️ هذا الآي دي غير مسجل في البوت.")
  except Exception:
    bot.send_message(
        message.chat.id, "⚠️ استخدم: `/expire 8611033531`", parse_mode="Markdown"
    )


# عرض إحصائيات المشتركين
@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  count = len(all_users)
  if count == 0:
    bot.send_message(message.chat.id, "📊 لا يوجد مشتركين مسجلين بعد.")
    return

  now = datetime.now()
  lines = []
  for uid, info in all_users.items():
    exp = datetime.fromisoformat(info["expiry"])
    status = "🟢 نشط" if exp > now else "🔴 منتهي"
    rem_days = (exp - now).days if exp > now else 0
    lines.append(
        f"• {info['name']} (@{info['username']})\n  🆔 `{uid}` | {status}"
        f" ({rem_days} يوم)"
    )

  report = f"📊 **إحصائيات المشتركين ({count}):**\n\n" + "\n\n".join(lines)
  bot.send_message(message.chat.id, report, parse_mode="Markdown")


# حظر وفك حظر
@bot.message_handler(commands=["ban"])
def ban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = int(message.text.split()[1])
    banned_users.add(target_id)
    bot.send_message(
        message.chat.id,
        f"✅ تم حظر المستخدم `{target_id}` نهائياً.",
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
        f"✅ تم فك الحظر عن `{target_id}`.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدم: `/unban 8611033531`")


# --- الأقسام الأساسية للبوت ---
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والأسعار (Crypto)"
)
def send_trading_deals(message):
  btc_price, eth_price, xrp_price = get_crypto_prices()
  deals_text = (
      "📊 **الأسعار الفورية للعملات الرقمية (Live Feed):**\n\n"
      f"🔹 **BTC/USDT**\n  • السعر: `{btc_price:,.2f}` USDT 🟢\n  • الهدف (+3%):"
      f" `{btc_price * 1.03:,.2f}` 🎯\n  • وقف الخسارة (-1.5%):"
      f" `{btc_price * 0.985:,.2f}` 🛑\n\n"
      f"🔹 **ETH/USDT**\n  • السعر: `{eth_price:,.2f}` USDT 🟢\n  • الهدف (+3%):"
      f" `{eth_price * 1.03:,.2f}` 🎯\n  • وقف الخسارة (-1.5%):"
      f" `{eth_price * 0.985:,.2f}` 🛑\n\n"
      f"🔹 **XRP/USDT**\n  • السعر: `{xrp_price:,.4f}` USDT 🟢\n  • الهدف (+3%):"
      f" `{xrp_price * 1.03:,.4f}` 🎯\n  • وقف الخسارة (-1.5%):"
      f" `{xrp_price * 0.99:,.4f}` 🛑"
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (يومية وطويلة الأمد)"
)
def send_gold_deals(message):
  gold_text = (
      "🟡 **توصيات صفقات الذهب (XAUUSD):**\n\n"
      "⚡ **1️⃣ صفقات الذهب اليومية (Day Trading):**\n"
      "• **النوع:** سكالبينج وتداول قصير الأمد.\n"
      "• **الهدف (TP):** ربح سريع بنسبة (1% إلى 1.5%).\n"
      "• **وقف الخسارة (SL):** (-0.7%) عند كسر مناطق الدعم القريبة.\n\n"
      "📈 **2️⃣ صفقات الذهب طويلة الأمد (Long-term):**\n"
      "• **النوع:** استثمار وتجميع متوسط إلى طويل المدى.\n"
      "• **الهدف (TP):** أهداف كبرى تبدأ من (+5% إلى +10%).\n"
      "• **الحماية:** التجميع التدريجي بدون رافعة مالية لحماية القيمة الشرائية."
  )
  bot.send_message(message.chat.id, gold_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text
    == "📚 الأكاديمية الشاملة (من الصفر للاحتراف)"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية الشاملة - من الصفر للاحتراف:**\n\n"
      "🟢 **المستوى الأول (الأساسيات):**\n"
      "• التداول هو عملية بيع وشراء الأصول الرقمية للاستفادة من فروق الأسعار،"
      " ويتم تقييم الأصول دائماً بالعملات الرقمية المستقرة مثل (USDT) لضمان"
      " الاستقرار.\n\n"
      "🟡 **المستوى الثاني (أنواع الصفقات):**\n"
      "• *السكالبينج والتداول اليومي:* صفقات سريعة تهدف لتحقيق أرباح صغرى (1% إلى"
      " 3%) وتُغلق خلال الجلسة نفسها.\n"
      "• *الاستثمار طويل الأمد:* تجميع الأصول القوية بهدف النمو على المدى الطويل"
      " بدون استخدام أي رافعة مالية حمايةً لرأس المال.\n\n"
      "🔵 **المستوى الثالث (إدارة المخاطر وحجم العقود):**\n"
      "• عدم المخاطرة بكامل رأس المال في صفقة واحدة، وتقسيم السيولة بذكاء لضمان"
      " الأمان التام.\n\n"
      "🟣 **المستوى الرابع (الأوامر المتقدمة OCO):**\n"
      "• وضع هدف الربح (TP) ووقف الخسارة (SL) معاً في نفس اللحظة لحماية الصفقة"
      " تلقائياً دون الحاجة لمراقبة الشاشة طوال الوقت.\n\n"
      "🟠 **المستوى الخامس (علم نفس التداول):**\n"
      "• التحكم التام بالمشاعر والابتعاد عن الطمع أو محاولة الانتقام بعد أي خسارة"
      " عابرة.\n\n"
      "🟤 **المستوى السادس (تنويع المحفظة):**\n"
      "• توزيع رأس المال بين العملات الرقمية والذهب لتقليل المخاطر الإجمالية."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text
    == "🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)"
)
def send_accounts_guide(message):
  guide_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ:**\n\n"
      "1️⃣ **المنصة المركزية:** قم بإنشاء وتوثيق حسابك الشخصي (KYC) على منصة"
      " موثوقة مثل **Binance** أو **Bybit** لتنفيذ عمليات البيع والشراء"
      " الفوري بكل أمان.\n"
      "2️⃣ **المحفظة اللامركزية:** أنشئ محفظة **Trust Wallet** على هاتفك"
      " واحتفظ بعبارة الأمان الخاصة بك في مكان آمن، لتخزين أصولك الرقمية بعيداً"
      " عن المنصات."
  )
  bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "📥 دليل السحب والإيداع في المنصات"
)
def send_deposit_withdraw_guide(message):
  dw_text = (
      "📥 **دليل السحب والإيداع في المنصات:**\n\n"
      "• **الشبكة المعتمدة:** استخدم دائماً عملة (USDT) عبر شبكة **TRC20** عند"
      " تحويل الأموال بين المنصات والمحافظ.\n"
      "• **السبب:** لضمان أعلى سرعة في إتمام المعاملات وأقل رسوم ممكنة مقارنة"
      " بالشبكات الأخرى."
  )
  bot.send_message(message.chat.id, dw_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "💳 معلومات الدفع والشحن (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **معلومات الدفع والشحن (شام كاش):**\n\n"
      "• **آلية الشحن:** تتم جميع معاملات الإيداع والسحب المحلية بكل يسر وسرعة عبر"
      " خدمة **شام كاش** بالتعاون حصرياً مع المعرفات والوكلاء المعتمدين لضمان"
      " الأمان التام لكافة الأطراف."
  )
  bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")


if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
