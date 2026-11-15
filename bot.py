import os
from flask import Flask
import telebot
from telebot import types

# التوكن الصحيح للبوت
TOKEN = "8928709566:AAE8G20dfLOqdo7GXJ9APGPqH7OTdyq5leg"
bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)


@app.route("/")
def home():
  return "Bot is running 24/7!"


# القائمة الرئيسية والأزرار الأربعة الاحترافية
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


# قسم الصفقات المقترحة والأسعار
@bot.message_handler(
    func=lambda message: message.text == "📊 الصفقات المقترحة والأسعار"
)
def send_trading_deals(message):
  deals_text = (
      "📊 **الصفقات والأَسعار الفورية المقترحة (Binance):**\n\n"
      "🔹 **BTC/USDT**\n"
      "  • السعر الحالي: 64,700.72 USDT\n"
      "  • الهدف المقترح (TP): 65,994.73 🎯\n"
      "  • وقف الخسارة (SL): 63,730.21 🛑\n\n"
      "🔹 **ETH/USDT**\n"
      "  • السعر الحالي: 1,809.58 USDT\n"
      "  • الهدف المقترح (TP): 1,845.77 🎯\n"
      "  • وقف الخسارة (SL): 1,782.44 🛑\n\n"
      "🔹 **XRP/USDT**\n"
      "  • السعر الحالي: 0.96 USDT\n"
      "  • الهدف المقترح (TP): 0.97 🎯\n"
      "  • وقف الخسارة (SL): 0.94 🛑\n\n"
      "⚠️ **ملاحظة:** التداول ينطوي على مخاطر، التزم بإدارة رأس المال."
  )
  bot.send_message(message.chat.id, deals_text, parse_mode="Markdown")


# قسم الأكاديمية الشاملة
@bot.message_handler(
    func=lambda message: message.text
    == "📚 الأكاديمية الشاملة (من الصفر للاحتراف)"
)
def send_academy(message):
  academy_text = (
      "📚 **الأكاديمية الشاملة - المستوى الأول:**\n\n"
      "1️⃣ **ما هو التداول؟** بيع وشراء الأصول الرقمية لتحقيق الربح من فروق"
      " الأسعار.\n"
      "2️⃣ **ما هو زوج العملات (مثل BTC/USDT)؟** الطرف الأيسر هو العملة"
      " المتداولة، والطرف الأيمن هو عملة التقييم (USDT).\n"
      "3️⃣ **إدارة المخاطر:** السر الأساسي للاستمرار والنجاح في السوق الرقمي"
      " الذي يعمل 24/7."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


# قسم فتح الحسابات وإنشاء المحافظ
@bot.message_handler(
    func=lambda message: message.text
    == "🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)"
)
def send_accounts_guide(message):
  guide_text = (
      "🌐 **دليل فتح الحسابات وإنشاء المحافظ:**\n\n"
      "• **منصة Binance / Bybit:** يتم التسجيل عبر البريد الإلكتروني وتوثيق"
      " الحساب (KYC) لضمان الأمان الكامل.\n"
      "• **المحافظ اللامركزية:** مثل Trust Wallet أو MetaMask لتخزين الأصول"
      " بشكل آمن مع الاحتفاظ بعبارة الاسترداد (Seed Phrase)."
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


# تشغيل البوت مع سيرفر الـ Flask
if __name__ == "__main__":
  import threading

  def run_bot():
    bot.infinity_polling()

  t = threading.Thread(target=run_bot)
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
