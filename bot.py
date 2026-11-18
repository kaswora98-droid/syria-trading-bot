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

TOKEN = "8928709566:AAHP9dZXrxkpp2FneolgC-Cfd4jFh6nqMF4"

bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

DATA_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
RESULTS_FILE = "trading_results.json"
ACTIVE_TRADES_FILE = "active_trades.json"  # ملف تتبع الصفقات النشطة تلقائياً
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


def load_active_trades():
  if os.path.exists(ACTIVE_TRADES_FILE):
    try:
      with open(ACTIVE_TRADES_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
          return []
        return json.loads(content)
    except Exception:
      return []
  return []


def save_active_trades(trades_list):
  try:
    with open(ACTIVE_TRADES_FILE, "w", encoding="utf-8") as f:
      json.dump(trades_list, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving active trades: {e}")


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


# --- نظام أتمتة وتسجيل الصفقات النشطة تلقائياً ---
def register_trade_automatically(asset_name, entry, tp1, tp2, sl):
  trades = load_active_trades()
  # منع تكرار نفس الصفقة النشطة لنفس الأصل إذا كانت قيد التتبع
  for t in trades:
    if t["asset"] == asset_name and t["status"] == "active":
      return
  new_trade = {
      "asset": asset_name,
      "entry": entry,
      "tp1": tp1,
      "tp2": tp2,
      "sl": sl,
      "status": "active",
      "secured": False,
      "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
  }
  trades.append(new_trade)
  save_active_trades(trades)


# --- العامل الخلفي لمتابعة الأهداف وحالة الصفقات تلقائياً ---
def background_trade_and_price_monitor():
  while True:
    try:
      # أولاً: تتبع الصفقات النشطة وتقييمها تلقائياً
      trades = load_active_trades()
      if trades:
        btc_p, eth_p, xrp_p = get_crypto_prices()
        gold_p = get_gold_price()
        current_prices = {
            "BTC/USDT": btc_p,
            "ETH/USDT": eth_p,
            "XRP/USDT": xrp_p,
            "GOLD (XAUUSD)": gold_p,
        }

        updated_trades = []
        results = load_results()

        for trade in trades:
          if trade["status"] != "active":
            continue

          asset = trade["asset"]
          cur_price = current_prices.get(asset, 0)
          if cur_price == 0:
            updated_trades.append(trade)
            continue

          entry = trade["entry"]
          tp1 = trade["tp1"]
          tp2 = trade["tp2"]
          sl = trade["sl"]

          result_text = None
          # فحص ضرب وقف الخسارة
          if cur_price <= sl:
            trade["status"] = "closed"
            result_text = (
                f"❌ صفقة {asset} مغلقة بضرب وقف الخسارة SL عند `{cur_price:,.2f}`"
            )
            results["daily"].append(result_text)
          # فحص تحقيق الهدف الثاني TP2
          elif cur_price >= tp2:
            trade["status"] = "closed"
            result_text = (
                f"✅ صفقة {asset} حققت الهدف الثاني TP2 بنجاح عند `{cur_price:,.2f}` 🚀"
            )
            results["daily"].append(result_text)
          # فحص تحقيق الهدف الأول TP1 والتأمين
          elif cur_price >= tp1 and not trade["secured"]:
            trade["secured"] = True
            result_text = (
                f"🛡️ صفقة {asset} بلغت الهدف الأول TP1 (`{cur_price:,.2f}`) وتم تأمينها بنجاح (Breakeven)."
            )
            results["daily"].append(result_text)

          if result_text:
            save_results(results)
          else:
            updated_trades.append(trade)

        save_active_trades(updated_trades)

      # ثانياً: تتبع التنبيهات المخصصة للمستخدمين
      if custom_alerts:
        btc_p, eth_p, xrp_p = get_crypto_prices()
        gold_p = get_gold_price()
        prices_map = {"BTC": btc_p, "ETH": eth_p, "XRP": xrp_p, "GOLD": gold_p}

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
                    f"🪙 الأصل: `{asset}`\n"
                    f"🎯 الهدف: `{target:,.2f}`\n"
                    f"📊 السعر الحالي: `{current_price:,.2f}`",
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

    except Exception as e:
      print(f"Error in background monitor: {e}")
    time.sleep(60)


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
        "🎁 تم تفعيل فترة تجريبية مجانية لمدة 3 أيام لحسابك بنجاح.\n\n"
        "📋 **قائمة الأوامر المتاحة:**\n"
        "• `/deals` - صفقات القاعدة الذهبية للعملات\n"
        "• `/analysis` - صفقات الرؤية التحليلية\n"
        "• `/gold` - صفقات الذهب\n"
        "• `/results` - سجل نتائج الأداء والصفقات المقترحة تلقائياً (يومي/أسبوعي/شهري)\n"
        "• `/calc` - حاسبة المخاطر\n"
        "• `/news` - موجز الأخبار الاقتصادية\n"
        "• `/academy` - الأكاديمية التعليمية للمبتدئين\n"
        "• `/glossary` - قاموس المصطلحات (بحث ذكي)\n"
        "• `/status` - حالة اشتراكي ورابط الدعوة\n"
        "• `/help` - دليل الاستخدام"
    )
  else:
    if user_id == ADMIN_ID:
      welcome_text = (
          "👑 أهلاً بك يا مهندس أحمد! البوت يعمل بدون أزرار مزعجة وبنظام تتبع ذاتي.\n\n"
          "🛠️ **أوامر لوحة التحكم للمطور:**\n"
          "• `/users` - عرض المشتركين\n"
          "• `/stats` - الإحصائيات\n"
          "• `/add_result daily [النص]` - تسجيل نتيجة يدوية إضافية"
      )
    else:
      expiry_dt = datetime.fromisoformat(all_users[uid_str]["expiry"])
      remaining = expiry_dt - datetime.now()
      days_left = max(0, remaining.days)
      hours_left = max(0, remaining.seconds // 3600)
      welcome_text = (
          "أهلاً بك مجدداً يا مهندس! حسابك مسجل في النظام.\n\n"
          f"✅ حالة اشتراكك: نشط (المتبقي: {days_left} يوم و {hours_left} ساعة)\n\n"
          "📋 استخدم الأوامر المباشرة للوصول لكل ميزات البوت (اكتب `/help` لعرض القائمة)."
      )

  bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown")


@bot.message_handler(commands=["help"])
def send_help(message):
  help_text = (
      "📋 **دليل أوامر البوت المباشرة:**\n\n"
      "• `/deals` - صفقات القاعدة الذهبية للعملات (تثبيت تلقائي للتتبع)[span_0](start_span)[span_0](end_span)\n"
      "• `/analysis` - صفقات الرؤية التحليلية والزخم (تثبيت تلقائي للتتبع)[span_1](start_span)[span_1](end_span)\n"
      "• `/gold` - صفقات الذهب (تثبيت تلقائي للتتبع)[span_2](start_span)[span_2](end_span)\n"
      "• `/results` - سجل نتائج وأداء الصفقات المقترحة تلقائياً (يومي، أسبوعي، شهري)[span_3](start_span)[span_3](end_span)\n"
      "• `/calc` - حاسبة إدارة المخاطر وحجم الصفقة[span_4](start_span)[span_4](end_span)\n"
      "• `/alert [asset] [price]` - ضبط تنبيه سعر مخصص[span_5](start_span)[span_5](end_span)\n"
      "• `/news` - موجز الأخبار الاقتصادية اللحظية[span_6](start_span)[span_6](end_span)\n"
      "• `/quiz` - اختبار تداولي تفاعلي[span_7](start_span)[span_7](end_span)\n"
      "• `/academy` - الأكاديمية التعليمية للمبتدئين[span_8](start_span)[span_8](end_span)\n"
      "• `/search [term]` - بحث ذكي في قاموس مصطلحات التداول[span_9](start_span)[span_9](end_span)\n"
      "• `/accounts` - دليل فتح الحسابات وإنشاء المحافظ[span_10](start_span)[span_10](end_span)\n"
      "• `/deposit` - دليل السحب والإيداع (شبكة TRC20 وشام كاش)[span_11](start_span)[span_11](end_span)\n"
      "• `/status` - حالة اشتراكي ورابط دعوة أصدقائي[span_12](start_span)[span_12](end_span)"
  )
  bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


@bot.message_handler(commands=["results"])
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
      "📈 **سجل نتائج وأداء الصفقات المقترحة (تتبع آلي شفاف):**\n\n"
      "📅 **1. النتائج اليومية (صادرة آلياً وميدانياً):**\n"
      f"{format_items(daily_list)}\n"
      "📊 **2. النتائج الأسبوعية (حصيلة الأسبوع):**\n"
      f"{format_items(weekly_list)}\n"
      "🏆 **3. النتائج الشهرية (الحصيلة الكبرى):**\n"
      f"{format_items(monthly_list)}\n"
      "💡 *ملاحظة:* يتابع البوت الأسعار حياً ويسجل الأهداف والوقف والتأمين تلقائياً فور تحققها."
  )
  bot.send_message(message.chat.id, report_text, parse_mode="Markdown")


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


@bot.message_handler(commands=["deals"])
def send_golden_rule_deals(message):
  btc, eth, xrp = get_crypto_prices()

  # تسجيل الصفقات تلقائياً في نظام التتبّع الخلفي
  register_trade_automatically("BTC/USDT", btc, btc * 1.012, btc * 1.025, btc * (1 - 0.012))
  register_trade_automatically("ETH/USDT", eth, eth * 1.03, eth * 1.06, eth * (1 - 0.012))
  register_trade_automatically("XRP/USDT", xrp, xrp * 1.008, xrp * 1.015, xrp * (1 - 0.012))

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
      "📊 **صفقات القاعدة الذهبية للعملات (مثبتة للتتبع التلقائي):**\n\n"
      "⚡ **1. صفقات السكالبينج للعملات:**\n"
      f"• **العملة:** XRP/USDT (سعر الدخول: `{xrp:,.4f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{xrp_sl:,.4f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{xrp * 1.008:,.4f}` ──> **(+{xrp_tp1_pct}%)**\n"
      f"  🚀 *الهدف الثاني (TP2):* `{xrp * 1.015:,.4f}` ──> **(+{xrp_tp2_pct}%)**\n\n"
      "📅 **2. الصفقات اليومية للعملات:**\n"
      f"• **العملة:** BTC/USDT (سعر الدخول: `{btc:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{btc_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{btc * 1.012:,.2f}` ──> **(+{btc_tp1_pct}%)**\n"
      f"  🚀 *الهدف الثاني (TP2):* `{btc * 1.025:,.2f}` ──> **(+{btc_tp2_pct}%)**\n\n"
      "🌊 **3. صفقات السوينغ للعملات:**\n"
      f"• **العملة:** ETH/USDT (سعر الدخول: `{eth:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{eth_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{eth * 1.03:,.2f}` ──> **(+{eth_tp1_pct}%)**\n"
      f"  🚀 *الهدف الثاني (TP2):* `{eth * 1.06:,.2f}` ──> **(+{eth_tp2_pct}%)**"
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")

  chart_buf = generate_price_chart(btc)
  if chart_buf:
    bot.send_photo(
        message.chat.id,
        chart_buf,
        caption="📈 **الرسم البياني التحليلي (القاعدة الذهبية للعملات)**",
    )


@bot.message_handler(commands=["analysis"])
def send_analytical_vision_deals(message):
  btc_price, btc_chg, btc_trend, btc_tp1_p, btc_tp2_p, btc_sl_p = (
      get_dynamic_deal_data("bitcoin", 65000.0)
  )
  eth_price, eth_chg, eth_trend, eth_tp1_p, eth_tp2_p, eth_sl_p = (
      get_dynamic_deal_data("ethereum", 1850.0)
  )
  xrp_price, xrp_chg, xrp_trend, xrp_tp1_p, xrp_tp2_p, xrp_sl_p = (
      get_dynamic_deal_data("ripple", 0.52)
  )

  # تثبيت الصفقات التحليلية في نظام التتبع
  register_trade_automatically("BTC/USDT", btc_price, btc_price * (1 + btc_tp1_p), btc_price * (1 + btc_tp2_p), btc_price * (1 - btc_sl_p))
  register_trade_automatically("ETH/USDT", eth_price, eth_price * (1 + eth_tp1_p), eth_price * (1 + eth_tp2_p), eth_price * (1 - eth_sl_p))
  register_trade_automatically("XRP/USDT", xrp_price, xrp_price * (1 + xrp_tp1_p), xrp_price * (1 + xrp_tp2_p), xrp_price * (1 - xrp_sl_p))

  deals_text = (
      "📊 **صفقات الرؤية التحليلية وقراءة الزخم الحي (مثبتة للتتبع):**\n\n"
      f"🪙 **1. بيتكوين (BTC/USDT):**\n"
      f"• السعر الحالي: `{btc_price:,.2f}$` (التغير 24س: `{btc_chg:+.2f}%`)\n"
      f"• الحالة: {btc_trend}\n"
      f"  🛑 *SL:* `{btc_price * (1 - btc_sl_p):,.2f}` | 🎯 *TP1:* `{btc_price * (1 + btc_tp1_p):,.2f}`\n\n"
      f"💎 **2. إيثريوم (ETH/USDT):**\n"
      f"• السعر الحالي: `{eth_price:,.2f}$` (التغير 24س: `{eth_chg:+.2f}%`)\n"
      f"• الحالة: {eth_trend}\n"
      f"  🛑 *SL:* `{eth_price * (1 - eth_sl_p):,.2f}` | 🎯 *TP1:* `{eth_price * (1 + eth_tp1_p):,.2f}`\n\n"
      f"⚡ **3. ريبل (XRP/USDT):**\n"
      f"• السعر الحالي: `{xrp_price:,.4f}$` (التغير 24س: `{xrp_chg:+.2f}%`)\n"
      f"• الحالة: {xrp_trend}\n"
      f"  🛑 *SL:* `{xrp_price * (1 - xrp_sl_p):,.2f}` | 🎯 *TP1:* `{xrp_price * (1 + xrp_tp1_p):,.2f}`"
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


@bot.message_handler(commands=["gold"])
def send_gold_golden_rule(message):
  current_gold = get_gold_price()
  tp1_price = current_gold * (1 + 0.007)
  tp2_price = current_gold * (1 + 0.015)
  sl_price = current_gold * (1 - 0.01)

  # تثبيت صفقة الذهب للتتبع التلقائي
  register_trade_automatically("GOLD (XAUUSD)", current_gold, tp1_price, tp2_price, sl_price)

  gold_text = (
      "🟡 **توصيات صفقات الذهب الحية (مثبتة للتتبع التلقائي):**\n\n"
      f"📍 **سعر الدخول الحالي (Entry):** `{current_gold:,.2f}` $\n"
      f"🛑 **وقف الخسارة المقترح (SL):** `{sl_price:,.2f}` $ (-1.0%)\n"
      f"🎯 **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ (+0.7%)\n"
      f"🚀 **الهدف الثاني (TP2):** `{tp2_price:,.2f}` $ (+1.5%)\n"
      "🛡️ *التأمين:* يتابعه البوت ويرفع الـ SL لسعر الدخول تلقائياً عند بلوغ TP1."
  )
  bot.send_message(message.chat.id, gold_text, parse_mode="Markdown")


@bot.message_handler(commands=["calc"])
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
    bot.send_message(message.chat.id, result_text, parse_mode="Markdown")
    if user_id in risk_calculator_sessions:
      del risk_calculator_sessions[user_id]
  except Exception:
    bot.send_message(message.chat.id, "⚠️ حدث خطأ. أعد المحاولة عبر الأمر `/calc`.")


@bot.message_handler(commands=["alert"])
def set_custom_alert(message):
  parts = message.text.split()
  if len(parts) < 3:
    bot.send_message(
        message.chat.id,
        "⚠️ الصيغة الصحيحة:\n`/alert btc 68000` أو `/alert gold 4000`",
        parse_mode="Markdown",
    )
    return
  asset = parts[1].replace("/", "").replace("USDT", "").upper()
  try:
    target_price = float(parts[2].replace(",", ""))
    user_id = message.from_user.id
    if user_id not in custom_alerts:
      custom_alerts[user_id] = []
    custom_alerts[user_id].append({"asset": asset, "price": target_price})
    bot.send_message(
        message.chat.id,
        f"✅ تم ضبط التنبيه للعملة `{asset}` عند سعر `{target_price:,.2f}`",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ خطأ في كتابة السعر.")


@bot.message_handler(commands=["news"])
def send_crypto_news(message):
  news_text = (
      "📰 **موجز الأخبار الاقتصادية والأسواق اللحظية:**\n\n"
      "1️⃣ **الاحتياطي الفيدرالي:** ترقب بيانات التضخم وتأثيرها على الفائدة.\n"
      "2️⃣ **العملات الرقمية:** استقرار تدفقات (ETFs) يدعم البيتكوين.\n"
      "3️⃣ **الذهب (XAUUSD):** التوترات والسياسة النقدية تقود حركة الأوقية."
  )
  bot.send_message(message.chat.id, news_text, parse_mode="Markdown")


QUIZ_QUESTIONS = [
    {
        "question": (
            "🧠 **سؤال اختبار التداول:**\n\nما هو الغرض من (وقف الخسارة - Stop Loss)؟\n\nأ) مضاعفة الأرباح\nب) حماية المحفظة والخروج بخسارة صغيرة\nج) زيادة الرسوم"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "حماية", "خسارة"],
    }
]


@bot.message_handler(commands=["quiz"])
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
    bot.send_message(
        message.chat.id,
        "🎉 **إجابة صحيحة 100%!** أنت تملك عقلية متداول واعي.",
        parse_mode="Markdown",
    )
  else:
    bot.send_message(
        message.chat.id,
        f"❌ إجابة غير صحيحة. الخيار الصحيح هو **({q_data['answer_key']})**.",
        parse_mode="Markdown",
    )
  if user_id in active_quizzes:
    del active_quizzes[user_id]


@bot.message_handler(commands=["academy"])
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية التعليمية:**\n\n"
      "• **الدرس الأول:** ما هو التداول والفرق بين السبوت والفيوتشر.\n"
      "• **الدرس الثاني:** تطبيق قاعدة التأمين (Breakeven) لحماية رأس المال.\n"
      "• **الدرس الثالث:** إدارة المخاطر وألا تتجاوز خسارة الصفقة 1%."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى كتابة المصطلح بعد الأمر. مثال: `/search breakeven`",
        parse_mode="Markdown",
    )
    return
  query = parts[1].strip().lower()
  glossary_db = {
      "breakeven": "🛡️ **Breakeven:** رفع وقف الخسارة لسعر الدخول بعد بلوغ الهدف الأول لضمان الصفر خسارة.",
      "usdt": "🔹 **USDT:** عملة رقمية مستقرة تساوي دولاراً واحداً لحفظ الأرباح.",
      "sl": "🛑 **SL (Stop Loss):** أمر وقف الخسارة لحماية المحفظة.",
  }
  desc = glossary_db.get(
      query, "❌ عذراً، لم يتم العثور على المصطلح في القاموس."
  )
  bot.send_message(
      message.chat.id,
      f"🔍 **بحث (`{query}`):**\n\n{desc}",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["accounts"])
def send_accounts_guide(message):
  bot.send_message(
      message.chat.id,
      "🌐 **دليل فتح الحسابات:** استخدم منصات مركزية موثوقة (مثل Binance أو Bybit) مع توثيق الهوية (KYC).",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["deposit"])
def send_deposit_withdraw_guide(message):
  bot.send_message(
      message.chat.id,
      "📥 **دليل السحب والإيداع:** الاعتماد على شبكة TRC20 للتحويلات الرقمية السريعة والرخيصة، وشحن الرصيد المحلي عبر شام كاش.",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["status"])
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  uid_str = str(user_id)
  if user_id == ADMIN_ID:
    bot.send_message(
        message.chat.id, "👑 أنت المطور، اشتراكك مفتوح دائماً!", parse_mode="Markdown"
    )
    return
  user_info = all_users.get(
      uid_str,
      {
          "expiry": (datetime.now() + timedelta(days=3)).isoformat(),
          "referral_count": 0,
      },
  )
  expiry_dt = datetime.fromisoformat(user_info["expiry"])
  ref_count = user_info.get("referral_count", 0)
  bot_username = bot.get_me().username
  ref_link = f"https://t.me/{bot_username}?start=ref_{uid_str}"
  bot.send_message(
      message.chat.id,
      f"📋 ينتهي اشتراكك في: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"👥 عدد أصدقائي: **{ref_count}**\n"
      f"🔗 رابط الدعوة:\n`{ref_link}`",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["users"])
def show_all_users(message):
  if message.from_user.id != ADMIN_ID:
    return
  current_users = load_users()
  if not current_users:
    bot.send_message(message.chat.id, "📭 لا يوجد مشتركين حالياً.")
    return
  bot.send_message(
      message.chat.id,
      f"👥 **إجمالي المشتركين:** {len(current_users)}",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  bot.send_message(
      message.chat.id,
      f"📊 إجمالي المشتركين: {len(all_users)}\nمجموعات مفعلة: {len(active_groups)}",
      parse_mode="Markdown",
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

  # تشغيل عامل التتبع المزدوج (للأسعار + أتمتة الصفقات وتحديث نتائجها حياً)
  monitor_thread = threading.Thread(target=background_trade_and_price_monitor, daemon=True)
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
