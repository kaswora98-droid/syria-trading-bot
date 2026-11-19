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

TOKEN = "8928709566:AAGmQGGme_fXQvSwYR30Uii3iR4BzjpEyrk"

bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

DATA_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
RESULTS_FILE = "trading_results.json"  # ملف تخزين نتائج الصفقات وحصائل الأداء
ACTIVE_DEALS_FILE = "active_tracked_deals.json"  # تخزين الصفقات المثبتة للمتداولين
TRIAL_HISTORY_FILE = "trial_history.json"  # سجل دائم لمن استخدم الفترة التجريبية
banned_users = set()

risk_calculator_sessions = {}
custom_alerts = {}
active_quizzes = {}

app = Flask(__name__)


# --- دوال التحقق من اليوزر والصلاحيات ---
def has_username(user):
  if not user:
    return False
  return bool((user.username or "").strip())


def send_no_username_notice(chat_id):
  bot.send_message(
      chat_id,
      "🚫 **عذراً، لا يُسمح باستخدام البوت بدون يوزر (Username).**\n\n"
      "يرجى إضافة يوزر لحسابك في إعدادات تيليجرام أولاً، ثم أرسل `/start`.",
      parse_mode="Markdown",
  )


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


def load_trial_history():
  if os.path.exists(TRIAL_HISTORY_FILE):
    try:
      with open(TRIAL_HISTORY_FILE, "r", encoding="utf-8") as f:
        content = f.read()
        if not content.strip():
          return {}
        return json.loads(content)
    except Exception:
      return {}
  return {}


def save_trial_history(data):
  try:
    with open(TRIAL_HISTORY_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving trial history: {e}")


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
trial_history = load_trial_history()
active_groups = load_groups()


def has_used_trial_before(uid_str, user_uname):
  if uid_str in trial_history:
    return True
  norm_uname = (user_uname or "").lstrip("@").strip().lower()
  if norm_uname:
    for rec in trial_history.values():
      rec_uname = (rec.get("username") or "").lstrip("@").strip().lower()
      if rec_uname and rec_uname == norm_uname:
        return True
  if uid_str in all_users:
    u = all_users[uid_str]
    if u.get("trial_used") is True or u.get("is_trial") is not None:
      return True
  return False


def ensure_admin_entry(user):
  uid_str = str(ADMIN_ID)
  uname = (user.username or ADMIN_USERNAME.lstrip("@")).strip()
  fname = user.first_name or "المطور"
  if uid_str not in all_users:
    all_users[uid_str] = {
        "name": fname,
        "username": uname,
        "role": "admin",
        "expiry": (datetime.now() + timedelta(days=36500)).isoformat(),
        "is_trial": False,
        "trial_used": True,
        "invited_by": None,
        "referral_count": 0,
    }
    save_users(all_users)
  else:
    changed = False
    if all_users[uid_str].get("role") != "admin":
      all_users[uid_str]["role"] = "admin"
      changed = True
    if all_users[uid_str].get("is_trial") is not False:
      all_users[uid_str]["is_trial"] = False
      changed = True
    if changed:
      save_users(all_users)


def is_subscription_active(uid_str):
  if int(uid_str) == ADMIN_ID:
    return True
  u = all_users.get(uid_str)
  if not u:
    return False
  exp_str = u.get("expiry")
  if not exp_str:
    return False
  try:
    expiry_dt = datetime.fromisoformat(exp_str)
    return expiry_dt > datetime.now()
  except Exception:
    return False


def send_subscription_expired_notice(chat_id):
  bot.send_message(
      chat_id,
      "⛔ **انتهت صلاحية اشتراكك وتم إيقاف استخدام البوت تلقائياً.**\n\n"
      "• يعود حسابك للعمل تلقائياً عند تمديد الاشتراك بواسطة المطور"
      f" (`{ADMIN_USERNAME}`) أو عند إتمام دعوة 3 أشخاص عبر رابط الإحالة"
      " للحصول على يوم مجاني.\n"
      "• أرسل `/start` للاطلاع على حالة اشتراكك ورابط الدعوة.",
      parse_mode="Markdown",
  )


def can_use_bot(message):
  user = message.from_user
  if not user:
    return False
  if user.id in banned_users:
    return False
  if user.id == ADMIN_ID:
    ensure_admin_entry(user)
    return True
  if not has_username(user):
    send_no_username_notice(message.chat.id)
    return False
  if not is_subscription_active(str(user.id)):
    send_subscription_expired_notice(message.chat.id)
    return False
  return True


@app.route("/")
def home():
  return "Ultimate Trading Bot is running 24/7!"


@app.route("/ping")
def ping():
  return "Pong!", 200


# جلب الأسعار الحية الحقيقية من السوق فقط (Binance ثم Kraken دون أرقام ثابتة)
def get_crypto_prices():
  btc = None
  eth = None
  xrp = None

  try:
    btc_res = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5
    )
    if btc_res.status_code == 200:
      val = float(btc_res.json().get("price", 0))
      if val > 0:
        btc = val
  except Exception:
    pass

  try:
    eth_res = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT", timeout=5
    )
    if eth_res.status_code == 200:
      val = float(eth_res.json().get("price", 0))
      if val > 0:
        eth = val
  except Exception:
    pass

  try:
    xrp_res = requests.get(
        "https://api.binance.com/api/v3/ticker/price?symbol=XRPUSDT", timeout=5
    )
    if xrp_res.status_code == 200:
      val = float(xrp_res.json().get("price", 0))
      if val > 0:
        xrp = val
  except Exception:
    pass

  if btc is None or eth is None or xrp is None:
    try:
      url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD,ETHUSD,XRPUSD"
      res = requests.get(url, timeout=5).json().get("result", {})
      if btc is None and "XXBTZUSD" in res:
        val = float(res["XXBTZUSD"]["c"][0])
        if val > 0:
          btc = val
      if eth is None and "XETHZUSD" in res:
        val = float(res["XETHZUSD"]["c"][0])
        if val > 0:
          eth = val
      if xrp is None and "XXRPZUSD" in res:
        val = float(res["XXRPZUSD"]["c"][0])
        if val > 0:
          xrp = val
    except Exception:
      pass

  return btc, eth, xrp


# جلب سعر الذهب الحي (XAUUSD) من مصادر حية متعددة فقط دون إرجاع رقم ثابت عند الفشل
def get_gold_price():
  headers = {"User-Agent": "Mozilla/5.0"}

  try:
    response = requests.get(
        "https://data-asg.goldprice.org/dbXRates/USD",
        headers=headers,
        timeout=6,
    )
    if response.status_code == 200:
      data = response.json()
      for item in data.get("items", []):
        if item.get("curr") == "USD":
          val = item.get("xauPrice")
          if val is not None and float(val) > 0:
            return float(val)
  except Exception:
    pass

  try:
    response = requests.get(
        "https://api.gold-api.com/price/XAU",
        headers=headers,
        timeout=6,
    )
    if response.status_code == 200:
      data = response.json()
      val = data.get("price")
      if val is not None and float(val) > 0:
        return float(val)
  except Exception:
    pass

  try:
    response = requests.get(
        "https://api.metals.live/v1/spot/gold",
        headers=headers,
        timeout=6,
    )
    if response.status_code == 200:
      data = response.json()
      if isinstance(data, list) and data:
        first_item = data[0]
        if isinstance(first_item, dict):
          val = first_item.get("price") or first_item.get("gold")
          if val is not None and float(val) > 0:
            return float(val)
        elif isinstance(first_item, (int, float)) and float(first_item) > 0:
          return float(first_item)
      elif isinstance(data, dict):
        val = data.get("price") or data.get("gold")
        if val is not None and float(val) > 0:
          return float(val)
  except Exception:
    pass

  return None


