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


# دالة لجلب السعر الحقيقي من بينانس
def get_binance_price(symbol):
  try:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    response = requests.get(url, timeout=5)
    data = response.json()
    return float(data["price"])
  except Exception:
    return None


# القائمة الرئيسية والأزرار الأربعة
@bot.message_handler(commands=["start"])
def send_welcome(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn1 = types.KeyboardButton("📊 الصفقات المقترحة والأسعار")
  btn2 = types.KeyboardButton("📚 الأكاديمية الشاملة (من الصفر للاحتراف)")
  btn3 = types.KeyboardButton("🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)")
  btn4 = types.KeyboardButton("💳 معلومات الدفع والشحن (شام كاش)")
  markup.add(btn1, btn2, btn3, btn4)

  welcome_text = (
      "أهلاً بك في بوت التداول الذكي الشامل! 🤖\nاختر من الأزرار أدناه للبدء:"
  )
  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# قسم الصفقات المقترحة والأسعار الحقيقية بمعادلة احترافية (هدف أعلى من الخسارة)
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والأسعار"
)
def send_trading_deals(message):
  btc_price = get_binance_price("BTCUSDT")
  eth_price = get_binance_price("ETHUSDT")
  xrp_price = get_binance_price("XRPUSDT")

  btc_str = f"{btc_price:,.2f}" if btc_price else "غير متوفر"
  eth_str = f"{eth_price:,.2f}" if eth_price else "غير متوفر"
  xrp_str = f"{xrp_price:,.4f}" if xrp_price else "غير متوفر"

  # المعادلة الاحترافية الصحيحة: الهدف (+3%) ووقف الخسارة (-1.5%)
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
    xrp_sl = f"{xrp_price * 0.985:,.4f}"
  else:
    xrp_tp, xrp_sl = "---", "---"

  deals_text = (
      "📊 **الأسعار الفورية والحقيقية (مباشرة من Binance):**\n\n"
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
      "⚠️ **ملاحظة:** الصفقات مخصصة للتداول الفوري (Spot) بدون رافعة مالية"
      " لضمان الأمان الكامل وإدارة المخاطر."
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


# قسم الأكاديمية الشاملة
@bot.message_handler(
    func=lambda message: message.text
    == "📚 الأكاديمية الشاملة (من الصفر للاحتراف)"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية الشاملة - من الصفر للاحتراف:**\n\n"
      "🟢 **المستوى الأول: الأساسيات والمفاهيم**\n"
      "• **ما هو التداول؟** بيع وشراء الأصول الرقمية لتحقيق الربح من فروق"
      " الأسعار.\n"
      "• **ما هو زوج العملات (BTC/USDT)؟** الطرف الأيسر هو العملة المتداولة،"
      " والطرف الأيمن هو عملة التقييم (USDT).\n"
      "• **سوق العملات الرقمية:** سوق عالمي لا يغلق، يعمل 24 ساعة طوال أيام"
      " الأسبوع.\n\n"
      "🟡 **المستوى الثاني: التحليل الفني وقراءة الشارت**\n"
      "• **الشموع اليابانية:** فهم حركة السعر (افتتاح، إغلاق، أعلى وأدنى سعر).\n"
      "• **الدعم والمقاومة:** مستويات سابقة ارتد منها السعر وتعتبر مناطق محورية"
      " لاتخاذ القرار.\n"
      "• **المؤشرات الفنية:** مثل مؤشر القوة النسبية (RSI) والمتوسطات"
      " المتحركة.\n\n"
      "🔵 **المستوى الثالث: استراتيجيات التداول وإدارة المخاطر**\n"
      "• **تحديد الهدف (TP) وقف الخسارة (SL):** لحماية رأس المال وضمان الأرباح"
      " بانتظام.\n"
      "• **إدارة المخاطر:** عدم المخاطرة بأكثر من 1-2% من إجمالي رأس المال في"
      " الصفقات الفردية.\n"
      "• **الصبر والانضباط:** العامل النفسي الأهم في نجاح المتداول."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


# قسم فتح الحسابات وإنشاء المحافظ
@bot.message_handler(
    func=lambda message: message.text
    == "🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)"
)
def send_accounts_guide(message):
  guide_text = (
      "🌐 **الدليل التفصيلي لفتح الحسابات وإنشاء المحافظ:**\n\n"
      "1️⃣ **فتح وتوثيق حساب في المنصات المركزية (Binance / Bybit):**\n"
      "• قم بتحميل تطبيق المنصة أو زيارة الموقع الرسمي.\n"
      "• سجل باستخدام بريدك الإلكتروني وكلمة مرور قوية.\n"
      "• أكمل عملية التحقق من الهوية (KYC) عبر رفع صورة الهوية الشخصية أو"
      " جواز السفر لفتح كافة ميزات التداول والسحب بأمان تام.\n\n"
      "2️⃣ **إنشاء المحافظ اللامركزية (Trust Wallet / MetaMask):**\n"
      "• حمل تطبيق Trust Wallet من المتجر الرسمي.\n"
      "• أنشئ محفظة جديدة واحفظ **عبارة الاسترداد (12 كلمة سرية)** في مكان"
      " آمن ورقي تماماً.\n"
      "• لا تشارك هذه الكلمات مع أي شخص نهائياً لأنها مفتاح التحكم بأصولك.\n\n"
      "3️⃣ **الربط والأمان:**\n"
      "• فعّل مصادقة الخطوتين (2FA) عبر تطبيق Google Authenticator لحماية"
      " حسابك من أي اختراق."
  )
  bot.send_message(message.chat.id, guide_text, parse_mode="Markdown")


# قسم معلومات الدفع والشحن (شام كاش)
@bot.message_handler(
    func=lambda message: message.text == "💳 معلومات الدفع والشحن (شام كاش)"
)
def send_payment_info(message):
  payment_text = (
      "💳 **معلومات الدفع والشحن (شام كاش):**\n\n"
      "• يمكنك إتمام عمليات الإيداع والشحن بسهولة وبشكل آمن عبر خدمة **شام"
      " كاش**.\n"
      "• يرجى التواصل مع الدعم أو المعرف المعتمد لإتمام عملية التحويل وتأكيد"
      " رصيدك بدقة."
  )
  bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")


if __name__ == "__main__":
  bot.remove_webhook()
  bot.set_webhook(url=f"{RENDER_URL}/{TOKEN}")

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
