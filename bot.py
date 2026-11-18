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
RESULTS_FILE = "trading_results.json"  # ملف تخزين نتائج الصفقات الحقيقية
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


# دوال حفظ واسترجاع نتائج الصفقات (يومي، أسبوعي، شهري)
def load_results():
  if os.path.exists(RESULTS_FILE):
    try:
      with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
          return {"daily": [], "weekly": [], "monthly": []}
        return json.loads(content)
    except Exception:
      return {"daily": [], "weekly": [], "monthly": []}
  return {"daily": [], "weekly": [], "monthly": []}


def save_results(data):
  try:
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving results: {e}")


# دوال إدارة وتثبيت الصفقات النشطة للمستخدمين (محدثة لدعم حفظ عدة أنواع صفقات معاً دون مسح)
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
  
  # زر نتائج وأداء الصفقات المقترحة حقيقياً
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

  # التحقق مما إذا كان المستخدم مسجلاً من قبل لمنع تكرار التجربة عند مسح الدردشة
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
    # المستخدم مسجل مسبقاً، لا يتم منحه فترة تجريبية جديدة أبداً
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


# --- ميزة عرض نتائج الصفقات المقترحة (يومي، أسبوعي، شهري) حقيقياً ---
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
    for item in items[-6:]:  # عرض آخر 6 صفقات أو نتائج مسجلة
      res += f"  {item}\n"
    return res

  report_text = (
      "📈 **سجل نتائج وأداء الصفقات المقترحة (شفافية السوق):**\n\n"
      "📅 **1. النتائج اليومية (صفقات اليوم):**\n"
      f"{format_items(daily_list)}\n"
      "📊 **2. النتائج الأسبوعية (حصيلة الأسبوع):**\n"
      f"{format_items(weekly_list)}\n"
      "🏆 **3. النتائج الشهرية (الحصيلة الكبرى):**\n"
      f"{format_items(monthly_list)}\n"
      "💡 *ملاحظة:* يتم تحديث النتائج فور إغلاق الصفقة (حقيقية بربح ✅ أو خسارة ❌ أو تأمين 🛡️)."
  )
  send_with_menu(message, report_text)


