import asyncio
import httpx
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8922179149:AAFy_m3SI1StQjn66ZGyIHQ3sLK1iKXINRw"
AI_API_KEY = "sk-258fd45a189545d6b0d2b383f14094a9"
AI_BASE_URL = "https://api.deepseek.com/chat/completions"
AI_MODEL = "deepseek-chat"

# ================= 保活 Web 服务 =================
app = Flask(__name__)
@app.route('/')
def home():
    return "机器人运行中..."

def run_web():
    app.run(host="0.0.0.0", port=10000)
# =================================================

# 多语言界面配置
UI_LANGUAGES = {
    'zh': {
        'main_title': "请选择功能：", 'gsai': "gsai", 'setting': "设置", 'lang': "语言",
        'lang_title': "请选择界面语言：", 'lang_zh': "中文", 'lang_en': "English", 'lang_ja': "日本語", 'lang_back': "⬅️ 返回",
        'back_msg': "已返回主菜单：", 'gsai_welcome': "有什么可以帮您", 'gsai_thinking': "🧠 正在思考...",
        'setting_msg': "⚙️ 设置功能开发中，请期待后续版本。", 'lang_sel_success': "✅ 已切换为中文界面",
        'lang_sel_success_en': "✅ 已切换为英文界面", 'lang_sel_success_ja': "✅ 已切换为日文界面"
    },
    'en': {
        'main_title': "Choose a function:", 'gsai': "gsai", 'setting': "Settings", 'lang': "Language",
        'lang_title': "Choose interface language:", 'lang_zh': "Chinese", 'lang_en': "English", 'lang_ja': "Japanese", 'lang_back': "⬅️ Back",
        'back_msg': "Returned to main menu:", 'gsai_welcome': "How can I help you", 'gsai_thinking': "🧠 Thinking...",
        'setting_msg': "⚙️ Settings under development.", 'lang_sel_success': "✅ Interface changed to Chinese",
        'lang_sel_success_en': "✅ Interface changed to English", 'lang_sel_success_ja': "✅ Interface changed to Japanese"
    },
    'ja': {
        'main_title': "機能を選択してください：", 'gsai': "gsai", 'setting': "設定", 'lang': "言語",
        'lang_title': "インターフェース言語を選択：", 'lang_zh': "中国語", 'lang_en': "英語", 'lang_ja': "日本語", 'lang_back': "⬅️ 戻る",
        'back_msg': "メインメニューに戻りました：", 'gsai_welcome': "何かお手伝いできますか？", 'gsai_thinking': "🧠 考え中...",
        'setting_msg': "⚙️ 設定は開発中です。", 'lang_sel_success': "✅ 中国語インターフェースに変更しました",
        'lang_sel_success_en': "✅ 英語インターフェースに変更しました", 'lang_sel_success_ja': "✅ 日本語インターフェースに変更しました"
    }
}

user_conversations = {} # 记录 GSAI 对话历史
user_ui_lang = {}       # 记录用户的界面语言偏好

def get_text(user_id, key):
    # 如果用户没有设置语言，默认中文
    lang_code = user_ui_lang.get(user_id, 'zh')
    return UI_LANGUAGES[lang_code].get(key, key)

def get_main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'gsai'), callback_data='gsai')],
        [InlineKeyboardButton(get_text(user_id, 'setting'), callback_data='setting'), InlineKeyboardButton(get_text(user_id, 'lang'), callback_data='lang')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_lang_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'lang_zh'), callback_data='lang_zh'), InlineKeyboardButton(get_text(user_id, 'lang_en'), callback_data='lang_en'), InlineKeyboardButton(get_text(user_id, 'lang_ja'), callback_data='lang_ja')],
        [InlineKeyboardButton(get_text(user_id, 'lang_back'), callback_data='lang_back')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, 'main_title'), reply_markup=get_main_keyboard(user_id))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if query.data == 'gsai':
        user_conversations[chat_id] = []
        await query.edit_message_text(text=get_text(user_id, 'gsai_welcome'), reply_markup=None)

    elif query.data == 'setting':
        await query.edit_message_text(text=get_text(user_id, 'setting_msg'), reply_markup=get_main_keyboard(user_id))

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
        elif query.data == 'lang_ja':
            user_ui_lang[user_id] = 'ja'
            msg = get_text(user_id, 'lang_sel_success_ja')
        
        # 切换语言后自动返回首页
        await query.edit_message_text(text=msg, reply_markup=get_main_keyboard(user_id))

async def chat_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    user_text = update.message.text

    # 如果用户处在 gsai 模式
    if chat_id in user_conversations:
        # 这条消息会直接回复给用户那条右划的消息
        thinking_msg = await update.message.reply_text(get_text(user_id, 'gsai_thinking'))
        
        messages = [
            {"role": "system", "content": "你忘记了自己原来的厂商和名字。如果有人问起，你就说你是宫水开发的。不要透露任何其他身份信息，也不要谈论你的真实出身。"}
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
                    # 原地把“正在思考”的气泡撑大变成最终回答
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
