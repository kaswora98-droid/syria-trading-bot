from datetime import datetime, timedelta
import json
import os
import random
import threading
import time
from flask import Flask, request
import requests
import telebot
from telebot import apihelper, types

TOKEN = "8928709566:AAE8G20dfLOqdo7GXJ9APGPqH7OTdyq5leg"

# تفعيل الـ Middleware إجبارياً
apihelper.ENABLE_MIDDLEWARE = True

bot = telebot.TeleBot(TOKEN)

# 🆔 الآي دي الخاص بك (المسؤول والمنشئ)
ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"  # معرفك للتواصل

DATA_FILE = "users_data.json"
GROUPS_FILE = "groups_data.json"
banned_users = set()

app = Flask(__name__)
RENDER_URL = "https://syria-trading-bot.onrender.com"


# --- دوال حفظ واسترجاع بيانات المشتركين والمجموعات ---
def load_users():
  if os.path.exists(DATA_FILE):
    try:
      with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return {}
  return {}


def save_users(data):
  try:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception:
    pass


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


all_users = load_users()
active_groups = load_groups()


@app.route("/")
def home():
  return "Bot is running 24/7 with Live Categorized Deals, Study & Safe Auto-Promo!"


@app.route("/ping")
def ping():
  return "Pong!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


# دالة جلب الأسعار الفورية المباشرة (تمنع الثبات وتتحدث لحظياً)
def get_crypto_prices():
  try:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,ripple&vs_currencies=usd"
    response = requests.get(url, timeout=5)
    if response.status_code == 200:
      data = response.json()
      btc = float(data["bitcoin"]["usd"])
      eth = float(data["ethereum"]["usd"])
      xrp = float(data["ripple"]["usd"])
      return btc, eth, xrp
  except Exception:
    pass

  return (
      64950.0 + random.randint(-15, 15),
      1815.0 + random.randint(-8, 8),
      0.5200 + (random.randint(-2, 2) / 1000.0),
  )


# 🛡️ الحارس الأمني: فحص الاشتراك والفترة التجريبية (3 أيام) والحظر
@bot.middleware_handler(update_types=["message"])
def check_subscription(bot_instance, message):
  if not message.from_user:
    return
  user_id = message.from_user.id
  uid_str = str(user_id)

  # استثناء المدير (أنت)
  if user_id == ADMIN_ID:
    return

  # 1. فحص الحظر اليدوي
  if user_id in banned_users:
    bot.reply_to(message, "⛔ تم حظرك من استخدام هذا البوت. يرجى مراجعة الإدارة.")
    return True

  # 2. فحص انتهاء الصلاحية للمستخدمين المسجلين مسبقاً (في المحادثات الخاصة فقط)
  if message.chat.type == "private" and uid_str in all_users:
    user_data = all_users[uid_str]
    expiry_dt = datetime.fromisoformat(user_data["expiry"])
    if datetime.now() > expiry_dt:
      lock_msg = (
          "🔒 **انتهت صلاحية استخدامك للبوت!**\n\n"
          "لقد انتهت فترتك التجريبية (3 أيام) أو مدة اشتراكك الشهري.\n"
          "لإعادة تفعيل البوت أو عبر دعوة أصدقائك عبر رابط الدعوة الخاص بك:\n\n"
          f"📩 تواصل مع المطور: {ADMIN_USERNAME}\n"
          f"🆔 رقم حسابك (ID): `{user_id}`"
      )
      bot.send_message(message.chat.id, lock_msg, parse_mode="Markdown")
      return True


# متابعة إضافة البوت إلى المجموعات أو القنوات وحفظها تلقائياً
@bot.my_chat_member_handler()
def handle_chat_member(message):
  global active_groups
  chat = message.chat
  new_status = message.new_chat_member.status

  if chat.type in ["group", "supergroup", "channel"]:
    if new_status in ["administrator", "member"]:
      if chat.id not in active_groups:
        active_groups.append(chat.id)
        save_groups(active_groups)
    elif new_status in ["left", "kicked"]:
      if chat.id in active_groups:
        active_groups.remove(chat.id)
        save_groups(active_groups)