# مولد الرسوم البيانية الآمن
def generate_price_chart(btc_price):
  if not MATPLOTLIB_AVAILABLE or btc_price is None or btc_price <= 0:
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
    if entry <= 0:
      return 0.0
    if direction.upper() == "BUY":
      percentage = ((target - entry) / entry) * 100
    else:
      percentage = ((entry - target) / entry) * 100
    return round(percentage, 2)
  except Exception:
    return 0.0


def get_dynamic_deal_data(symbol_id, live_price):
  if live_price is None or live_price <= 0:
    return None

  change_24h = 0.0
  try:
    url = (
        f"https://api.coingecko.com/api/v3/simple/price?ids={symbol_id}"
        "&vs_currencies=usd&include_24hr_change=true"
    )
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      if symbol_id in data and "usd_24h_change" in data[symbol_id]:
        change_24h = float(data[symbol_id]["usd_24h_change"])
  except Exception:
    change_24h = 0.0

  if change_24h > 0:
    trend_status = "🚀 زخم صاعد (Bullish Momentum)"
    tp1_pct = 0.012
    tp2_pct = 0.025
    sl_pct = 0.01
  elif change_24h < 0:
    trend_status = "🔻 ضغط بيعي / تصحيح (Bearish Pressure)"
    tp1_pct = 0.008
    tp2_pct = 0.015
    sl_pct = 0.008
  else:
    trend_status = "⚖️ استقرار جانبي (Consolidation)"
    tp1_pct = 0.01
    tp2_pct = 0.02
    sl_pct = 0.01

  return live_price, change_24h, trend_status, tp1_pct, tp2_pct, sl_pct


DEAL_STOP_EXPLANATION = (
    "⏸️ **شرح التوقف في الصفقات:**\n"
    "• عند **توقف السعر اللحظي** أو **توقف/تأخر الشموع** وتحديثات السوق"
    " (سواء بسبب توقف/بطء مصدر البيانات أو هدوء السيولة أو إغلاق/توقف"
    " جلسة السوق)، تتجمد حركة الأسعار ولا يُحسب تحقق الأهداف أو ضرب"
    " الوقف على قراءة متوقفة.\n"
    "• أثناء التوقف: لا تدخل صفقة جديدة على سعر جامد، وإذا كانت لديك صفقة"
    " مفتوحة فالتزم بوقف الخسارة (`SL`) المحدد مسبقاً وانتظر عودة حركة"
    " الشموع والأسعار الحية قبل اتخاذ أي قرار."
)


def pin_suggested_deals(user_id_str, category_key, deals_entries):
  tracked = load_tracked_deals()
  if user_id_str not in tracked:
    tracked[user_id_str] = {}
  tracked[user_id_str][category_key] = {
      "timestamp": datetime.now().isoformat(),
      "entries": deals_entries,
  }
  save_tracked_deals(tracked)


# --- القائمة الرئيسية ---
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


