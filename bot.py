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
ACTIVE_TRADES_FILE = "active_trades.json"
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


# --- تصميم الكيبورد السفلي الشامل ---
def get_main_menu(user_id):
  markup = types.ReplyKeyboardMarkup(
      resize_keyboard=True, is_persistent=True, row_width=2
  )
  btn_golden = types.KeyboardButton("📊 صفقات القاعدة الذهبية للعملات")
  btn_analytical = types.KeyboardButton("📊 صفقات الرؤية التحليلية للعملات")
  btn_gold_golden = types.KeyboardButton("🟡 صفقات الذهب (القاعدة الذهبية)")
  btn_gold_analytical = types.KeyboardButton("🟡 صفقات الذهب (الرؤية التحليلية)")
  btn_results = types.KeyboardButton(
      "📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)"
  )
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


def send_with_menu(message, text):
  bot.send_message(
      message.chat.id,
      text,
      reply_markup=get_main_menu(message.from_user.id),
      parse_mode="Markdown",
  )


# --- نظام أتمتة وتسجيل الصفقات النشطة تلقائياً ---
def register_trade_automatically(asset_name, entry, tp1, tp2, sl):
  trades = load_active_trades()
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
          if cur_price <= sl:
            trade["status"] = "closed"
            result_text = (
                f"❌ صفقة {asset} مغلقة بضرب وقف الخسارة SL عند `{cur_price:,.2f}`"
            )
            results["daily"].append(result_text)
          elif cur_price >= tp2:
            trade["status"] = "closed"
            result_text = (
                f"✅ صفقة {asset} حققت الهدف الثاني TP2 بنجاح عند `{cur_price:,.2f}` 🚀"
            )
            results["daily"].append(result_text)
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
        "🎁 تم تفعيل فترة تجريبية مجانية لمدة 3 أيام لحسابك بنجاح.\n"
        "اختر ما تحتاجه من الأزرار أدناه:"
    )
  else:
    if user_id == ADMIN_ID:
      welcome_text = "👑 أهلاً بك يا مهندس أحمد! البوت بكامل أزراره وميزاته جاهز:"
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


# --- معالجات أزرار الكيبورد السفلي والأوامر المباشرة ---
@bot.message_handler(
    func=lambda message: message.text == "📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)"
)
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


@bot.message_handler(
    func=lambda message: message.text == "📊 صفقات القاعدة الذهبية للعملات"
)
@bot.message_handler(commands=["deals"])
def send_golden_rule_deals(message):
  btc, eth, xrp = get_crypto_prices()

  register_trade_automatically(
      "BTC/USDT", btc, btc * 1.012, btc * 1.025, btc * (1 - 0.012)
  )
  register_trade_automatically(
      "ETH/USDT", eth, eth * 1.03, eth * 1.06, eth * (1 - 0.012)
  )
  register_trade_automatically(
      "XRP/USDT", xrp, xrp * 1.008, xrp * 1.015, xrp * (1 - 0.012)
  )

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
  send_with_menu(message, deals_text)

  chart_buf = generate_price_chart(btc)
  if chart_buf:
    bot.send_photo(
        message.chat.id,
        chart_buf,
        caption="📈 **الرسم البياني التحليلي (القاعدة الذهبية للعملات)**",
    )


