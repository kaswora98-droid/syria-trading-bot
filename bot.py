import json
import os
import threading
import time
from datetime import datetime, timedelta
from flask import Flask
import requests
import telebot
from telebot import types

# ==========================================
# 1. إعدادات البوت والمطور (ثوابت النظام)
# ==========================================
API_TOKEN = "8928709566:AAGmQGGme_fXQvSwYR30Uii3iR4BzjpEyrk"
ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

USERS_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
RESULTS_FILE = "trading_results.json"
TRACKED_DEALS_FILE = "active_tracked_deals.json"

bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")
app = Flask(__name__)

# حالة المستخدمين المؤقتة للعمليات التفاعلية
user_states = {}
pending_groups = {}


# ==========================================
# 2. إدارة ملفات البيانات المحلية
# ==========================================
def load_json(filename, default_value):
  if not os.path.exists(filename):
    with open(filename, "w", encoding="utf-8") as f:
      json.dump(default_value, f, ensure_ascii=False, indent=2)
    return default_value
  try:
    with open(filename, "r", encoding="utf-8") as f:
      return json.load(f)
  except Exception:
    return default_value


def save_json(filename, data):
  try:
    with open(filename, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=2)
  except Exception as e:
    print(f"Error saving {filename}: {e}")


def load_users():
  return load_json(USERS_FILE, {})


def save_users(data):
  save_json(USERS_FILE, data)


def load_groups():
  return load_json(GROUPS_FILE, {})


def save_groups(data):
  save_json(GROUPS_FILE, data)


def load_results():
  default_res = {"daily": [], "weekly": [], "monthly": []}
  data = load_json(RESULTS_FILE, default_res)
  for key in ("daily", "weekly", "monthly"):
    if key not in data or not isinstance(data[key], list):
      data[key] = []
  return data


def save_results(data):
  save_json(RESULTS_FILE, data)


def load_tracked_deals():
  return load_json(TRACKED_DEALS_FILE, [])


def save_tracked_deals(data):
  save_json(TRACKED_DEALS_FILE, data)


# ==========================================
# 3. التحقق من اليوزر والاشتراك والصلاحيات
# ==========================================
def has_username(user):
  if not user:
    return False
  uname = (user.username or "").strip()
  return len(uname) > 0


def deny_no_username(chat_id):
  bot.send_message(
      chat_id,
      "🚫 **عذراً، لا يُسمح باستخدام البوت بدون يوزر (Username).**\n\n"
      "يرجى وضع يوزر خاص بحسابك على تيليجرام (مثال: `@username`) من"
      " إعدادات الحساب أولاً، ثم أرسل `/start` للمتابعة.",
  )


def ensure_admin_recorded(user):
  users = load_users()
  uid_str = str(ADMIN_ID)
  if uid_str not in users:
    users[uid_str] = {
        "name": user.first_name or "المطور",
        "username": user.username or ADMIN_USERNAME.lstrip("@"),
        "role": "admin",
        "trial_used": True,
        "joined_at": datetime.now().isoformat(),
        "expires_at": None,
    }
    save_users(users)
  else:
    updated = False
    if users[uid_str].get("role") != "admin":
      users[uid_str]["role"] = "admin"
      updated = True
    if user.username and users[uid_str].get("username") != user.username:
      users[uid_str]["username"] = user.username
      updated = True
    if updated:
      save_users(users)


def is_subscription_active(user_id):
  if user_id == ADMIN_ID:
    return True
  users = load_users()
  u = users.get(str(user_id))
  if not u:
    return False
  exp_str = u.get("expires_at")
  if not exp_str:
    return False
  try:
    exp_dt = datetime.fromisoformat(exp_str)
    return datetime.now() < exp_dt
  except Exception:
    return False


def check_access(message):
  user = message.from_user
  if not user:
    return False
  if user.id == ADMIN_ID:
    ensure_admin_recorded(user)
    return True
  if not has_username(user):
    deny_no_username(message.chat.id)
    return False
  if not is_subscription_active(user.id):
    bot.send_message(
        message.chat.id,
        f"⚠️ اشتراكك منتهٍ أو غير مفعل. تواصل مع المطور {ADMIN_USERNAME}"
        " للتجديد.",
    )
    return False
  return True


