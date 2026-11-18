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


# دوال حفظ واسترجاع نتائج الصفقات (يومي، أسبوعي، شهري مع طابع زمني للتجميع التلقائي)
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


# دوال إدارة وتثبيت الصفقات النشطة للمستخدمين
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


# جلب الأسعار الحية الحقيقية من السوق (Binance أولاً ثم Kraken احتياطياً)
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


# جلب سعر الذهب الحي (XAUUSD) المحدث
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


# مولد الرسوم البيانية الآمن
def generate_price_chart(btc_price):
  if not MATPLOTLIB_AVAILABLE:
    return None
  try:
    fig, ax = plt.subplots(figsize=(6, 3))
    prices = [
        btc_price * 0.99,
        btc_price * 0.995,
        btc_price * 0.992,
        btc_price * 1.002,
        btc_price,
    ]
    times = ["الان", "قبل ساعة", "قبل 3 ساعات", "قبل 6 ساعات", "السابقة"]

    ax.plot(
        times,
        prices,
        marker="o",
        color="#2b8a3e",
        linewidth=2,
        markersize=6,
    )
    ax.set_title("حركة السعر التحليلية (BTC/USDT)", fontsize=10, color="#333")
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.xticks(rotation=15, fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=150)
    buf.seek(0)
    plt.close(fig)
    return buf
  except Exception:
    return None


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
        trend_status = "🚀 زخم صاعد (Bullish Momentum)"
        tp1_pct = 0.012
        tp2_pct = 0.025
        sl_pct = 0.01
      else:
        trend_status = "🔻 ضغط بيعي / تصحيح (Bearish Pressure)"
        tp1_pct = 0.008
        tp2_pct = 0.015
        sl_pct = 0.008

      return price, change_24h, trend_status, tp1_pct, tp2_pct, sl_pct
  except Exception:
    pass
  return default_price, 0.0, "⚖️ استقرار جانبي (Consolidation)", 0.01, 0.02, 0.01