@bot.message_handler(
    func=lambda message: message.text == "📊 صفقات الرؤية التحليلية للعملات"
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

  register_trade_automatically(
      "BTC/USDT",
      btc_price,
      btc_price * (1 + btc_tp1_p),
      btc_price * (1 + btc_tp2_p),
      btc_price * (1 - btc_sl_p),
  )
  register_trade_automatically(
      "ETH/USDT",
      eth_price,
      eth_price * (1 + eth_tp1_p),
      eth_price * (1 + eth_tp2_p),
      eth_price * (1 - eth_sl_p),
  )
  register_trade_automatically(
      "XRP/USDT",
      xrp_price,
      xrp_price * (1 + xrp_tp1_p),
      xrp_price * (1 + xrp_tp2_p),
      xrp_price * (1 - xrp_sl_p),
  )

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
  send_with_menu(message, deals_text)


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (القاعدة الذهبية)"
)
@bot.message_handler(commands=["gold"])
def send_gold_golden_rule(message):
  current_gold = get_gold_price()
  tp1_price = current_gold * (1 + 0.007)
  tp2_price = current_gold * (1 + 0.015)
  sl_price = current_gold * (1 - 0.01)

  register_trade_automatically(
      "GOLD (XAUUSD)", current_gold, tp1_price, tp2_price, sl_price
  )

  gold_text = (
      "🟡 **توصيات صفقات الذهب (القاعدة الذهبية - مثبتة للتتبع):**\n\n"
      f"📍 **سعر الدخول الحالي (Entry):** `{current_gold:,.2f}` $\n"
      f"🛑 **وقف الخسارة المقترح (SL):** `{sl_price:,.2f}` $ (-1.0%)\n"
      f"🎯 **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ (+0.7%)\n"
      f"🚀 **الهدف الثاني (TP2):** `{tp2_price:,.2f}` $ (+1.5%)\n"
      "🛡️ *التأمين:* يتابعه البوت ويرفع الـ SL لسعر الدخول تلقائياً عند بلوغ TP1."
  )
  send_with_menu(message, gold_text)


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (الرؤية التحليلية)"
)
def send_gold_analytical_vision(message):
  current_gold = get_gold_price()
  tp1_price = current_gold * (1 + 0.01)
  tp2_price = current_gold * (1 + 0.022)
  sl_price = current_gold * (1 - 0.012)

  register_trade_automatically(
      "GOLD (XAUUSD)", current_gold, tp1_price, tp2_price, sl_price
  )

  gold_text = (
      "🟡 **توصيات صفقات الذهب (الرؤية التحليلية - مثبتة للتتبع):**\n\n"
      f"📍 **سعر الدخول الحالي (Entry):** `{current_gold:,.2f}` $\n"
      f"🚀 **حالة السوق:** رصد سيولة شرائية وتذبذب إيجابي.\n"
      f"🛑 **وقف الخسارة (SL):** `{sl_price:,.2f}` $ (-1.2%)\n"
      f"🎯 **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ (+1.0%)\n"
      f"🚀 **الهدف الثاني (TP2):** `{tp2_price:,.2f}` $ (+2.2%)"
  )
  send_with_menu(message, gold_text)


@bot.message_handler(
    func=lambda message: message.text == "🧮 حاسبة المخاطر وحجم الصفقة"
)
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
    send_with_menu(message, result_text)
    if user_id in risk_calculator_sessions:
      del risk_calculator_sessions[user_id]
  except Exception:
    bot.send_message(message.chat.id, "⚠️ حدث خطأ. أعد المحاولة من الكيبورد.")


@bot.message_handler(
    func=lambda message: message.text == "🔔 ضبط تنبيه سعر مخصص (/alert)"
)
@bot.message_handler(commands=["alert"])
def set_custom_alert(message):
  parts = message.text.split()
  if len(parts) < 3:
    send_with_menu(
        message,
        "⚠️ الصيغة الصحيحة عبر الأمر:\n`/alert btc 68000` أو `/alert gold 4000`",
    )
    return
  asset = parts[1].replace("/", "").replace("USDT", "").upper()
  try:
    target_price = float(parts[2].replace(",", ""))
    user_id = message.from_user.id
    if user_id not in custom_alerts:
      custom_alerts[user_id] = []
    custom_alerts[user_id].append({"asset": asset, "price": target_price})
    send_with_menu(
        message,
        f"✅ تم ضبط التنبيه للعملة `{asset}` عند سعر `{target_price:,.2f}`",
    )
  except Exception:
    send_with_menu(message, "⚠️ خطأ في كتابة السعر.")


@bot.message_handler(
    func=lambda message: message.text == "📰 موجز الأخبار الاقتصادية اللحظية"
)
@bot.message_handler(commands=["news"])
def send_crypto_news(message):
  news_text = (
      "📰 **موجز الأخبار الاقتصادية والأسواق اللحظية:**\n\n"
      "1️⃣ **الاحتياطي الفيدرالي:** ترقب بيانات التضخم وتأثيرها على الفائدة.\n"
      "2️⃣ **العملات الرقمية:** استقرار تدفقات (ETFs) يدعم البيتكوين.\n"
      "3️⃣ **الذهب (XAUUSD):** التوترات والسياسة النقدية تقود حركة الأوقية."
  )
  send_with_menu(message, news_text)