# ==========================================
# 4. جلب الأسعار الحية فقط (بدون أرقام ثابتة)
# ==========================================
def get_crypto_prices():
  """جلب الأسعار الحية للعملات فقط (BTC, ETH, XRP) دون إرجاع قيم ثابتة."""
  prices = {}

  # المصدر الأول: CoinGecko
  try:
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum,ripple&vs_currencies=usd"
    )
    resp = requests.get(url, timeout=8)
    if resp.status_code == 200:
      data = resp.json()
      if data.get("bitcoin", {}).get("usd"):
        prices["BTC"] = float(data["bitcoin"]["usd"])
      if data.get("ethereum", {}).get("usd"):
        prices["ETH"] = float(data["ethereum"]["usd"])
      if data.get("ripple", {}).get("usd"):
        prices["XRP"] = float(data["ripple"]["usd"])
  except Exception:
    pass

  # المصدر الثاني: Binance لأي عملة لم تُجلب بعد
  binance_map = {
      "BTC": "BTCUSDT",
      "ETH": "ETHUSDT",
      "XRP": "XRPUSDT",
  }
  for sym, pair in binance_map.items():
    if sym not in prices or prices[sym] is None or prices[sym] <= 0:
      try:
        r = requests.get(
            f"https://api.binance.com/api/v3/ticker/price?symbol={pair}",
            timeout=6,
        )
        if r.status_code == 200:
          val = float(r.json().get("price", 0))
          if val > 0:
            prices[sym] = val
      except Exception:
        pass

  return prices


def get_gold_price():
  """جلب السعر الحي للذهب (XAU/USD) فقط؛ يُرجع None عند تعذر السعر الحي."""
  headers = {"User-Agent": "Mozilla/5.0"}

  # المصدر الأول: goldprice.org
  try:
    resp = requests.get(
        "https://data-asg.goldprice.org/dbXRates/USD",
        headers=headers,
        timeout=8,
    )
    if resp.status_code == 200:
      data = resp.json()
      for item in data.get("items", []):
        if item.get("curr") == "USD":
          xau = item.get("xauPrice")
          if xau and float(xau) > 0:
            return round(float(xau), 2)
  except Exception:
    pass

  # المصدر الثاني: مصدر حي احتياطي
  try:
    resp = requests.get("https://open.er-api.com/v6/latest/XAU", timeout=8)
    if resp.status_code == 200:
      usd_val = resp.json().get("rates", {}).get("USD")
      if usd_val and float(usd_val) > 0:
        return round(float(usd_val), 2)
  except Exception:
    pass

  return None


def get_dynamic_deal_data(symbol_key, live_price):
  """حساب مستويات الدخول والوقف والأهداف بناءً على السعر الحي فقط."""
  if live_price is None or float(live_price) <= 0:
    return None

  p = float(live_price)

  if symbol_key == "XRP":
    decimals = 4
    sl = round(p * (1 - 0.012), decimals)
    tp1 = round(p * (1 + 0.008), decimals)
    tp2 = round(p * (1 + 0.015), decimals)
    return {
        "pair": "XRP/USDT",
        "entry": round(p, decimals),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp1_pct": "+0.8%",
        "tp2_pct": "+1.5%",
        "insurance": f"جني 50% ونقل وقف الخسارة لسعر الدخول ({round(p, decimals)}).",
    }

  if symbol_key == "BTC":
    decimals = 2
    sl = round(p * (1 - 0.012), decimals)
    tp1 = round(p * (1 + 0.012), decimals)
    tp2 = round(p * (1 + 0.025), decimals)
    return {
        "pair": "BTC/USDT",
        "entry": round(p, decimals),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp1_pct": "+1.2%",
        "tp2_pct": "+2.5%",
        "insurance": (
            f"جني نصف الربح وحرك وقف الخسارة لنقطة الدخول ({round(p, decimals):,.2f})."
        ),
    }

  if symbol_key == "ETH":
    decimals = 2
    sl = round(p * (1 - 0.012), decimals)
    tp1 = round(p * (1 + 0.030), decimals)
    tp2 = round(p * (1 + 0.060), decimals)
    return {
        "pair": "ETH/USDT",
        "entry": round(p, decimals),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp1_pct": "+3.0%",
        "tp2_pct": "+6.0%",
        "insurance": f"تأمين الصفقة عند الدخول ({round(p, decimals):,.2f}).",
    }

  if symbol_key == "XAU":
    decimals = 2
    sl = round(p * (1 - 0.012), decimals)
    tp1 = round(p * (1 + 0.010), decimals)
    tp2 = round(p * (1 + 0.020), decimals)
    return {
        "pair": "XAU/USD",
        "entry": round(p, decimals),
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp1_pct": "+1.0%",
        "tp2_pct": "+2.0%",
        "insurance": f"تأمين الصفقة عند الدخول ({round(p, decimals):,.2f} $).",
    }

  return None