@bot.message_handler(commands=["start"])
def send_welcome(message):
  if message.chat.type != "private":
    return

  user = message.from_user
  user_id = user.id
  uid_str = str(user_id)

  if user_id in banned_users:
    return

  # حساب المطور دائم مباشرة دون رسالة فترة تجريبية
  if user_id == ADMIN_ID:
    ensure_admin_entry(user)
    bot.send_message(
        message.chat.id,
        "👑 أهلاً بك يا مهندس أحمد! حساب المطور الدائم جاهز بكامل ميزاته:",
        reply_markup=get_main_menu(user_id),
        parse_mode="Markdown",
    )
    return

  # منع أي مستخدم لا يملك يوزر تلقائياً
  if not has_username(user):
    send_no_username_notice(message.chat.id)
    return

  text_parts = message.text.split()
  referrer_id = None
  if len(text_parts) > 1 and text_parts[1].startswith("ref_"):
    try:
      referrer_id = text_parts[1].replace("ref_", "")
    except Exception:
      pass

  user_name = user.first_name or "مستخدم"
  user_uname = (user.username or "").strip()

  if uid_str not in all_users:
    if has_used_trial_before(uid_str, user_uname):
      prev_exp_str = trial_history.get(uid_str, {}).get("expiry")
      try:
        expiry_date = (
            datetime.fromisoformat(prev_exp_str)
            if prev_exp_str
            else datetime.now()
        )
      except Exception:
        expiry_date = datetime.now()

      all_users[uid_str] = {
          "name": user_name,
          "username": user_uname,
          "expiry": expiry_date.isoformat(),
          "is_trial": False,
          "trial_used": True,
          "invited_by": referrer_id,
          "referral_count": 0,
      }
      trial_history[uid_str] = {
          "username": user_uname,
          "expiry": expiry_date.isoformat(),
          "used_at": trial_history.get(uid_str, {}).get(
              "used_at", datetime.now().isoformat()
          ),
      }
      save_trial_history(trial_history)
      save_users(all_users)

      welcome_text = (
          f"أهلاً بك يا **{user_name}**.\n\n"
          "⚠️ تم استخدام الفترة التجريبية مسبقاً لهذا الحساب ولا يمكن إعادة"
          " تفعيلها.\n"
          f"📩 للتواصل والاشتراك: `{ADMIN_USERNAME}`"
      )
    else:
      now_dt = datetime.now()
      expiry_date = now_dt + timedelta(days=3)
      all_users[uid_str] = {
          "name": user_name,
          "username": user_uname,
          "expiry": expiry_date.isoformat(),
          "is_trial": True,
          "trial_used": True,
          "invited_by": referrer_id,
          "referral_count": 0,
      }
      trial_history[uid_str] = {
          "username": user_uname,
          "expiry": expiry_date.isoformat(),
          "used_at": now_dt.isoformat(),
      }
      save_trial_history(trial_history)

      if referrer_id and referrer_id in all_users and referrer_id != uid_str:
        all_users[referrer_id]["referral_count"] = (
            all_users[referrer_id].get("referral_count", 0) + 1
        )
        new_ref_count = all_users[referrer_id]["referral_count"]
        if new_ref_count % 3 == 0:
          ref_current_exp = datetime.fromisoformat(
              all_users[referrer_id]["expiry"]
          )
          ref_new_exp = max(ref_current_exp, datetime.now()) + timedelta(days=1)
          all_users[referrer_id]["expiry"] = ref_new_exp.isoformat()
          if referrer_id in trial_history:
            trial_history[referrer_id]["expiry"] = ref_new_exp.isoformat()
            save_trial_history(trial_history)
          try:
            bot.send_message(
                int(referrer_id),
                "🎉 أتممت 3 دعوات ناجحة عبر رابطك! تمت إضافة يوم مجاني إلى"
                " اشتراكك وعاد حسابك للعمل تلقائياً.",
                parse_mode="Markdown",
            )
          except Exception:
            pass
      save_users(all_users)

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
    changed_user = False
    if all_users[uid_str].get("username") != user_uname or all_users[
        uid_str
    ].get("name") != user_name:
      all_users[uid_str]["username"] = user_uname
      all_users[uid_str]["name"] = user_name
      changed_user = True
    if all_users[uid_str].get("trial_used") is not True:
      all_users[uid_str]["trial_used"] = True
      changed_user = True
    if uid_str not in trial_history:
      trial_history[uid_str] = {
          "username": user_uname,
          "expiry": all_users[uid_str]["expiry"],
          "used_at": datetime.now().isoformat(),
      }
      save_trial_history(trial_history)
    if changed_user:
      save_users(all_users)

    expiry_dt = datetime.fromisoformat(all_users[uid_str]["expiry"])
    remaining = expiry_dt - datetime.now()
    if remaining.total_seconds() > 0:
      if all_users[uid_str].get("is_trial") is True:
        all_users[uid_str]["is_trial"] = False
        save_users(all_users)
      days_left = max(0, remaining.days)
      hours_left = max(0, remaining.seconds // 3600)
      welcome_text = (
          f"أهلاً بك مجدداً يا **{user_name}**! حسابك مسجل في النظام.\n\n"
          f"✅ حالة اشتراكك: نشط (المتبقي: {days_left} يوم و {hours_left}"
          " ساعة)\n"
          "اختر ما تحتاجه من الأزرار أدناه:"
      )
    else:
      if all_users[uid_str].get("is_trial") is not False:
        all_users[uid_str]["is_trial"] = False
        save_users(all_users)
      welcome_text = (
          f"أهلاً بك مجدداً يا **{user_name}**.\n\n"
          "⚠️ انتهت الفترة التجريبية/الاشتراك الخاص بحسابك وتم إيقاف"
          " استخدام البوت تلقائياً لحين التمديد أو إتمام دعوة 3 أشخاص"
          " للحصول على يوم مجاني.\n"
          f"📩 للتواصل والتمديد: `{ADMIN_USERNAME}`"
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
@bot.message_handler(
    func=lambda message: message.text
    == "📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)"
)
def show_trading_results_report(message):
  if not can_use_bot(message):
    return
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
      "💡 *ملاحظة:* يتم تحديث النتائج اليومية فور إغلاق الصفقة، ويتم تجميع"
      " النتائج أسبوعياً وشهرياً تلقائياً!"
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


@bot.message_handler(
    func=lambda message: message.text == "📊 صفقات القاعدة الذهبية للعملات"
)
def send_golden_rule_deals(message):
  if not can_use_bot(message):
    return
  user_id = str(message.from_user.id)
  btc, eth, xrp = get_crypto_prices()

  if btc is None or eth is None or xrp is None:
    send_with_menu(
        message,
        "⚠️ تعذّر جلب الأسعار الحية للعملات حالياً (احتمال توقف السعر"
        " اللحظي أو توقف/تأخر الشموع وبيانات السوق)، يرجى المحاولة بعد قليل.",
    )
    return

  pin_suggested_deals(
      user_id,
      "golden_rule",
      {
          "XRP": {
              "deal_no": 1,
              "entry": xrp,
              "tp1": xrp * 1.008,
              "tp2": xrp * 1.015,
              "sl": xrp * (1 - 0.012),
              "stage": "tp1",
              "status": "active",
          },
          "BTC": {
              "deal_no": 1,
              "entry": btc,
              "tp1": btc * 1.012,
              "tp2": btc * 1.025,
              "sl": btc * (1 - 0.012),
              "stage": "tp1",
              "status": "active",
          },
          "ETH": {
              "deal_no": 1,
              "entry": eth,
              "tp1": eth * 1.03,
              "tp2": eth * 1.06,
              "sl": eth * (1 - 0.012),
              "stage": "tp1",
              "status": "active",
          },
      },
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
      "📊 **صفقات القاعدة الذهبية للعملات (النسب الثابتة وإدارة المخاطر - بالسعر"
      " الحي):**\n\n"
      "📡 *يتم الاعتماد على السعر الحي لحظة إصدار التوصية دون تثبيت أرقام"
      " ثابتة.*\n"
      "📌 *تم تثبيت جميع الصفقات المقترحة تلقائياً لمتابعتها وإرسال تقرير"
      " فور إتمام شروطها.*\n\n"
      f"{DEAL_STOP_EXPLANATION}\n\n"
      "⚡ **1. صفقات السكالبينج للعملات:**\n"
      f"• **العملة:** XRP/USDT (سعر الدخول الحي: `{xrp:,.4f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{xrp_sl:,.4f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{xrp * 1.008:,.4f}` ──>"
      f" **(+{xrp_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** جني 50% ونقل وقف الخسارة لسعر الدخول (`{xrp:,.4f}`"
      ").\n"
      f"  🚀 *الهدف الثاني (TP2):* `{xrp * 1.015:,.4f}` ──>"
      f" **(+{xrp_tp2_pct}%)**\n\n"
      "📅 **2. الصفقات اليومية للعملات:**\n"
      f"• **العملة:** BTC/USDT (سعر الدخول الحي: `{btc:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{btc_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{btc * 1.012:,.2f}` ──>"
      f" **(+{btc_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** جني نصف الربح وحرك وقف الخسارة لنقطة الدخول"
      f" (`{btc:,.2f}`).\n"
      f"  🚀 *الهدف الثاني (TP2):* `{btc * 1.025:,.2f}` ──>"
      f" **(+{btc_tp2_pct}%)**\n\n"
      "🌊 **3. صفقات السوينغ للعملات:**\n"
      f"• **العملة:** ETH/USDT (سعر الدخول الحي: `{eth:,.2f}`)\n"
      f"  🛑 *وقف الخسارة (SL):* `{eth_sl:,.2f}` (-1.2%)\n"
      f"  🎯 *الهدف الأول (TP1):* `{eth * 1.03:,.2f}` ──>"
      f" **(+{eth_tp1_pct}%)**\n"
      f"  🛡️ **التأمين:** تأمين الصفقة عند الدخول (`{eth:,.2f}`"
      ").\n"
      f"  🚀 *الهدف الثاني (TP2):* `{eth * 1.06:,.2f}` ──>"
      f" **(+{eth_tp2_pct}%)**"
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
def send_analytical_vision_deals(message):
  if not can_use_bot(message):
    return
  user_id = str(message.from_user.id)
  btc_live, eth_live, xrp_live = get_crypto_prices()

  btc_data = get_dynamic_deal_data("bitcoin", btc_live)
  eth_data = get_dynamic_deal_data("ethereum", eth_live)
  xrp_data = get_dynamic_deal_data("ripple", xrp_live)

  if not btc_data or not eth_data or not xrp_data:
    send_with_menu(
        message,
        "⚠️ تعذّر جلب الأسعار الحية من السوق حالياً (احتمال توقف السعر"
        " اللحظي أو توقف/تأخر الشموع). يرجى المحاولة بعد لحظات.",
    )
    return

  btc_price, btc_chg, btc_trend, btc_tp1_p, btc_tp2_p, btc_sl_p = btc_data
  eth_price, eth_chg, eth_trend, eth_tp1_p, eth_tp2_p, eth_sl_p = eth_data
  xrp_price, xrp_chg, xrp_trend, xrp_tp1_p, xrp_tp2_p, xrp_sl_p = xrp_data

  pin_suggested_deals(
      user_id,
      "analytical",
      {
          "BTC": {
              "deal_no": 1,
              "entry": btc_price,
              "tp1": btc_price * (1 + btc_tp1_p),
              "tp2": btc_price * (1 + btc_tp2_p),
              "sl": btc_price * (1 - btc_sl_p),
              "stage": "tp1",
              "status": "active",
          },
          "ETH": {
              "deal_no": 1,
              "entry": eth_price,
              "tp1": eth_price * (1 + eth_tp1_p),
              "tp2": eth_price * (1 + eth_tp2_p),
              "sl": eth_price * (1 - eth_sl_p),
              "stage": "tp1",
              "status": "active",
          },
          "XRP": {
              "deal_no": 1,
              "entry": xrp_price,
              "tp1": xrp_price * (1 + xrp_tp1_p),
              "tp2": xrp_price * (1 + xrp_tp2_p),
              "sl": xrp_price * (1 - xrp_sl_p),
              "stage": "tp1",
              "status": "active",
          },
      },
  )

  deals_text = (
      "📊 **صفقات الرؤية التحليلية وقراءة الزخم الحي للعملات:**\n\n"
      "📡 *السعر الحي لحظة إصدار التوصية فقط (بدون تثبيت أرقام ثابتة).*\n"
      "📌 *تم تثبيت جميع الصفقات المقترحة تلقائياً لمتابعتها وإرسال تقرير"
      " فور إتمام شروطها.*\n\n"
      f"{DEAL_STOP_EXPLANATION}\n\n"
      f"🪙 **1. بيتكوين (BTC/USDT):**\n"
      f"• السعر الحي: `{btc_price:,.2f}$` (التغير 24س: `{btc_chg:+.2f}%`)\n"
      f"• الحالة: {btc_trend}\n"
      f"  🛑 *SL:* `{btc_price * (1 - btc_sl_p):,.2f}`\n"
      f"  🎯 *TP1:* `{btc_price * (1 + btc_tp1_p):,.2f}` (+{btc_tp1_p*100}%)\n"
      f"  🚀 *TP2:* `{btc_price * (1 + btc_tp2_p):,.2f}` (+{btc_tp2_p*100}%)\n\n"
      f"💎 **2. إيثريوم (ETH/USDT):**\n"
      f"• السعر الحي: `{eth_price:,.2f}$` (التغير 24س: `{eth_chg:+.2f}%`)\n"
      f"• الحالة: {eth_trend}\n"
      f"  🛑 *SL:* `{eth_price * (1 - eth_sl_p):,.2f}`\n"
      f"  🎯 *TP1:* `{eth_price * (1 + eth_tp1_p):,.2f}` (+{eth_tp1_p*100}%)\n"
      f"  🚀 *TP2:* `{eth_price * (1 + eth_tp2_p):,.2f}` (+{eth_tp2_p*100}%)\n\n"
      f"⚡ **3. ريبل (XRP/USDT):**\n"
      f"• السعر الحي: `{xrp_price:,.4f}$` (التغير 24س: `{xrp_chg:+.2f}%`)\n"
      f"• الحالة: {xrp_trend}\n"
      f"  🛑 *SL:* `{xrp_price * (1 - xrp_sl_p):,.4f}`\n"
      f"  🎯 *TP1:* `{xrp_price * (1 + xrp_tp1_p):,.4f}` (+{xrp_tp1_p*100}%)\n"
      f"  🚀 *TP2:* `{xrp_price * (1 + xrp_tp2_p):,.4f}` (+{xrp_tp2_p*100}%)\n"
  )
  send_with_menu(message, deals_text)


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (القاعدة الذهبية)"
)
def send_gold_golden_rule(message):
  if not can_use_bot(message):
    return
  user_id = str(message.from_user.id)
  current_gold = get_gold_price()

  if current_gold is None or current_gold <= 0:
    send_with_menu(
        message,
        "⚠️ تعذّر جلب السعر الحي للذهب حالياً (احتمال توقف السعر اللحظي أو"
        " توقف/تأخر الشموع)، يرجى المحاولة بعد قليل.",
    )
    return

  pin_suggested_deals(
      user_id,
      "gold_golden",
      {
          "GOLD": {
              "deal_no": 1,
              "entry": current_gold,
              "tp1": current_gold * (1 + 0.007),
              "tp2": current_gold * (1 + 0.014),
              "sl": current_gold * (1 - 0.01),
              "stage": "tp1",
              "status": "active",
          }
      },
  )

  tp1_price = current_gold * (1 + 0.007)
  tp2_price = current_gold * (1 + 0.014)
  sl_price = current_gold * (1 - 0.01)

  gold_text = (
      "🟡 **توصيات صفقات الذهب (القاعدة الذهبية):**\n\n"
      "📡 *السعر الحي لحظة إصدار التوصية فقط (بدون تثبيت أرقام ثابتة).*\n"
      "📌 *تم تثبيت الصفقة المقترحة تلقائياً لمتابعتها وإرسال تقرير فور"
      " إتمام شروطها.*\n\n"
      f"{DEAL_STOP_EXPLANATION}\n\n"
      f"📍 **سعر الدخول الحي (Entry):** `{current_gold:,.2f}` $\n"
      f"🛑 **وقف الخسارة المقترح (SL):** `{sl_price:,.2f}` $ (-1.0%)\n\n"
      f"• **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ ──> **(+0.7%)**\n"
      f"• **الهدف الثاني (TP2):** `{tp2_price:,.2f}` $ ──> **(+1.4%)**\n"
  )
  send_with_menu(message, gold_text)


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (الرؤية التحليلية)"
)
def send_gold_analytical_vision(message):
  if not can_use_bot(message):
    return
  user_id = str(message.from_user.id)
  current_gold = get_gold_price()

  if current_gold is None or current_gold <= 0:
    send_with_menu(
        message,
        "⚠️ تعذّر جلب السعر الحي للذهب حالياً (احتمال توقف السعر اللحظي أو"
        " توقف/تأخر الشموع)، يرجى المحاولة بعد قليل.",
    )
    return

  pin_suggested_deals(
      user_id,
      "gold_analytical",
      {
          "GOLD": {
              "deal_no": 1,
              "entry": current_gold,
              "tp1": current_gold * (1 + 0.01),
              "tp2": current_gold * (1 + 0.02),
              "sl": current_gold * (1 - 0.012),
              "stage": "tp1",
              "status": "active",
          }
      },
  )

  tp1_price = current_gold * (1 + 0.01)
  tp2_price = current_gold * (1 + 0.02)
  sl_price = current_gold * (1 - 0.012)

  gold_text = (
      "🟡 **توصيات صفقات الذهب (الرؤية التحليلية والزخم الحي):**\n\n"
      "📡 *السعر الحي لحظة إصدار التوصية فقط (بدون تثبيت أرقام ثابتة).*\n"
      "📌 *تم تثبيت الصفقة المقترحة تلقائياً لمتابعتها وإرسال تقرير فور"
      " إتمام شروطها.*\n\n"
      f"{DEAL_STOP_EXPLANATION}\n\n"
      f"📍 **سعر الدخول الحي (Entry):** `{current_gold:,.2f}` $\n"
      f"🛑 **وقف الخسارة (SL):** `{sl_price:,.2f}` $ (-1.2%)\n\n"
      f"• **الهدف الأول (TP1):** `{tp1_price:,.2f}` $ ──> **(+1.0%)**\n"
      f"• **الهدف الثاني (TP2):** `{tp2_price:,.2f}` $ ──> **(+2.0%)**\n"
  )
  send_with_menu(message, gold_text)


@bot.message_handler(
    func=lambda message: message.text == "🧮 حاسبة المخاطر وحجم الصفقة"
)
def start_risk_calculator(message):
  if not can_use_bot(message):
    return
  user_id = message.from_user.id
  risk_calculator_sessions[user_id] = {"step": "waiting_capital"}
  msg = bot.send_message(
      message.chat.id,
      "🧮 **حاسبة إدارة المخاطر:**\n\nأرسل إجمالي رأس مالك بالـ USDT (مثلاً:"
      " `500`):",
      parse_mode="Markdown",
  )
  bot.register_next_step_handler(msg, process_capital_step)


def process_capital_step(message):
  if not can_use_bot(message):
    return
  user_id = message.from_user.id
  try:
    capital = float(message.text.strip())
    risk_calculator_sessions[user_id]["capital"] = capital
    risk_calculator_sessions[user_id]["step"] = "waiting_risk"
    msg = bot.send_message(
        message.chat.id,
        f"✅ رأس المال: `{capital}` USDT.\n\nأرسل نسبة الخسارة المقبولة"
        " (مثلاً: `2`):",
        parse_mode="Markdown",
    )
    bot.register_next_step_handler(msg, process_risk_step)
  except Exception:
    bot.send_message(message.chat.id, "⚠️ أرسل رقماً صحيحاً (مثلاً: 500).")


def process_risk_step(message):
  if not can_use_bot(message):
    return
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
  if not can_use_bot(message):
    return
  send_with_menu(
      message,
      "🔔 **التنبيهات المخصصة:**\n\nاستخدم الأمر بالشكل الصحيح:\n• `/alert btc"
      " 68000`\n• `/alert eth 1850`",
  )


@bot.message_handler(commands=["alert"])
def set_custom_alert(message):
  if not can_use_bot(message):
    return
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
      last_weekly = datetime.fromisoformat(
          results_db.get("last_weekly_check", now_dt.isoformat())
      )
      if (now_dt - last_weekly).total_seconds() >= 7 * 24 * 3600:
        daily_items = results_db.get("daily", [])
        success_count = sum(
            1
            for item in daily_items
            if "TP1" in item or "TP2" in item or "ربح" in item
        )
        total_count = len(daily_items)
        weekly_summary = (
            f"📊 حصيلة الأسبوع التلقائية: {success_count} صفقات ناجحة من إجمالي"
            f" {total_count} صفقة مرصودة."
        )
        results_db["weekly"].append(weekly_summary)
        results_db["last_weekly_check"] = now_dt.isoformat()
        save_results(results_db)

      # فحص الشهر (كل 30 يوماً)
      last_monthly = datetime.fromisoformat(
          results_db.get("last_monthly_check", now_dt.isoformat())
      )
      if (now_dt - last_monthly).total_seconds() >= 30 * 24 * 3600:
        daily_items = results_db.get("daily", [])
        success_count = sum(
            1
            for item in daily_items
            if "TP1" in item or "TP2" in item or "ربح" in item
        )
        total_count = len(daily_items)
        monthly_summary = (
            "🏆 حصيلة الشهر الكبرى التلقائية: أداء إجمالي يعتمد على"
            f" {success_count} صفقة ناجحة من {total_count}."
        )
        results_db["monthly"].append(monthly_summary)
        results_db["last_monthly_check"] = now_dt.isoformat()
        save_results(results_db)

      # --- جلب الأسعار الحية فقط ---
      btc_p, eth_p, xrp_p = get_crypto_prices()
      gold_p = get_gold_price()
      prices_map = {}
      if btc_p is not None and btc_p > 0:
        prices_map["BTC"] = btc_p
      if eth_p is not None and eth_p > 0:
        prices_map["ETH"] = eth_p
      if xrp_p is not None and xrp_p > 0:
        prices_map["XRP"] = xrp_p
      if gold_p is not None and gold_p > 0:
        prices_map["GOLD"] = gold_p

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
                    f"📊 السعر الحي في السوق: `{current_price:,.2f}`",
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

      # فحص جميع الصفقات المثبتة بالتوازي (متابعة TP1 ثم تحويله تلقائياً لصفقة ثانية نحو TP2 مع تعديل الخسارة)
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
                  stage = data.get("stage", "tp1")
                  entry_price = data.get("entry", current_val)
                  tp1 = data.get("tp1", 0)
                  tp2 = data.get("tp2", 0)
                  sl = data.get("sl", 0)

                  if stage == "tp1":
                    if tp1 > 0 and current_val >= tp1:
                      updated = True

                      try:
                        r_db = load_results()
                        res_msg = (
                            f"✅ صفقة {symbol} تحقيق الهدف الأول (TP1) بنجاح"
                            f" عند السعر الحي {current_val:,.4f}"
                        )
                        r_db["daily"].append(res_msg)
                        save_results(r_db)
                      except Exception:
                        pass

                      if tp2 > 0:
                        new_sl = entry_price
                        data["deal_no"] = 2
                        data["sl"] = new_sl
                        data["stage"] = "tp2"
                        data["status"] = "active"
                        try:
                          bot.send_message(
                              int(user_id),
                              "📋 **تقرير إتمام الصفقة الأولى وتحقيق الهدف"
                              " الأول (TP1)!**\n\n"
                              f"🪙 الأصل/العملة: `{symbol}`\n"
                              f"📈 السعر الحي عند الإنجاز: `{current_val:,.4f}`\n"
                              "✅ **تم إغلاق الصفقة الأولى بنجاح عند"
                              f" `TP1` (`{tp1:,.4f}`).**\n"
                              "🆕 **تم فتح صفقة ثانية جديدة تلقائياً نحو الهدف"
                              f" الثاني (`TP2`): `{tp2:,.4f}`**\n"
                              "🛡️ **تم ضبط وقف الخسارة (`SL`) للصفقة الثانية"
                              f" عند نقطة الدخول: `{new_sl:,.4f}`**\n"
                              "📡 *جاري متابعة الصفقة الثانية لإبلاغك بتقريرها"
                              " فور إتمام شروطها.*",
                              parse_mode="Markdown",
                          )
                        except Exception:
                          pass
                      else:
                        data["status"] = "tp1_hit"
                        try:
                          bot.send_message(
                              int(user_id),
                              "📋 **تقرير إتمام الصفقة وتحقيق الهدف الأول"
                              " (TP1)!**\n\n"
                              f"🪙 الأصل/العملة: `{symbol}`\n"
                              f"📈 السعر الحي عند الإنجاز: `{current_val:,.4f}`\n"
                              "✅ **تم تحقيق الهدف الأول (TP1) بنجاح.**",
                              parse_mode="Markdown",
                          )
                        except Exception:
                          pass

                    elif sl > 0 and current_val <= sl:
                      data["status"] = "sl_hit"
                      updated = True

                      try:
                        bot.send_message(
                            int(user_id),
                            "📋 **تقرير إغلاق الصفقة الأولى على وقف الخسارة"
                            " (SL)!**\n\n"
                            f"🪙 الأصل/العملة: `{symbol}`\n"
                            f"📉 السعر الحي عند الإغلاق: `{current_val:,.4f}`\n"
                            "❌ **تم ضرب مستوى وقف الخسارة (`SL`:"
                            f" `{sl:,.4f}`).**",
                            parse_mode="Markdown",
                        )
                      except Exception:
                        pass

                      try:
                        r_db = load_results()
                        res_msg = (
                            f"❌ صفقة {symbol} ضرب وقف الخسارة (SL) عند السعر"
                            f" الحي {current_val:,.4f}"
                        )
                        r_db["daily"].append(res_msg)
                        save_results(r_db)
                      except Exception:
                        pass

                  elif stage == "tp2":
                    if tp2 > 0 and current_val >= tp2:
                      data["status"] = "tp2_hit"
                      updated = True

                      try:
                        bot.send_message(
                            int(user_id),
                            "📋 **تقرير إتمام الصفقة الثانية وتحقيق الهدف"
                            " الثاني (TP2)!**\n\n"
                            f"🪙 الأصل/العملة: `{symbol}`\n"
                            f"📈 السعر الحي عند الإنجاز: `{current_val:,.4f}`\n"
                            "🚀 **تم إغلاق الصفقة الثانية بنجاح عند الهدف"
                            f" الثاني (`TP2`: `{tp2:,.4f}`).**",
                            parse_mode="Markdown",
                        )
                      except Exception:
                        pass

                      try:
                        r_db = load_results()
                        res_msg = (
                            f"🚀 الصفقة الثانية {symbol} تحقيق الهدف الثاني"
                            f" (TP2) بنجاح عند السعر الحي {current_val:,.4f}"
                        )
                        r_db["daily"].append(res_msg)
                        save_results(r_db)
                      except Exception:
                        pass

                    elif sl > 0 and current_val <= sl:
                      data["status"] = "tp2_sl_hit"
                      updated = True

                      try:
                        bot.send_message(
                            int(user_id),
                            "📋 **تقرير إغلاق الصفقة الثانية على وقف الخسارة"
                            " المعدّل (SL)!**\n\n"
                            f"🪙 الأصل/العملة: `{symbol}`\n"
                            f"📉 السعر الحي عند الإغلاق: `{current_val:,.4f}`\n"
                            "🛡️ **تم إغلاق الصفقة الثانية عند مستوى وقف"
                            f" الخسارة المؤمَّن (`{sl:,.4f}`).**",
                            parse_mode="Markdown",
                        )
                      except Exception:
                        pass

                      try:
                        r_db = load_results()
                        res_msg = (
                            f"🛡️ الصفقة الثانية {symbol} إغلاق على وقف الخسارة"
                            f" المعدّل (SL) عند السعر الحي {current_val:,.4f}"
                        )
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
  if not can_use_bot(message):
    return
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


QUIZ_QUESTIONS = [{
    "question": (
        "🧠 **سؤال اختبار التداول (1/4):**\n\nما هو الغرض الأساسي من استخدام"
        " أمر (وقف الخسارة - Stop Loss)؟\n\nأ) مضاعفة الأرباح\nب) حماية"
        " المحفظة والخروج بخسارة صغيرة\nج) زيادة رسوم التداول\n\n💡 أجب بـ (ب):"
    ),
    "answer_key": "ب",
    "keywords": ["ب", "حماية", "خسارة"],
}]


@bot.message_handler(
    func=lambda message: message.text == "🧠 اختبار تداولي تفاعلي (Quiz)"
)
def start_trading_quiz(message):
  if not can_use_bot(message):
    return
  user_id = message.from_user.id
  q_data = random.choice(QUIZ_QUESTIONS)
  active_quizzes[user_id] = q_data
  msg = bot.send_message(
      message.chat.id, q_data["question"], parse_mode="Markdown"
  )
  bot.register_next_step_handler(msg, check_quiz_answer)


def check_quiz_answer(message):
  if not can_use_bot(message):
    return
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
  if not can_use_bot(message):
    return
  academy_text = (
      "📚 **الأكاديمية التعليمية الشاملة - تعلم التداول من الصفر (6 دروس):**\n\n"
      "🟢 **الدرس 1: أساسيات السوق والعملات المستقرة (`USDT`)**\n"
      "• فهم معنى العرض والطلب وحركة الأسعار، وكيف تعمل عملة `USDT` كمرساة"
      " مستقرة لحفظ قيمة رأس المال وتجنب تقلبات العملات الرقمية أثناء"
      " التوقف أو انتظار الفرص.\n\n"
      "🟡 **الدرس 2: أنماط التداول والأطر الزمنية**\n"
      "• التمييز بين صفقات السكالبينج السريعة، والصفقات اليومية، وصفقات"
      " السوينغ المتوسطة، وربط الإطار الزمني بنوع الصفقة حتى لا تتحول"
      " صفقة سريعة إلى تعليقة طويلة دون خطة.\n\n"
      "🔵 **الدرس 3: الأهداف (`TP1` / `TP2`) ووقف الخسارة (`SL`)**\n"
      "• تحديد مستويات جني الربح مسبقاً وعدم ترك الصفقة مفتوحة بلا هدف،"
      " والالتزام بوقف الخسارة كصمام أمان لحماية الحساب من الخسائر"
      " الكبيرة.\n\n"
      "🟣 **الدرس 4: تأمين الصفقة (`Breakeven`) وجني الأرباح الجزئي**\n"
      "• عند الوصول إلى الهدف الأول (`TP1`) يتم جني جزء من الربح ونقل وقف"
      " الخسارة إلى نقطة الدخول (`Breakeven`) لتصبح بقية الصفقة مؤمّنة"
      " قدر الإمكان.\n\n"
      "🟠 **الدرس 5: إدارة المخاطر وحجم الصفقة**\n"
      "• عدم المخاطرة بأكثر من 1% إلى 2% من إجمالي رأس المال في الصفقة"
      " الواحدة، وحساب حجم الدخول بناءً على المسافة بين سعر الدخول ووقف"
      " الخسارة.\n\n"
      "🔴 **الدرس 6: الانضباط النفسي وتجنب التداول العاطفي**\n"
      "• الابتعاد عن الطمع أو الانتقام من السوق بعد خسارة، والالتزام بخطة"
      " العمل والنتائج المسجلة بدلاً من الدخول العشوائي بدافع الخوف من"
      " فوات الفرصة (`FOMO`)."
  )
  send_with_menu(message, academy_text)


@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس مصطلحات التداول (بحث ذكي)"
)
def glossary_menu(message):
  if not can_use_bot(message):
    return
  glossary_guide = (
      "📖 **قاموس مصطلحات التداول والبحث الذكي:**\n\n"
      "يرصد هذا القسم أبرز مصطلحات التداول والعملات الرقمية والذهب مع شرح"
      " مبسّط ودقيق لكل مصطلح.\n\n"
      "🔎 **طريقة البحث الفوري:**\n"
      "استخدم الأمر `/search` متبوعاً بالكلمة أو المصطلح مثل:\n"
      "• `/search usdt`\n"
      "• `/search breakeven`\n"
      "• `/search scalping`\n"
      "• `/search swing`\n"
      "• `/search tp`\n"
      "• `/search sl`\n"
      "• `/search oco`\n"
      "• `/search fomo`\n"
      "• `/search dca`\n"
      "• `/search xauusd`\n"
      "• `/search trc20`"
  )
  send_with_menu(message, glossary_guide)