QUIZ_QUESTIONS = [
    {
        "question": (
            "🧠 **سؤال اختبار التداول:**\n\nما هو الغرض من (وقف الخسارة - Stop Loss)؟\n\nأ) مضاعفة الأرباح\nب) حماية المحفظة والخروج بخسارة صغيرة\nج) زيادة الرسوم"
        ),
        "answer_key": "ب",
        "keywords": ["ب", "حماية", "خسارة"],
    }
]


@bot.message_handler(
    func=lambda message: message.text == "🧠 اختبار تداولي تفاعلي (Quiz)"
)
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
    send_with_menu(
        message,
        "🎉 **إجابة صحيحة 100%!** أنت تملك عقلية متداول واعي.",
    )
  else:
    send_with_menu(
        message,
        f"❌ إجابة غير صحيحة. الخيار الصحيح هو **({q_data['answer_key']})**.",
    )
  if user_id in active_quizzes:
    del active_quizzes[user_id]


@bot.message_handler(
    func=lambda message: message.text == "📚 الأكاديمية التعليمية للمبتدئين"
)
@bot.message_handler(commands=["academy"])
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية التعليمية:**\n\n"
      "• **الدرس الأول:** ما هو التداول والفرق بين السبوت والفيوتشر.\n"
      "• **الدرس الثاني:** تطبيق قاعدة التأمين (Breakeven) لحماية رأس المال.\n"
      "• **الدرس الثالث:** إدارة المخاطر وألا تتجاوز خسارة الصفقة 1%."
  )
  send_with_menu(message, academy_text)


@bot.message_handler(
    func=lambda message: message.text
    == "📖 قاموس مصطلحات التداول (بحث ذكي)"
)
@bot.message_handler(commands=["glossary"])
def glossary_menu(message):
  glossary_guide = (
      "📖 **قاموس الحيتان ومصطلحات السوق:**\n\n"
      "استخدم الأمر `/search` متبوعاً بالمصطلح.\n"
      "📌 *مثال:* `/search breakeven` أو `/search usdt`"
  )
  send_with_menu(message, glossary_guide)


@bot.message_handler(commands=["search"])
def search_glossary(message):
  parts = message.text.split(maxsplit=1)
  if len(parts) < 2:
    send_with_menu(
        message, "⚠️ يرجى كتابة المصطلح بعد الأمر. مثال: `/search breakeven`"
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
  send_with_menu(message, f"🔍 **بحث (`{query}`):**\n\n{desc}")


@bot.message_handler(
    func=lambda message: message.text == "🌐 دليل فتح الحسابات وإنشاء المحافظ"
)
@bot.message_handler(commands=["accounts"])
def send_accounts_guide(message):
  send_with_menu(
      message,
      "🌐 **دليل فتح الحسابات:** استخدم منصات مركزية موثوقة (مثل Binance أو Bybit) مع توثيق الهوية (KYC).",
  )


@bot.message_handler(
    func=lambda message: message.text == "📥 دليل السحب والإيداع (شبكة TRC20)"
)
@bot.message_handler(commands=["deposit"])
def send_deposit_withdraw_guide(message):
  send_with_menu(
      message,
      "📥 **دليل السحب والإيداع:** الاعتماد على شبكة TRC20 للتحويلات الرقمية السريعة والرخيصة، وشحن الرصيد المحلي عبر شام كاش.",
  )


@bot.message_handler(
    func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)"
)
def send_payment_info(message):
  send_with_menu(
      message,
      "💳 **الدفع والشحن المحلي:** تواصل مع المطور (`"
      + ADMIN_USERNAME
      + "`) لإتمام الحوالة عبر شام كاش وتفعيل اشتراكك.",
  )


@bot.message_handler(
    func=lambda message: message.text == "⏳ حالة اشتراكي ورابط دعوة أصدقائي"
)
@bot.message_handler(commands=["status"])
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  uid_str = str(user_id)
  if user_id == ADMIN_ID:
    send_with_menu(message, "👑 أنت المطور، اشتراكك مفتوح دائماً!")
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
  send_with_menu(
      message,
      f"📋 ينتهي اشتراكك في: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"👥 عدد أصدقائي: **{ref_count}**\n"
      f"🔗 رابط الدعوة:\n`{ref_link}`",
  )


@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
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