def fmt_num(val, is_crypto_large=False):
  if is_crypto_large:
    return f"{val:,.2f}"
  return f"{val}"


def register_tracked_deal(chat_id, deal_type, deal_info):
  """تسجيل صفقة مبنية على سعر حي فقط لمتابعتها في الخلفية."""
  if not deal_info:
    return
  deals = load_tracked_deals()
  deals.append({
      "chat_id": chat_id,
      "type": deal_type,
      "pair": deal_info["pair"],
      "entry": deal_info["entry"],
      "sl": deal_info["sl"],
      "tp1": deal_info["tp1"],
      "tp2": deal_info["tp2"],
      "tp1_hit": False,
      "tp2_hit": False,
      "sl_hit": False,
      "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
  })
  save_tracked_deals(deals)


def append_daily_result(text_line):
  res = load_results()
  now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
  res["daily"].append(f"[{now_str}] {text_line}")
  save_results(res)


# ==========================================
# 5. القوائم والأزرار الرئيسية
# ==========================================
def main_menu_keyboard(user_id=None):
  kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  kb.add(
      types.KeyboardButton("📊 صفقات العملات (القاعدة الذهبية)"),
      types.KeyboardButton("🟡 توصيات صفقات الذهب"),
  )
  kb.add(
      types.KeyboardButton(
          "📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)"
      ),
      types.KeyboardButton("🛡️ إدارة المخاطر وحاسبة العقود"),
  )
  kb.add(
      types.KeyboardButton("📢 ربط البوت بقناة / مجموعة"),
      types.KeyboardButton("ℹ️ معلومات الاشتراك والدعم"),
  )
  if user_id == ADMIN_ID:
    kb.add(types.KeyboardButton("🛠️ لوحة تحكم المطور"))
  return kb


# ==========================================
# 6. الأوامر ومعالجات الرسائل
# ==========================================
@bot.message_handler(commands=["start"])
def send_welcome(message):
  user = message.from_user
  uid = user.id
  uid_str = str(uid)
  first_name = user.first_name or "مستخدم"
  username = (user.username or "").strip()

  # حساب المطور دائم مباشرة دون رسالة فترة تجريبية
  if uid == ADMIN_ID:
    ensure_admin_recorded(user)
    text = (
        "👑 أهلاً بك يا مهندس أحمد! حساب المطور الدائم جاهز بكامل ميزاته.\n"
        "اختر ما تحتاجه من القائمة الرئيسية:"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard(uid))
    return

  # منع أي مستخدم لا يملك يوزر تلقائياً
  if not has_username(user):
    deny_no_username(message.chat.id)
    return

  users = load_users()
  if uid_str not in users:
    exp_dt = datetime.now() + timedelta(days=3)
    users[uid_str] = {
        "name": first_name,
        "username": username,
        "trial_used": True,
        "joined_at": datetime.now().isoformat(),
        "expires_at": exp_dt.isoformat(),
    }
    save_users(users)

    try:
      admin_msg = (
          "🔔 **مشترك جديد انضم إلى البوت!**\n"
          f"👤 الاسم: {first_name}\n"
          f"🆔 المعرف (ID): `{uid}`\n"
          f"🌐 اليوزر: @{username}\n"
          f"👥 إجمالي المشتركين الآن: {len(users)}"
      )
      bot.send_message(ADMIN_ID, admin_msg)
    except Exception:
      pass

    welcome_text = (
        "🎉 أهلاً بك في بوت التداول الذكي والشامل! 🤖\n\n"
        "🎁 تم تفعيل فترة تجريبية مجانية لمدة 3 أيام لحسابك بنجاح.\n"
        "اختر ما تحتاجه من الأزرار أدناه:"
    )
    bot.send_message(
        message.chat.id, welcome_text, reply_markup=main_menu_keyboard(uid)
    )
    return

  # تحديث اليوزر أو الاسم في السجل إذا تغير
  if users[uid_str].get("username") != username or users[uid_str].get(
      "name"
  ) != first_name:
    users[uid_str]["username"] = username
    users[uid_str]["name"] = first_name
    save_users(users)

  if is_subscription_active(uid):
    exp_dt = datetime.fromisoformat(users[uid_str]["expires_at"])
    rem = exp_dt - datetime.now()
    days_left = max(0, rem.days)
    hours_left = max(0, rem.seconds // 3600)
    text = (
        f"👋 أهلاً بك مجدداً يا **{first_name}** (@{username})!\n"
        f"⏳ المتبقي من اشتراكك: **{days_left}** يوم و **{hours_left}** ساعة.\n"
        "اختر ما تحتاجه من الأزرار أدناه:"
    )
  else:
    text = (
        f"👋 أهلاً بك مجدداً يا **{first_name}** (@{username}).\n"
        "⚠️ انتهت الفترة التجريبية/الاشتراك الخاص بحسابك ولن يتم تجديدها"
        " تلقائياً.\n"
        f"📩 للتواصل وتفعيل الاشتراك: {ADMIN_USERNAME}"
    )

  bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard(uid))


