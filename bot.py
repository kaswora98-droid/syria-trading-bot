import datetime
import json
import os
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# إعداد خادم الويب لإرضاء منصة Render وفتح بورت الاستماع
app = Flask(__name__)


@app.route("/")
def home():
  return "Syria Trading Bot is running 24/7 successfully!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# --- التوكن الحقيقي الصحيح الخاص ببوتك ---
TOKEN = "8928709566:AAE8G20dfLOqdo7GXJ9APGPqH7OTdyq5leg"
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8611033531
USERS_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"


def load_data(filename):
  if not os.path.exists(filename):
    return {}
  try:
    with open(filename, "r", encoding="utf-8") as f:
      return json.load(f)
  except:
    return {}


def save_data(filename, data):
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)


# --- دالة حساب نسبة الربح المئوية للصفقة ---
def calculate_profit_percentage(entry_price, target_price, direction="BUY"):
  try:
    entry = float(entry_price)
    target = float(target_price)
    if direction.upper() == "BUY":
      percentage = ((target - entry) / entry) * 100
    else:
      percentage = ((entry - target) / entry) * 100
    return round(percentage, 2)
  except:
    return 0.0


# --- القائمة الرئيسية (الأزرار كاملة وثابتة) ---
def get_main_menu():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والرسوم البيانية")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب اليومية والاستثمارية")
  btn3 = types.KeyboardButton("🧮 حاسبة المخاطر وحجم الصفقة")
  btn4 = types.KeyboardButton("📚 الأكاديمية التعليمية للمبتدئين")
  btn5 = types.KeyboardButton("🛡️ استراتيجية التأمين (DCA)")
  btn6 = types.KeyboardButton("ℹ️ معلومات اشتراكي")
  btn7 = types.KeyboardButton("🔔 ضبط تنبيه سعر مخصص (/alert)")
  btn8 = types.KeyboardButton("🧠 اختبار تداولي تفاعلي (Quiz)")
  btn9 = types.KeyboardButton("📚 قاموس مصطلحات التداول (بحث ذكي)")
  btn10 = types.KeyboardButton("📥 دليل السحب والإيداع (شبكة TRC20)")
  markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10)
  return markup


# --- أمر البداية /start وإغلاق ثغرة التجربة نهائياً مع إبقاء الأزرار ظاهرة ---
@bot.message_handler(commands=["start"])
def handle_start(message):
  user_id = str(message.from_user.id)
  users = load_data(USERS_FILE)

  # التحقق مما إذا كان المستخدم مسجلاً مسبقاً (حتى لو مسح المحادثة أو انتهى اشتراكه)
  if user_id in users:
    bot.send_message(
        message.chat.id,
        "أهلاً بك مجدداً يا مهندس! حسابك مسجل مسبقاً في النظام.",
        reply_markup=get_main_menu(),
    )
    return

  # مستخدم جديد كلياً لأول مرة
  trial_days = 3
  expiry_date = (
      datetime.datetime.now() + datetime.timedelta(days=trial_days)
  ).isoformat()

  users[user_id] = {
      "username": message.from_user.username or "No Username",
      "first_name": message.from_user.first_name or "User",
      "joined_date": datetime.datetime.now().isoformat(),
      "expiry_date": expiry_date,
      "is_trial_used": True,
      "invites": 0,
  }
  save_data(USERS_FILE, users)

  # إرسال تنبيه فوري للمطور
  try:
    bot.send_message(
        ADMIN_ID,
        f"🚨 **مشترك جديد انضم للبوت!**\n👤 الاسم: {message.from_user.first_name}\n🆔 المعرف: `{user_id}`",
        parse_mode="Markdown",
    )
  except:
    pass

  bot.send_message(
      message.chat.id,
      "🎉 أهلاً بك في **بوت التداول الذكي والشامل** (`SyriaTradingBot`)!\n\n"
      f"🎁 تم تفعيل **فترة تجريبية مجانية لمدة {trial_days} أيام** لحسابك بنجاح.\n"
      "اختر من القائمة أدناه لاستكشاف الأقسام والخدمات:",
      reply_markup=get_main_menu(),
      parse_mode="Markdown",
  )


# --- نموذج إرسال الصفقة مع النسب المئوية للأهداف ---
def format_trade_signal(
    coin, entry, tp1, tp2, sl, direction="BUY", notes="توصية سبوت آمنة"
):
  tp1_pct = calculate_profit_percentage(entry, tp1, direction)
  tp2_pct = calculate_profit_percentage(entry, tp2, direction)
  sl_pct = calculate_profit_percentage(entry, sl, direction)

  signal_text = (
      f"🚨 **توصية جديدة ({coin})**\n\n"
      f"📍 **النوع:** {'شراء (Buy / Spot)' if direction=='BUY' else 'بيع'}\n"
      f"📥 **سعر الدخول:** `{entry}`\n\n"
      f"🎯 **الأهداف الاستثمارية:**\n"
      f"  • **الهدف الأول (TP1):** `{tp1}` ──> **(+{tp1_pct}%)**\n"
      f"  • **الهدف الثاني (TP2):** `{tp2}` ──> **(+{tp2_pct}%)**\n\n"
      f"🛑 **وقف الخسارة (SL):** `{sl}` ──> **({sl_pct}%)**\n\n"
      f"💡 **ملاحظة:** {notes}\n"
      f"🔒 *تأمين الصفقة بنقل وقف الخسارة لسعر الدخول فور بلوغ TP1.*"
  )
  return signal_text