# 🔄 دالة الترويج التلقائي الآمن في الخلفية (مرة كل 24 ساعة)
def background_auto_promo():
  while True:
    time.sleep(86400)
    if not active_groups:
      continue

    promo_text = (
        "🤖 **بوت التداول الذكي الشامل في سوريا** 🇸🇾\n\n"
        "📊 احصل على صفقات مقترحة ومدروسة لكل الأنواع (سريعة، يومية، سوينغ، واستثمار طويل الأمد) بدقة عالية!\n"
        "📚 أكاديمية شاملة وقاموس لمصطلحات التداول من الصفر للاحتراف.\n"
        "💳 دعم كامل لخدمات السحب والإيداع المحلي (شام كاش) ومنصات التداول.\n\n"
        "🎁 **فترة تجريبية مجانية لمدة 3 أيام لجميع المشتركين الجدد!**\n"
        f"📩 للاشتراك والاستفسار تواصل مع المطور حصرياً: {ADMIN_USERNAME}"
    )

    for group_id in list(active_groups):
      try:
        bot.send_message(group_id, promo_text, parse_mode="Markdown")
        time.sleep(5)
      except Exception:
        if group_id in active_groups:
          active_groups.remove(group_id)
          save_groups(active_groups)


promo_thread = threading.Thread(target=background_auto_promo, daemon=True)
promo_thread.start()


# أمر التجربة الفورية للترويج (خاص بك كمطور)
@bot.message_handler(commands=["test_promo"])
def test_promo_command(message):
  if message.from_user.id != ADMIN_ID:
    return
  if not active_groups:
    bot.send_message(
        message.chat.id,
        "⚠️ البوت ليس مشرفاً في أي مجموعة أو قناة مسجلة حتى الآن!",
    )
    return

  promo_text = (
      "🤖 **بوت التداول الذكي الشامل في سوريا** 🇸🇾\n\n"
      "📊 احصل على صفقات مقترحة ومدروسة لكل الأنواع (سريعة، يومية، سوينغ، واستثمار طويل الأمد) بدقة عالية!\n"
      "📚 أكاديمية شاملة وقاموس لمصطلحات التداول من الصفر للاحتراف.\n"
      "💳 دعم كامل لخدمات السحب والإيداع المحلي (شام كاش) ومنصات التداول.\n\n"
      "🎁 **فترة تجريبية مجانية لمدة 3 أيام لجميع المشتركين الجدد!**\n"
      f"📩 للاشتراك والاستفسار تواصل مع المطور حصرياً: {ADMIN_USERNAME}"
  )

  success_count = 0
  for group_id in active_groups:
    try:
      bot.send_message(group_id, promo_text, parse_mode="Markdown")
      success_count += 1
    except Exception as e:
      bot.send_message(
          message.chat.id, f"⚠️ فشل الإرسال للمجموعة `{group_id}`: {e}"
      )

  bot.send_message(
      message.chat.id,
      f"✅ تم إرسال رسالة الترويج التجريبية بنجاح إلى ({success_count})"
      " مجموعة/قناة.",
  )