@bot.message_handler(
    func=lambda m: m.text == "📊 صفقات العملات (القاعدة الذهبية)"
)
def handle_crypto_deals(message):
  if not check_access(message):
    return

  wait_msg = bot.send_message(
      message.chat.id, "⏳ جاري جلب الأسعار الحية للعملات..."
  )
  prices = get_crypto_prices()

  xrp_deal = get_dynamic_deal_data("XRP", prices.get("XRP"))
  btc_deal = get_dynamic_deal_data("BTC", prices.get("BTC"))
  eth_deal = get_dynamic_deal_data("ETH", prices.get("ETH"))

  try:
    bot.delete_message(message.chat.id, wait_msg.message_id)
  except Exception:
    pass

  if not xrp_deal and not btc_deal and not eth_deal:
    bot.send_message(
        message.chat.id,
        "⚠️ تعذّر جلب الأسعار الحية للعملات حالياً، يرجى المحاولة بعد قليل.",
    )
    return

  lines = [
      "📊 **صفقات القاعدة الذهبية للعملات (النسب الثابتة وإدارة المخاطر - بالسعر الحي):**\n",
      "📡 *يتم الاعتماد على السعر الحي لحظة إصدار التوصية دون تثبيت أرقام ثابتة.*\n",
  ]

  if xrp_deal:
    register_tracked_deal(message.chat.id, "crypto_scalp", xrp_deal)
    lines.append(
        "⚡ **1. صفقات السكالبينج للعملات:**\n"
        f"• العملة: {xrp_deal['pair']} (سعر الدخول الحي: {xrp_deal['entry']})\n"
        f"  🛑 وقف الخسارة (SL): {xrp_deal['sl']} (-1.2%)\n"
        f"  🎯 الهدف الأول (TP1): {xrp_deal['tp1']} ──> ({xrp_deal['tp1_pct']})\n"
        f"  🛡️ التأمين: {xrp_deal['insurance']}\n"
        f"  🚀 الهدف الثاني (TP2): {xrp_deal['tp2']} ──> ({xrp_deal['tp2_pct']})\n"
    )
  else:
    lines.append(
        "⚡ **1. صفقات السكالبينج للعملات (XRP/USDT):** ⚠️ السعر الحي غير متاح"
        " حالياً.\n"
    )

  if btc_deal:
    register_tracked_deal(message.chat.id, "crypto_daily", btc_deal)
    lines.append(
        "📅 **2. الصفقات اليومية للعملات:**\n"
        f"• العملة: {btc_deal['pair']} (سعر الدخول الحي:"
        f" {fmt_num(btc_deal['entry'], True)})\n"
        f"  🛑 وقف الخسارة (SL): {fmt_num(btc_deal['sl'], True)} (-1.2%)\n"
        f"  🎯 الهدف الأول (TP1): {fmt_num(btc_deal['tp1'], True)} ──>"
        f" ({btc_deal['tp1_pct']})\n"
        f"  🛡️ التأمين: {btc_deal['insurance']}\n"
        f"  🚀 الهدف الثاني (TP2): {fmt_num(btc_deal['tp2'], True)} ──>"
        f" ({btc_deal['tp2_pct']})\n"
    )
  else:
    lines.append(
        "📅 **2. الصفقات اليومية للعملات (BTC/USDT):** ⚠️ السعر الحي غير متاح"
        " حالياً.\n"
    )

  if eth_deal:
    register_tracked_deal(message.chat.id, "crypto_swing", eth_deal)
    lines.append(
        "🌊 **3. صفقات السوينغ للعملات:**\n"
        f"• العملة: {eth_deal['pair']} (سعر الدخول الحي:"
        f" {fmt_num(eth_deal['entry'], True)})\n"
        f"  🛑 وقف الخسارة (SL): {fmt_num(eth_deal['sl'], True)} (-1.2%)\n"
        f"  🎯 الهدف الأول (TP1): {fmt_num(eth_deal['tp1'], True)} ──>"
        f" ({eth_deal['tp1_pct']})\n"
        f"  🛡️ التأمين: {eth_deal['insurance']}\n"
        f"  🚀 الهدف الثاني (TP2): {fmt_num(eth_deal['tp2'], True)} ──>"
        f" ({eth_deal['tp2_pct']})\n"
    )
  else:
    lines.append(
        "🌊 **3. صفقات السوينغ للعملات (ETH/USDT):** ⚠️ السعر الحي غير متاح"
        " حالياً.\n"
    )

  bot.send_message(message.chat.id, "\n".join(lines))