# --- لوحة تحكم المطور (الإحصائيات) ---
@bot.message_handler(commands=["users"])
def admin_users_list(message):
  if message.from_user.id != ADMIN_ID:
    return
  users = load_data(USERS_FILE)
  text = f"👥 **إجمالي المشتركين:** {len(users)}\n\n"
  for uid, info in list(users.items())[-15:]:
    text += f"• {info.get('first_name')} (`{uid}`) - ينتهي: {info.get('expiry_date')[:10]}\n"
  bot.send_message(message.chat.id, text, parse_mode="Markdown")


# --- معالجة الأزرار والخدمات ---
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
  text = message.text
  user_id = str(message.from_user.id)

  if text == "📊 الصفقات المقترحة والرسوم البيانية":
    sample_signal = format_trade_signal(
        "BTC/USDT", 64200, 66500, 68800, 62800, "BUY", "تحليلي فني للسبوت"
    )
    bot.send_message(
        message.chat.id,
        sample_signal,
        reply_markup=get_main_menu(),
        parse_mode="Markdown",
    )

  elif text == "🟡 صفقات الذهب اليومية والاستثمارية":
    sample_gold = format_trade_signal(
        "XAUUSD (الذهب)", 2380, 2405, 2430, 2365, "BUY", "تذبذب جلسة نيويورك"
    )
    bot.send_message(
        message.chat.id,
        sample_gold,
        reply_markup=get_main_menu(),
        parse_mode="Markdown",
    )

  elif text == "ℹ️ معلومات اشتراكي":
    users = load_data(USERS_FILE)
    user_info = users.get(user_id)
    if user_info:
      expiry = user_info.get("expiry_date", "مجهول")[:10]
      bot.send_message(
          message.chat.id,
          f"👤 **معلومات حسابك:**\n🆔 المعرف: `{user_id}`\n📅 تاريخ انتهاء الاشتراك: `{expiry}`",
          reply_markup=get_main_menu(),
          parse_mode="Markdown",
      )
    else:
      bot.send_message(
          message.chat.id,
          "أرسل /start لتسجيل حسابك وبدء الفترة التجريبية.",
          reply_markup=get_main_menu(),
      )

  elif text == "🧮 حاسبة المخاطر وحجم الصفقة":
    bot.send_message(
        message.chat.id,
        "🧮 **حاسبة المخاطر:**\nادخل حجم رأس مالك ونسبة المخاطرة (مثلاً 1%) ليتم حساب الخسارة القصوى بأمان.",
        reply_markup=get_main_menu(),
    )

  elif text == "📚 الأكاديمية التعليمية للمبتدئين":
    bot.send_message(
        message.chat.id,
        "📚 **الأكاديمية التعليمية:**\nمرجعك الشامل لفهم الأسواق وإدارة المخاطر خطوة بخطوة.",
        reply_markup=get_main_menu(),
    )

  elif text == "🛡️ استراتيجية التأمين (DCA)":
    bot.send_message(
        message.chat.id,
        "🛡️ **استراتيجية حماية الأصل الأساسي:**\nنظام يعتمد على جني 25% من الأرباح الصافية وتحويلها لـ USDT دون المساس بكمية الأصول الأساسية (مثل البيتكوين).",
        reply_markup=get_main_menu(),
    )

  elif text == "🔔 ضبط تنبيه سعر مخصص (/alert)":
    bot.send_message(
        message.chat.id,
        "🔔 أرسل الأمر متبوعاً بالعملة والسعر، مثل: `/alert BTC 65000`",
        reply_markup=get_main_menu(),
    )

  elif text == "🧠 اختبار تداولي تفاعلي (Quiz)":
    bot.send_message(
        message.chat.id,
        "🧠 أهلاً بك في اختبار الوعي التداولي! جاهز للإجابة على الأسئلة؟",
        reply_markup=get_main_menu(),
    )

  elif text == "📚 قاموس مصطلحات التداول (بحث ذكي)":
    bot.send_message(
        message.chat.id,
        "📚 استخدم الأمر `/search` متبوعاً بالمصطلح للبحث في قاموس الحيتان والمفاهيم.",
        reply_markup=get_main_menu(),
    )

  elif text == "📥 دليل السحب والإيداع (شبكة TRC20)":
    bot.send_message(
        message.chat.id,
        "📥 دليل العمليات وشبكة TRC20 ومعلومات الشحن عبر محفظة شام كاش.",
        reply_markup=get_main_menu(),
    )


if __name__ == "__main__":
  # تشغيل خادم Flask لإرضاء منصة Render وفتح البورت
  flask_thread = Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()
  print("Flask web server started successfully...")

  # حذف الويب هوك القديم لتجنب التعارض (خطأ 409)
  try:
    bot.remove_webhook()
    print("Webhook removed successfully. Starting polling...")
  except Exception as e:
    print(f"Error removing webhook: {e}")

  # تشغيل البوت
  bot.infinity_polling()