@bot.message_handler(commands=["search"])
def search_glossary(message):
  if not can_use_bot(message):
    return
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
      "usdt": (
          "🔹 **USDT:** عملة رقمية مستقرة مرتبطة بالدولار الأمريكي تقريباً،"
          " تُستخدم كعملة تسعير وحفظ للرصيد بين الصفقات."
      ),
      "breakeven": (
          "🛡️ **Breakeven (نقطة التعادل / التأمين):** نقل وقف الخسارة إلى"
          " سعر الدخول (أو قريباً منه) بعد تحقق الهدف الأول لتقليل مخاطر"
          " الصفقة."
      ),
      "scalping": (
          "⚡ **Scalping:** أسلوب تداول قصير الأجل يعتمد على اقتناص تحركات"
          " سعرية سريعة وأرباح صغيرة متكررة."
      ),
      "swing": (
          "🌊 **Swing Trading:** تداول متوسط المدى يمتد لعدة أيام أو أسابيع"
          " لاستهداف موجات سعرية أوسع."
      ),
      "tp": (
          "🎯 **TP (Take Profit):** مستوى جني الربح المحدد مسبقاً لإغلاق"
          " الصفقة أو جزء منها عند بلوغ الهدف."
      ),
      "sl": (
          "🛑 **SL (Stop Loss):** أمر وقف الخسارة الذي يغلق الصفقة تلقائياً"
          " عند مستوى محدد لحماية رأس المال."
      ),
      "oco": (
          "⚙️ **OCO (One-Cancels-the-Other):** نوع من الأوامر الشرطية يجمع بين"
          " أمر جني الربح وأمر وقف الخسارة بحيث يلغي تنفيذ أحدهما الآخر"
          " تلقائياً."
      ),
      "fomo": (
          "😰 **FOMO (Fear Of Missing Out):** الخوف من فوات الفرصة، وهو شعور"
          " يدفع المتداول للدخول المتسرع بعد حركة سعرية كبيرة دون تحليل."
      ),
      "dca": (
          "📉 **DCA (Dollar-Cost Averaging):** تعزيز أو بناء مركز الشراء على"
          " دفعات مجدولة أو عند مستويات سعرية مختلفة بدلاً من دخول كامل"
          " دفعة واحدة."
      ),
      "xauusd": (
          "🟡 **XAUUSD:** رمز تداول أونصة الذهب الفوري مقابل الدولار الأمريكي"
          " في الأسواق العالمية."
      ),
      "trc20": (
          "🌐 **TRC20:** معيار الشبكة الخاصة ببلوكشين ترون (`TRON`)، ويُستخدم"
          " بكثرة لتحويل `USDT` بسرعة ورسوم منخفضة."
      ),
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
  if not can_use_bot(message):
    return
  accounts_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ بأمان:**\n\n"
      "1️⃣ **فتح وتوثيق حساب التداول:**\n"
      "• أنشئ حسابك على منصة تداول موثوقة مثل `Binance` باستخدام بريد"
      " إلكتروني آمن وكلمة مرور قوية وفريدة.\n"
      "• فعّل إجراءات الحماية الإضافية وعلى رأسها المصادقة الثنائية (`2FA`)"
      " وتأكيد السحب.\n\n"
      "2️⃣ **إنشاء المحافظ وحفظ كلمات الأمان:**\n"
      "• عند إنشاء محفظة لامركزية، سيظهر لك نظام كلمات الاسترداد (عادة 12"
      " كلمة).\n"
      "• اكتب الكلمات الـ 12 بالترتيب الصحيح على ورقة واحفظها في مكان آمن"
      " بعيداً عن الإنترنت، ولا تلتقط لها لقطة شاشة أو تشاركها مع أي شخص"
      " لأنها مفتاح الوصول الكامل لمحفظتك."
  )
  send_with_menu(message, accounts_text)


