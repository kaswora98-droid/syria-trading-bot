import os
from flask import Flask, request
import requests
import telebot
from telebot import types

TOKEN = "8928709566:AAE8G20dfLOqdo7GXJ9APGPqH7OTdyq5leg"
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)
RENDER_URL = "https://syria-trading-bot.onrender.com"


@app.route("/")
def home():
  return "Bot is running 24/7!"


@app.route("/ping")
def ping():
  return "Pong!", 200


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
  json_string = request.get_data().decode("utf-8")
  update = telebot.types.Update.de_json(json_string)
  bot.process_new_updates([update])
  return "!", 200


def get_binance_price(symbol):
  try:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url, timeout=3)
    if response.status_code == 200:
      data = response.json()
      return float(data["price"])
  except Exception:
    pass
  return None


# القائمة الرئيسية
@bot.message_handler(commands=["start"])
def send_welcome(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والأسعار (Crypto)")
  btn2 = types.KeyboardButton("🟡 صفقات الذهب (يومية وطويلة الأمد)")
  btn3 = types.KeyboardButton("📚 الأكاديمية الشاملة (من الصفر للاحتراف)")
  btn4 = types.KeyboardButton("🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)")
  btn5 = types.KeyboardButton("📥 دليل السحب والإيداع في المنصات")
  btn6 = types.KeyboardButton("💳 معلومات الدفع والشحن (شام كاش)")
  markup.add(btn1, btn2, btn3, btn4, btn5, btn6)

  welcome_text = (
      "أهلاً بك في بوت التداول الذكي الشامل! 🤖\nاختر من الأزرار أدناه للبدء:"
  )
  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# قسم صفقات العملات الرقمية
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والأسعار (Crypto)"
)
def send_trading_deals(message):
  btc_price = get_binance_price("BTCUSDT")
  eth_price = get_binance_price("ETHUSDT")
  xrp_price = get_binance_price("XRPUSDT")

  btc_str = f"{btc_price:,.2f}" if btc_price else "غير متوفر"
  eth_str = f"{eth_price:,.2f}" if eth_price else "غير متوفر"
  xrp_str = f"{xrp_price:,.4f}" if xrp_price else "غير متوفر"

  if btc_price:
    btc_tp = f"{btc_price * 1.03:,.2f}"
    btc_sl = f"{btc_price * 0.985:,.2f}"
  else:
    btc_tp, btc_sl = "---", "---"

  if eth_price:
    eth_tp = f"{eth_price * 1.03:,.2f}"
    eth_sl = f"{eth_price * 0.985:,.2f}"
  else:
    eth_tp, eth_sl = "---", "---"

  if xrp_price:
    xrp_tp = f"{xrp_price * 1.03:,.4f}"
    xrp_sl = f"{xrp_price * 0.99:,.4f}"
  else:
    xrp_tp, xrp_sl = "---", "---"

  deals_text = (
      "📊 **الأسعار الفورية للعملات الرقمية (Binance):**\n\n"
      f"🔹 **BTC/USDT**\n"
      f"  • السعر الحالي: {btc_str} USDT\n"
      f"  • الهدف المقترح (TP +3%): {btc_tp} 🎯\n"
      f"  • وقف الخسارة (SL -1.5%): {btc_sl} 🛑\n\n"
      f"🔹 **ETH/USDT**\n"
      f"  • السعر الحالي: {eth_str} USDT\n"
      f"  • الهدف المقترح (TP +3%): {eth_tp} 🎯\n"
      f"  • وقف الخسارة (SL -1.5%): {eth_sl} 🛑\n\n"
      f"🔹 **XRP/USDT**\n"
      f"  • السعر الحالي: {xrp_str} USDT\n"
      f"  • الهدف المقترح (TP +3%): {xrp_tp} 🎯\n"
      f"  • وقف الخسارة (SL -1.5%): {xrp_sl} 🛑\n\n"
      "👑 **القاعدة الذهبية لأنواع الصفقات:**\n"
      "• **السكالبينج:** ربح سريع (0.5% - 1%) مع وقف خسارة ضيق.\n"
      "• **اليومية:** أهداف مدروسة (2% - 3%) تغلق بنهاية اليوم.\n"
      "• **طويلة الأمد:** أهداف كبرى (+5% فأكثر) بدون رافعة مالية.\n\n"
      "⚠️ **ملاحظة:** تداول فوري (Spot) آمن تماماً لإدارة المخاطر."
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


# قسم صفقات الذهب
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


# قسم الأكاديمية الشاملة (الموسّع بكافة المحاور المتقدمة)
@bot.message_handler(
    func=lambda message: message.text
    == "📚 الأكاديمية الشاملة (من الصفر للاحتراف)"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية الشاملة - من الصفر للاحتراف:**\n\n"
      "🟢 **المستوى الأول: الأساسيات والمفاهيم**\n"
      "• **ما هو التداول؟** بيع وشراء الأصول لتحقيق الربح من فروق الأسعار.\n"
      "• **أزواج العملات والأصول:** فهم حركة السعر والتقييم بالعملات المستقرة"
      " (USDT).\n\n"
      "🟡 **المستوى الثاني: أنواع الصفقات (يومية وطويلة الأمد)**\n"
      "• **السكالبينج والتداول اليومي:** صفقات قصيرة تفتح وتغلق سريعاً لاصطياد"
      " الأرباح.\n"
      "• **التداول الاستثماري طويل الأمد:** صفقات التأرجح وتجميع الأصول لأشهر"
      " أو سنوات.\n\n"
      "🔵 **المستوى الثالث: إدارة رأس المال وحجم العقود (Position Sizing)**\n"
      "• **قاعدة تقسيم السيولة:** عدم وضع رأس المال كاملاً في صفقة واحدة (أبداً"
      " لا تضع كل البيض في سلة واحدة).\n"
      "• **إدارة المخاطر:** ألا تتجاوز الخسارة في الصفقة الواحدة نسبة مئوية"
      " صغيرة من إجمالي الحساب.\n\n"
      "🟣 **المستوى الرابع: الأوامر المتقدمة في المنصات (OCO Orders)**\n"
      "• **ما هو أمر OCO؟** أداة متقدمة تتيح لك وضع هدف الربح (TP) ووقف"
      " الخسارة (SL) معاً في نفس اللحظة؛ فإذا تحقق أحدهما يتم إلغاء الآخر"
      " تلقائياً لحماية حقوقك.\n\n"
      "🟠 **المستوى الخامس: علم نفس التداول (Trading Psychology)**\n"
      "• **السيطرة على المشاعر:** الطمع والخوف هما العدوان اللدودان للمتداول.\n"
      "• **تجنب الانتقام (Revenge Trading):** عدم محاولة تعويض الخسارة فوراً"
      " بصفقات عشوائية متهورة بعد ضرب وقف الخسارة.\n\n"
      "🟤 **المستوى السادس: تنويع المحفظة (Diversification & Hedging)**\n"
      "• توزيع الاستثمار بين الأصول الرقمية (مثل البيتكوين) والمعادن (مثل الذهب)"
      " لتقليل المخاطر الإجمالية وتعزيز استقرار المحفظة."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


# قسم فتح الحسابات
@bot.message_handler(
    func=lambda message: message.text
    == "🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)"
)
def send_accounts_guide(message):
  guide_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ:**\n\n"
      "• قم بفتح حساب موثق (KYC) على منصة Binance أو Bybit للتداول الفوري،"
      " وأنشئ محفظة لامركزية (Trust Wallet) لتخزين أصولك بأمان."
  )
  bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")


# قسم السحب والإيداع
@bot.message_handler(
    func=lambda message: message.text == "📥 دليل السحب والإيداع في المنصات"
)
def send_deposit_withdraw_guide(message):
  dw_text = (
      "📥 **دليل السحب والإيداع:**\n\n"
      "• استخدم دائماً عملة USDT عبر شبكة **TRC20** لضمان سرعة المعاملات وانخفاض"
      " الرسوم."
  )
  bot.send_message(message.chat.id, dw_text, parse_mode="Markdown")


# قسم الدفع والشحن (شام كاش)
@bot.message_handler(
    func=lambda message: message.text == "💳 معلومات الدفع والشحن (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **معلومات الدفع والشحن (شام كاش):**\n\n"
      "• تتم معاملات الشحن والإيداع بكل أمان وسهولة عبر خدمة **شام كاش**"
      " بالتعاون مع المعرفات المعتمدة."
  )
  bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")


if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
