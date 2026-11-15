import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
import urllib.request
import json

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# دالة جلب الصفقات والأسعار الفورية مع الأهداف
async def get_crypto_signals():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbols=[\"BTCUSDT\",\"ETHUSDT\",\"XRPUSDT\"]"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
        text = "📊 **الصفقات والأسعار الفورية المقترحة (Binance):**\n\n"
        for item in data:
            symbol = item['symbol'].replace('USDT', '/USDT')
            price = float(item['price'])
            tp = price * 1.02
            sl = price * 0.985
            
            text += f"🔹 **{symbol}**\n"
            text += f"   • السعر الحالي: `{price:,.2f}` USDT\n"
            text += f"   • 🎯 الهدف المقترح (TP): `{tp:,.2f}`\n"
            text += f"   • 🛑 وقف الخسارة (SL): `{sl:,.2f}`\n\n"
            
        text += "⚠️ *ملاحظة: التداول ينطوي على مخاطر، التزم بإدارة رأس المال.*"
        return text
    except Exception as e:
        return "⚠️ تعذر جلب الصفقات حالياً، تأكد من اتصال الإنترنت."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 الصفقات المقترحة والأسعار", callback_data='prices')],
        [InlineKeyboardButton("📖 الأكاديمية الشاملة (من الصفر للاحتراف)", callback_data='academy_menu')],
        [InlineKeyboardButton("🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)", callback_data='platforms')],
        [InlineKeyboardButton("💳 معلومات الدفع والشحن (شام كاش)", callback_data='payment')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "أهلاً بك في بوت التداول الذكي الشامل! 🤖\nاختر من الأزرار أدناه للبدء:",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'prices':
        price_text = await get_crypto_signals()
        back_kb = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='main_menu')]]
        await query.edit_message_text(text=price_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_kb))
        
    elif query.data == 'academy_menu':
        ac_keyboard = [
            [InlineKeyboardButton("1️⃣ المستوى 1: أساسيات التداول", callback_data='lvl1')],
            [InlineKeyboardButton("2️⃣ المستوى 2: التحليل والشموع", callback_data='lvl2')],
            [InlineKeyboardButton("3️⃣ المستوى 3: أوامر المنصة (Buy/Sell)", callback_data='lvl3')],
            [InlineKeyboardButton("4️⃣ المستوى 4: إدارة المخاطر ورأس المال", callback_data='lvl4')],
            [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='main_menu')]
        ]
        await query.edit_message_text(
            "📖 **أكاديمية التداول الاحترافية:**\nاختر المستويات أدناه للبدء بالتعلم خطوة بخطوة:",
            reply_markup=InlineKeyboardMarkup(ac_keyboard)
        )
        
    elif query.data == 'lvl1':
        text = (
            "1️⃣ **المستوى الأول: أساسيات التداول الرقمي**\n\n"
            "• **ما هو التداول؟** بيع وشراء الأصول الرقمية لتحقيق الربح من فروق الأسعار.\n"
            "• **ما هو زوج العملات (مثل BTC/USDT)؟** الطرف الأيسر هو العملة المتداولة (البيتكوين)، والطرف الأيمن هو عملة التقييم (الدولار الرقمي USDT).\n"
            "• **السوق الرقمي:** يعمل 24 ساعة طوال أيام الأسبوع."
        )
        back_kb = [[InlineKeyboardButton("🔙 رجوع لقائمة الأكاديمية", callback_data='academy_menu')]]
        await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_kb))
        
    elif query.data == 'lvl2':
        text = (
            "2️⃣ **المستوى الثاني: الشموع اليابانية والتحليل الفني**\n\n"
            "• **الشموع اليابانية:** الخضراء تعني صعود السعر، والحمراء تعني هبوطه.\n"
            "• **الدعم والمقاومة:** مناطق تاريخية يرتد منها السعر صعوداً أو هبوطاً."
        )
        back_kb = [[InlineKeyboardButton("🔙 رجوع لقائمة الأكاديمية", callback_data='academy_menu')]]
        await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_kb))

    elif query.data == 'lvl3':
        text = (
            "3️⃣ **المستوى الثالث: أوامر المنصة (كيف تنفذ صفقتك؟)**\n\n"
            "• **Market (السعر الفوري):** شراء أو بيع فوري بالسعر الحالي.\n"
            "• **Limit (الأمر المحدد):** تحديد سعر معين لا تتم الصفقة إلا عنده.\n"
            "• **Stop Loss (وقف الخسارة):** أمر لحماية المحفظة يغلق الصفقة تلقائياً عند خسارة محددة.\n"
            "• **Take Profit (جني الأرباح):** أمر يغلق الصفقة تلقائياً عند تحقيق الهدف."
        )
        back_kb = [[InlineKeyboardButton("🔙 رجوع لقائمة الأكاديمية", callback_data='academy_menu')]]
        await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_kb))

    elif query.data == 'lvl4':
        text = (
            "4️⃣ **المستوى الرابع: إدارة المخاطر (سر النجاح الأبدي)**\n\n"
            "• **قاعدة النسبة المئوية:** لا تخاطر بأكثر من 1-2% من محفظتك في الصفقة الواحدة.\n"
            "• **الالتزام بوقف الخسارة:** حماية رأس المال أهم من البحث عن الربح السريع."
        )
        back_kb = [[InlineKeyboardButton("🔙 رجوع لقائمة الأكاديمية", callback_data='academy_menu')]]
        await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_kb))
        
    elif query.data == 'platforms':
        platforms_text = (
            "🌐 **دليل فتح الحسابات وإنشاء المحافظ بالتفصيل:**\n\n"
            "1️⃣ **فتح وتوثيق الحساب على Binance:**\n"
            "   • حمّل تطبيق Binance من متجر التطبيقات أو زر موقعهم الرسمي.\n"
            "   • اضغط على 'Register' وسجل ببريدك الإلكتروني وأنشئ كلمة مرور قوية.\n"
            "   • قم بتوثيق الهوية (KYC) عبر رفع صورة جواز السفر أو الهوية الشخصية لضمان أمان حسابك.\n\n"
            "2️⃣ **إنشاء المحفظة الرقمية داخل المنصة:**\n"
            "   • بمجرد دخولك للمنصة، يتم إنشاء محافظك تلقائياً.\n"
            "   • **محفظة الفوري (Spot Wallet):** مخصصة لتداول العملات وشراء الأصول وتنفيذ الصفقات.\n"
            "   • **محفظة التمويل (Funding Wallet):** مخصصة لبيع وشراء العملات عبر منصة P2P (الشحن والسحب).\n\n"
            "3️⃣ **ربط وشحن المحفظة محلياً في سوريا:**\n"
            "   • انتقل إلى قسم **P2P Trading** داخل التطبيق.\n"
            "   • اختر وسيلة الدفع المحلية **شام كاش** وتواصل مع الوسطاء المعتمدين لشحن رصيدك من الـ USDT بكل سهولة وأمان."
        )
        back_kb = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='main_menu')]]
        await query.edit_message_text(text=platforms_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_kb))
        
    elif query.data == 'payment':
        payment_text = (
            "💳 **طرق الإيداع والسحب عبر شام كاش:**\n\n"
            "• يتم التعامل عبر شبكة وسطاء Binance P2P المعتمدين في سوريا باستخدام **شام كاش**.\n"
            "• تحويل المبلغ بالليرة السورية للوكيل المحلي، فيقوم بتحويل رصيد الـ (USDT) مباشرة إلى محفظة التمويل (Funding) الخاصة بك على منصة Binance."
        )
        back_kb = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data='main_menu')]]
        await query.edit_message_text(text=payment_text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(back_kb))
        
    elif query.data == 'main_menu':
        keyboard = [
            [InlineKeyboardButton("📊 الصفقات المقترحة والأسعار", callback_data='prices')],
            [InlineKeyboardButton("📖 الأكاديمية الشاملة (من الصفر للاحتراف)", callback_data='academy_menu')],
            [InlineKeyboardButton("🌐 فتح الحسابات وإنشاء المحافظ (دليل تفصيلي)", callback_data='platforms')],
            [InlineKeyboardButton("💳 معلومات الدفع والشحن (شام كاش)", callback_data='payment')]
        ]
        await query.edit_message_text(
            "أهلاً بك مجدداً في القائمة الرئيسية للبوت 🤖\nاختر من الأزرار أدناه للمتابعة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

if __name__ == '__main__':
    TOKEN = '8928709566:AAE8G20dfLOqdo7GXJ9APGPqH7OTdyq5leg'
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    
    print("🤖 البوت يعمل الآن مع الدليل التفصيلي لفتح الحسابات والمحافظ...")
    app.run_polling()