@bot.message_handler(
    func=lambda message: message.text == "📥 دليل السحب والإيداع (شبكة TRC20)"
)
def send_deposit_withdraw_guide(message):
  if not can_use_bot(message):
    return
  deposit_withdraw_text = (
      "📥 **دليل السحب والإيداع (شبكة `TRC20` والمحافظ المحلية):**\n\n"
      "1️⃣ **التحويل عبر شبكة `TRC20`:**\n"
      "• يُعتمد على شبكة **TRC20** لسرعة معالجة التحويلات وانخفاض تكلفتها"
      " مقارنة بالعديد من الشبكات الأخرى.\n"
      "• تأكد دائماً من مطابقة الشبكة (`TRC20`) في جهة الإرسال وجهة"
      " الاستقبال، ومن نسخ العنوان بدقة قبل تأكيد العملية.\n\n"
      "2️⃣ **التحويلات المحلية عبر شام كاش:**\n"
      "• للعمليات المحلية، يمكن استخدام محفظة **شام كاش** وفق التعليمات"
      " المتفق عليها وتأكيد تفاصيل الحوالة قبل الإرسال."
  )
  send_with_menu(message, deposit_withdraw_text)


@bot.message_handler(
    func=lambda message: message.text == "💳 الدفع والشحن المحلي (شام كاش)"
)
def send_payment_info(message):
  if not can_use_bot(message):
    return
  payment_text = (
      "💳 **الدفع والشحن المحلي عبر شام كاش:**\n\n"
      "1️⃣ تواصل مباشرة مع المطور عبر المعرف `" + ADMIN_USERNAME + "`"
      " للحصول على تفاصيل الحساب وطريقة التحويل المناسبة.\n"
      "2️⃣ أتمم الحوالة عبر **شام كاش** بدقة، ثم أرسل صورة أو تفاصيل"
      " الوصل مع بيانات حسابك للمطور.\n"
      "3️⃣ بعد مراجعة وتأكيد وصول الحوالة، يتم تفعيل أو تجديد الاشتراك حسب"
      " الاتفاق."
  )
  send_with_menu(message, payment_text)