@bot.message_handler(func=lambda m: m.text == "🟡 توصيات صفقات الذهب")
def handle_gold_deals(message):
  if not check_access(message):
    return

  wait_msg = bot.send_message(
      message.chat.id, "⏳ جاري جلب السعر الحي للذهب (XAU/USD)..."
  )
  gold_live = get_gold_price()
  gold_deal = get_dynamic_deal_data("XAU", gold_live)

  try:
    bot.delete_message(message.chat.id, wait_msg.message_id)
  except Exception:
    pass

  if not gold_deal:
    bot.send_message(
        message.chat.id,
        "⚠️ تعذّر جلب السعر الحي للذهب حالياً، يرجى المحاولة بعد قليل.",
    )
    return

  register_tracked_deal(message.chat.id, "gold", gold_deal)

  msg = (
      "🟡 **توصيات صفقات الذهب (الرؤية التحليلية والزخم الحي):**\n\n"
      "📡 *السعر الحي لحظة إصدار التوصية فقط (بدون تثبيت أرقام ثابتة).*\n\n"
      f"📍 سعر الدخول الحي (Entry): {fmt_num(gold_deal['entry'], True)} $\n"
      f"🛑 وقف الخسارة (SL): {fmt_num(gold_deal['sl'], True)} $ (-1.2%)\n\n"
      f"• الهدف الأول (TP1): {fmt_num(gold_deal['tp1'], True)} $ ──>"
      f" ({gold_deal['tp1_pct']})\n"
      f"• الهدف الثاني (TP2): {fmt_num(gold_deal['tp2'], True)} $ ──>"
      f" ({gold_deal['tp2_pct']})\n"
      f"🛡️ التأمين: {gold_deal['insurance']}"
  )
  bot.send_message(message.chat.id, msg)


@bot.message_handler(
    func=lambda m: m.text
    == "📈 نتائج وأداء الصفقات المقترحة (يومي/أسبوعي/شهري)"
)
def handle_results_menu(message):
  if not check_access(message):
    return

  res = load_results()
  daily_txt = "\n".join(res["daily"][-15:]) if res["daily"] else "لا توجد نتائج يومية مسجلة بعد."
  weekly_txt = (
      "\n".join(res["weekly"][-15:])
      if res["weekly"]
      else "لا توجد نتائج أسبوعية مسجلة بعد."
  )
  monthly_txt = (
      "\n".join(res["monthly"][-15:])
      if res["monthly"]
      else "لا توجد نتائج شهرية مسجلة بعد."
  )

  msg = (
      "📈 **نتائج وأداء الصفقات المقترحة:**\n\n"
      f"🗓️ **النتائج اليومية:**\n{daily_txt}\n\n"
      f"📆 **النتائج الأسبوعية:**\n{weekly_txt}\n\n"
      f"🗃️ **النتائج الشهرية:**\n{monthly_txt}"
  )
  bot.send_message(message.chat.id, msg)


@bot.message_handler(func=lambda m: m.text == "🛡️ إدارة المخاطر وحاسبة العقود")
def handle_risk_calculator_prompt(message):
  if not check_access(message):
    return
  user_states[message.from_user.id] = "WAITING_CAPITAL"
  bot.send_message(
      message.chat.id,
      "🛡️ **حاسبة إدارة المخاطر (مخاطرة 1.2%):**\n"
      "أرسل رأس المال بالدولار (مثال: `1000`):",
  )