# --- القائمة الرئيسية ---
def get_main_menu(user_id):
  markup = types.ReplyKeyboardMarkup(
      resize_keyboard=True, is_persistent=True, row_width=2
  )
  btn_golden = types.KeyboardButton("📊 صفقات القاعدة الذهبية للعملات")
  btn_analytical = types.KeyboardButton("📊 صفقات الرؤية التحليلية للعملات")
  btn_gold_golden = types.KeyboardButton("🟡 صفقات الذهب (القاعدة الذهبية)")
  btn_gold_analytical = types.KeyboardButton("🟡 صفقات الذهب (الرؤية التحليلية)")
  
  btn_results = types.KeyboardButton("📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)")

  btn_calc = types.KeyboardButton("🧮 حاسبة المخاطر وحجم الصفقة")
  btn_alerts = types.KeyboardButton("🔔 ضبط تنبيه سعر مخصص (/alert)")
  btn_news = types.KeyboardButton("📰 موجز الأخبار الاقتصادية اللحظية")
  btn_quiz = types.KeyboardButton("🧠 اختبار تداولي تفاعلي (Quiz)")
  btn3 = types.KeyboardButton("📚 الأكاديمية التعليمية للمبتدئين")
  btn_glossary = types.KeyboardButton("📖 قاموس مصطلحات التداول (بحث ذكي)")
  btn4 = types.KeyboardButton("🌐 دليل فتح الحسابات وإنشاء المحافظ")
  btn5 = types.KeyboardButton("📥 دليل السحب والإيداع (شبكة TRC20)")
  btn6 = types.KeyboardButton("💳 الدفع والشحن المحلي (شام كاش)")
  btn7 = types.KeyboardButton("⏳ حالة اشتراكي ورابط دعوة أصدقائي")

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("🛠️ لوحة تحكم المطور")
    markup.add(
        btn_golden,
        btn_analytical,
        btn_gold_golden,
        btn_gold_analytical,
        btn_results,
        btn_calc,
        btn_alerts,
        btn_news,
        btn_quiz,
        btn3,
        btn_glossary,
        btn4,
        btn5,
        btn6,
        btn7,
        btn_admin,
    )
  else:
    markup.add(
        btn_golden,
        btn_analytical,
        btn_gold_golden,
        btn_gold_analytical,
        btn_results,
        btn_calc,
        btn_alerts,
        btn_news,
        btn_quiz,
        btn3,
        btn_glossary,
        btn4,
        btn5,
        btn6,
        btn7,
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


# --- ميزة عرض نتائج الصفقات المقترحة (يومي، أسبوعي، شهري) ---
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
      "📊 **2. النتائج الأسبوعية (الحصيلة التلقائية كل 7 أيام):**\n"
      f"{format_items(weekly_list)}\n"
      "🏆 **3. النتائج الشهرية (الحصيلة الكبرى كل 30 يوماً):**\n"
      f"{format_items(monthly_list)}\n"
      "💡 *ملاحظة:* يتم تحديث النتائج اليومية فور إغلاق الصفقة، ويتم تجميع النتائج أسبوعياً وشهرياً تلقائياً!"
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

  xrp_tp1_pct = calculate_profit_percentage(xrp, xrp * 1.008, "BUY")
  xrp_tp2_pct = calculate_profit_percentage(xrp, xrp * 1.015, "BUY")
  btc_tp1_pct = calculate_profit_percentage(btc, btc * 1.012, "BUY")
  btc_tp2_pct = calculate_profit_percentage(btc, btc * 1.025, "BUY")
  eth_tp1_pct = calculate_profit_percentage(eth, eth * 1.03, "BUY")
  eth_tp2_pct = calculate_profit_percentage(eth, eth * 1.06, "BUY")

  xrp_sl = xrp * (1 - 0.012)
  btc_sl = btc * (1 - 0.012)
  eth_sl = eth * (1 - 0.012)

  deals_text = (
      "📊 **صفقات القاعدة الذهبية للعملات (النسب الثابتة وإدارة المخاطر - بالسعر الحي):**\n\n"
      "📌 *تم تثبيت هذه الأسعار كمرجع لمتابعة أهدافك تلقائياً في الخلفية.*\n\n"
      "⚡ **1. صفقات السكالبينج للعملات:**\n"
      f"• **العملة:** XRP/USDT (سعر الدخول: `{xrp:,.4f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{xrp_sl:,.4f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{xrp * 1.008:,.4f}` ──> **(+{xrp_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** جني 50% ونقل وقف الخسارة لسعر الدخول (`{xrp:,.4f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{xrp * 1.015:,.4f}` ──> **(+{xrp_tp2_pct}%)**\n\n"
      "📅 **2. الصفقات اليومية للعملات:**\n"
      f"• **العملة:** BTC/USDT (سعر الدخول: `{btc:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{btc_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{btc * 1.012:,.2f}` ──> **(+{btc_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** جني نصف الربح وحرك وقف الخسارة لنقطة الدخول (`{btc:,.2f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{btc * 1.025:,.2f}` ──> **(+{btc_tp2_pct}%)**\n\n"
      "🌊 **3. صفقات السوينغ للعملات:**\n"
      f"• **العملة:** ETH/USDT (سعر الدخول: `{eth:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{eth_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{eth * 1.03:,.2f}` ──> **(+{eth_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** تأمين الصفقة عند الدخول (`{eth:,.2f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{eth * 1.06:,.2f}` ──> **(+{eth_tp2_pct}%)**"
  )
  send_with_menu(message, deals_text)

  chart_buf = generate_price_chart(btc)
  if chart_buf:
    bot.send_photo(
        message.chat.id,
        chart_buf,
        caption="📈 **الرسم البياني التحليلي (القاعدة الذهبية للعملات)**",
    )


@bot.message_handler(func=lambda message: message.text == "📊 صفقات الرؤية التحليلية للعملات")
def send_analytical_vision_deals(message):
  user_id = str(message.from_user.id)
  btc_price, btc_chg, btc_trend, btc_tp1_p, btc_tp2_p, btc_sl_p = (
      get_dynamic_deal_data("bitcoin", 65000.0)
  )
  eth_price, eth_chg, eth_trend, eth_tp1_p, eth_tp2_p, eth_sl_p = (
      get_dynamic_deal_data("ethereum", 1850.0)
  )
  xrp_price, xrp_chg, xrp_trend, xrp_tp1_p, xrp_tp2_p, xrp_sl_p = (
      get_dynamic_deal_data("ripple", 0.52)
  )

  tracked = load_tracked_deals()
  if user_id not in tracked:
    tracked[user_id] = {}
  tracked[user_id]["analytical"] = {
      "timestamp": datetime.now().isoformat(),
      "entries": {
          "BTC": {"entry": btc_price, "tp1": btc_price * (1 + btc_tp1_p), "sl": btc_price * (1 - btc_sl_p), "status": "active"},
          "ETH": {"entry": eth_price, "tp1": eth_price * (1 + eth_tp1_p), "sl": eth_price * (1 - eth_sl_p), "status": "active"},
          "XRP": {"entry": xrp_price, "tp1": xrp_price * (1 + xrp_tp1_p), "sl": xrp_price * (1 - xrp_sl_p), "status": "active"}
      }
  }
  save_tracked_deals(tracked)

  deals_text = (
      "📊 **صفقات الرؤية التحليلية وقراءة الزخم الحي للعملات:**\n\n"
      "📌 *تم تثبيت هذه الأسعار كمرجع لمتابعة أهدافك تلقائياً في الخلفية.*\n\n"
      f"🪙 **1. بيتكوين (BTC/USDT):**\n"
      f"• السعر الحالي: `{btc_price:,.2f}$` (التغير 24س: `{btc_chg:+.2f}%`)\n"
      f"• الحالة: {btc_trend}\n"
      f"  🛑 *SL:* `{btc_price * (1 - btc_sl_p):,.2f}`\n"
      f"  🎯 *TP1:* `{btc_price * (1 + btc_tp1_p):,.2f}` (+{btc_tp1_p*100}%)\n\n"
      f"💎 **2. إيثريوم (ETH/USDT):**\n"
      f"• السعر الحالي: `{eth_price:,.2f}$` (التغير 24س: `{eth_chg:+.2f}%`)\n"
      f"• الحالة: {eth_trend}\n"
      f"  🛑 *SL:* `{eth_price * (1 - eth_sl_p):,.2f}`\n"
      f"  🎯 *TP1:* `{eth_price * (1 + eth_tp1_p):,.2f}` (+{eth_tp1_p*100}%)\n\n"
      f"⚡ **3. ريبل (XRP/USDT):**\n"
      f"• السعر الحالي: `{xrp_price:,.4f}$` (التغير 24س: `{xrp_chg:+.2f}%`)\n"
      f"• الحالة: {xrp_trend}\n"
      f"  🛑 *SL:* `{xrp_price * (1 - xrp_sl_p):,.4f}`\n"
      f"  🎯 *TP1:* `{xrp_price * (1 + xrp_tp1_p):,.2f}` (+{xrp_tp1_p*100}%)\n"
  )
  send_with_menu(message, deals_text)


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (القاعدة الذهبية)"
)
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
              "tp1": current_gold * (1 + 0.007),
              "sl": current_gold * (1 - 0.01),
              "status": "active"
          }
      }
  }
  save_tracked_deals(tracked)

  tp1_price = current_gold * (1 + 0.007)
  sl_price = current_gold * (1 - 0.01)

  gold_text = (
      "🟡 **توصيات صفقات الذهب (القاعدة الذهبية):**\n\n"
      "📌 *تم تثبيت هذا السعر كمرجع لتتبع الأهداف تلقائياً في الخلفية.*\n\n"
      f"📍 **سعر الدخول الحالي (Entry):** `{current_gold:,.2f}` $\n"
      f"🛑 **وقف الخسارة المقترح (SL):** `{sl_price:,.2f}` $ (-1.0%)\n\n"
      f"• **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ ──> **(+0.7%)**\n"
  )
  send_with_menu(message, gold_text)


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (الرؤية التحليلية)"
)
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
              "tp1": current_gold * (1 + 0.01),
              "sl": current_gold * (1 - 0.012),
              "status": "active"
          }
      }
  }
  save_tracked_deals(tracked)

  tp1_price = current_gold * (1 + 0.01)
  sl_price = current_gold * (1 - 0.012)

  gold_text = (
      "🟡 **توصيات صفقات الذهب (الرؤية التحليلية والزخم الحي):**\n\n"
      "📌 *تم تثبيت هذا السعر كمرجع لتتبع الأهداف تلقائياً في الخلفية.*\n\n"
      f"📍 **سعر الدخول الحالي (Entry):** `{current_gold:,.2f}` $\n"
      f"🛑 **وقف الخسارة (SL):** `{sl_price:,.2f}` $ (-1.2%)\n\n"
      f"• **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ ──> **(+1.0%)**\n"
  )
  send_with_menu(message, gold_text)