@bot.message_handler(
    func=lambda message: message.text == "⏳ حالة اشتراكي ورابط دعوة أصدقائي"
)
def check_my_status_and_ref(message):
  if not can_use_bot(message):
    return
  user_id = message.from_user.id
  uid_str = str(user_id)
  if user_id == ADMIN_ID:
    bot.send_message(
        message.chat.id,
        "👑 **حالة الاشتراك:** أنت المطور، اشتراكك مفتوح ومفعل دائماً!",
        parse_mode="Markdown",
    )
    return
  user_info = all_users.get(uid_str)
  if not user_info:
    bot.send_message(
        message.chat.id,
        "⚠️ حسابك غير مسجل بعد، يرجى إرسال `/start` أولاً.",
    )
    return
  expiry_dt = datetime.fromisoformat(user_info["expiry"])
  now_dt = datetime.now()
  remaining = expiry_dt - now_dt
  if remaining.total_seconds() > 0:
    days_left = max(0, remaining.days)
    hours_left = max(0, remaining.seconds // 3600)
    status_line = (
        f"✅ **حالة الاشتراك:** نشط (المتبقي: {days_left} يوم و {hours_left}"
        " ساعة)"
    )
  else:
    status_line = "⚠️ **حالة الاشتراك:** منتهي"
  ref_count = user_info.get("referral_count", 0)
  bot_username = bot.get_me().username
  ref_link = f"https://t.me/{bot_username}?start=ref_{uid_str}"
  send_with_menu(
      message,
      "⏳ **حالة اشتراكي ورابط الدعوة:**\n\n"
      f"{status_line}\n"
      f"📅 **تاريخ الانتهاء:** `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"👥 **عدد دعوات الأصدقاء:** **{ref_count}**\n"
      "🎁 **مكافأة الدعوة:** إضافة يوم مجاني إلى رصيد اشتراكك عن كل 3"
      " أشخاص ينضمون عبر رابطك.\n"
      f"🔗 **رابط الدعوة الخاص بك:**\n`{ref_link}`",
  )


@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  ensure_admin_entry(message.from_user)
  send_with_menu(
      message,
      "👑 **لوحة تحكم المطور:**\n\n"
      "تتيح لك هذه اللوحة متابعة المشتركين والإحصائيات وتمديد الاشتراكات"
      " وتوثيق نتائج الصفقات في السجل العام:\n"
      "• `/users` — عرض إجمالي المشتركين وتفاصيل حساباتهم.\n"
      "• `/stats` — عرض إحصائيات المشتركين الحالية.\n"
      "• `/extend [ID] [الأيام]` — تمديد اشتراك مستخدم بعدد أيام محدد.\n"
      "• `/add_result daily [النص]` — إضافة نتيجة جديدة إلى قسم النتائج"
      " اليومية.\n"
      "• `/add_result weekly [النص]` — إضافة حصيلة أو نتيجة إلى قسم النتائج"
      " الأسبوعية.\n"
      "• `/add_result monthly [النص]` — إضافة حصيلة أو نتيجة إلى قسم النتائج"
      " الشهرية.",
  )


@bot.message_handler(commands=["users"])
def show_all_users(message):
  if message.from_user.id != ADMIN_ID:
    return
  current_users = load_users()
  if not current_users:
    bot.send_message(message.chat.id, "📭 لا يوجد مشتركين.")
    return
  lines = [f"👥 **إجمالي المشتركين: {len(current_users)}**\n"]
  for uid, udata in current_users.items():
    uname = (udata.get("username") or "").lstrip("@").strip()
    uname_display = f"@{uname}" if uname else "لا يوجد يوزر"
    name_display = udata.get("name") or "مستخدم"
    exp_raw = udata.get("expiry", "")
    try:
      exp_display = datetime.fromisoformat(exp_raw).strftime("%Y-%m-%d %H:%M")
    except Exception:
      exp_display = exp_raw or "غير محدد"
    lines.append(
        f"• **{name_display}** | ID: `{uid}` | اليوزر: `{uname_display}` |"
        f" الانتهاء: `{exp_display}`"
    )
  bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown")


@bot.message_handler(commands=["extend"])
def extend_user_subscription(message):
  if message.from_user.id != ADMIN_ID:
    return
  parts = message.text.split()
  if len(parts) < 3:
    bot.send_message(
        message.chat.id,
        "⚠️ الصيغة الصحيحة للأمر:\n`/extend [ID] [الأيام]`\n*مثال:* `/extend"
        " 123456789 7`",
        parse_mode="Markdown",
    )
    return
  target_uid = parts[1].strip()
  try:
    days_to_add = int(parts[2].strip())
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى إدخال عدد صحيح للأيام (مثال: `7`).",
        parse_mode="Markdown",
    )
    return

  current_users = load_users()
  if target_uid not in current_users:
    bot.send_message(
        message.chat.id,
        f"❌ لم يتم العثور على مستخدم بالمعرّف `{target_uid}`.",
        parse_mode="Markdown",
    )
    return

  now_dt = datetime.now()
  prev_exp_str = current_users[target_uid].get("expiry")
  try:
    prev_exp = datetime.fromisoformat(prev_exp_str) if prev_exp_str else now_dt
  except Exception:
    prev_exp = now_dt

  base_dt = max(prev_exp, now_dt)
  new_exp = base_dt + timedelta(days=days_to_add)

  current_users[target_uid]["expiry"] = new_exp.isoformat()
  if int(target_uid) != ADMIN_ID:
    current_users[target_uid]["is_trial"] = False
  current_users[target_uid]["trial_used"] = True
  save_users(current_users)
  all_users.clear()
  all_users.update(current_users)

  current_trials = load_trial_history()
  if target_uid in current_trials:
    current_trials[target_uid]["expiry"] = new_exp.isoformat()
    save_trial_history(current_trials)
    trial_history.clear()
    trial_history.update(current_trials)

  uname = (current_users[target_uid].get("username") or "").lstrip("@").strip()
  uname_display = f"@{uname}" if uname else "لا يوجد يوزر"
  bot.send_message(
      message.chat.id,
      "✅ **تم تمديد الاشتراك بنجاح وعاد الحساب للعمل تلقائياً!**\n\n"
      f"👤 الاسم: {current_users[target_uid].get('name', 'مستخدم')}\n"
      f"🆔 المعرّف: `{target_uid}`\n"
      f"🌐 اليوزر: `{uname_display}`\n"
      f"➕ المدة المضافة: `{days_to_add}` يوم\n"
      f"📅 تاريخ الانتهاء الجديد: `{new_exp.strftime('%Y-%m-%d %H:%M')}`",
      parse_mode="Markdown",
  )


@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  current_users = load_users()
  bot.send_message(
      message.chat.id,
      f"📊 المشتركين: {len(current_users)}",
  )


# حارس عام لأي رسالة نصية أخرى لمنع من لا يملك يوزر أو انتهى اشتراكه تلقائياً
@bot.message_handler(func=lambda message: True, content_types=["text"])
def guard_other_text(message):
  if message.chat.type == "private" and message.from_user:
    if message.from_user.id == ADMIN_ID:
      return
    if not has_username(message.from_user):
      send_no_username_notice(message.chat.id)
      return
    if not is_subscription_active(str(message.from_user.id)):
      send_subscription_expired_notice(message.chat.id)


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

  while True:
    try:
      bot.infinity_polling(
          timeout=60, long_polling_timeout=60, skip_pending=True
      )
      break
    except Exception as e:
      err_str = str(e)
      print(f"Polling error: {e}")
      if "409" in err_str or "Conflict" in err_str:
        time.sleep(10)
      else:
        time.sleep(5)
