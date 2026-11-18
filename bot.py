import telebot
from telebot import types
import json
import os
import threading
import time
from datetime import datetime, timedelta

# --- الإعدادات الأساسية (التوكن الجديد) ---
TOKEN = "8928709566:AAHP9dZXrxkpp2FneolgC-Cfd4jFh6nqMF4"
ADMIN_ID = 8611033531
ADMIN_USERNAME = "@alone123987"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "users_data.json"

# --- دوال إدارة وتخزين بيانات المستخدمين ---
def load_users():
    """قراءة بيانات المستخدمين مع حماية الكود من الانهيار لو كان الملف فارغاً"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(data):
    """حفظ بيانات المستخدمين محلياً بشكل فوري وآمن"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving users data: {e}")

# تهيئة بيانات المستخدمين عند بدء التشغيل
users_data = load_users()

# --- لوحة المفاتيح الرئيسية الأصلية للبوت ---
def get_main_keyboard(is_admin=False):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📊 الصفقات"),
        types.KeyboardButton("📰 موجز الأخبار الاقتصادية اللحظية")
    )
    markup.add(
        types.KeyboardButton("🧠 اختبار تداولي تفاعلي (Quiz)"),
        types.KeyboardButton("📚 الأكاديمية التعليمية للمبتدئين")
    )
    markup.add(
        types.KeyboardButton("📖 قاموس مصطلحات التداول (بحث ذكي)"),
        types.KeyboardButton("🌐 دليل السحب والإيداع (شبكة TRC20) وإستخراج المحافظ")
    )
    markup.add(
        types.KeyboardButton("⏳ حالة اشتراكي ورابط دعوة (شام كاش)"),
        types.KeyboardButton("💳 الدفع والشحن المحلي (شام كاش)")
    )
    if is_admin:
        markup.add(types.KeyboardButton("🛠 لوحة تحكم المطور"))
    return markup

# --- معالجة أمر البداية /start ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "No Username"
    first_name = message.from_user.first_name or "User"

    if user_id not in users_data:
        expiry_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        users_data[user_id] = {
            "username": username,
            "first_name": first_name,
            "expiry_date": expiry_date,
            "joined_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_users(users_data)

    is_admin = (message.from_user.id == ADMIN_ID)
    markup = get_main_keyboard(is_admin)

    bot.reply_to(message, f"أهلاً بك يا {first_name} في بوت التداول والأكاديمية الخاص بك.", reply_markup=markup)

# --- لوحة تحكم المطور (الزر النصي) ---
@bot.message_handler(func=lambda message: message.text == "🛠 لوحة تحكم المطور")
def admin_panel_text(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = (
        "👑 **لوحة تحكم المطور:**\n"
        "الأوامر المتاحة:\n"
        "• `/users` - لعرض قائمة المشتركين\n"
        "• `/stats` - لعرض الإحصائيات\n"
        "• `/add_days ID days` - لإضافة أيام للمشترك\n"
        "• `/ban ID` - لحظر مستخدم"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

# --- أمر الإحصائيات /stats ---
@bot.message_handler(commands=['stats'])
def admin_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "عذراً، هذا الأمر مخصص للمشرف فقط.")
        return
    
    current_users = load_users()
    total_users = len(current_users)
    text = f"📊 **إجمالي المشتركين:** {total_users}\n مجموعات مفعلة: 0"
    bot.reply_to(message, text, parse_mode="Markdown")

# --- أمر لوحة التحكم /users الأصلية مع أزرار الملف الشخصي ---
@bot.message_handler(commands=['users'])
def admin_users_list(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "عذراً، هذا الأمر مخصص للمشرف فقط.")
        return

    current_users = load_users()
    if not current_users:
        bot.reply_to(message, "📭 لا يوجد مشتركين في القاعدة حتى الآن.")
        return

    response = f"👥 **قائمة المشتركين المسجلين (الإجمالي: {len(current_users)}):**\n\n"
    markup = types.InlineKeyboardMarkup()
    
    for uid, info in current_users.items():
        fname = info.get('first_name', 'مستخدم')
        uname = info.get('username', 'بدون معرف')
        expiry = info.get('expiry_date', 'غير متوفر')
        
        response += f"👤 الاسم: {fname}\n🆔 المعرف: `{uid}`\n🌐 اليوزر: @{uname}\n⏳ ينتهي في: {expiry}\n------------------\n"
        markup.add(types.InlineKeyboardButton(f"🔗 فتح الملف الشخصي", url=f"tg://user?id={uid}"))

    if len(response) > 4000:
        response = response[:4000] + "\n...(تم اختصار القائمة لطولها)"

    bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode="Markdown")

# --- أمر إضافة الأيام للمشتركين /add_days ---
@bot.message_handler(commands=['add_days'])
def add_user_days(message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "الاستخدام الصحيح:\n`/add_days ID days`", parse_mode="Markdown")
        return

    target_id = args[1]
    try:
        days_to_add = int(args[2])
    except ValueError:
        bot.reply_to(message, "يرجى كتابة رقم صحيح للأيام.")
        return

    current_users = load_users()
    if target_id in current_users:
        try:
            current_expiry = datetime.strptime(current_users[target_id]["expiry_date"], "%Y-%m-%d %H:%M:%S")
            if current_expiry < datetime.now():
                current_expiry = datetime.now()
            new_expiry = current_expiry + timedelta(days=days_to_add)
            current_users[target_id]["expiry_date"] = new_expiry.strftime("%Y-%m-%d %H:%M:%S")
            save_users(current_users)
            bot.reply_to(message, f"تمت إضافة {days_to_add} أيام بنجاح للمستخدم `{target_id}`.", parse_mode="Markdown")
        except Exception as e:
            bot.reply_to(message, f"حدث خطأ أثناء تحديث تاريخ الاشتراك: {e}")
    else:
        bot.reply_to(message, "المستخدم غير مسجل في قاعدة البيانات.")

# --- خيط مراقبة الأسعار في الخلفية (Background Price Monitor) ---
def background_price_monitor():
    """خيط خلفي لإدارة وتنبيهات الأسعار الخاصة بالمشتركين"""
    while True:
        try:
            pass
        except Exception as e:
            print(f"Monitor error: {e}")
        time.sleep(60)

# تشغيل مراقب الأسعار بخيط مستقل
monitor_thread = threading.Thread(target=background_price_monitor, daemon=True)
monitor_thread.start()

# --- التشغيل المستمر للبوت ---
if __name__ == "__main__":
    print("Bot is starting...")
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as e:
            print(f"Polling error occurred: {e}")
            time.sleep(5)
