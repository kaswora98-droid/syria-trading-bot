import datetime
import json
import os
import random
from threading import Thread
import telebot
from telebot import types
from flask import Flask

# إعداد خادم الويب البسيط لإرضاء متطلبات البورت في منصة Render
app = Flask(__name__)


@app.route("/")
def home():
  return "Syria Trading Bot is running successfully 24/7!"


def run_flask():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


# --- إعدادات البوت والتوكن ---
TOKEN = os.environ.get(
    "BOT_TOKEN", "8928709566:ضع_التوكن_الكامل_هنا_بدون_فراغات"
)
bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8611033531
USERS_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"


# --- دوال إدارة البيانات وحفظها ---
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


# --- أمر البداية /start وإغلاق ثغرة التجربة نهائياً ---
@bot.message_handler(commands=["start"])
def handle_start(message):
  user_id = str(message.from_user.id)
  users = load_data(USERS_FILE)

  # التحقق مما إذا كان المستخدم مسجلاً مسبقاً (حتى لو انتهى اشتراكه أو مسح المحادثة)
  if user_id in users:
    bot.send_message(
        message.chat.id,
        "أهلاً بك مجدداً يا مهندس! حسابك مسجل مسبقاً في النظام.",
        reply_markup=get_main_menu(),
    )
    return

  # مستخدم جديد كلياً لأول مرة في تاريخ البوت
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
  }
  save_data(USERS_FILE, users)

  # إرسال تنبيه فوري للمطور (أنت)
  try:
    bot.send_message(
        ADMIN_ID,
        f"🚨 **مشترك جديد انضم للبوت!**\n👤 الاسم: {message.from_user.first_name}\n🆔 المعرف: `{user_id}`",
        parse_mode="Markdown",
    )
  except:
    pass

  # ترحيب بالمشترك الجديد
  bot.send_message(
      message.chat.id,
      "🎉 أهلاً بك في **بوت التداول الذكي والشامل** (`SyriaTradingBot`)!\n\n"
      f"🎁 تم تفعيل **فترة تجريبية مجانية لمدة {trial_days} أيام** لحسابك بنجاح.\n"
      "اختر من القائمة أدناه لاستكشاف الأقسام والخدمات:",
      reply_markup=get_main_menu(),
      parse_mode="Markdown",
  )


# --- القائمة الرئيسية ---
def get_main_menu():
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn1 = types.KeyboardButton("📊 الصفقات المقترحة")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب XAUUSD")
  btn3 = types.KeyboardButton("🧮 حاسبة المخاطر")
  btn4 = types.KeyboardButton("📚 الأكاديمية والقاموس")
  btn5 = types.KeyboardButton("🛡️ استراتيجية التأمين (DCA)")
  btn6 = types.KeyboardButton("ℹ️ معلومات اشتراكي")
  markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
  return markup


# --- نموذج إرسال صفقة مقترحة مع نسب الأهداف المئوية ---
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


# --- لوحة تحكم المطور (الإحصائيات والمشتركين) ---
@bot.message_handler(commands=["users"])
def admin_users_list(message):
  if message.from_user.id != ADMIN_ID:
    return
  users = load_data(USERS_FILE)
  text = f"👥 **إجمالي المشتركين:** {len(users)}\n\n"
  for uid, info in list(users.items())[-15:]:
    text += (
        f"• {info.get('first_name')} (`{uid}`) - ينتهي: {info.get('expiry_date')[:10]}\n"
    )
  bot.send_message(message.chat.id, text, parse_mode="Markdown")


# --- معالجة الأزرار النصية ---
@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
  text = message.text
  user_id = str(message.from_user.id)

  if text == "📊 الصفقات المقترحة":
    sample_signal = format_trade_signal(
        "BTC/USDT", 64200, 66500, 68800, 62800, "BUY", "تحليلي فني للسبوت"
    )
    bot.send_message(message.chat.id, sample_signal, parse_mode="Markdown")

  elif text == "🟡 صفقات الذهب XAUUSD":
    sample_gold = format_trade_signal(
        "XAUUSD (الذهب)", 2380, 2405, 2430, 2365, "BUY", "تذبذب جلسة نيويورك"
    )
    bot.send_message(message.chat.id, sample_gold, parse_mode="Markdown")

  elif text == "ℹ️ معلومات اشتراكي":
    users = load_data(USERS_FILE)
    user_info = users.get(user_id)
    if user_info:
      expiry = user_info.get("expiry_date", "مجهول")[:10]
      bot.send_message(
          message.chat.id,
          f"👤 **معلومات حسابك:**\n🆔 المعرف: `{user_id}`\n📅 تاريخ انتهاء الاشتراك: `{expiry}`",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(
          message.chat.id, "أرسل /start لتسجيل حسابك وبدء الفترة التجريبية."
      )

  elif text == "🧮 حاسبة المخاطر":
    bot.send_message(
        message.chat.id,
        "🧮 **حاسبة المخاطر:**\nادخل حجم رأس مالك ونسبة المخاطرة (مثلاً 1%) ليتم حساب الخسارة القصوى بأمان.",
    )

  elif text == "📚 الأكاديمية والقاموس":
    bot.send_message(
        message.chat.id,
        "📚 **الأكاديمية التعليمية:**\nاستخدم الأمر `/search` متبوعاً بالمصطلح للبحث السريع في قاموس الحيتان والمفاهيم.",
    )

  elif text == "🛡️ استراتيجية التأمين (DCA)":
    bot.send_message(
        message.chat.id,
        "🛡️ **استراتيجية حماية الأصل الأساسي:**\nنظام يعتمد على جني 25% من الأرباح الصافية وتحويلها لـ USDT دون المساس بكمية الأصول الأساسية (مثل البيتكوين).",
    )


# --- نقطة التشغيل الرئيسية (تشغيل خادم الويب والبوت معاً) ---
if __name__ == "__main__":
  # تشغيل خادم Flask في خلفية النظام لفتح البورت المطلوب لمنصة Render
  flask_thread = Thread(target=run_flask)
  flask_thread.daemon = True
  flask_thread.start()
  print("Flask web server started on port 10000...")

  # تشغيل بوت تيليجرام
  print("Telegram Bot is running securely...")
  bot.infinity_polling()