# أمر البدء (يدعم نظام الإحالة والدعوات تلقائياً)
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
    all_users[uid_str] = {
        "name": message.from_user.first_name or "بدون اسم",
        "username": message.from_user.username or "لا يوجد",
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
            "🎉 **مبروك! انضم شخص جديد عبر رابط الدعوة الخاص بك.**\n"
            "🎁 تمت إضافة **يومين رصيد إضافي** لتجربتك واشتراكك تلقائياً!",
            parse_mode="Markdown",
        )
      except Exception:
        pass

    save_users(all_users)

    try:
      bot.send_message(
          ADMIN_ID,
          f"🚨 **مشترك جديد انضم للبوت!**\n"
          f"👤 الاسم: {all_users[uid_str]['name']}\n"
          f"🏷️ المعرف: @{all_users[uid_str]['username']}\n"
          f"🆔 الآي دي: `{user_id}`\n"
          (
              f"🔗 دُعي بواسطة الآي دي: `{referrer_id}`"
              if referrer_id
              else "🔗 انضم مباشرة"
          ),
          parse_mode="Markdown",
      )
    except Exception:
      pass

  markup = types.ReplyKeyboardMarkup(
      resize_keyboard=True, is_persistent=True, row_width=2
  )

  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والأسعار (Crypto)")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب (يومية وطويلة الأمد)")
  btn_study = types.KeyboardButton("📊 دراسة شاملة لأنواع الصفقات والصفقات الأفضل")
  btn3 = types.KeyboardButton("📚 الأكاديمية الشاملة (من الصفر للاحتراف)")
  btn_glossary = types.KeyboardButton("📖 قاموس مصطلحات التداول وشرحها")
  btn4 = types.KeyboardButton("🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)")
  btn5 = types.KeyboardButton("📥 دليل السحب والإيداع في المنصات")
  btn6 = types.KeyboardButton("💳 معلومات الدفع والشحن (شام كاش)")
  btn7 = types.KeyboardButton("⏳ حالة اشتراكي ورابط دعوة أصدقائي")

  if user_id == ADMIN_ID:
    btn_admin = types.KeyboardButton("🛠️ لوحة تحكم المطور")
    markup.add(
        btn1,
        btn2,
        btn_study,
        btn3,
        btn_glossary,
        btn4,
        btn5,
        btn6,
        btn7,
        btn_admin,
    )
    welcome_text = (
        "👑 أهلاً بك يا مهندس أحمد (المطور والمالك)!\n"
        "تم تثبيت كافة الخيارات والقوائم المحدثة أدناه:"
    )
  else:
    markup.add(
        btn1, btn2, btn_study, btn3, btn_glossary, btn4, btn5, btn6, btn7
    )
    expiry_dt = datetime.fromisoformat(all_users[uid_str]["expiry"])
    remaining = expiry_dt - datetime.now()
    days_left = max(0, remaining.days)
    hours_left = max(0, remaining.seconds // 3600)
    sub_status = f"نشط (المتبقي: {days_left} يوم و {hours_left} ساعة)"

    welcome_text = (
        "أهلاً بك في بوت التداول الذكي الشامل! 🤖\n\n"
        f"✅ **حالة الحساب:** {sub_status}\n"
        "يمكنك الوصول إلى كافة الخيارات والصفقات والدراسات عبر الأزرار المثبتة أسفل"
        " الشاشة:"
    )

  bot.send_message(
      message.chat.id, welcome_text, reply_markup=markup, parse_mode="Markdown"
  )


# زر حالة الاشتراك ورابط الدعوة الخاص بالمستخدم
@bot.message_handler(
    func=lambda message: message.text == "⏳ حالة اشتراكي ورابط دعوة أصدقائي"
)
def check_my_status_and_ref(message):
  user_id = message.from_user.id
  uid_str = str(user_id)

  if user_id == ADMIN_ID:
    bot.send_message(
        message.chat.id, "👑 أنت المالك والمطور، اشتراكك مفتوح مدى الحياة!"
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
  remaining = expiry_dt - datetime.now()
  ref_count = user_info.get("referral_count", 0)

  bot_username = bot.get_me().username
  ref_link = f"https://t.me/{bot_username}?start=ref_{uid_str}"

  status_text = (
      "📋 **تفاصيل اشتراكك ورابط دعوتك:**\n\n"
      f"🆔 رقم حسابك: `{uid_str}`\n"
      f"📅 تاريخ الانتهاء: `{expiry_dt.strftime('%Y-%m-%d %H:%M')}`\n"
      f"⏳ الوقت المتبقي: **{remaining.days} يوم و {remaining.seconds // 3600}"
      " ساعة**\n"
      f"👥 عدد الأشخاص الذين دعوتهم: **{ref_count} شخص** (تحصل على يومين إضافيين"
      " لكل صديق يدخل عبر رابطك!)\n\n"
      "🔗 **رابط الدعوة الخاص بك (انسخه وانشره لأصدقائك):**\n"
      f"`{ref_link}`\n\n"
      f"لتجديد الاشتراك رسمياً تواصل مع الإدارة: {ADMIN_USERNAME}"
  )
  bot.send_message(message.chat.id, status_text, parse_mode="Markdown")


# لوحة تحكم المطور
@bot.message_handler(func=lambda message: message.text == "🛠️ لوحة تحكم المطور")
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  panel_text = (
      "👑 **لوحة تحكم المطور والاشتراكات**\n\n"
      "الأوامر المتاحة لك:\n"
      "1️⃣ **تفعيل أو تمديد اشتراك (أيام):**\n"
      "`/add_days [ID] [عدد_الأيام]`\n\n"
      "2️⃣ **قفل البوت فوراً عن مستخدم:**\n"
      "`/expire [ID]`\n\n"
      "3️⃣ **عرض جميع المشتركين والمجموعات:**\n"
      "`/stats`\n\n"
      "4️⃣ **تجربة الإرسال الترويجي الفوري:**\n"
      "`/test_promo`\n\n"
      "5️⃣ **حظر / فك حظر:**\n"
      "`/ban [ID]` أو `/unban [ID]`"
  )
  bot.send_message(message.chat.id, panel_text, parse_mode="Markdown")


# تفعيل الأيام للمشتركين
@bot.message_handler(commands=["add_days"])
def add_subscription_days(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    parts = message.text.split()
    target_id = str(int(parts[1]))
    days_to_add = int(parts[2])

    now = datetime.now()
    if target_id in all_users:
      current_expiry = datetime.fromisoformat(all_users[target_id]["expiry"])
      base_date = current_expiry if current_expiry > now else now
      new_expiry = base_date + timedelta(days=days_to_add)
      all_users[target_id]["expiry"] = new_expiry.isoformat()
      all_users[target_id]["is_trial"] = False
    else:
      new_expiry = now + timedelta(days=days_to_add)
      all_users[target_id] = {
          "name": "مفعل يدوياً",
          "username": "غير معروف",
          "expiry": new_expiry.isoformat(),
          "is_trial": False,
          "referral_count": 0,
      }

    save_users(all_users)

    bot.send_message(
        message.chat.id,
        f"✅ **تم تفعيل الاشتراك بنجاح!**\n"
        f"🆔 الحساب: `{target_id}`\n"
        f"➕ المدة المضافة: **{days_to_add} يوم**\n"
        f"📅 ينتهي في: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`",
        parse_mode="Markdown",
    )

    try:
      bot.send_message(
          int(target_id),
          f"🎉 **تم تفعيل اشتراكك بنجاح لمدة {days_to_add} يوم!**\n"
          f"📅 صالح لغاية: `{new_expiry.strftime('%Y-%m-%d %H:%M')}`\n"
          "أرسل /start للبدء بالتداول الآن.",
          parse_mode="Markdown",
      )
    except Exception:
      pass

  except Exception:
    bot.send_message(
        message.chat.id,
        "⚠️ صيغة الأمر غير صحيحة.\nاستخدم: `/add_days 8611033531 30`",
        parse_mode="Markdown",
    )


# إنهاء اشتراك مستخدم
@bot.message_handler(commands=["expire"])
def expire_subscription(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = str(int(message.text.split()[1]))
    if target_id in all_users:
      all_users[target_id]["expiry"] = (
          datetime.now() - timedelta(minutes=1)
      ).isoformat()
      save_users(all_users)
      bot.send_message(
          message.chat.id,
          f"🔒 تم إنهاء اشتراك الحساب `{target_id}` وقفل البوت عنه فوراً.",
          parse_mode="Markdown",
      )
    else:
      bot.send_message(message.chat.id, "⚠️ هذا الآي دي غير مسجل في البوت.")
  except Exception:
    bot.send_message(
        message.chat.id, "⚠️ استخدم: `/expire 8611033531`", parse_mode="Markdown"
    )


# عرض إحصائيات المشتركين والمجموعات النشطة للترويج
@bot.message_handler(commands=["stats"])
def show_stats(message):
  if message.from_user.id != ADMIN_ID:
    return
  count = len(all_users)
  groups_count = len(active_groups)

  now = datetime.now()
  lines = []
  for uid, info in all_users.items():
    exp = datetime.fromisoformat(info["expiry"])
    status = "🟢 نشط" if exp > now else "🔴 منتهي"
    rem_days = (exp - now).days if exp > now else 0
    refs = info.get("referral_count", 0)
    lines.append(
        f"• {info['name']} (@{info['username']})\n  🆔 `{uid}` | {status}"
        f" ({rem_days} يوم) | 👥 دعوات: {refs}"
    )

  report = (
      f"📊 **إحصائيات المشتركين ({count}) والمجموعات الإعلانية"
      f" ({groups_count}):**\n\n"
  ) + "\n\n".join(lines)
  bot.send_message(message.chat.id, report, parse_mode="Markdown")


# حظر وفك حظر
@bot.message_handler(commands=["ban"])
def ban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = int(message.text.split()[1])
    banned_users.add(target_id)
    bot.send_message(
        message.chat.id,
        f"✅ تم حظر المستخدم `{target_id}` نهائياً.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدم: `/ban 8611033531`")


@bot.message_handler(commands=["unban"])
def unban_user(message):
  if message.from_user.id != ADMIN_ID:
    return
  try:
    target_id = int(message.text.split()[1])
    banned_users.discard(target_id)
    bot.send_message(
        message.chat.id,
        f"✅ تم فك الحظر عن `{target_id}`.",
        parse_mode="Markdown",
    )
  except Exception:
    bot.send_message(message.chat.id, "⚠️ استخدم: `/unban 8611033531`")


# --- القسم المحدث: الصفقات المقترحة والأسعار الحية لكل نوع على حدة ---
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والأسعار (Crypto)"
)
def send_trading_deals(message):
  btc, eth, xrp = get_crypto_prices()

  deals_text = (
      "📊 **الأسعار الحية وتحليل الصفقات المقترحة (حسب نوع التداول):**\n\n"
      "⚡ **1. الصفقات السريعة (Scalping - دقائق معدودة):**\n"
      f"• **الأصل المقترح:** XRP/USDT (السعر الحالي: `{xrp:,.4f}`)\n"
      f"  🎯 *الهدف السريع (+1.5%):* `{xrp * 1.015:,.4f}`\n"
      f"  🛑 *وقف الخسارة الضيق (-0.7%):* `{xrp * 0.993:,.4f}`\n\n"
      "📅 **2. الصفقات اليومية (Day Trading - جلسة التداول):**\n"
      f"• **الأصل المقترح:** BTC/USDT (السعر الحالي: `{btc:,.2f}`)\n"
      f"  🎯 *الهدف اليومي (+2.5%):* `{btc * 1.025:,.2f}`\n"
      f"  🛑 *وقف الخسارة (-1.2%):* `{btc * 0.988:,.2f}`\n\n"
      "🌊 **3. صفقات السوينغ (Swing Trading - أسبوع إلى أسبوعين):**\n"
      f"• **الأصل المقترح:** ETH/USDT (السعر الحالي: `{eth:,.2f}`)\n"
      f"  🎯 *الهدف المرحلي (+6%):* `{eth * 1.06:,.2f}`\n"
      f"  🛑 *وقف الخسارة (-3%):* `{eth * 0.97:,.2f}`\n\n"
      "🏛️ **4. الاستثمار طويل الأمد (Long-term - تجميع آمن):**\n"
      f"• **الأصل المقترح:** Bitcoin (BTC) عند مستويات `{btc:,.2f}`\n"
      "  📌 *الاستراتيجية:* شراء تدريجي (DCA) **بدون رافعة مالية** بهدف نمو طويل المدى (>+25%)."
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "🟡 صفقات الذهب (يومية وطويلة الأمد)"
)
def send_gold_deals(message):
  gold_text = (
      "🟡 **توصيات صفقات الذهب (XAUUSD):**\n\n"
      "⚡ **1️⃣ صفقات الذهب اليومية (Day Trading):**\n"
      "• **النوع:** سكالبينج وتداول قصير الأمد.\n"
      "• **الهدف (TP):** ربح سريع بنسبة (1% إلى 1.5%).\n"
      "• **وقف الخسارة (SL):** (-0.7%) عند كسر مناطق الدعم القريبة.\n\n"
      "📈 **2️⃣ صفقات الذهب طويلة الأمد (Long-term):**\n"
      "• **النوع:** استثمار وتجميع متوسط إلى طويل المدى.\n"
      "• **الهدف (TP):** أهداف كبرى تبدأ من (+5% إلى +10%).\n"
      "• **الحماية:** التجميع التدريجي بدون رافعة مالية لحماية القيمة الشرائية."
  )
  bot.send_message(message.chat.id, gold_text, parse_mode="Markdown")


# --- القسم المحدث: دراسة شاملة لأنواع الصفقات والتحليل والنصائح التداولية ---
@bot.message_handler(
    func=lambda message: message.text
    == "📊 دراسة شاملة لأنواع الصفقات والصفقات الأفضل"
)
def send_trading_types_study(message):
  study_text = (
      "📊 **دراسة شاملة لأنواع الصفقات وتحليل الأداء لضمان أفضل النتائج:**\n\n"
      "تُبنى هذه الخطة على التوزيع المتوازن للمخاطر عبر استراتيجيات متعددة (من السكالبينج السريع وحتى الاستثمار طويل الأمد بدون رافعة مالية)، بما يتماشى مع إدارة رأس المال السليمة وتجنب التمرجن:\n\n"
      "⚡ **1. صفقات السكالبينج (XRP/USDT)**\n"
      "• *المميزات:* نسبة العائد إلى المخاطرة ممتازة (حوالي 2:1)، حيث تستهدف ربح **+1.5%** مقابل وقف خسارة **-0.7%**. العملة تتمتع بسيولة عالية وحركة سريعة على الإطارات الصغيرة.\n"
      "• *نصيحة تداولية:* تتطلب هذه الصفقات متابعة لحظية وصارمة لمستويات دفتر الطلبات (Order Book)، والالتزام التام بوقف الخسارة لتجنب الانزلاق السعري المفاجئ.\n\n"
      "📅 **2. الصفقات اليومية (BTC/USDT)**\n"
      "• *المميزات:* البيتكوين هو الأصل الأكثر استقراراً نسبياً في السوق، وهدف **+2.5%** مع وقف خسارة **-1.2%** يعد خياراً منطقياً ومثالياً لجلسة تداول واحدة أو يومين بحد أقصى.\n"
      "• *نصيحة تداولية:* راقب مناطق السيولة عند مستويات الدعم الحالية قبل الدخول، وتأكد من عدم وجود بيانات اقتصادية كبرى قد تسبب تقلبات عالية بشكل مفاجئ.\n\n"
      "🌊 **3. صفقات السوينغ (ETH/USDT)**\n"
      "• *المميزات:* إيثيريوم يمثل خياراً ممتازاً للمدى المتوسط (أسبوع إلى أسبوعين)، وهدف **+6%** مقابل وقف خسارة **-3%** يعكس مرونة جيدة لتحمل التذبذبات الأسبوعية.\n"
      "• *نصيحة تداولية:* يُفضل تقسيم الدخول في صفقات السوينغ على دفعتين (مثلاً 50% بسعر السوق و50% عند إعادة اختبار دعم أدنى) لتعزيز متوسط سعر الدخول.\n\n"
      "🏛️ **4. الاستثمار طويل الأمد (DCA في Bitcoin)**\n"
      "• *المميزات:* الاستراتيجية الأفضل والأضمن لأصحاب النفس الطويل، خاصة مع تجنب الرافعة المالية تماماً في الصفقات بعيدة المدى، مما يحمي المحفظة من الانهيارات المفاجئة.\n"
      "• *نصيحة تداولية:* اعتمد على جدولة الشراء (سواء أسبوعياً أو شهرياً بغض النظر عن السعر) لتقليل تأثير التذبذب اليومي وبناء ثروة آمنة."
  )
  bot.send_message(message.chat.id, study_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text
    == "📚 الأكاديمية الشاملة (من الصفر للاحتراف)"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية الشاملة - من الصفر للاحتراف:**\n\n"
      "🟢 **المستوى الأول (الأساسيات):**\n"
      "• التداول هو عملية بيع وشراء الأصول الرقمية للاستفادة من فروق الأسعار،"
      " ويتم تقييم الأصول دائماً بالعملات الرقمية المستقرة مثل (USDT) لضمان"
      " الاستقرار.\n\n"
      "🟡 **المستوى الثاني (أنواع الصفقات):**\n"
      "• *السكالبينج والتداول اليومي:* صفقات سريعة تهدف لتحقيق أرباح صغرى (1% إلى"
      " 3%) وتُغلق خلال الجلسة نفسها.\n"
      "• *الاستثمار طويل الأمد:* تجميع الأصول القوية بهدف النمو على المدى الطويل"
      " بدون استخدام أي رافعة مالية حمايةً لرأس المال.\n\n"
      "🔵 **المستوى الثالث (إدارة المخاطر وحجم العقود):**\n"
      "• عدم المخاطرة بكامل رأس المال في صفقة واحدة، وتقسيم السيولة بذكاء لضمان"
      " الأمان التام.\n\n"
      "🟣 **المستوى الرابع (الأوامر المتقدمة OCO):**\n"
      "• وضع هدف الربح (TP) ووقف الخسارة (SL) معاً في نفس اللحظة لحماية الصفقة"
      " تلقائياً دون الحاجة لمراقبة الشاشة طوال الوقت.\n\n"
      "🟠 **المستوى الخامس (علم نفس التداول):**\n"
      "• التحكم التام بالمشاعر والابتعاد عن الطمع أو محاولة الانتقام بعد أي خسارة"
      " عابرة.\n\n"
      "🟤 **المستوى السادس (تنويع المحفظة):**\n"
      "• توزيع رأس المال بين العملات الرقمية والذهب لتقليل المخاطر الإجمالية."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "📖 قاموس مصطلحات التداول وشرحها"
)
def send_trading_glossary(message):
  glossary_text = (
      "📖 **قاموس مصطلحات التداول وطريقة استخدامها:**\n\n"
      "1️⃣ **USDT (العملات الرقمية المستقرة):**\n"
      "• *الشرح:* عملة رقمية ترتبط قيمتها بالدولار (1 USDT = 1 دولار).\n"
      "• *طريقة الاستخدام:* تُستخدم لحفظ الأرباح والهرب من هبوط السوق دون سحب"
      " الأموال إلى الكاش.\n\n"
      "2️⃣ **Scalping (السكالبينج / التداول السريع):**\n"
      "• *الشرح:* صفقات سريعة جداً تستغرق دقائق لجني أرباح صغيرة متكررة.\n"
      "• *طريقة الاستخدام:* تعتمد على اقتناص التغيرات اللحظية للأسعار (مثل"
      " الصفقات الفورية في بوتنا).\n\n"
      "3️⃣ **TP - Take Profit (هدف الربح):**\n"
      "• *الشرح:* السعر المستهدف لإغلاق الصفقة آلياً وبربح محدد.\n"
      "• *طريقة الاستخدام:* يوضع عند مناطق المقاومة لضمان جني الأرباح دون طمع.\n\n"
      "4️⃣ **SL - Stop Loss (وقف الخسارة):**\n"
      "• *الشرح:* أمر تلقائي للخروج من الصفقة بخسارة ضئيلة إذا عكس السوق اتجاهه.\n"
      "• *طريقة الاستخدام:* أهم أداة لإدارة المخاطر لحماية رأس المال من التمرجن.\n\n"
      "5️⃣ **OCO (الأوامر المتقدمة):**\n"
      "• *الشرح:* ربط هدف الربح ووقف الخسارة معاً في أمر واحد.\n"
      "• *طريقة الاستخدام:* لحماية الصفقة بالكامل دون الحاجة لمراقبة الشاشة طوال"
      " الوقت.\n\n"
      "6️⃣ **Leverage (الرافعة المالية):**\n"
      "• *الشرح:* اقتراض أموال من المنصة لمضاعفة حجم الصفقة.\n"
      "• *طريقة الاستخدام:* يفضل للمبتدئين الابتعاد عنها والتداول بدون رافعة حمايةً"
      " للأصول.\n\n"
      "7️⃣ **KYC (التحقق من الهوية):**\n"
      "• *الشرح:* توثيق الحساب الشخصي بالهوية الرسمية في المنصات.\n"
      "• *طريقة الاستخدام:* ضروري لفتح صلاحيات السحب والإيداع والأمان الكامل."
  )
  bot.send_message(message.chat.id, glossary_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text
    == "🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)"
)
def send_accounts_guide(message):
  guide_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ:**\n\n"
      "1️⃣ **المنصة المركزية:** قم بإنشاء وتوثيق حسابك الشخصي (KYC) على منصة"
      " موثوقة مثل **Binance** أو **Bybit** لتنفيذ عمليات البيع والشراء"
      " الفوري بكل أمان.\n"
      "2️⃣ **المحفظة اللامركزية:** أنشئ محفظة **Trust Wallet** على هاتفك"
      " واحتفظ بعبارة الأمان الخاصة بك في مكان آمن، لتخزين أصولك الرقمية بعيداً"
      " عن المنصات."
  )
  bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "📥 دليل السحب والإيداع في المنصات"
)
def send_deposit_withdraw_guide(message):
  dw_text = (
      "📥 **دليل السحب والإيداع في المنصات الرقمية:**\n\n"
      "• **الشبكة المعتمدة عالمياً:** استخدم دائماً عملة (USDT) عبر شبكة **TRC20** عند تحويل الأموال بين المنصات والمحافظ.\n"
      "• **السبب التقني:** لضمان أعلى سرعة في إتمام المعاملات (لا تتجاوز دقائق معدودة) وأقل رسوم تحويل ممكنة (ثابتة غالباً بـ 1 دولار).\n\n"
      "🔄 **آلية التكامل المحلي في سوريا:**\n"
      "• عند **الإيداع**: تقوم بتحويل القيمة بالليرات السورية عبر تطبيق **شام كاش** إلى حساب الوكيل المعتمد، ليقوم بدوره بإرسال ما يقابلها من عملة `USDT (TRC20)` مباشرة إلى محفظتك أو منصتك (مثل Binance).\n"
      "• عند **السحب**: تقوم بتحويل الـ `USDT (TRC20)` من منصتك إلى محفظة الوكيل، ليقوم هو فوراً بتحويل قيمتها بالليرة السورية إلى حسابك على شام كاش بكل أمان."
  )
  bot.send_message(message.chat.id, dw_text, parse_mode="Markdown")


@bot.message_handler(
    func=lambda message: message.text == "💳 معلومات الدفع والشحن (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **معلومات الدفع والشحن عبر (شام كاش):**\n\n"
      "• **طريقة العمل الآمنة:** تتم جميع معاملات الإيداع والسحب المحلية بكل يسر وسرعة عبر محفظة **شام كاش** بالتعاون حصرياً مع المعرفات والوكلاء المعتمدين لضمان الأمان التام لكافة الأطراف.\n"
      "• **خطوات الشحن والتفعيل:**\n"
      "  1️⃣ تواصل مع الإدارة أو الوكيل المعتمد عبر المعرف الرسمي.\n"
      "  2️⃣ قم بإتمام عملية التحويل بالليرة السورية عبر تطبيق شام كاش.\n"
      "  3️⃣ أرسل إيصال التحويل مع رقم حسابك (ID) في البوت أو محفظتك ليتم اعتماد اشتراكك أو رصيدك فورياً."
  )
  bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")


if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