# أمر خاص للمطور لتسجيل نتيجة صفقة أو ملخص يومي/أسبوعي/شهري
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
        "`/add_result weekly 📊 حصيلة الأسبوع: 4 صفقات ناجحة و 1 صفقة خاسرة`\n"
        "`/add_result monthly 🏆 حصيلة الشهر: أرباح إجمالية +14.2%`",
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
      f"  🚀 *الهدف الثاني (TP2):* `{xrp * 1.015:,.4f}` ──> **(+{xrp_tp2_pct}%)**\n"
      f"  ⏱️ **نوع الإغلاق المعتمد للعملات:**\n"
      f"    • ⚡ *الإغلاق اللحظي الفوري:* للخروج المباشر عند ملامسة السعر للهدف بدقة.\n"
      f"    • 🕯️ *إغلاق الشمعة (Candle Close):* لتأكيد كسر المستوى وثبات الإغلاق الزمني.\n\n"
      "📅 **2. الصفقات اليومية للعملات:**\n"
      f"• **العملة:** BTC/USDT (سعر الدخول: `{btc:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{btc_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{btc * 1.012:,.2f}` ──> **(+{btc_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** جني نصف الربح وحرك وقف الخسارة لنقطة الدخول (`{btc:,.2f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{btc * 1.025:,.2f}` ──> **(+{btc_tp2_pct}%)**\n"
      f"  ⏱️ **نوع الإغلاق المعتمد للعملات:**\n"
      f"    • ⚡ *الإغلاق اللحظي الفوري:* لتنفيذ أمر السوق الفوري.\n"
      f"    • 🕯️ *إغلاق الشمعة (Candle Close):* بانتظار إغلاق شمعة الـ 4 ساعات.\n\n"
      "🌊 **3. صفقات السوينغ للعملات:**\n"
      f"• **العملة:** ETH/USDT (سعر الدخول: `{eth:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{eth_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{eth * 1.03:,.2f}` ──> **(+{eth_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** تأمين الصفقة عند الدخول (`{eth:,.2f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{eth * 1.06:,.2f}` ──> **(+{eth_tp2_pct}%)**\n"
      f"  ⏱️ **نوع الإغلاق المعتمد للعملات:**\n"
      f"    • ⚡ *الإغلاق اللحظي الفوري:* عند ضرب الهدف بالمللي.\n"
      f"    • 🕯️ *إغلاق الشمعة (Candle Close):* إغلاق شمعة اليومي لتأكيد الاتجاه.\n\n"
      "🏛️ **4. الاستثمار طويل الأمد (DCA + حماية الأصل):**\n"
      "• بيع **25% من الأرباح الصافية فقط** وتحويلها لـ USDT ككاش مع **الحفاظ على كمية البيتكوين الأساسية كاملة** دون تآكل."
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
      f"  🎯 *TP1:* `{btc_price * (1 + btc_tp1_p):,.2f}` (+{btc_tp1_p*100}%)\n"
      f"  🚀 *TP2:* `{btc_price * (1 + btc_tp2_p):,.2f}` (+{btc_tp2_p*100}%)\n"
      f"  ⏱️ *الإغلاق للعملات:* ⚡ إغلاق لحظي فوري / 🕯️ إغلاق شمعة مؤكد.\n\n"
      f"💎 **2. إيثريوم (ETH/USDT):**\n"
      f"• السعر الحالي: `{eth_price:,.2f}$` (التغير 24س: `{eth_chg:+.2f}%`)\n"
      f"• الحالة: {eth_trend}\n"
      f"  🛑 *SL:* `{eth_price * (1 - eth_sl_p):,.2f}`\n"
      f"  🎯 *TP1:* `{eth_price * (1 + eth_tp1_p):,.2f}` (+{eth_tp1_p*100}%)\n"
      f"  🚀 *TP2:* `{eth_price * (1 + eth_tp2_p):,.2f}` (+{eth_tp2_p*100}%)\n"
      f"  ⏱️ *الإغلاق للعملات:* ⚡ إغلاق لحظي فوري / 🕯️ إغلاق شمعة مؤكد.\n\n"
      f"⚡ **3. ريبل (XRP/USDT):**\n"
      f"• السعر الحالي: `{xrp_price:,.4f}$` (التغير 24س: `{xrp_chg:+.2f}%`)\n"
      f"• الحالة: {xrp_trend}\n"
      f"  🛑 *SL:* `{xrp_price * (1 - xrp_sl_p):,.2f}`\n"
      f"  🎯 *TP1:* `{xrp_price * (1 + xrp_tp1_p):,.2f}` (+{xrp_tp1_p*100}%)\n"
      f"  ⏱️ *الإغلاق للعملات:* ⚡ إغلاق لحظي فوري / 🕯️ إغلاق شمعة مؤكد.\n\n"
      "🛡️ **نظام التأمين:** يتم تفعيل Breakeven (نقل وقف الخسارة لسعر الدخول) فور بلوغ الهدف الأول تلقائياً."
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
  tp2_price = current_gold * (1 + 0.015)
  sl_price = current_gold * (1 - 0.01)

  gold_text = (
      "🟡 **توصيات صفقات الذهب (القاعدة الذهبية):**\n\n"
      "📌 *تم تثبيت هذا السعر كمرجع لتتبع الأهداف تلقائياً في الخلفية.*\n\n"
      f"📍 **سعر الدخول الحالي (Entry):** `{current_gold:,.2f}` $\n"
      f"🛑 **وقف الخسارة المقترح (SL):** `{sl_price:,.2f}` $ (-1.0%)\n\n"
      "⚡ **1️⃣ صفقات الذهب اليومية:**\n"
      f"• **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ ──> **(+0.7%)**\n"
      f"  • 🛡️ **التأمين:** فور تحقق الهدف الأول، أغلق 50% من العقد وانقل وقف الخسارة لسعر الدخول (`{current_gold:,.2f}`).\n"
      f"  • ⏱️ **نوع الإغلاق:** ⚡ إغلاق لحظي ملامس / 🕯️ إغلاق شمعة 4 ساعات.\n"
      f"• **الهدف الثاني (TP2):** `{tp2_price:,.2f}` $ ──> **(+1.5%)**\n\n"
      "📈 **2️⃣ استثمار وتجميع الذهب:** بدون رافعة مالية مع حماية الأصل الأساسي."
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
  tp2_price = current_gold * (1 + 0.022)
  sl_price = current_gold * (1 - 0.012)

  gold_text = (
      "🟡 **توصيات صفقات الذهب (الرؤية التحليلية والزخم الحي):**\n\n"
      "📌 *تم تثبيت هذا السعر كمرجع لتتبع الأهداف تلقائياً في الخلفية.*\n\n"
      f"📍 **سعر الدخول الحالي (Entry):** `{current_gold:,.2f}` $\n"
      f"🚀 **حالة السوق:** رصد سيولة شرائية وتذبذب إيجابي.\n"
      f"🛑 **وقف الخسارة (SL):** `{sl_price:,.2f}` $ (-1.2%)\n\n"
      "⚡ **الأهداف الحية الديناميكية:**\n"
      f"• **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ ──> **(+1.0%)**\n"
      f"  • 🛡️ **التأمين:** تأمين الصفقة برفع الـ SL لسعر الدخول (`{current_gold:,.2f}`).\n"
      f"  • ⏱️ **نوع الإغلاق:** ⚡ إغلاق لحظي / 🕯️ إغلاق شمعة.\n"
      f"• **الهدف الثاني (TP2):** `{tp2_price:,.2f}` $ ──> **(+2.2%)**\n\n"
      "🛡️ **إدارة المخاطر:** الالتزام بحاسبة المخاطر وعدم تجاوز 1% من رأس المال."
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


# --- حلقة المراقبة الآلية المدمجة في الخلفية لتتبع كافة صفقات المستخدم بالتوازي مع الترحيل التلقائي للنتائج ---
def background_price_monitor():
  while True:
    try:
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
                    f"🪙 العملة/الأصل: `{asset}`\n"
                    f"🎯 السعر المستهدف: `{target:,.2f}`\n"
                    f"📊 السعر الحالي في السوق: `{current_price:,.2f}`\n\n"
                    f"⚡ حان الوقت لمراجعة الشارت واتخاذ القرار المناسب.",
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

      # فحص جميع الصفقات المثبتة لجميع أنواع الأزرار بالتوازي
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
                    
                    # 1. إرسال إشعار فوري للمستخدم
                    try:
                      bot.send_message(
                          int(user_id),
                          f"🎯 **تحديث نتيجة صفقة مثبتة (إنجاز تلقائي)!**\n\n"
                          f"🪙 الأصل/العملة: `{symbol}`\n"
                          f"📈 السعر الحالي: `{current_val:,.2f}`\n"
                          f"✅ **مبروك! تم تحقيق الهدف الأول (TP1) بنجاح.**\n"
                          f"🛡️ *التوصية:* تفعيل التأمين (Breakeven) وجني الأرباح الجزئية.",
                          parse_mode="Markdown",
                      )
                    except Exception:
                      pass
                    
                    # 2. الترحيل التلقائي لسجل الأداء العام ليظهر للمشتركين
                    try:
                      results_db = load_results()
                      res_msg = f"✅ صفقة {symbol} تحقيق الهدف (TP1) بنجاح عند سعر {current_val:,.2f}"
                      results_db["daily"].append(res_msg)
                      save_results(results_db)
                    except Exception:
                      pass
                  
                  elif sl > 0 and current_val <= sl:
                    data["status"] = "sl_hit"
                    updated = True
                    
                    # 1. إرسال إشعار فوري للمستخدم
                    try:
                      bot.send_message(
                          int(user_id),
                          f"🛑 **تحديث نتيجة صفقة مثبتة (إغلاق وقائي)!**\n\n"
                          f"🪙 الأصل/العملة: `{symbol}`\n"
                          f"📉 السعر الحالي: `{current_val:,.2f}`\n"
                          f"❌ **تم ضرب مستوى وقف الخسارة (SL) وحماية المحافظة.**",
                          parse_mode="Markdown",
                      )
                    except Exception:
                      pass
                    
                    # 2. الترحيل التلقائي لسجل الأداء العام ليظهر للمشتركين
                    try:
                      results_db = load_results()
                      res_msg = f"❌ صفقة {symbol} ضرب وقف الخسارة (SL) عند سعر {current_val:,.2f}"
                      results_db["daily"].append(res_msg)
                      save_results(results_db)
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
      "• ترقب الأسواق لبيانات التضخم الأمريكية القادمة وتأثيرها المباشر على قرارات الفيدرالي وحركة الذهب والعملات.\n\n"
      "2️⃣ **سوق العملات الرقمية (Crypto):**\n"
      "• استقرار تدفقات صناديق الاستثمار المتداولة (ETFs) يعزز مناطق الدعم الحالية للبيتكوين.\n\n"
      "3️⃣ **سوق الذهب العالمي (XAUUSD):**\n"
      "• الأحداث الجيوسياسية وتحركات الدولار تقود أسعار الذهب نحو مستويات قياسية جديدة.\n\n"
      "💡 *نصيحة المطور:* لا تفتح صفقات كبرى أثناء صدور الأخبار الاقتصادية الحساسة لتجنب الانزلاق السعري المفاجئ."
  )
  send_with_menu(message, news_text)


QUIZ_QUESTIONS = [
    {
        "question": (
            "🧠 **سؤال اختبار التداول (1/4):**\n\nما هو الغرض الأساسي من استخدام أمر (وقف الخسارة - Stop Loss)؟\n\nأ) مضاعفة الأرباح 10 أضعاف\nب) حماية المحفظة والخروج بخسارة صغيرة عند انعكاس السوق\nج) زيادة رسوم التداول في المنصة\n\n💡 أجب بـ (ب) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "حماية", "خسارة"],
    },
    {
        "question": (
            "🧠 **سؤال اختبار التداول (2/4):**\n\nماذا تعني العملة الرقمية (USDT) في عالم التداول؟\n\nأ) عملة رقمية متذبذبة ترتفع وتنهبط بعنف\nب) عملة مستقرة تساوي دولاراً واحداً دائماً لحفظ الأرباح\nج) عملة مخصصة لتعدين البيتكوين فقط\n\n💡 أجب بـ (ب) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "مستقرة", "دولار"],
    },
    {
        "question": (
            "🧠 **سؤال اختبار التداول (3/4):**\n\nما هي النسبة الآمنة الموصى بالمخاطرة بها في الصفقة الواحدة للمبتدئين؟\n\nأ) من 50% إلى 100% من رأس المال\nب) من 1% إلى 2% فقط للحفاظ على المحفظة\nج) لا داعي لحساب نسب المخاطرة\n\n💡 أجب بـ (ب) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "1%", "2%", "واحد", "اثنان"],
    },
    {
        "question": (
            "🧠 **سؤال اختبار التداول (4/4):**\n\nما هو سوق (السبوت - Spot) في التداول؟\n\nأ) شراء الأصول وامتلاكها حقيقةً بدون رافعة مالية\nب) الاقتراض والاستدانة بمضاعفات ضخمة\nج) التداول العشوائي بدون تحليل\n\n💡 أجب بـ (أ) أو اكتب الخيار الصحيح:"
        ),
        "answer_key": "أ",
        "keywords": ["أ", "شراء", "امتلاك", "بدون"],
    },
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
        "🎉 **إجابة صحيحة 100% بارك الله فيك!**\nأنت تملك عقليّة متداول واعي يعرف كيف يحمي أمواله.",
    )
  else:
    send_with_menu(
        message,
        f"❌ إجابة غير صحيحة.\nالخيار الصحيح هو **({q_data['answer_key']})**.",
    )
  if user_id in active_quizzes:
    del active_quizzes[user_id]


@bot.message_handler(
    func=lambda message: message.text == "📚 الأكاديمية التعليمية للمبتدئين"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية التعليمية - تعلم التداول من الصفر حتى الاحتراف:**\n\n"
      "🟢 **الدرس الأول (ما هو التداول؟):**\n"
      "• هو عملية بيع وشراء الأصول الرقمية (مثل العملات أو الذهب) للاستفادة من فرق السعر.\n"
      "• يتم قياس وتسعير الأصول دائماً مقابل العملة المستقرة والدولار الرقمي (`USDT`).\n\n"
      "🟡 **الدرس الثاني (فهم أنواع الصفقات وتأمينها):**\n"
      "• تنقسم الصفقات إلى سريعة جداً (سكالبينج)، يومية، متوسطة الأمد (سوينغ)، أو استثمار طويل الأمد (DCA).\n"
      "• احرص دائماً على تطبيق **قاعدة التأمين (Breakeven)** برفع وقف الخسارة لسعر الدخول بعد بلوغ الهدف الأول.\n\n"
      "🔵 **الدرس الثالث (إدارة المخاطر وحماية رأس المال):**\n"
      "• القاعدة الذهبية: **لا تضع كل البيض في سلة واحدة.**\n"
      "• لا تستخدم كل أموالك في صفقة واحدة أبداً، واجعل خسارة أي صفقة لا تتجاوز 1% إلى 2% من إجمالي مالك.\n\n"
      "🟣 **الدرس الرابع (حماية الأصول في الاستثمار طويل الأمد):**\n"
      "• عند جني الأرباح في استراتيجيات DCA الصاعدة، يتم بيع جزء من الأرباح الصافية فقط وتحويله لـ USDT مع **الحفاظ على كمية البيتكوين الأساسية كاملة دون تآكل**.\n\n"
      "🟠 **الدرس الخامس (السيطرة على المشاعر):**\n"
      "• أكبر عدو للمتداول هو (الطمع) و(الخوف) والرغبة في الانتقام من السوق بعد صفقة خاسرة.\n"
      "• الالتزام بالخطة هو طريقك الوحيد للنجاح المستدام."
  )
  send_with_menu(message, academy_text)


@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس مصطلحات التداول (بحث ذكي)"
)
def glossary_menu(message):
  glossary_guide = (
      "📖 **قاموس الحيتان ومصطلحات السوق العتيقة:**\n\n"
      "لتحترف لغة الكبار، استخدم الأمر `/search` متبوعاً بالكلمة التي تقصدها.\n"
      "📌 *مثال:* `/search breakeven` أو `/search OCO` أو `/search USDT`\n\n"
      "---\n"
      "**فهرس المصطلحات المتاحة في الديوان:**\n"
      "1️⃣ **USDT** (الملاذ الآمن المستقر)\n"
      "2️⃣ **Breakeven** (تأمين الصفقة / نقطة التعادل)\n"
      "3️⃣ **Scalping** (اقتناص الفتات السريع)\n"
      "4️⃣ **TP / Take Profit** (مرفأ جني الأرباح)\n"
      "5️⃣ **SL / Stop Loss** (طوق النجاة / وقف الخسارة)\n"
      "6️⃣ **OCO** (الحارس المزدوج للأوامر)\n"
      "7️⃣ **Leverage** (أداة الانتحار / الرافعة المالية)\n"
      "8️⃣ **KYC** (بصمة الهوية المشروطة)\n"
      "9️⃣ **DCA** (التجميع الهادئ المستمر)"
  )
  send_with_menu(message, glossary_guide)


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى كتابة المصطلح بعد الأمر.\n*مثال:* `/search breakeven`",
        parse_mode="Markdown",
    )
    return

  query = parts[1].strip().lower()
  if query == "oso":
    query = "oco"

  glossary_db = {
      "usdt": (
          "🔹 **USDT (الملاذ الآمن المستقر):**\n"
          "عملة رقمية مشفرة ثابتة القيمة تساوي دولاراً أمريكياً واحداً دائماً.\n"
          "💡 *فائدتها:* تستخدم لحفظ الأرباح والهرب من هبوط السوق دون الحاجة لتحويل الأموال لكاش ورقي."
      ),
      "breakeven": (
          "🛡️ **Breakeven (تأمين الصفقة / نقطة التعادل):**\n"
          "إجراء وقائي يقوم به المتداول المحترف بعد تحرك السعر في صالحه وتحقيق الهدف الأول (TP1)، وذلك بجني نصف الربح ونقل أمر وقف الخسارة (SL) إلى سعر الدخول تماماً.\n"
          "💡 *النتيجة:* تضمن عدم خسارة أي سنت من رأس مالك حتى لو انعكس السوق فجأة!"
      ),
      "scalping": (
          "⚡ **Scalping (اقتناص الفتات السريع):**\n"
          "صفقات سريعة جداً تخطف أرباحاً صغيرة (مثل 1% أو 1.5%) خلال دقائق معدودة وتُغلق فوراً."
      ),
      "tp": (
          "🎯 **TP / Take Profit (مرفأ جني الأرباح):**\n"
          "السعر المحدد مسبقاً الذي يأخذ عنده البوت أو المنصة أرباحك تلقائياً ويغلق الصفقة."
      ),
      "sl": (
          "🛑 **SL / Stop Loss (طوق النجاة / وقف الخسارة):**\n"
          "السعر الذي يحمي محفظتك ويخرجك بخسارة صغيرة جداً ومحدودة إذا عكس السوق اتجاهه."
      ),
      "oco": (
          "🟣 **OCO (الحارس المزدوج للأوامر):**\n"
          "وضع هدف الربح (TP) ووقف الخسارة (SL) معاً في نفس اللحظة، بحيث إذا تحقق أحدهما يُلغى الآخر تلقائياً لتنام مرتاح البال."
      ),
      "leverage": (
          "⚖️ **Leverage (أداة الانتحار / الرافعة المالية):**\n"
          "استدانة أموال من المنصة لمضاعفة حجم الصفقة والأرباح (وتعظيم الخسائر أيضاً). ⚠️ *ننصح المبتدئين بالابتعاد عنها والالتزام بالسبوت فقط.*"
      ),
      "kyc": (
          "🆔 **KYC (بصمة الهوية المشروطة):**\n"
          "توثيق الهوية الرسمية عبر إرسال صور الأوراق الثبوتية للمنصة لفتح صلاحيات السحب والإيداع بأمان تام."
      ),
      "dca": (
          "🏛️ **DCA (التجميع الهادئ المستمر):**\n"
          "استراتيجية شراء الأصل (مثل البيتكوين) بمبالغ ثابتة على فترات منتظمة بغض النظر عن السعر، مع جني جزء من الأرباح الصافية فقط والحفاظ على كمية الأصل كاملة."
      ),
      "bull": (
          "🐂 **Bull Market (سوق الثيران):**\n"
          "سوق صاعد وإيجابي تسوده حالة التفاؤل وارتفاع الأسعار على المدى الطويل."
      ),
      "bear": (
          "🐻 **Bear Market (سوق الدببة):**\n"
          "سوق هابط وسلبي تسوده المخاوف وانخفاض الأسعار، ويحتاج إلى صبر واستراتيجيات تجميع."
      ),
  }

  found = False
  for key, desc in glossary_db.items():
    if query in key or query in desc.lower():
      bot.send_message(
          message.chat.id,
          f"🔍 **نتيجة البحث في الديوان عن (`{query}`):**\n\n{desc}",
          parse_mode="Markdown",
      )
      found = True
      break

  if not found:
    bot.send_message(
        message.chat.id,
        f"❌ عذراً، لم نجد مصطلحاً يطابق (`{query}`). جرب بحثاً آخر مثل: `breakeven`, `usdt`, `tp`, `sl`, `oco`.",
        parse_mode="Markdown",
    )


@bot.message_handler(
    func=lambda message: message.text == "🌐 دليل فتح الحسابات وإنشاء المحافظ"
)
def send_accounts_guide(message):
  accounts_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ (الخطوة الأولى للاحتراف):**\n\n"
      "🏛️ **1. منصات التداول المركزية (مثل Binance أو Bybit):**\n"
      "• هي البورصة الكبرى التي ستشتري وتبيع من خلالها العملات الرقمية والذهب وتنفيذ الصفقات.\n"
      "• **طريقة التسجيل:** تحميل التطبيق الرسمي من المتجر، التسجيل عبر البريد الإلكتروني، وإنشاء كلمة مرور قوية.\n"
      "• **توثيق الهوية (KYC):** ضروري جداً لحماية حسابك وسحب أرباحك بأمان، ويتم عبر رفع صورة جواز السفر أو الهوية الشخصية.\n\n"
      "👛 **2. المحافظ اللامركزية (مثل Trust Wallet أو MetaMask):**\n"
      "• هي محفظتك الخاصة لتخزين أصولك بشكل بعيد عن المنصات وتحت سيطرتك الكاملة.\n"
      "• **قاعدة الأمان الذهبية:** عند إنشاء المحفظة سيعطيك التطبيق (12 كلمة سرية)، احفظهم في مكان آمن ورقي بعيداً عن الإنترنت ولا تعطهم لأي شخص نهائياً لأن من يملكهم يملك أموالك.\n\n"
      "💡 *نصيحة المطور:* ابدأ دائماً بتوثيق حسابك على إحدى المنصات الموثوقة، وتعلّم ببطء وثبات قبل ضخ أي أموال حقيقية."
  )
  send_with_menu(message, accounts_text)


@bot.message_handler(
    func=lambda message: message.text
    == "📥 دليل السحب والإيداع (شبكة TRC20)"
)
def send_deposit_withdraw_guide(message):
  deposit_withdraw_text = (
      "📥 **دليل الإيداع والسحب (الطريق الآمن لأموالك):**\n\n"
      "🌐 **1. لماذا نعتمد شبكة TRC20 تحديداً؟**\n"
      "• هي الشبكة الأكثر استخداماً وأماناً للتحويلات الرقمية لعملة `USDT`.\n"
      "• تتميز بسرعتها الفائقة في وصول الأموال (لا تتجاوز بضع دقائق).\n"
      "• رسوم التحويل فيها ثابتة ورخيصة جداً (1 دولار فقط بغض النظر عن حجم الحوالة).\n"
      "• ⚠️ **تنبيه هام:** تأكد دائماً عند السحب أو الإيداع من اختيار شبكة **TRC20 (Tron)** حصرياً لكي لا تضيع أموالك في شبكة خاطئة.\n\n"
      "🔄 **2. آلية الإيداع والشحن (عبر الوكلاء وشام كاش):**\n"
      "• لتحويل أموالك المحلية إلى رصيد رقمي `USDT` في منصتك، تتواصل مع الوكيل المعتمد وتتم عملية التحويل بالليرة السورية عبر تطبيق **شام كاش**.\n"
      "• يقوم الوكيل فوراً بإرسال ما يقابلها من عملات مستقرة إلى عنوان محفظتك الرقمية.\n\n"
      "💵 **3. آلية سحب الأرباح (كاش أو محفظة محلية):**\n"
      "• عندما ترغب بسحب أرباحك، تقوم بتحويل الـ `USDT` من منصتك إلى عنوان محفظة الوكيل.\n"
      "• يستلم الوكيل العملات ويقوم بتسليمك المبلغ نقداً أو تحويله إلى حسابك على شام كاش بكل سهولة وأمان."
  )
  send_with_menu(message, deposit_withdraw_text)


@bot.message_handler(
    func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **معلومات الدفع والشحن عبر محفظة (شام كاش):**\n\n"
      "تعتبر محفظة **شام كاش** الوسيلة المحلية الأسهل والأسرع لإتمام المعاملات المالية وتفعيل الاشتراكات أو شحن الرصيد في سوريا.\n\n"
      "📌 **خطوات إتمام الدفع أو الشحن بنجاح:**\n"
      "  1️⃣ تواصل حصرياً مع المطور أو الوكيل المعتمد عبر المعرف الرسمي (`"
      + ADMIN_USERNAME
      + "` لتأكيد تفاصيل الحوالة).\n"
      "  2️⃣ قم بإتمام عملية التحويل بالليرة السورية عبر تطبيق شام كاش إلى الحساب المعتمد.\n"
      "  3️⃣ أرسل صورة إيصال التحويل (الوصل) مع رقم حسابك التعريفي (`ID`) داخل البوت للإدارة.\n"
      "  4️⃣ سيقوم النظام أو الإدارة بمراجعة الحوالة وتفعيل اشتراكك أو رصيدك فورياً خلال دقائق معدودة!"
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
      f"📋 ينتهي اشتراكك في: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n👥 عدد أصدقائي: **{ref_count}**\n🔗 رابط الدعوة:\n`{ref_link}`",
  )


@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  send_with_menu(
      message,
      "👑 **لوحة تحكم المطور:**\n"
      "الأوامر المتاحة:\n"
      "• `/users` - عرض المشتركين\n"
      "• `/stats` - الإحصائيات\n"
      "• `/add_result daily [النص]` - تسجيل نتيجة صفقة يومية\n"
      "• `/add_result weekly [النص]` - تسجيل حصيلة أسبوعية\n"
      "• `/add_result monthly [النص]` - تسجيل حصيلة شهرية",
  )


@bot.message_handler(commands=["users"])
def show_all_users(message):
  if message.from_user.id != ADMIN_ID:
    return

  current_users = load_users()

  if not current_users:
    bot.send_message(message.chat.id, "📭 لا يوجد مشتركين في القاعدة حتى الآن.")
    return

  bot.send_message(
      message.chat.id,
      f"👥 **قائمة المشتركين المسجلين (الإجمالي: {len(current_users)}):**",
      parse_mode="Markdown",
  )

  for uid, info in list(current_users.items())[-15:]:
    user_name = info.get("name", "بدون اسم")
    user_uname = info.get("username", "لا يوجد")
    expiry_date = info.get("expiry", "")[:10]

    text = (
        f"👤 **الاسم:** {user_name}\n"
        f"🆔 المعرف: `{uid}`\n"
        f"🌐 اليوزر: `@{user_uname}`\n"
        f"⏳ ينتهي في: `{expiry_date}`"
    )

    markup = types.InlineKeyboardMarkup()
    profile_btn = types.InlineKeyboardButton(
        text="💬 فتح الملف الشخصي", url=f"tg://user?id={uid}"
    )
    markup.add(profile_btn)

    try:
      bot.send_message(
          message.chat.id, text, reply_markup=markup, parse_mode="Markdown"
      )
    except Exception:
      pass


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(
      message.chat.id,
      f"📊 إجمالي المشتركين: {len(all_users)}\nمجموعات مفعلة: {len(active_groups)}",
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
  print("Flask web server started successfully...")

  alert_thread = threading.Thread(target=background_price_monitor, daemon=True)
  alert_thread.start()
  print("Background price and multi-deals monitor worker started...")

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
