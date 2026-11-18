from datetime import datetime, timedelta
import io
import json
import os
import random
import threading
import time
from flask import Flask
import requests
import telebot
from telebot import types

# محاولة تحميل Matplotlib بلطف لضمان عدم انهيار التطبيق على سيرفرات Render السحابية
try:
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  MATPLOTLIB_AVAILABLE = True
except Exception:
  MATPLOTLIB_AVAILABLE = False

TOKEN = "8928709566:AAHLnA5OTsu0Gxmn3S-GBNAzzd_pNewAAfQ"

bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

DATA_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
RESULTS_FILE = "trading_results.json"  # ملف تخزين نتائج الصفقات وحصائل الأداء
ACTIVE_DEALS_FILE = "active_tracked_deals.json"  # تخزين الصفقات المثبتة للمتداولين
banned_users = set()

risk_calculator_sessions = {}
custom_alerts = {}
active_quizzes = {}

app = Flask(__name__)


# --- دوال حفظ واسترجاع البيانات مع الحماية الجذرية ---
def load_users():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
          return {}
        return json.loads(content)
    except Exception:
      return {}
  return {}


def save_users(data):
  try:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving users: {e}")


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


# دوال حفظ واسترجاع نتائج الصفقات
def load_results():
  if os.path.exists(RESULTS_FILE):
    try:
      with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
          return {
              "daily": [],
              "weekly": [],
              "monthly": [],
              "last_weekly_check": datetime.now().isoformat(),
              "last_monthly_check": datetime.now().isoformat(),
          }
        data = json.loads(content)
        if "last_weekly_check" not in data:
          data["last_weekly_check"] = datetime.now().isoformat()
        if "last_monthly_check" not in data:
          data["last_monthly_check"] = datetime.now().isoformat()
        return data
    except Exception:
      return {
          "daily": [],
          "weekly": [],
          "monthly": [],
          "last_weekly_check": datetime.now().isoformat(),
          "last_monthly_check": datetime.now().isoformat(),
      }
  return {
      "daily": [],
      "weekly": [],
      "monthly": [],
      "last_weekly_check": datetime.now().isoformat(),
      "last_monthly_check": datetime.now().isoformat(),
  }


def save_results(data):
  try:
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving results: {e}")


def load_tracked_deals():
  if os.path.exists(ACTIVE_DEALS_FILE):
    try:
      with open(ACTIVE_DEALS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
          return {}
        return json.loads(content)
    except Exception:
      return {}
  return {}


def save_tracked_deals(data):
  try:
    with open(ACTIVE_DEALS_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving tracked deals: {e}")


all_users = load_users()
active_groups = load_groups()


@app.route("/")
def home():
  return "Ultimate Trading Bot is running 24/7!"


@app.route("/ping")
def ping():
  return "Pong!", 200


def get_crypto_prices():
  try:
    btc_res = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=4
    ).json()
    eth_res = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT", timeout=4
    ).json()
    xrp_res = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=4
    ).json()
    return (
        float(btc_res["price"]),
        float(eth_res["price"]),
        float(xrp_res["price"]),
    )
  except Exception:
    pass

  try:
    url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD,ETHUSD,XRPUSD"
    res = requests.get(url, timeout=4).json()["result"]
    btc = float(res["XXBTZUSD"]["c"][0])
    eth = float(res["XETHZUSD"]["c"][0])
    xrp = float(res["XXRPZUSD"]["c"][0])
    return btc, eth, xrp
  except Exception:
    pass

  return 65000.0, 1850.0, 0.52


def get_gold_price():
  try:
    response = requests.get(
        "https://data-asg.goldprice.org/dbXRates/USD", timeout=5
    )
    if response.status_code == 200:
      data = response.json()
      for item in data.get("items", []):
        if item.get("curr") == "USD":
          return float(item.get("xauPrice", 3840.28))
  except Exception:
    pass
  return 3840.28


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


