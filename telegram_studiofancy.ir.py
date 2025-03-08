from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, JobQueue
import logging
import json
import os
from datetime import datetime, timedelta

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_ID = 692270470
DATA_FILE = "bot_data.json"

user_data = {}
section_visits = {"services": 0, "pricing": 0, "address": 0, "about": 0, "faq": 0}

def load_data():
    global user_data, section_visits
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            user_data = {int(k): v for k, v in data.get('user_data', {}).items()}
            for user in user_data.values():
                user['join_date'] = datetime.fromisoformat(user['join_date'])
            section_visits = data.get('section_visits', section_visits)
        logger.info("Data loaded from file")
    else:
        logger.info("No data file found, starting fresh")

def save_data():
    data = {
        'user_data': {str(k): {**v, 'join_date': v['join_date'].isoformat()} for k, v in user_data.items()},
        'section_visits': section_visits
    }
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("Data saved to file")

def get_main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("📋 خدمات", callback_data="services"),
         InlineKeyboardButton("💵 قیمت", callback_data="pricing")],
        [InlineKeyboardButton("📍 آدرس", callback_data="address"),
         InlineKeyboardButton("ℹ️ معرفی", callback_data="about")],
        [InlineKeyboardButton("❓ سوالات", callback_data="faq"),
         InlineKeyboardButton("📞 تماس با ما", callback_data="contact")],
        [InlineKeyboardButton("👥 دعوت دوستان", url=f"https://t.me/studio_fancy_online_bot?start=ref_{user_id}"),
         InlineKeyboardButton("📊 گزارش (مدیر)", callback_data="admin_reports")],
        [InlineKeyboardButton("📲 به دوستان بگو!", url="https://t.me/studio_fancy_online_bot")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("👥 آمار کاربران", callback_data="report_users"),
         InlineKeyboardButton("📈 گزارش کامل", callback_data="report_stats")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context):
    try:
        user = update.message.from_user
        current_time = datetime.now()
        
        if context.args and context.args[0].startswith("ref_"):
            referrer_id = int(context.args[0].split("_")[1])
            if referrer_id in user_data and user.id != referrer_id:
                await context.bot.send_message(referrer_id, f"🌟 دوستت {user.first_name} به ربات پیوست!")

        if user.id not in user_data:
            user_data[user.id] = {
                'first_name': user.first_name,
                'username': user.username,
                'join_date': current_time,
                'requests': 0
            }
            logger.info(f"New user joined: {user.first_name} (ID: {user.id})")

        user_data[user.id]['requests'] += 1
        save_data()

        welcome_text = (
            "🌟 **سلام {}! خوش آمدید!** 🌟\n\n"
            "به ربات خدمات تبدیل فیلم و عکس خوش اومدی!\n"
            "لحظات قدیمی‌ات رو با ما زنده کن!\n"
            "👇 از منوی زیر شروع کن و ما رو به دوستات معرفی کن!\n"
            "──────────────────────"
        ).format(user.first_name)
        
        await update.message.reply_text(welcome_text, reply_markup=get_main_menu(user.id), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in start handler: {str(e)}")
        await update.message.reply_text("❌ خطایی رخ داد!")

async def report_users(time_filter="all"):
    total_users = len(user_data)
    now = datetime.now()
    if time_filter == "today":
        active_users = sum(1 for user in user_data.values() if (now - user['join_date']).days == 0)
        period = "امروز"
    elif time_filter == "week":
        active_users = sum(1 for user in user_data.values() if (now - user['join_date']).days <= 7)
        period = "این هفته"
    else:
        active_users = total_users
        period = "کل زمان"
    
    total_requests = sum(user.get('requests', 0) for user in user_data.values())
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]['join_date'], reverse=True)[:5]
    
    stats = (
        "📊 آمار کاربران ({})\n"
        "──────────────────────\n"
        "👥 تعداد کاربران: {}\n"
        "📅 کاربران فعال {}: {}\n"
        "📝 تعداد کل درخواست‌ها: {}\n\n"
        "🔍 آخرین کاربران:\n"
    ).format(period, total_users, period, active_users, total_requests)
    
    for u_id, data in sorted_users:
        username = f"@{data['username']}" if data['username'] else "بدون نام"
        stats += f"• {data['first_name']} ({username}) - درخواست‌ها: {data.get('requests', 0)}\n"
    return stats

