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


# القائمة الرئيسية
@bot.message_handler(commands=["start"])
def send_welcome(message):
  markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
  btn1 = types.KeyboardButton("📚 الأكاديمية")
  btn2 = types.KeyboardButton("📊 الصفقات المقترحة والأسعار")
  btn3 = types.KeyboardButton("🌐 المنصات العالمية")
  markup.add(btn1, btn2, btn3)

  welcome_text = (
      "مرحباً بك في بوت التداول والأكاديمية الرقمية!\nاختر ما يناسبك من"
      " القائمة أدناه:"
  )
  bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# قسم الأكاديمية
@bot.message_handler(func=lambda message: message.text == "📚 الأكاديمية")
def send_academy(message):
  academy_text = (
      "1️⃣ **المستوى الأول: أساسيات التداول الرقمي**\n\n"
      "• **ما هو التداول؟** بيع وشراء الأصول الرقمية لتحقيق الربح من فروق"
      " الأسعار.\n• **ما هو زوج العملات (مثل BTC/USDT)؟** الطرف الأيسر هو العملة"
      " المتداولة (البيتكوين)، والطرف الأيمن هو عملة التقييم (الدولار الرقمي"
      " USDT).\n• **السوق الرقمي:** يعمل 24 ساعة طوال أيام الأسبوع."
  )
  bot.send_message(message.chat.id, academy_text, parse_mode="Markdown")


# قسم الصفقات المقترحة (النسخة الثابتة والمستقرة)
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


# قسم المنصات العالمية
@bot.message_handler(func=lambda message: message.text == "🌐 المنصات العالمية")
def send_platforms(message):
  bot.send_message(
      message.chat.id,
      "🌐 يمكنك تداول العملات الرقمية عبر أشهر المنصات العالمية مثل Binance و"
      " Bybit.",
  )


# تشغيل البوت مع سيرفر الـ Flask
if __name__ == "__main__":
  import threading

  def run_bot():
    bot.infinity_polling()

  t = threading.Thread(target=run_bot)
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
