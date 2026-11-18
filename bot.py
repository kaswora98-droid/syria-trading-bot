import json
import os
import threading
import time
import requests
import telebot
from telebot import types
from flask import Flask

# إعدادات التوكن وصلاحيات المشرف
TOKEN = os.getenv("BOT_TOKEN", "7407026857:AAH0mPoxUv5wR5yCqJgqR_G8y4Q1XgR5n2s")  # ضع توكن بوتك هنا أو عبر متغير البيئة
ADMIN_IDS = [8611033531]  # معرف المشرف الأساسي

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# مسارات ملفات التخزين المحلي
USERS_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
ACTIVE_TRADES_FILE = "active_trades.json"
TRADING_RESULTS_FILE = "trading_results.json"


# دوال مساعدة لإدارة البيانات والملفات
def load_json(filename, default_value):
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return default_value
  return default_value


def save_json(filename, data):
  try:
    with open(filename, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii, indent=4)
  except Exception as e:
    print(f"Error saving {filename}: {e}")


# تهيئة الملفات الأساسية
active_trades = load_json(ACTIVE_TRADES_FILE, [])
trading_results = load_json(TRADING_RESULTS_FILE, [])


# دالة الكيبورد السفلي الثابت (ReplyKeyboardMarkup) حسب تفضيلك
def get_main_keyboard(user_id):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn_deals = types.KeyboardButton("📊 الصفقات المقترحة")
  btn_analysis = types.KeyboardButton("📈 التحليل الفني")
  btn_gold = types.KeyboardButton("🪙 أسعار الذهب والعملات")
  btn_results = types.KeyboardButton("📜 نتائج التداول")
  btn_alert = types.KeyboardButton("🔔 تنبيهات الأسعار")

  markup.add(btn_deals, btn_analysis)
  markup.add(btn_gold, btn_results)
  markup.add(btn_alert)

  if user_id in ADMIN_IDS:
    btn_admin = types.KeyboardButton("⚙️ لوحة المشرف")
    markup.add(btn_admin)

  return markup


# مسار الـ Flask الأساسي ليبقي السيرفر مستيقظاً عبر UptimeRobot
@app.route("/")
def home():
  return "Bot is running live and active 24/7!"


@app.route("/ping")
def ping():
  return "PONG", 200


# دالة تتبع الأسعار والصفقات في الخلفية
def background_trade_and_price_monitor():
  while True:
    try:
      # منطق الفحص والتحقق من الأهداف والوقف للصفقات النشطة
      time.sleep(60)
    except Exception as e:
      print(f"Error in background monitor: {e}")
      time.sleep(60)


# أمر البداية /start
@bot.message_handler(commands=["start"])
def send_welcome(message):
  user_id = message.from_user.id
  welcome_text = (
      f"أهلاً بك يا مهندس في بوت التداول المتطور والتحليل اللحظي.\n"
      f"جميع الأدوات والكيبورد السفلي جاهزة لخدمتك."
  )
  bot.send_message(
      message.chat.id, welcome_text, reply_markup=get_main_keyboard(user_id)
  )


# التعامل مع أزرار الكيبورد السفلي والنصوص
@bot.message_handler(
    func=lambda message: message.text
    in [
        "📊 الصفقات المقترحة",
        "📈 التحليل الفني",
        "🪙 أسعار الذهب والعملات",
        "📜 نتائج التداول",
        "🔔 تنبيهات الأسعار",
        "⚙️ لوحة المشرف",
    ]
)
def handle_reply_buttons(message):
  user_id = message.from_user.id
  text = message.text

  if text == "📊 الصفقات المقترحة":
    bot.send_message(
        message.chat.id,
        "إليك الصفقات المقترحة الحالية ورابط التتبع التلقائي:",
        reply_markup=get_main_keyboard(user_id),
    )
  elif text == "📈 التحليل الفني":
    bot.send_message(
        message.chat.id,
        "جاري جلب أحدث بيانات التحليل الفني والشموع...",
        reply_markup=get_main_keyboard(user_id),
    )
  elif text == "🪙 أسعار الذهب والعملات":
    bot.send_message(
        message.chat.id,
        "أسعار الذهب (XAUUSD) وعملات Spot الحالية متصلة مباشرة بالسوق.",
        reply_markup=get_main_keyboard(user_id),
    )
  elif text == "📜 نتائج التداول":
    bot.send_message(
        message.chat.id,
        "سجل نتائج الصفقات المحققة ومتابعة الأهداف (TP/SL):",
        reply_markup=get_main_keyboard(user_id),
    )
  elif text == "🔔 تنبيهات الأسعار":
    bot.send_message(
        message.chat.id,
        "أدخل السعر المطلوب لتنبيهك عند وصول السوق إليه:",
        reply_markup=get_main_keyboard(user_id),
    )
  elif text == "⚙️ لوحة المشرف" and user_id in ADMIN_IDS:
    bot.send_message(
        message.chat.id,
        "مرحباً بك في لوحة تحكم المشرف الأساسي.",
        reply_markup=get_main_keyboard(user_id),
    )


if __name__ == "__main__":

  def run_flask():
    try:
      port = int(os.environ.get("PORT", 10000))
      app.run(host="0.0.0.0", port=port, use_reloader=False)
    except Exception as e:
      print(f"Flask error: {e}")

  # تشغيل سيرفر الويب في خلفية منفصلة
  flask_thread = threading.Thread(target=run_flask, daemon=True)
  flask_thread.start()
  print("Flask web server started successfully...")

  # تشغيل عامل مراقبة الصفقات والأسعار
  monitor_thread = threading.Thread(
      target=background_trade_and_price_monitor, daemon=True
  )
  monitor_thread.start()
  print("Background trade and price monitor worker started...")

  try:
    bot.remove_webhook()
    print("Webhook removed successfully.")
    time.sleep(2)
  except Exception as e:
    print(f"Error removing webhook: {e}")

  print("Starting bot polling...")
  try:
    bot.infinity_polling(
        timeout=60, long_polling_timeout=60, skip_pending=True
    )
  except Exception as e:
    print(f"Polling error: {e}")
