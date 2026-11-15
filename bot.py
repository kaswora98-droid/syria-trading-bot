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


# قسم الأكاديمية الشاملة (جميع المستويات من الصفر للاحتراف)
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


# قسم فتح الحسابات وإنشاء المحافظ (دليل تفصيلي كامل)
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


# تشغيل البوت مع سيرفر الـ Flask
if __name__ == "__main__":
  import threading

  def run_bot():
    bot.infinity_polling()

  t = threading.Thread(target=run_bot)
  t.start()

  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