@bot.message_handler(
    func=lambda message: message.text == "🧮 حاسبة المخاطر وحجم الصفقة"
)
def start_risk_calculator(message):
  user_id = message.from_user.id
  risk_calculator_sessions[user_id] = {"step": "waiting_capital"}
  msg = bot.send_message(
      message.chat.id,
      "🧮 **حاسبة إدارة المخاطر:**\n\nأرسل إجمالي رأس مالك بالـ USDT (مثلاً: `500`):",
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
        f"✅ رأس المال: `{capital}` USDT.\n\nأرسل نسبة الخسارة المقبولة (مثلاً: `2`):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_risk_step)
  except Exception:
    bot.send_message(message.chat.id, "⚠️ أرسل رقماً صحيحاً (مثلاً: 500).")


def process_risk_step(message):
  user_id = message.from_user.id
  try:
    risk_pct = float(message.text.strip())
    session = risk_calculator_sessions.get(user_id, {})
    capital = session.get("capital", 500)
    max_loss = capital * (risk_pct / 100.0)
    result_text = (
        "📊 **نتيجة حساب المخاطر:**\n\n"
        f"💰 رأس المال: `{capital}` USDT\n"
        f"🎯 نسبة المخاطرة: `{risk_pct}%`\n"
        f"🛑 أقصى مبلغ للخسارة: **`{max_loss:.2f}` USDT**"
    )
    send_with_menu(message, result_text)
    if user_id in risk_calculator_sessions:
      del risk_calculator_sessions[user_id]
  except Exception:
    bot.send_message(message.chat.id, "⚠️ حدث خطأ. أعد المحاولة من الزر الرئيسي.")


@bot.message_handler(
    func=lambda message: message.text == "🔔 ضبط تنبيه سعر مخصص (/alert)"
)
def custom_alert_guide(message):
  send_with_menu(
      message,
      "🔔 **التنبيهات المخصصة:**\n\nاستخدم الأمر بالشكل الصحيح:\n• `/alert btc 68000`\n• `/alert eth 1850`",
  )


@bot.message_handler(commands=["alert"])
def set_custom_alert(message):
  user_id = message.from_user.id
  parts = message.text.split()
  if len(parts) < 3:
    bot.send_message(
        message.chat.id, "⚠️ الصيغة الصحيحة: `/alert btc 68000`"
    )
    return
  asset = parts[1].replace("/", "").replace("USDT", "").upper()
  try:
    target_price = float(parts[2].replace(",", ""))
    if user_id not in custom_alerts:
      custom_alerts[user_id] = []
    custom_alerts[user_id].append({"asset": asset, "price": target_price})
    bot.send_message(
        message.chat.id,
        f"✅ تم ضبط التنبيه الحقيقي للعملة `{asset}` عند سعر `{target_price:,.2f}`",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ في كتابة السعر.")


# --- حلقة المراقبة الآلية في الخلفية مع التجميع الأسبوعي والشهري التلقائي ---
def background_price_monitor():
  while True:
    try:
      # --- فحص التجميع التلقائي للأسبوع والشهر ---
      results_db = load_results()
      now_dt = datetime.now()

      # فحص الأسبوع (كل 7 أيام)
      last_weekly = datetime.fromisoformat(results_db.get("last_weekly_check", now_dt.isoformat()))
      if (now_dt - last_weekly).total_seconds() >= 7 * 24 * 3600:
        daily_items = results_db.get("daily", [])
        success_count = sum(1 for item in daily_items if "TP1" in item or "ربح" in item)
        total_count = len(daily_items)
        weekly_summary = f"📊 حصيلة الأسبوع التلقائية: {success_count} صفقات ناجحة من إجمالي {total_count} صفقة مرصودة."
        results_db["weekly"].append(weekly_summary)
        results_db["last_weekly_check"] = now_dt.isoformat()
        save_results(results_db)

      # فحص الشهر (كل 30 يوماً)
      last_monthly = datetime.fromisoformat(results_db.get("last_monthly_check", now_dt.isoformat()))
      if (now_dt - last_monthly).total_seconds() >= 30 * 24 * 3600:
        daily_items = results_db.get("daily", [])
        success_count = sum(1 for item in daily_items if "TP1" in item or "ربح" in item)
        total_count = len(daily_items)
        monthly_summary = f"🏆 حصيلة الشهر الكبرى التلقائية: أداء إجمالي يعتمد على {success_count} صفقة ناجحة من {total_count}."
        results_db["monthly"].append(monthly_summary)
        results_db["last_monthly_check"] = now_dt.isoformat()
        save_results(results_db)

      # --- جلب الأسعار الحية ---
      btc_p, eth_p, xrp_p = get_crypto_prices()
      gold_p = get_gold_price()
      prices_map = {"BTC": btc_p, "ETH": eth_p, "XRP": xrp_p, "GOLD": gold_p}

      # فحص التنبيهات المخصصة
      if custom_alerts:
        for user_id in list(custom_alerts.keys()):
          user_alerts_list = custom_alerts[user_id]
          remaining_alerts = []
          for alert in user_alerts_list:
            asset = alert["asset"]
            target = alert["price"]
            current_price = prices_map.get(asset, 0)
            triggered = current_price >= target if current_price > 0 else False
            if triggered:
              try:
                bot.send_message(
                    user_id,
                    f"🚨 **تنبيه سعر حقيقي وصل لهدفه!**\n\n"
                    f"🪙 الأصل/العملة: `{asset}`\n"
                    f"🎯 السعر المستهدف: `{target:,.2f}`\n"
                    f"📊 السعر الحالي في السوق: `{current_price:,.2f}`",
                    parse_mode="Markdown",
                )
              except Exception:
                pass
            else:
              remaining_alerts.append(alert)
          if remaining_alerts:
            custom_alerts[user_id] = remaining_alerts
          else:
            del custom_alerts[user_id]

      # فحص جميع الصفقات المثبتة بالتوازي
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
                      bot.send_message(
                          int(user_id),
                          f"🎯 **تحديث نتيجة صفقة مثبتة (إنجاز تلقائي)!**\n\n"
                          f"🪙 الأصل/العملة: `{symbol}`\n"
                          f"📈 السعر الحالي: `{current_val:,.2f}`\n"
                          f"✅ **مبروك! تم تحقيق الهدف الأول (TP1) بنجاح.**",
                          parse_mode="Markdown",
                      )
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
                      bot.send_message(
                          int(user_id),
                          f"🛑 **تحديث نتيجة صفقة مثبتة (إغلاق وقائي)!**\n\n"
                          f"🪙 الأصل/العملة: `{symbol}`\n"
                          f"📉 السعر الحالي: `{current_val:,.2f}`\n"
                          f"❌ **تم ضرب مستوى وقف الخسارة (SL).**",
                          parse_mode="Markdown",
                      )
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


@bot.message_handler(
    func=lambda message: message.text == "📰 موجز الأخبار الاقتصادية اللحظية"
)
def send_crypto_news(message):
  news_text = (
      "📰 **موجز الأخبار الاقتصادية والأسواق اللحظية:**\n\n"
      "1️⃣ **الاحتياطي الفيدرالي وأسعار الفائدة:**\n"
      "• ترقب الأسواق لبيانات التضخم وتأثيرها على الفيدرالي.\n\n"
      "2️⃣ **سوق العملات الرقمية (Crypto):**\n"
      "• استقرار تدفقات صناديق الاستثمار المتداولة.\n\n"
      "3️⃣ **سوق الذهب العالمي (XAUUSD):**\n"
      "• الأحداث الجيوسياسية تقود الذهب لمستويات قوية."
  )
  send_with_menu(message, news_text)


QUIZ_QUESTIONS = [
    {
        "question": (
            "🧠 **سؤال اختبار التداول (1/4):**\n\nما هو الغرض الأساسي من استخدام أمر (وقف الخسارة - Stop Loss)؟\n\nأ) مضاعفة الأرباح\nب) حماية المحفظة والخروج بخسارة صغيرة\nج) زيادة رسوم التداول\n\n💡 أجب بـ (ب):"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "حماية", "خسارة"],
    }
]


@bot.message_handler(
    func=lambda message: message.text == "🧠 اختبار تداولي تفاعلي (Quiz)"
)
def start_trading_quiz(message):
  user_id = message.from_user.id
  q_data = random.choice(QUIZ_QUESTIONS)
  active_quizzes[user_id] = q_data
  msg = bot.send_message(
      message.chat.id, q_data["question"], parse_mode="Markdown"
  )
  bot.register_next_step_handler(msg, check_quiz_answer)


def check_quiz_answer(message):
  user_id = message.from_user.id
  ans = message.text.strip().lower()
  q_data = active_quizzes.get(user_id)
  if not q_data:
    return
  if any(k in ans for k in q_data["keywords"]):
    send_with_menu(
        message,
        "🎉 **إجابة صحيحة 100%!**",
    )
  else:
    send_with_menu(
        message,
        f"❌ الإجابة الصحيحة هي **({q_data['answer_key']})**.",
    )
  if user_id in active_quizzes:
    del active_quizzes[user_id]


@bot.message_handler(
    func=lambda message: message.text == "📚 الأكاديمية التعليمية للمبتدئين"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية التعليمية - تعلم التداول من الصفر:**\n\n"
      "🟢 **الدرس الأول:** ما هو التداول والعملات المستقرة (`USDT`).\n"
      "🟡 **الدرس الثاني:** أنواع الصفقات والتأمين (`Breakeven`).\n"
      "🔵 **الدرس الثالث:** إدارة المخاطر وعدم تجاوز 1% إلى 2%."
  )
  send_with_menu(message, academy_text)


@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس مصطلحات التداول (بحث ذكي)"
)
def glossary_menu(message):
  glossary_guide = (
      "📖 **قاموس الحيتان ومصطلحات السوق:**\n\n"
      "استخدم الأمر `/search` متبوعاً بالكلمة مثل:\n"
      "• `/search breakeven`\n"
      "• `/search OCO`\n"
      "• `/search USDT`"
  )
  send_with_menu(message, glossary_guide)


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى كتابة المصطلح بعد الأمر. *مثال:* `/search breakeven`",
        parse_mode="Markdown",
    )
    return

  query = parts[1].strip().lower()
  glossary_db = {
      "usdt": "🔹 **USDT:** عملة رقمية ثابتة تساوي دولاراً واحداً لحفظ الأرباح.",
      "breakeven": "🛡️ **Breakeven:** تأمين الصفقة برفع الوقف لنقطة الدخول بعد هدف TP1.",
      "scalping": "⚡ **Scalping:** صفقات سريعة لخطف أرباح صغيرة.",
      "tp": "🎯 **TP:** سعر جني الأرباح.",
      "sl": "🛑 **SL:** وقف الخسارة لحماية المحفظة.",
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
        f"❌ عذراً، لم نجد مصطلحاً يطابق (`{query}`).",
        parse_mode="Markdown",
    )