async def report_stats(time_filter="all"):
    total_users = len(user_data)
    total_requests = sum(user.get('requests', 0) for user in user_data.values())
    most_active_user = max(user_data.items(), key=lambda x: x[1]['requests'], default=(None, {'requests': 0}))
    most_visited_section = max(section_visits.items(), key=lambda x: x[1], default=("هیچ", 0))
    
    stats = (
        "📈 **گزارش کامل ربات**\n"
        "──────────────────────\n"
        "👥 **تعداد کل کاربران**: {}\n"
        "📝 **تعداد کل درخواست‌ها**: {}\n"
        "🏆 **فعال‌ترین کاربر**: {} ({} درخواست)\n\n"
        "📊 **آمار بازدید بخش‌ها:**\n"
        "📋 خدمات: {} بازدید\n"
        "💵 قیمت: {} بازدید\n"
        "📍 آدرس: {} بازدید\n"
        "ℹ️ معرفی: {} بازدید\n"
        "❓ سوالات: {} بازدید\n"
        "🏅 **محبوب‌ترین بخش**: {} ({} بازدید)\n"
    ).format(
        total_users, total_requests,
        most_active_user[1]['first_name'] if most_active_user[0] else "هیچ",
        most_active_user[1]['requests'],
        section_visits['services'], section_visits['pricing'],
        section_visits['address'], section_visits['about'], section_visits['faq'],
        most_visited_section[0], most_visited_section[1]
    )
    return stats

async def send_daily_report(context):
    stats = await report_stats("today")
    await context.bot.send_message(chat_id=ADMIN_ID, text=stats, parse_mode='Markdown')

