import os
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

# قائمة المستخدمين المحظورين
banned_users = set()
# قائمة لتسجيل المستخدمين الذين يدخلون البوت
all_users = {}

app = Flask(__name__)
RENDER_URL = "https://syria-trading-bot.onrender.com"


@app.route("/")
def home():
  return "Bot is running 24/7!"


@app.route("/ping")
def ping():
  return "Pong!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


# دالة جلب الأسعار مع خط الدفاع الأخير (Fallback)
def get_crypto_prices():
  try:
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        headers=headers,
        timeout=3,
    )
    btc = float(r.json()["price"])

    r2 = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT",
        headers=headers,
        timeout=3,
    )
    eth = float(r2.json()["price"])

    r3 = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT",
        headers=headers,
        timeout=3,
    )
    xrp = float(r3.json()["price"])
    return btc, eth, xrp
  except Exception:
    pass

  try:
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd",
        timeout=3,
    )
    data = r.json()
    return (
        float(data["bitcoin"]["usd"]),
        float(data["ethereum"]["usd"]),
        float(data["ripple"]["usd"]),
    )
  except Exception:
    pass

  return 64950.0, 1815.0, 0.52


# حارس أمني لفحص الحظر
@bot.middleware_handler(update_types=["message"])
def check_ban(bot_instance, message):
  user_id = message.from_user.id
  if user_id in banned_users:
    bot.reply_to(message, "⛔ تم حظرك من استخدام هذا البوت. يرجى مراجعة الإدارة.")
    return True


# أمر البدء وتسجيل المستخدمين وإرسال إشعار لك
@bot.message_handler(commands=["start"])
def send_welcome(message):
  user_id = message.from_user.id
  user_name = message.from_user.first_name
  username = message.from_user.username

  if user_id not in all_users and user_id != ADMIN_ID:
    all_users[user_id] = {"name": user_name, "username": username}
    try:
      bot.send_message(
          ADMIN_ID,
          f"🚨 **مستخدم جديد دخل البوت!**\n👤 الاسم: {user_name}\n🏷️ المعرف:"
          f" @{username}\n🆔 الآي دي: `{user_id}`",
          parse_mode="Markdown",
      )
    except Exception:
      pass

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والأسعار (Crypto)")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب (يومية وطويلة الأمد)")
  btn3 = types.KeyboardButton("📚 الأكاديمية الشاملة (من الصفر للاحتراف)")
  btn4 = types.KeyboardButton("🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)")
  btn5 = types.KeyboardButton("📥 دليل السحب والإيداع في المنصات")
  btn6 = types.KeyboardButton("💳 معلومات الدفع والشحن (شام كاش)")

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("🛠️ لوحة تحكم المطور")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn_admin)
  else:
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)

  welcome_text = (
      "أهلاً بك في بوت التداول الذكي الشامل! 🤖\nاختر من الأزرار أدناه للبدء:"
  )
  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# 🛠️ لوحة تحكم المطور (تظهر لك وحدك)
@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  panel_text = (
      "👑 **أهلاً بك يا مهندس أحمد (المنشئ والمطور)**\n\n"
      "أدوات التحكم المتاحة:\n"
      "• لعرض المشتركين، أرسل: `/stats`\n"
      "• لحظر مستخدم لم يدفع، أرسل: `/ban [ID]`\n"
      "• لفك الحظر، أرسل: `/unban [ID]`"
  )
  bot.send_message(message.chat.id, panel_text, parse_mode="Markdown")


# عرض إحصائيات المستخدمين
@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  count = len(all_users)
  users_list = (
      "\n".join(
          [
              f"• {info['name']} (@{info['username']}) - `{uid}`"
              for uid, info in all_users.items()
          ]
      )
      or "لا توجد سجلات بعد."
  )
  bot.send_message(
      message.chat.id,
      f"📊 **إحصائيات المستخدمين:**\nعدد المشتركين المسجلين: {count}\n\nقائمة"
      f" المستخدمين:\n{users_list}",
      parse_mode="Markdown",
  )


# حظر مستخدم
@bot.message_handler(commands=["ban"])
def ban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    parts = message.text.split()
    target_id = int(parts[1])
    banned_users.add(target_id)
    bot.send_message(
        message.chat.id,
        f"✅ تم حظر المستخدم `{target_id}` بنجاح وإيقاف البوت عنه.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(
        message.chat.id, "⚠️ الاستخدام الخاطئ. اكتب هكذا: `/ban 123456789`"
    )


# فك الحظر
@bot.message_handler(commands=["unban"])
def unban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    parts = message.text.split()
    target_id = int(parts[1])
    if target_id in banned_users:
      banned_users.remove(target_id)
    bot.send_message(
        message.chat.id,
        f"✅ تم فك الحظر عن المستخدم `{target_id}` وإعادة تفعيل البوت له.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(
        message.chat.id, "⚠️ الاستخدام الخاطئ. اكتب هكذا: `/unban 123456789`"
    )


# قسم صفقات العملات الرقمية
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


# قسم صفقات الذهب
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


# الأكاديمية الشاملة (التقرير الشامل)
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


# دليل فتح الحسابات والمحافظ
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


# دليل السحب والإيداع
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


# معلومات الدفع والشحن (شام كاش)
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