@bot.message_handler(
    func=lambda m: user_states.get(m.from_user.id) == "WAITING_CAPITAL"
)
def process_capital_input(message):
  if not check_access(message):
    user_states.pop(message.from_user.id, None)
    return
  uid = message.from_user.id
  user_states.pop(uid, None)
  try:
    cap = float(message.text.strip().replace(",", ""))
    if cap <= 0:
      raise ValueError()
    risk_amt = round(cap * 0.012, 2)
    tp1_1to1 = round(risk_amt * 1.0, 2)
    tp2_1to2 = round(risk_amt * 2.0, 2)
    bot.send_message(
        message.chat.id,
        f"💼 رأس المال: **{cap:,.2f} $**\n"
        f"🛑 الحد الأقصى للخسارة (1.2%): **{risk_amt:,.2f} $**\n"
        f"🎯 ربح متوقع (نسبة 1:1): **{tp1_1to1:,.2f} $**\n"
        f"🚀 ربح متوقع (نسبة 1:2): **{tp2_1to2:,.2f} $**",
    )
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ يرجى إدخال رقم صحيح أكبر من الصفر (مثال: `1000`).",
    )


@bot.message_handler(func=lambda m: m.text == "📢 ربط البوت بقناة / مجموعة")
def handle_link_group_prompt(message):
  if not check_access(message):
    return
  user_states[message.from_user.id] = "WAITING_GROUP_ID"
  bot.send_message(
      message.chat.id,
      "📢 **ربط البوت بقناة أو مجموعة:**\n"
      "أضف البوت كمشرف في القناة أو المجموعة، ثم أرسل معرفها (مثل `-1001234567890`):",
  )


@bot.message_handler(
    func=lambda m: user_states.get(m.from_user.id) == "WAITING_GROUP_ID"
)
def process_group_link(message):
  if not check_access(message):
    user_states.pop(message.from_user.id, None)
    return
  uid = message.from_user.id
  user_states.pop(uid, None)
  chat_id_str = message.text.strip()
  try:
    target_id = int(chat_id_str)
    groups = load_groups()
    groups[str(target_id)] = {
        "owner_id": uid,
        "linked_at": datetime.now().isoformat(),
    }
    save_groups(groups)
    bot.send_message(
        message.chat.id, f"✅ تم ربط المعرف `{target_id}` بنجاح."
    )
  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ معرف غير صالح. أرسل رقماً صحيحاً يبدأ بـ `-100` للمجموعات/القنوات.",
    )


@bot.message_handler(func=lambda m: m.text == "ℹ️ معلومات الاشتراك والدعم")
def handle_info_support(message):
  if not check_access(message):
    return
  uid = message.from_user.id
  users = load_users()
  u = users.get(str(uid))
  if uid == ADMIN_ID:
    status_line = "👑 الحساب: مطور النظام (دائم)"
  elif u and is_subscription_active(uid):
    exp_dt = datetime.fromisoformat(u["expires_at"])
    status_line = f"✅ الاشتراك نشط حتى: `{exp_dt.strftime('%Y-%m-%d %H:%M')}`"
  else:
    status_line = "⚠️ الاشتراك غير نشط حالياً."

  bot.send_message(
      message.chat.id,
      f"ℹ️ **معلومات الاشتراك والدعم:**\n"
      f"🆔 معرفك: `{uid}`\n"
      f"{status_line}\n"
      f"📩 للتواصل والدعم: {ADMIN_USERNAME}",
  )


@bot.message_handler(func=lambda m: m.text == "🛠️ لوحة تحكم المطور")
def handle_admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  ensure_admin_recorded(message.from_user)
  bot.send_message(
      message.chat.id,
      "👑 **لوحة تحكم المطور:**\n"
      "• `/users` - عرض المشتركين\n"
      "• `/stats` - الإحصائيات\n"
      "• `/add_result daily [النص]` - إضافة نتيجة يومية\n"
      "• `/add_result weekly [النص]` - إضافة نتيجة أسبوعية\n"
      "• `/add_result monthly [النص]` - إضافة نتيجة شهرية",
  )


@bot.message_handler(commands=["users"])
def cmd_users(message):
  if message.from_user.id != ADMIN_ID:
    return
  users = load_users()
  bot.send_message(message.chat.id, f"👥 إجمالي المشتركين: {len(users)}")