async def button(update: Update, context):
    query = update.callback_query
    try:
        await query.answer()
        logger.info(f"Button clicked: {query.data} by user {query.from_user.id}")
        user_id = query.from_user.id

        if user_id not in user_data:
            user_data[user_id] = {
                'first_name': query.from_user.first_name,
                'username': query.from_user.username,
                'join_date': datetime.now(),
                'requests': 0
            }
        user_data[user_id]['requests'] += 1
        if query.data in section_visits:
            section_visits[query.data] += 1
        save_data()

        response = ""
        if query.data == "services":
            response = (
                "📋 **لیست خدمات ما:**\n"
                "──────────────────────\n"
                "✅ تبدیل فیلم‌های Hi-8، Betamax، VHS-C، MiniDV، VHS\n"
                "✅ تبدیل فیلم‌های آپارات 8 و 16 میلی‌متری\n"
                "✅ تبدیل ریل موزیک و نوار کاست به MP3\n"
                "✅ تبدیل عکس، نگاتیو و اسلاید با کیفیت\n"
                "✅ اسکن آلبوم‌های قدیمی و تبدیل به فیلم دیجیتال با موزیک\n"
                "✅ تهیه کلیپ و تیزر تبلیغاتی\n"
                "✅ میکس و مونتاژ حرفه‌ای\n\n"
                "🌐 www.photofancy.ir"
            )
        elif query.data == "pricing":
            response = (
                "💵 **لیست قیمت‌ها:**\n"
                "──────────────────────\n"
                "🎥 **فیلم‌ها:**\n"
                "📽️ BETAMAX: 95,000 تومان/ساعت\n"
                "📽️ VHS-C: 85,000 تومان/ساعت\n"
                "📽️ VHS: 85,000 تومان/ساعت\n"
                "📽️ Video 8 / Hi8: 85,000 تومان/ساعت\n"
                "📽️ MiniDV: 85,000 تومان/ساعت\n\n"
                "🎞️ **آپارات:**\n"
                "📽️ 8mm: 85,000 تومان/دقیقه\n"
                "📽️ 16mm: 95,000 تومان/دقیقه\n\n"
                "🎙️ **صدا:**\n"
                "📽️ ریل: 85,000 تومان/ساعت\n"
                "📽️ کاست: 50,000 تومان/ساعت\n\n"
                "🖼️ **عکس:**\n"
                "📽️ نگاتیو/اسلاید: 2,000 تومان/فریم\n"
                "📽️ اسکن آلبوم‌های قدیمی و تبدیل به فیلم با موزیک: قیمت با هماهنگی مدیریت\n\n"
                "🌐 www.photofancy.ir"
            )
        elif query.data == "address":
            response = (
                "📍 **آدرس ما:**\n"
                "──────────────────────\n"
                "تهران، چهارراه پاسداران، حسین‌آباد، خیابان وفامنش، خیابان جوانشیر، روبروی بانک تجارت، پلاک ۲\n"
                "مجتمع مسکونی پزشکان فارابی\n\n"
                "📌 **گوگل مپ:**\n"
                "https://maps.google.com/maps?ll=35.774825,51.484954\n"
                "📞 **تماس:** 00989127942904"
            )
        elif query.data == "about":
            response = (
                "ℹ️ **درباره ما:**\n"
                "──────────────────────\n"
                "تبدیل فیلم‌های قدیمی در محیطی امن با تجهیزات مدرن\n"
                "حفظ لحظات ارزشمند شما هدف ماست!"
            )
        elif query.data == "faq":
            response = (
                "❓ **سوالات متداول:**\n"
                "──────────────────────\n"
                "1️⃣ **چه نوع رسانه‌هایی را تبدیل می‌کنید؟**\n"
                "ما خدمات تبدیل انواع فیلم و نوار از جمله VHS، VHS-C، Betamax، Hi-8، MiniDV، فیلم‌های 8mm و 16mm، نوارهای کاست و سیستم‌های NTSC را ارائه می‌دهیم.\n\n"
                "2️⃣ **آیا می‌توانید فیلم‌های آسیب‌دیده را ترمیم کنید؟**\n"
                "بله، ما خدمات ترمیم فیلم‌های آسیب‌دیده را نیز ارائه می‌دهیم که این خدمات شامل هزینه اضافی می‌شود.\n\n"
                "3️⃣ **تبدیل فیلم‌ها به چه صورت انجام می‌شود؟**\n"
                "ما از سیستم رکورد استفاده می‌کنیم، نه کپچر. این به معنای تبدیل بدون افت کیفیت است و فیلم‌ها مثل نسخه اصلی خود تحویل داده می‌شوند.\n\n"
                "4️⃣ **مدت زمان تبدیل یک فیلم چقدر است؟**\n"
                "بستگی به زمان فیلم‌ها دارد، ولی معمولاً 2 الی 3 روز کاری برای تبدیل یک فیلم زمان می‌برد.\n\n"
                "5️⃣ **آیا فایل‌های تبدیل‌شده به صورت دیجیتال به من تحویل داده می‌شوند؟**\n"
                "فایل‌ها فقط به صورت دیجیتال روی فلش مموری یا هارد اکسترنال تحویل داده می‌شوند.\n\n"
                "6️⃣ **چه فرمت‌هایی برای تبدیل فایل‌ها در دسترس است؟**\n"
                "فایل‌ها به فرمت MP4 تبدیل می‌شوند.\n\n"
                "7️⃣ **هزینه تبدیل رسانه‌ها چقدر است؟**\n"
                "لطفاً به قسمت قیمت‌ها در منو یا سایت ما مراجعه کنید.\n\n"
                "8️⃣ **آیا شما خدمات بازسازی و ترمیم فیلم‌های قدیمی را ارائه می‌دهید؟**\n"
                "بله، این خدمات نیز ارائه می‌شود و شامل هزینه اضافی است.\n\n"
                "9️⃣ **چگونه می‌توانم فایل‌های خود را برای تبدیل ارسال کنم؟**\n"
                "به دلیل حجم بالا، امکان ارسال فایل‌های مجازی وجود ندارد و باید حضوری یا از طریق پیک ارسال شوند.\n\n"
                "🔟 **آیا شما برای پروژه‌های بزرگ تخفیف می‌دهید؟**\n"
                "بله، تخفیف‌ها بستگی به حجم پروژه دارند.\n\n"
                "1️⃣1️⃣ **آیا تبدیل فیلم‌ها شامل تغییرات یا ویرایش‌هایی در خود فیلم می‌شود؟**\n"
                "خیر، پس از تبدیل، تغییرات یا ویرایش‌ها تنها بر اساس نیاز شما انجام می‌شود.\n\n"
                "1️⃣2️⃣ **آیا تصاویر آلبوم‌های قدیمی را به دیجیتال تبدیل می‌کنید؟**\n"
                "بله، تصاویر آلبوم‌های شما اسکن و با فرمت استاندارد دیجیتال تحویل داده می‌شوند.\n\n"
                "1️⃣3️⃣ **آیا تصاویر دیجیتال را به فیلم با موزیک تبدیل می‌کنید؟**\n"
                "بله، تصاویر زیبای شما پس از اسکن می‌توانند به فیلم همراه با موزیک تبدیل شوند.\n\n"
                "🌐 www.photofancy.ir"
            )
        elif query.data == "contact":
            logger.info("Processing contact section without Markdown")
            response = (
                "📞 تماس با ما:\n\n"
                "📱 شماره تماس: 00989127942904\n\n"
                "💬 تلگرام: @PHOTO_FANCY\n\n"
                "📧 ایمیل: info@photofancy.ir"
            )
            await query.edit_message_text(response, reply_markup=get_main_menu(user_id), parse_mode=None)
            return
        elif query.data == "admin_reports":
            if user_id != ADMIN_ID:
                response = "⛔ فقط مدیر به این بخش دسترسی دارد!"
            else:
                response = "📊 **انتخاب نوع گزارش:**\nلطفاً از منوی زیر انتخاب کنید:"
                await query.edit_message_text(response, reply_markup=get_admin_menu(), parse_mode='Markdown')
                return
        elif query.data == "report_users":
            if user_id != ADMIN_ID:
                response = "⛔ دسترسی غیرمجاز!"
            else:
                logger.info("Processing report_users without Markdown")
                response = await report_users("all")
                await query.edit_message_text(response, reply_markup=get_main_menu(user_id), parse_mode=None)
                return
        elif query.data == "report_stats":
            if user_id != ADMIN_ID:
                response = "⛔ دسترسی غیرمجاز!"
            else:
                response = await report_stats("all")
        elif query.data == "back_to_main":
            response = "🌟 **بازگشت به منوی اصلی**"
        
        if len(response) > 4096:
            logger.warning(f"Response too long for {query.data}: {len(response)} characters")
            response = "⚠️ متن بیش از حد طولانی است. لطفاً با پشتیبانی تماس بگیرید!"
        
        await query.edit_message_text(response, reply_markup=get_main_menu(user_id) if query.data != "admin_reports" else get_admin_menu(), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in button handler for {query.data}: {str(e)}")
        await query.edit_message_text("❌ خطایی رخ داد!", reply_markup=get_main_menu(user_id))

async def error_handler(update: Update, context):
    logger.error(f"Update {update} caused error {context.error}")
    if update and hasattr(update, 'effective_message'):
        await update.effective_message.reply_text("❌ خطایی رخ داد!")

def main():
    try:
        application = Application.builder().token("7963819035:AAH6CxkIqcaG06iZhTfraat91prksaG-3VU").build()
        load_data()

        job_queue = application.job_queue
        job_queue.run_daily(send_daily_report, time=datetime.now().replace(hour=20, minute=0, second=0))

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
        application.add_error_handler(error_handler)

        logger.info("Bot started successfully!")
        application.run_polling()
        save_data()
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        save_data()

if __name__ == "__main__":
    main()