@bot.message_handler(
    func=lambda message: message.text == "🌐 دليل فتح الحسابات وإنشاء المحافظ"
)
def send_accounts_guide(message):
  accounts_text = (
      "🌐 **دليل فتح الحسابات:**\n\n"
      "1. توثيق الحساب على المنصة (Binance).\n"
      "2. حفظ كلمات الأمان (12 كلمة) في المحافظ اللامركزية بعيداً عن الإنترنت."
  )
  send_with_menu(message, accounts_text)


@bot.message_handler(
    func=lambda message: message.text == "📥 دليل السحب والإيداع (شبكة TRC20)"
)
def send_deposit_withdraw_guide(message):
  deposit_withdraw_text = (
      "📥 **دليل السحب والإيداع:**\n\n"
      "• الاعتماد الحصري على شبكة **TRC20** لرخص وسرعة التحويل.\n"
      "• استخدام محفظة شام كاش للتحويلات المحلية."
  )
  send_with_menu(message, deposit_withdraw_text)


@bot.message_handler(
    func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **الشحن عبر شام كاش:**\n\n"
      "تواصل مع المطور (`" + ADMIN_USERNAME + "`) لإتمام الحوالة وإرسال الوصل."
  )
  send_with_menu(message, payment_text)


@bot.message_handler(
    func=lambda message: message.text == "⏳ حالة اشتراكي ورابط دعوة أصدقائي"
)
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  uid_str = str(user_id)
  if user_id == ADMIN_ID:
    bot.send_message(message.chat.id, "👑 أنت المطور، اشتراكك مفتوح دائماً!")
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
  send_with_menu(
      message,
      f"📋 ينتهي اشتراكك في: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n👥 دعوات الأصدقاء: **{ref_count}**\n🔗 رابط الدعوة:\n`{ref_link}`",
  )


@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  send_with_menu(
      message,
      "👑 **لوحة تحكم المطور:**\n"
      "• `/users` - عرض المشتركين\n"
      "• `/stats` - الإحصائيات\n"
      "• `/add_result daily [النص]` - إضافة نتيجة يومية",
  )


@bot.message_handler(commands=["users"])
def show_all_users(message):
  if message.from_user.id != ADMIN_ID:
    return
  current_users = load_users()
  if not current_users:
    bot.send_message(message.chat.id, "📭 لا يوجد مشتركين.")
    return
  bot.send_message(
      message.chat.id,
      f"👥 **إجمالي المشتركين: {len(current_users)}**",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(
      message.chat.id,
      f"📊 المشتركين: {len(all_users)}",
  )


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
    bot.remove_webhook()
    time.sleep(2)
  except Exception as e:
    print(f"Error removing webhook: {e}")

  try:
    bot.infinity_polling(
        timeout=60, long_polling_timeout=60, skip_pending=True
    )
  except Exception as e:
    print(f"Polling error: {e}")
