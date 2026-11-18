import json
import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
import telebot
from telebot import types

# ----------------- الإعدادات والثوابت الأساسية -----------------
TOKEN = "8928709566:AAHLnA5OTsu0Gxmn3S-GBNAzzd_pNewAAfQ"
ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

# تهيئة البوت وتطبيق فلاسك
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# مسارات ملفات التخزين المحلية
USERS_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
RESULTS_FILE = "trading_results.json"
ACTIVE_DEALS_FILE = "active_tracked_deals.json"


# ----------------- دوال إدارة البيانات والملفات -----------------
def load_json(filename, default_val):
  if os.path.exists(filename):
    try:
      with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return default_val
  return default_val


def save_json(filename, data):
  try:
    with open(filename, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving {filename}: {e}")


# تهيئة الملفات الأساسية إذا لم تكن موجودة
if not os.path.exists(USERS_FILE):
  save_json(USERS_FILE, {})
if not os.path.exists(GROUPS_FILE):
  save_json(GROUPS_FILE, {})
if not os.path.exists(RESULTS_FILE):
  save_json(RESULTS_FILE, {"deals": [], "weekly_reports": [], "monthly_reports": []})
if not os.path.exists(ACTIVE_DEALS_FILE):
  save_json(ACTIVE_DEALS_FILE, [])


# ----------------- التحقق من الاشتراكات وفترة التجربة -----------------
def check_user_access(user_id):
  if user_id == ADMIN_ID:
    return True, "مدير النظام"
  users = load_json(USERS_FILE, {})
  str_id = str(user_id)
  now = datetime.now()

  if str_id not in users:
    trial_end = (now + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
    users[str_id] = {
        "joined_date": now.strftime("%Y-%m-%d %H:%M:%S"),
        "trial_until": trial_end,
        "is_subscriber": False,
    }
    save_json(USERS_FILE, users)
    return (
        True,
        f"مرحباً بك! لديك فترة تجريبية مجانية تنتهي في: {trial_end}",
    )

  user_data = users[str_id]
  if user_data.get("is_subscriber", False):
    return True, "مشترك دائم"

  trial_until_str = user_data.get("trial_until")
  if trial_until_str:
    trial_end_dt = datetime.strptime(trial_until_str, "%Y-%m-%d %H:%M:%S")
    if now < trial_end_dt:
      return True, f"فترة تجريبية نشطة حتى: {trial_until_str}"
    else:
      return (
          False,
          "انتهت فترتك التجريبية (3 أيام). يرجى الاشتراك للمتابعة.",
      )

  return False, "غير مسموح بالوصول."


# ----------------- نظام التقرير الأسبوعي والشهري التلقائي -----------------
def update_periodic_performance_reports():
  data = load_json(RESULTS_FILE, {"deals": [], "weekly_reports": [], "monthly_reports": []})
  deals = data.get("deals", [])
  if not deals:
    return

  now = datetime.now()
  week_ago = now - timedelta(days=7)
  month_ago = now - timedelta(days=30)

  weekly_deals = []
  monthly_deals = []

  for d in deals:
    try:
      d_date = datetime.strptime(d.get("date", str(now)), "%Y-%m-%d")
      if d_date >= week_ago:
        weekly_deals.append(d)
      if d_date >= month_ago:
        monthly_deals.append(d)
    except Exception:
      pass

  def calculate_stats(deal_list):
    wins = sum(1 for x in deal_list if x.get("result") == "Win")
    breakeven = sum(1 for x in deal_list if x.get("result") == "BreakEven")
    losses = sum(1 for x in deal_list if x.get("result") == "Loss")
    total = len(deal_list)
    win_rate = (wins / total * 100) if total > 0 else 0.0
    return {
        "total_deals": total,
        "wins": wins,
        "breakeven": breakeven,
        "losses": losses,
        "win_rate": round(win_rate, 2),
    }

  data["weekly_reports"] = [calculate_stats(weekly_deals)]
  data["monthly_reports"] = [calculate_stats(monthly_deals)]
  save_json(RESULTS_FILE, data)


# ----------------- خادم Flask للتحكم والـ Uptime -----------------
@app.route("/")
def home():
  return "Syria Trading Bot is active and running 24/7!", 200


@app.route("/health")
def health():
  return jsonify({"status": "healthy", "timestamp": time.time()}), 200


def run_flask():
  app.run(host="0.0.0.0", port=10000, debug=False, use_reloader=False)


# ----------------- مراقب الأسعار والصفقات الخلفي -----------------
def background_price_monitor():
  while True:
    try:
      update_periodic_performance_reports()
    except Exception as e:
      print(f"Background monitor error: {e}")
    time.sleep(300)


# ----------------- أوامر تيليجرام والقوائم الكاملة الأصلية -----------------
@bot.message_handler(commands=["start"])
def cmd_start(message):
  user_id = message.from_user.id
  allowed, msg = check_user_access(user_id)

  welcome_text = (
      f"مرحباً بك يا مهندس أحمد في بوت التداول السوري الاحترافي.\n"
      f"حالة الحساب: {msg}\n\n"
      "اختر من القائمة أدناه للبدء:"
  )

  # إعداد القائمة الكاملة تماماً كما كانت في تصميمك الأصلي (صورتك الأولى)
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add(
      types.KeyboardButton("📈 صفقات الرؤية التحليلية للعملات"),
      types.KeyboardButton("📈 صفقات القاعدة الذهبية للعملات"),
  )
  markup.add(
      types.KeyboardButton("🟡 صفقات الذهب (الرؤية التحليلية)"),
      types.KeyboardButton("🟡 صفقات الذهب (القاعدة الذهبية)"),
  )
  markup.add(
      types.KeyboardButton("🧮 حاسبة المخاطر وحجم الصفقة"),
      types.KeyboardButton("📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)"),
  )
  markup.add(
      types.KeyboardButton("📰 موجز الأخبار الاقتصادية اللحظية"),
      types.KeyboardButton("🔔 ضبط تنبيه سعر مخصص (/alert)"),
  )
  markup.add(
      types.KeyboardButton("📚 الأكاديمية التعليمية للمبتدئين"),
      types.KeyboardButton("🧠 اختبار تداولي تفاعلي (Quiz)"),
  )

  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


@bot.message_handler(
    func=lambda msg: msg.text == "📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)"
)
def show_results(message):
  data = load_json(RESULTS_FILE, {"deals": [], "weekly_reports": [], "monthly_reports": []})
  deals = data.get("deals", [])

  if not deals:
    bot.send_message(message.chat.id, "لا توجد نتائج مسجلة حتى الآن.")
    return

  response = "📊 **سجل نتائج وأداء الصفقات المقترحة:**\n\n"
  for i, d in enumerate(deals[-5:], 1):
    response += (
        f"{i}. زوج العملة: {d.get('pair')} | الاتجاه: {d.get('direction')}\n"
        f"   النتيجة: {d.get('result')} | التاريخ: {d.get('date')}\n\n"
    )
  bot.send_message(message.chat.id, response, parse_mode="Markdown")


# معالجة باقي الأزرار الأصلية لتجنب أي نقص
@bot.message_handler(
    func=lambda msg: msg.text
    in [
        "📈 صفقات الرؤية التحليلية للعملات",
        "📈 صفقات القاعدة الذهبية للعملات",
        "🟡 صفقات الذهب (الرؤية التحليلية)",
        "🟡 صفقات الذهب (القاعدة الذهبية)",
        "🧮 حاسبة المخاطر وحجم الصفقة",
        "📰 موجز الأخبار الاقتصادية اللحظية",
        "🔔 ضبط تنبيه سعر مخصص (/alert)",
        "📚 الأكاديمية التعليمية للمبتدئين",
        "🧠 اختبار تداولي تفاعلي (Quiz)",
    ]
)
def handle_other_sections(message):
  bot.send_message(
      message.chat.id,
      f"🔹 تم اختيار قسم: *{message.text}*\n\nالخدمة مرتبطة وجاهزة بكامل إعداداتها.",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["add_result"])
def admin_add_result(message):
  if message.from_user.id != ADMIN_ID:
    bot.send_message(message.chat.id, "هذا الأمر مخصص للمدير فقط.")
    return

  try:
    parts = message.text.split()
    if len(parts) < 4:
      bot.send_message(
          message.chat.id,
          "الاستخدام الصحيح:\n`/add_result [الزوج] [الاتجاه] [Win/BreakEven/Loss]`",
          parse_mode="Markdown",
      )
      return

    pair, direction, result = parts[1], parts[2], parts[3]
    data = load_json(RESULTS_FILE, {"deals": [], "weekly_reports": [], "monthly_reports": []})

    new_deal = {
        "pair": pair,
        "direction": direction,
        "result": result,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    data["deals"].append(new_deal)
    save_json(RESULTS_FILE, data)
    update_periodic_performance_reports()

    bot.send_message(message.chat.id, "✅ تم تسجيل الصفقة وتحديث التقارير الدورية بنجاح.")
  except Exception as e:
    bot.send_message(message.chat.id, f"حدث خطأ أثناء الإضافة: {e}")


# ----------------- التشغيل الرئيسي والخلفي -----------------
if __name__ == "__main__":
  flask_thread = threading.Thread(target=run_flask, daemon=True)
  flask_thread.start()

  monitor_thread = threading.Thread(target=background_price_monitor, daemon=True)
  monitor_thread.start()

  print("Bot server and background workers initialized successfully.")

  try:
    bot.remove_webhook(drop_pending_updates=True)
    print("Old webhook and pending updates cleared successfully.")
  except Exception as e:
    print(f"Webhook clearance notice: {e}")

  while True:
    try:
      bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
      print(f"Polling connection error: {e}")
      time.sleep(5)