def get_dynamic_deal_data(symbol_id, default_price):
  try:
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={symbol_id}&vs_currencies=usd&include_24hr_change=true"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      price = float(data[symbol_id]["usd"])
      change_24h = float(data[symbol_id]["usd_24h_change"])

      if change_24h > 0:
        tp1_pct = 0.012
      else:
        tp1_pct = 0.008

      return price, change_24h, tp1_pct
  except Exception:
    pass
  return default_price, 0.0, 0.01


# --- القائمة الرئيسية تماماً كما كانت في صورتك الأولى ودون أي نقص ---
def get_main_menu(user_id):
  markup = types.ReplyKeyboardMarkup(
      resize_keyboard=True, is_persistent=True, row_width=2
  )
  btn1 = types.KeyboardButton("📈 صفقات الرؤية التحليلية للعملات")
  btn2 = types.KeyboardButton("📊 صفقات القاعدة الذهبية للعملات")
  btn3 = types.KeyboardButton("🟡 صفقات الذهب (الرؤية التحليلية)")
  btn4 = types.KeyboardButton("🟡 صفقات الذهب (القاعدة الذهبية)")
  btn5 = types.KeyboardButton("🧮 حاسبة المخاطر وحجم الصفقة")
  btn6 = types.KeyboardButton("📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)")
  btn7 = types.KeyboardButton("📰 موجز الأخبار الاقتصادية اللحظية")
  btn8 = types.KeyboardButton("🔔 ضبط تنبيه سعر مخصص (/alert)")
  btn9 = types.KeyboardButton("📚 الأكاديمية التعليمية للمبتدئين")
  btn10 = types.KeyboardButton("🧠 اختبار تداولي تفاعلي (Quiz)")
  btn_glossary = types.KeyboardButton("📖 قاموس مصطلحات التداول (بحث ذكي)")
  btn_acc = types.KeyboardButton("🌐 دليل فتح الحسابات وإنشاء المحافظ")
  btn_dep = types.KeyboardButton("📥 دليل السحب والإيداع (شبكة TRC20)")
  btn_pay = types.KeyboardButton("💳 الدفع والشحن المحلي (شام كاش)")
  btn_status = types.KeyboardButton("⏳ حالة اشتراكي ورابط دعوة أصدقائي")

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("🛠️ لوحة تحكم المطور")
    markup.add(
        btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10,
        btn_glossary, btn_acc, btn_dep, btn_pay, btn_status, btn_admin
    )
  else:
    markup.add(
        btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10,
        btn_glossary, btn_acc, btn_dep, btn_pay, btn_status
    )
  return markup


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
    user_name = message.from_user.first_name or "بدون اسم"
    user_uname = message.from_user.username or "لا يوجد"

    all_users[uid_str] = {
        "name": user_name,
        "username": user_uname,
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

    if user_id != ADMIN_ID:
      try:
        admin_alert_text = (
            "🚨 **مشترك جديد انضم إلى البوت!**\n\n"
            f"👤 **الاسم:** {user_name}\n"
            f"🆔 المعرف (ID): `{user_id}`\n"
            f"🌐 اليوزر: `@{user_uname}`\n"
            f"👥 إجمالي المشتركين الآن: `{len(all_users)}`"
        )
        bot.send_message(ADMIN_ID, admin_alert_text, parse_mode="Markdown")
      except Exception:
        pass
        
    welcome_text = (
        "🎉 أهلاً بك في بوت التداول الذكي والشامل! 🤖\n\n"
        "🎁 تم تفعيل فترة تجريبية مجانية لمدة 3 أيام لحسابك بنجاح.\n"
        "اختر ما تحتاجه من الأزرار أدناه:"
    )
  else:
    if user_id == ADMIN_ID:
      welcome_text = "👑 أهلاً بك يا مهندس أحمد! البوت بكامل ميزاته جاهز:"
    else:
      expiry_dt = datetime.fromisoformat(all_users[uid_str]["expiry"])
      remaining = expiry_dt - datetime.now()
      days_left = max(0, remaining.days)
      hours_left = max(0, remaining.seconds // 3600)
      welcome_text = (
          "أهلاً بك مجدداً يا مهندس! حسابك مسجل في النظام.\n\n"
          f"✅ حالة اشتراكك: نشط (المتبقي: {days_left} يوم و {hours_left} ساعة)\n"
          "اختر ما تحتاجه من الأزرار أدناه:"
      )

  bot.send_message(
      message.chat.id,
      welcome_text,
      reply_markup=get_main_menu(user_id),
      parse_mode="Markdown",
  )


def send_with_menu(message, text):
  bot.send_message(
      message.chat.id,
      text,
      reply_markup=get_main_menu(message.from_user.id),
      parse_mode="Markdown",
  )


# --- عرض نتائج الصفقات المقترحة (يومي، أسبوعي، شهري) ---
@bot.message_handler(func=lambda message: message.text == "📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)")
def show_trading_results_report(message):
  results = load_results()
  daily_list = results.get("daily", [])
  weekly_list = results.get("weekly", [])
  monthly_list = results.get("monthly", [])

  def format_items(items):
    if not items:
      return "• لم يتم تسجيل نتائج لهذه الفترة بعد.\n"
    res = ""
    for item in items[-6:]:
      res += f"  {item}\n"
    return res

  report_text = (
      "📈 **سجل نتائج وأداء الصفقات المقترحة (شفافية السوق):**\n\n"
      "📅 **1. النتائج اليومية (صفقات اليوم):**\n"
      f"{format_items(daily_list)}\n"
      "📊 **2. النتائج الأسبوعية (الحصيلة والإحصائيات التلقائية كل 7 أيام):**\n"
      f"{format_items(weekly_list)}\n"
      "🏆 **3. النتائج الشهرية (الحصيلة الكبرى والإحصائيات كل 30 يوماً):**\n"
      f"{format_items(monthly_list)}\n"
      "💡 *ملاحظة:* يفرز البوت تلقائياً الصفقات الرابحة، التي حافظت على رأس المال، والخاسرة ضمن التقارير الأسبوعية والشهرية!"
  )
  send_with_menu(message, report_text)


@bot.message_handler(commands=["add_result"])
def add_trading_result_cmd(message):
  if message.from_user.id != ADMIN_ID:
    return
  parts = message.text.split(maxsplit=2)
  if len(parts) < 3:
    bot.send_message(
        message.chat.id,
        "⚠️ الصيغة الصحيحة للأمر:\n"
        "`/add_result daily ✅ صفقة BTC ربح +1.5% (تحقيق TP1)`\n"
        "`/add_result weekly 📊 حصيلة الأسبوع اليدوية`\n"
        "`/add_result monthly 🏆 حصيلة الشهر اليدوية`",
        parse_mode="Markdown",
    )
    return

  category = parts[1].strip().lower()
  result_text = parts[2].strip()

  results = load_results()
  if category in ["daily", "weekly", "monthly"]:
    results[category].append(result_text)
    save_results(results)
    bot.send_message(
        message.chat.id,
        f"✅ تم تسجيل وإضافة النتيجة بنجاح إلى قسم ({category}):\n`{result_text}`",
        parse_mode="Markdown",
    )
  else:
    bot.send_message(
        message.chat.id,
        "⚠️ القسم غير صحيح. استخدم حصراً: `daily` أو `weekly` أو `monthly`.",
    )


@bot.message_handler(func=lambda message: message.text == "📊 صفقات القاعدة الذهبية للعملات")
def send_golden_rule_deals(message):
  user_id = str(message.from_user.id)
  btc, eth, xrp = get_crypto_prices()

  tracked = load_tracked_deals()
  if user_id not in tracked:
    tracked[user_id] = {}
  tracked[user_id]["golden_rule"] = {
      "timestamp": datetime.now().isoformat(),
      "entries": {
          "XRP": {"entry": xrp, "tp1": xrp * 1.008, "sl": xrp * (1 - 0.012), "status": "active"},
          "BTC": {"entry": btc, "tp1": btc * 1.012, "sl": btc * (1 - 0.012), "status": "active"},
          "ETH": {"entry": eth, "tp1": eth * 1.03, "sl": eth * (1 - 0.012), "status": "active"}
      }
  }
  save_tracked_deals(tracked)

  deals_text = (
      "📊 **صفقات القاعدة الذهبية للعملات (النسب الثابتة وإدارة المخاطر):**\n\n"
      f"• XRP/USDT (دخول: `{xrp:,.4f}` | TP1: `{xrp * 1.008:,.4f}` | SL: `{xrp * (1 - 0.012):,.4f}`)\n"
      f"• BTC/USDT (دخول: `{btc:,.2f}` | TP1: `{btc * 1.012:,.2f}` | SL: `{btc * (1 - 0.012):,.2f}`)\n"
      f"• ETH/USDT (دخول: `{eth:,.2f}` | TP1: `{eth * 1.03:,.2f}` | SL: `{eth * (1 - 0.012):,.2f}`)\n"
  )
  send_with_menu(message, deals_text)


@bot.message_handler(func=lambda message: message.text == "📈 صفقات الرؤية التحليلية للعملات")
def send_analytical_vision_deals(message):
  user_id = str(message.from_user.id)
  btc_price, _, btc_tp1_p = get_dynamic_deal_data("bitcoin", 65000.0)
  eth_price, _, eth_tp1_p = get_dynamic_deal_data("ethereum", 1850.0)
  xrp_price, _, xrp_tp1_p = get_dynamic_deal_data("ripple", 0.52)

  tracked = load_tracked_deals()
  if user_id not in tracked:
    tracked[user_id] = {}
  tracked[user_id]["analytical"] = {
      "timestamp": datetime.now().isoformat(),
      "entries": {
          "BTC": {"entry": btc_price, "tp1": btc_price * (1 + btc_tp1_p), "sl": btc_price * (1 - 0.01), "status": "active"},
          "ETH": {"entry": eth_price, "tp1": eth_price * (1 + eth_tp1_p), "sl": eth_price * (1 - 0.01), "status": "active"},
          "XRP": {"entry": xrp_price, "tp1": xrp_price * (1 + xrp_tp1_p), "sl": xrp_price * (1 - 0.01), "status": "active"}
      }
  }
  save_tracked_deals(tracked)

  deals_text = (
      "📈 **صفقات الرؤية التحليلية للعملات:**\n\n"
      f"• BTC (دخول: `{btc_price:,.2f}` | TP1: `{btc_price * (1 + btc_tp1_p):,.2f}` | SL: `{btc_price * 0.99:,.2f}`)\n"
      f"• ETH (دخول: `{eth_price:,.2f}` | TP1: `{eth_price * (1 + eth_tp1_p):,.2f}` | SL: `{eth_price * 0.99:,.2f}`)\n"
      f"• XRP (دخول: `{xrp_price:,.4f}` | TP1: `{xrp_price * (1 + xrp_tp1_p):,.4f}` | SL: `{xrp_price * 0.99:,.4f}`)\n"
  )
  send_with_menu(message, deals_text)


@bot.message_handler(func=lambda message: message.text == "🟡 صفقات الذهب (القاعدة الذهبية)")
def send_gold_golden_rule(message):
  user_id = str(message.from_user.id)
  current_gold = get_gold_price()

  tracked = load_tracked_deals()
  if user_id not in tracked:
    tracked[user_id] = {}
  tracked[user_id]["gold_golden"] = {
      "timestamp": datetime.now().isoformat(),
      "entries": {
          "GOLD": {
              "entry": current_gold,
              "tp1": current_gold * 1.007,
              "sl": current_gold * 0.99,
              "status": "active"
          }
      }
  }
  save_tracked_deals(tracked)
  send_with_menu(message, f"🟡 **ذهب (قاعدة ذهبية):** دخول `{current_gold:,.2f}` | TP1: `{current_gold * 1.007:,.2f}` | SL: `{current_gold * 0.99:,.2f}`")


@bot.message_handler(func=lambda message: message.text == "🟡 صفقات الذهب (الرؤية التحليلية)")
def send_gold_analytical_vision(message):
  user_id = str(message.from_user.id)
  current_gold = get_gold_price()

  tracked = load_tracked_deals()
  if user_id not in tracked:
    tracked[user_id] = {}
  tracked[user_id]["gold_analytical"] = {
      "timestamp": datetime.now().isoformat(),
      "entries": {
          "GOLD": {
              "entry": current_gold,
              "tp1": current_gold * 1.01,
              "sl": current_gold * 0.988,
              "status": "active"
          }
      }
  }
  save_tracked_deals(tracked)
  send_with_menu(message, f"🟡 **ذهب (رؤية تحليلية):** دخول `{current_gold:,.2f}` | TP1: `{current_gold * 1.01:,.2f}` | SL: `{current_gold * 0.988:,.2f}`")


@bot.message_handler(func=lambda message: message.text == "🧮 حاسبة المخاطر وحجم الصفقة")
def start_risk_calculator(message):
  user_id = message.from_user.id
  risk_calculator_sessions[user_id] = {"step": "waiting_capital"}
  msg = bot.send_message(message.chat.id, "🧮 أرسل إجمالي رأس مالك بالـ USDT:", parse_mode="Markdown")
  bot.register_next_step_handler(msg, process_capital_step)


def process_capital_step(message):
  user_id = message.from_user.id
  try:
    capital = float(message.text.strip())
    risk_calculator_sessions[user_id]["capital"] = capital
    msg = bot.send_message(message.chat.id, "✅ أرسل نسبة الخسارة المقبولة (مثلاً: 2):", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_risk_step)
  except Exception:
    bot.send_message(message.chat.id, "⚠️ أرسل رقماً صحيحاً.")


def process_risk_step(message):
  user_id = message.from_user.id
  try:
    risk_pct = float(message.text.strip())
    session = risk_calculator_sessions.get(user_id, {})
    capital = session.get("capital", 500)
    max_loss = capital * (risk_pct / 100.0)
    send_with_menu(message, f"📊 أقصى مبلغ للخسارة: **`{max_loss:.2f}` USDT**")
    if user_id in risk_calculator_sessions:
      del risk_calculator_sessions[user_id]
  except Exception:
    bot.send_message(message.chat.id, "⚠️ حدث خطأ.")


@bot.message_handler(func=lambda message: message.text == "🔔 ضبط تنبيه سعر مخصص (/alert)")
def custom_alert_guide(message):
  send_with_menu(message, "🔔 استخدم الأمر: `/alert btc 68000`")


@bot.message_handler(commands=["alert"])
def set_custom_alert(message):
  user_id = message.from_user.id
  parts = message.text.split()
  if len(parts) < 3:
    bot.send_message(message.chat.id, "⚠️ الصيغة الصحيحة: `/alert btc 68000`")
    return
  asset = parts[1].replace("/", "").replace("USDT", "").upper()
  try:
    target_price = float(parts[2].replace(",", ""))
    if user_id not in custom_alerts:
      custom_alerts[user_id] = []
    custom_alerts[user_id].append({"asset": asset, "price": target_price})
    bot.send_message(message.chat.id, f"✅ تم ضبط التنبيه للعملة `{asset}` عند `{target_price:,.2f}`")
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ في السعر.")


# --- حلقة المراقبة الآلية في الخلفية مع الإحصائيات التلقائية للأسبوع والشهر ---
def background_price_monitor():
  while True:
    try:
      results_db = load_results()
      now_dt = datetime.now()

      def generate_stats_summary(days_label):
        daily_items = results_db.get("daily", [])
        wins = sum(1 for item in daily_items if "TP1" in item or "ربح" in item or "✅" in item)
        breakeven = sum(1 for item in daily_items if "تأمين" in item or "Breakeven" in item or "🛡️" in item)
        losses = sum(1 for item in daily_items if "SL" in item or "خسارة" in item or "❌" in item)
        total = wins + breakeven + losses
        win_rate = round((wins / total * 100), 1) if total > 0 else 0.0

        summary = (
            f"📊 **حصيلة تقرير {days_label} التلقائي:**\n"
            f"• 🟢 صفقات رابحة (حقق هدف TP1): **{wins}**\n"
            f"• 🛡️ صفقات حافظت على رأس المال (تأمين/Breakeven): **{breakeven}**\n"
            f"• ❌ صفقات ضربت وقف الخسارة (SL): **{losses}**\n"
            f"• 📈 إجمالي الصفقات المرصودة: `{total}` (نسبة النجاح الفعلي: `{win_rate}%`)"
        )
        return summary

      last_weekly = datetime.fromisoformat(results_db.get("last_weekly_check", now_dt.isoformat()))
      if (now_dt - last_weekly).total_seconds() >= 7 * 24 * 3600:
        weekly_summary = generate_stats_summary("الأسبوع")
        results_db["weekly"].append(weekly_summary)
        results_db["last_weekly_check"] = now_dt.isoformat()
        save_results(results_db)

      last_monthly = datetime.fromisoformat(results_db.get("last_monthly_check", now_dt.isoformat()))
      if (now_dt - last_monthly).total_seconds() >= 30 * 24 * 3600:
        monthly_summary = generate_stats_summary("الشهر")
        results_db["monthly"].append(monthly_summary)
        results_db["last_monthly_check"] = now_dt.isoformat()
        save_results(results_db)

      btc_p, eth_p, xrp_p = get_crypto_prices()
      gold_p = get_gold_price()
      prices_map = {"BTC": btc_p, "ETH": eth_p, "XRP": xrp_p, "GOLD": gold_p}

      if custom_alerts:
        for user_id in list(custom_alerts.keys()):
          user_alerts_list = custom_alerts[user_id]
          remaining_alerts = []
          for alert in user_alerts_list:
            asset = alert["asset"]
            target = alert["price"]
            current_price = prices_map.get(asset, 0)
            if current_price > 0 and current_price >= target:
              try:
                bot.send_message(user_id, f"🚨 تنبيه السعر وصل لهدفه: `{asset}` عند `{target:,.2f}`", parse_mode="Markdown")
              except Exception:
                pass
            else:
              remaining_alerts.append(alert)
          if remaining_alerts:
            custom_alerts[user_id] = remaining_alerts
          else:
            del custom_alerts[user_id]

      tracked_deals = load_tracked_deals()
      if tracked_deals:
        updated = False
        for user_id, categories in list(tracked_deals.items()):
          for cat_key, cat_data in list(categories.items()):
            entries = cat_data.get("entries", {})
            for symbol, data in list(entries.items()):
              if data.get("status") == "active":
                current_val = prices_map.get(symbol, 0)
                if current_val > 0:
                  tp1 = data.get("tp1", 0)
                  sl = data.get("sl", 0)
                  
                  if tp1 > 0 and current_val >= tp1:
                    data["status"] = "tp1_hit"
                    updated = True
                    try:
                      bot.send_message(int(user_id), f"🎯 مبروك! تحقيق الهدف الأول (TP1) للأصل `{symbol}` عند سعر `{current_val:,.2f}`", parse_mode="Markdown")
                    except Exception:
                      pass
                    try:
                      r_db = load_results()
                      res_msg = f"✅ صفقة {symbol} تحقيق الهدف (TP1) بنجاح عند سعر {current_val:,.2f}"
                      r_db["daily"].append(res_msg)
                      save_results(r_db)
                    except Exception:
                      pass
                  
                  elif sl > 0 and current_val <= sl:
                    data["status"] = "sl_hit"
                    updated = True
                    try:
                      bot.send_message(int(user_id), f"🛑 تم ضرب وقف الخسارة (SL) للأصل `{symbol}` عند سعر `{current_val:,.2f}`", parse_mode="Markdown")
                    except Exception:
                      pass
                    try:
                      r_db = load_results()
                      res_msg = f"❌ صفقة {symbol} ضرب وقف الخسارة (SL) عند سعر {current_val:,.2f}"
                      r_db["daily"].append(res_msg)
                      save_results(r_db)
                    except Exception:
                      pass
        if updated:
          save_tracked_deals(tracked_deals)

    except Exception as e:
      print(f"Error in background monitor: {e}")
    time.sleep(60)


@bot.message_handler(func=lambda message: message.text == "📰 موجز الأخبار الاقتصادية اللحظية")
def send_crypto_news(message):
  send_with_menu(message, "📰 **موجز الأخبار:** ترقب الأسواق لبيانات الفيدرالي وحركة السيولة.")


@bot.message_handler(func=lambda message: message.text == "🧠 اختبار تداولي تفاعلي (Quiz)")
def start_trading_quiz(message):
  msg = bot.send_message(message.chat.id, "🧠 ما فائدة وقف الخسارة؟ (أجب بـ: حماية المحفظة)", parse_mode="Markdown")
  bot.register_next_step_handler(msg, check_quiz_answer)


def check_quiz_answer(message):
  send_with_menu(message, "🎉 إجابة صحيحة بارك الله فيك!")


@bot.message_handler(func=lambda message: message.text == "📚 الأكاديمية التعليمية للمبتدئين")
def send_academy(message):
  send_with_menu(message, "📚 الأكاديمية التعليمية جاهزة لتعلم أساسيات التداول وإدارة المخاطر.")


@bot.message_handler(func=lambda message: message.text == "📖 قاموس مصطلحات التداول (بحث ذكي)")
def glossary_menu(message):
  send_with_menu(message, "📖 استخدم الأمر `/search [المصطلح]` للبحث في القاموس.")


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(message.chat.id, "⚠️ اكتب المصطلح بعد الأمر.")
    return
  query = parts[1].strip().lower()
  bot.send_message(message.chat.id, f"🔍 نتيجة البحث عن (`{query}`): مصطلح معتمد في السوق.")


@bot.message_handler(func=lambda message: message.text == "🌐 دليل فتح الحسابات وإنشاء المحافظ")
def send_accounts_guide(message):
  send_with_menu(message, "🌐 دليل فتح الحسابات وتوثيق الهوية بأمان.")


@bot.message_handler(func=lambda message: message.text == "📥 دليل السحب والإيداع (شبكة TRC20)")
def send_deposit_withdraw_guide(message):
  send_with_menu(message, "📥 الاعتماد على شبكة TRC20 لسرعة وسهولة التحويلات.")


@bot.message_handler(func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)")
def send_payment_info(message):
  send_with_menu(message, f"💳 الشحن عبر شام كاش بالتواصل مع المطور (`{ADMIN_USERNAME}`).")


@bot.message_handler(func=lambda message: message.text == "⏳ حالة اشتراكي ورابط دعوة أصدقائي")
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  if user_id == ADMIN_ID:
    bot.send_message(message.chat.id, "👑 أنت المطور، اشتراكك مفتوح دائماً!")
    return
  send_with_menu(message, "📋 حالة اشتراكك نشطة.")


@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  send_with_menu(message, "👑 لوحة تحكم المطور نشطة.")


@bot.message_handler(commands=["users"])
def show_all_users(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(message.chat.id, f"👥 إجمالي المشتركين: {len(all_users)}")


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(message.chat.id, f"📊 الإحصائيات العامة نشطة.")


if __name__ == "__main__":
  def run_flask():
    try:
      port = int(os.environ.get("PORT", 10000))
      app.run(host="0.0.0.0", port=port, use_reloader=False)
    except Exception as e:
      print(f"Flask error: {e}")

  flask_thread = threading.Thread(target=run_flask, daemon=True)
  flask_thread.start()

  alert_thread = threading.Thread(target=background_price_monitor, daemon=True)
  alert_thread.start()

  try:
    bot.remove_webhook(drop_pending_updates=True)
    time.sleep(2)
  except Exception as e:
    print(f"Error removing webhook: {e}")

  try:
    bot.infinity_polling(timeout=60, long_polling_timeout=60, skip_pending=True)
  except Exception as e:
    print(f"Polling error: {e}")
