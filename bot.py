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
    # مستخدم جديد تماماً: منح فترة تجريبية 3 أيام لمنع استغلال مسح الدردشة
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
  # التحقق من الاشتراك الدائم
  if user_data.get("is_subscriber", False):
    return True, "مشترك دائم"

  # التحقق من انتهاء الفترة التجريبية
  trial_until_str = user_data.get("trial_until")
  if trial_until_str:
    trial_end_dt = datetime.strptime(trial_until_str, "%Y-%m-%d %H:%M:%S")
    if now < trial_end_dt:
      return True, f"فترة تجريبية نشطة حتى: {trial_until_str}"
    else:
      return (
          فالس,
          "انتهت فترتك التجريبية المجرّدة (3 أيام). يرجى الاشتراك للمتابعة.",
      )

  return False, "غير مسموح بالوصول."


# ----------------- نظام التقرير الأسبوعي والشهري التلقائي -----------------
def update_periodic_performance_reports():
  data = load_json(RESULTS_FILE, {"deals": [], "weekly_reports": [], "monthly_reports": []})
  deals = data.get("deals", [])
  if not deals:
    return

  now = datetime.now()
  # إحصائيات الأسبوع الأخير (آخر 7 أيام)
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
      # تحديث التقارير الدورية تلقائياً في الخلفية
      update_periodic_performance_reports()
    except Exception as e:
      print(f"Background monitor error: {e}")
    time.sleep(300)  # فحص كل 5 دقائق


# ----------------- أوامر تيليجرام (البوت) -----------------
@bot.message_handler(commands=["start"])
def cmd_start(message):
  user_id = message.from_user.id
  allowed, msg = check_user_access(user_id)

  welcome_text = (
      f"مرحباً بك يا مهندس أحمد في بوت التداول السوري الاحترافي.\n"
      f"حالة الحساب: {msg}\n\n"
      "اختر من القائمة أدناه للبدء:"
  )

  markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
  markup.add(
      types.KeyboardButton("📈 الصفقات والنتائج"),
      types.KeyboardButton("📊 إحصائيات الأداء"),
  )
  markup.add(
      types.KeyboardButton("💡 الذهب والأهداف"),
      types.KeyboardButton("⚙️ المساعدة"),
  )

  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


@bot.message_handler(func=lambda msg: msg.text == "📈 الصفقات والنتائج")
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


@bot.message_handler(func=lambda msg: msg.text == "📊 إحصائيات الأداء")
def show_stats_report(message):
  data = load_json(RESULTS_FILE, {"weekly_reports": [], "monthly_reports": []})
  weekly = data.get("weekly_reports", [{}])
  monthly = data.get("monthly_reports", [{}])

  w_stat = weekly[0] if weekly else {}
  m_stat = monthly[0] if monthly else {}

  text = (
      "📈 **التقرير الإحصائي للأداء:**\n\n"
      "🔹 **الملخص الأسبوعي (آخر 7 أيام):**\n"
      f"- إجمالي الصفقات: {w_stat.get('total_deals', 0)}\n"
      f"- صفقات رابحة (Win): {w_stat.get('wins', 0)}\n"
      f"- صفقات مؤمنة (Break-Even): {w_stat.get('breakeven', 0)}\n"
      f"- صفقات خاسرة (Loss): {w_stat.get('losses', 0)}\n"
      f"- نسبة النجاح: {w_stat.get('win_rate', 0.0)}%\n\n"
      "🔸 **الملخص الشهري (آخر 30 يوماً):**\n"
      f"- إجمالي الصفقات: {m_stat.get('total_deals', 0)}\n"
      f"- صفقات رابحة (Win): {m_stat.get('wins', 0)}\n"
      f"- صفقات مؤمنة (Break-Even): {m_stat.get('breakeven', 0)}\n"
      f"- صفقات خاسرة (Loss): {m_stat.get('losses', 0)}\n"
      f"- نسبة النجاح: {m_stat.get('win_rate', 0.0)}%\n"
  )
  bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(commands=["add_result"])
def admin_add_result(message):
  if message.from_user.id != ADMIN_ID:
    bot.send_message(message.chat.id, "هذا الأمر مخصص للمدير فقط.")
    return

  # مثال توضيحي لإضافة صفقة: /add_result XAUUSD BUY Win
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
  # تشغيل سيرفر Flask في خيط خلفي (Background Thread) للحفاظ على الـ Uptime
  flask_thread = threading.Thread(target=run_flask, daemon=True)
  flask_thread.start()

  # تشغيل مراقب الأسعار الخلفي
  monitor_thread = threading.Thread(target=target := background_price_monitor, daemon=True)
  monitor_thread.start()

  print("Bot server and background workers initialized successfully.")

  # إزالة الويب هوك القديم وإلغاء أي جلسات معلقة لمنع خطأ التعارض 409 نهائياً
  try:
    bot.remove_webhook(drop_pending_updates=True)
    print("Old webhook and pending updates cleared successfully.")
  except Exception as e:
    print(f"Webhook clearance notice: {e}")

  # بدء استقبال الرسائل والطلبات عبر التلفزيون/تيليجرام Long Polling باستقرار تان
  while True:
    try:
      bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
    except Exception as e:
      print(f"Polling connection error: {e}")
      time.sleep(5)