@bot.message_handler(commands=["stats"])
def cmd_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  users = load_users()
  groups = load_groups()
  tracked = load_tracked_deals()
  bot.send_message(
      message.chat.id,
      f"📊 **الإحصائيات:**\n"
      f"• المشتركون: {len(users)}\n"
      f"• المجموعات/القنوات المرتبطة: {len(groups)}\n"
      f"• الصفقات قيد المتابعة: {len(tracked)}",
  )


@bot.message_handler(commands=["add_result"])
def cmd_add_result(message):
  if message.from_user.id != ADMIN_ID:
    return
  parts = message.text.split(maxsplit=2)
  if len(parts) < 3 or parts[1] not in ("daily", "weekly", "monthly"):
    bot.send_message(
        message.chat.id,
        "⚠️ الصيغة: `/add_result daily|weekly|monthly النص`",
    )
    return
  period = parts[1]
  note = parts[2].strip()
  res = load_results()
  now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
  res[period].append(f"[{now_str}] {note}")
  save_results(res)
  bot.send_message(message.chat.id, f"✅ تمت الإضافة إلى قسم `{period}`.")


# حارس عام لأي رسالة أخرى: يمنع أي مستخدم لا يملك يوزر تلقائياً
@bot.message_handler(func=lambda m: True, content_types=["text"])
def fallback_guard(message):
  if message.from_user and message.from_user.id != ADMIN_ID:
    if not has_username(message.from_user):
      deny_no_username(message.chat.id)


# ==========================================
# 7. مراقبة الصفقات بالأسعار الحية في الخلفية
# ==========================================
def background_price_monitor():
  while True:
    try:
      deals = load_tracked_deals()
      if deals:
        crypto_prices = get_crypto_prices()
        gold_price = get_gold_price()
        updated = False

        for d in deals:
          pair = d.get("pair", "")
          curr = None
          if pair == "XRP/USDT":
            curr = crypto_prices.get("XRP")
          elif pair == "BTC/USDT":
            curr = crypto_prices.get("BTC")
          elif pair == "ETH/USDT":
            curr = crypto_prices.get("ETH")
          elif pair == "XAU/USD":
            curr = gold_price

          if curr is None or float(curr) <= 0:
            continue

          curr = float(curr)
          tp1 = float(d["tp1"])
          tp2 = float(d["tp2"])
          sl = float(d["sl"])

          if not d.get("tp1_hit") and curr >= tp1:
            d["tp1_hit"] = True
            updated = True
            line = f"🎯 تحقق الهدف الأول TP1 لصفقة {pair} عند السعر الحي {curr}"
            append_daily_result(line)
            try:
              bot.send_message(d["chat_id"], line)
            except Exception:
              pass

          if not d.get("tp2_hit") and curr >= tp2:
            d["tp2_hit"] = True
            updated = True
            line = f"🚀 تحقق الهدف الثاني TP2 لصفقة {pair} عند السعر الحي {curr}"
            append_daily_result(line)
            try:
              bot.send_message(d["chat_id"], line)
            except Exception:
              pass

          if not d.get("sl_hit") and curr <= sl:
            d["sl_hit"] = True
            updated = True
            line = f"🛑 تفعيل وقف الخسارة SL لصفقة {pair} عند السعر الحي {curr}"
            append_daily_result(line)
            try:
              bot.send_message(d["chat_id"], line)
            except Exception:
              pass

        if updated:
          remaining = [
              x for x in deals if not (x.get("tp2_hit") or x.get("sl_hit"))
          ]
          save_tracked_deals(remaining)
    except Exception as e:
      print(f"Error in background monitor: {e}")

    time.sleep(60)


# ==========================================
# 8. خادم Flask وتشغيل Long-Polling
# ==========================================
@app.route("/")
def index():
  return "Bot is alive and running.", 200


@app.route("/ping")
def ping():
  return "pong", 200


def run_flask():
  app.run(host="0.0.0.0", port=10000)


if __name__ == "__main__":
  flask_thread = threading.Thread(target=run_flask, daemon=True)
  flask_thread.start()

  monitor_thread = threading.Thread(target=background_price_monitor, daemon=True)
  monitor_thread.start()

  while True:
    try:
      bot.infinity_polling(
          skip_pending=True, timeout=20, long_polling_timeout=20
      )
    except Exception as e:
      print(f"Polling error: {e}")
      time.sleep(5)
