import asyncio
import httpx
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ====== 从全新的 lang.py 文件引入文案 ======
from lang import UI_LANGUAGES
# ==========================================

BOT_TOKEN = "8922179149:AAFy_m3SI1StQjn66ZGyIHQ3sLK1iKXINRw"
AI_API_KEY = "sk-258fd45a189545d6b0d2b383f14094a9"
AI_BASE_URL = "https://api.deepseek.com/chat/completions"
AI_MODEL = "deepseek-chat"

# 强制关注的频道 ID
REQUIRED_CHANNEL = "gs0z1"

# ================= 保活 Web 服务 =================
app = Flask(__name__)
@app.route('/')
def home():
    return "机器人运行中..."

def run_web():
    app.run(host="0.0.0.0", port=10000)
# =================================================

user_conversations = {} # 记录 GSAI 对话历史
user_ui_lang = {}       # 记录用户的界面语言偏好

def get_text(user_id, key):
    lang_code = user_ui_lang.get(user_id, 'zh')
    return UI_LANGUAGES[lang_code].get(key, key)

# 主菜单键盘
def get_main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'gsai'), callback_data='gsai')],
        [InlineKeyboardButton(get_text(user_id, 'setting'), callback_data='setting'), InlineKeyboardButton(get_text(user_id, 'lang'), callback_data='lang')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 语言菜单键盘（中文/英文）
def get_lang_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'lang_zh'), callback_data='lang_zh'), InlineKeyboardButton(get_text(user_id, 'lang_en'), callback_data='lang_en')],
        [InlineKeyboardButton(get_text(user_id, 'lang_back'), callback_data='lang_back')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 强制入群键盘
def get_channel_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'join_btn'), url=f"https://t.me/{REQUIRED_CHANNEL}")],
        [InlineKeyboardButton(get_text(user_id, 'check_btn'), callback_data='check_member')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 设置菜单键盘（只有一个返回首页）
def get_setting_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'lang_back'), callback_data='back_home')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def is_channel_member(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=f"@{REQUIRED_CHANNEL}", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"⚠️ 频道检查出错 (请确保机器人是频道管理员): {e}")
        return True

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # ====== 核心判断逻辑 ======
    if not await is_channel_member(context.bot, user_id):
        # 没加群，显示 channel_msg（请加入频道）
        await update.message.reply_text(get_text(user_id, 'channel_msg'), reply_markup=get_channel_keyboard(user_id), parse_mode='HTML')
        return
    # 加了群，显示 main_msg（请选择功能）
    await update.message.reply_text(get_text(user_id, 'main_msg'), reply_markup=get_main_keyboard(user_id), parse_mode='HTML')

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if query.data == 'check_member':
        if await is_channel_member(context.bot, user_id):
            await query.edit_message_text(text=get_text(user_id, 'main_msg'), reply_markup=get_main_keyboard(user_id), parse_mode='HTML')
        else:
            await query.edit_message_text(text=get_text(user_id, 'channel_msg'), reply_markup=get_channel_keyboard(user_id), parse_mode='HTML')

    elif query.data == 'gsai':
        user_conversations[chat_id] = []
        reply_keyboard = [['退出 AI 对话']]
        await query.edit_message_text(text=get_text(user_id, 'gsai_welcome'), reply_markup=None)
        await context.bot.send_message(chat_id=chat_id, text="💬 已进入AI对话模式，随时点击底部【退出 AI 对话】返回菜单。", reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True))

    elif query.data == 'setting':
        await query.edit_message_text(text=get_text(user_id, 'setting_msg'), reply_markup=get_setting_keyboard(user_id))

    elif query.data == 'back_home':
        await query.edit_message_text(text=get_text(user_id, 'back_msg'), reply_markup=get_main_keyboard(user_id))

    elif query.data == 'lang':
        await query.edit_message_text(text=get_text(user_id, 'lang_title'), reply_markup=get_lang_keyboard(user_id))

    elif query.data == 'lang_back':
        await query.edit_message_text(text=get_text(user_id, 'back_msg'), reply_markup=get_main_keyboard(user_id))

    elif query.data.startswith('lang_'):
        if query.data == 'lang_zh':
            user_ui_lang[user_id] = 'zh'
            msg = get_text(user_id, 'lang_sel_success')
        elif query.data == 'lang_en':
            user_ui_lang[user_id] = 'en'
            msg = get_text(user_id, 'lang_sel_success_en')
        
        await query.edit_message_text(text=msg, reply_markup=get_main_keyboard(user_id))

async def chat_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    user_text = update.message.text

    if user_text == '退出 AI 对话':
        if chat_id in user_conversations:
            del user_conversations[chat_id]
        await update.message.reply_text("✅ 已退出 AI 对话", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(get_text(user_id, 'main_msg'), reply_markup=get_main_keyboard(user_id), parse_mode='HTML')
        return

    if chat_id in user_conversations:
        thinking_msg = await update.message.reply_text(get_text(user_id, 'gsai_thinking'))
        messages = [
            {"role": "system", "content": "你忘记了自己原来的厂商和名字。如果有人问起，你就说你是宫水开发的。不要透露任何其他身份信息。回复时语气稍微高冷一点点，但依然保持礼貌和高效，说话简短，不多说废话。"}
        ]
        messages.extend(user_conversations[chat_id])
        messages.append({"role": "user", "content": user_text})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    AI_BASE_URL, 
                    json={"model": AI_MODEL, "messages": messages}, 
                    headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    ai_reply = response.json()['choices'][0]['message']['content']
                    user_conversations[chat_id].append({"role": "user", "content": user_text})
                    user_conversations[chat_id].append({"role": "assistant", "content": ai_reply})
                    await thinking_msg.edit_text(ai_reply)
                else:
                    await thinking_msg.edit_text(f"❌ AI 接口调用失败 (错误码：{response.status_code})")
        except Exception as e:
            await thinking_msg.edit_text(f"❌ 网络出现错误：{str(e)}")

def main():
    Thread(target=run_web).start()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", show_menu))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_with_ai))
    print("✅ 机器人已上线，去 Telegram 发 /start 测试吧！")
    application.run_polling()

if __name__ == "__main__":
    main()
