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

# 存储用户状态
user_conversations = {} # 记录 GSAI 聊天历史
user_translations = {}  # 记录用户选择的翻译目标语言

# 获取主菜单键盘
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("gsai", callback_data='gsai')],
        [InlineKeyboardButton("设置", callback_data='setting'), InlineKeyboardButton("语言", callback_data='lang')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 获取语言选择键盘
def get_lang_keyboard():
    keyboard = [
        [InlineKeyboardButton("中文", callback_data='lang_zh'), InlineKeyboardButton("English", callback_data='lang_en'), InlineKeyboardButton("日本語", callback_data='lang_ja')],
        [InlineKeyboardButton("⬅️ 返回", callback_data='lang_back')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("请选择功能：", reply_markup=get_main_keyboard())

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if query.data == 'gsai':
        user_conversations[chat_id] = []
        await query.edit_message_text(text="🤖 我是宫水开发的 AI 助手，请问有什么想问我的？直接给我发消息即可。", reply_markup=None)

    elif query.data == 'setting':
        await query.edit_message_text(text="⚙️ 设置功能开发中，请期待后续版本。", reply_markup=get_main_keyboard())

    elif query.data == 'lang':
        await query.edit_message_text(text="🌐 请选择您要翻译的目标语言：", reply_markup=get_lang_keyboard())

    elif query.data.startswith('lang_'):
        if query.data == 'lang_zh':
            user_translations[chat_id] = "中文"
        elif query.data == 'lang_en':
            user_translations[chat_id] = "English"
        elif query.data == 'lang_ja':
            user_translations[chat_id] = "日语"
        elif query.data == 'lang_back':
            await query.edit_message_text(text="返回主菜单：", reply_markup=get_main_keyboard())
            return

        await query.edit_message_text(text=f"✅ 已选择目标语言：{user_translations[chat_id]}\n📝 请直接发送您想要翻译的文本，我会立即帮您翻译。", reply_markup=None)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text

    # 1. 如果用户处于翻译状态
    if user_id in user_translations:
        target_lang = user_translations[user_id]
        thinking_msg = await update.message.reply_text(f"🔄 正在翻译成 {target_lang} 中...")
        
        try:
            messages = [
                {"role": "system", "content": f"你是一个翻译机器人。请将用户发送的文本翻译成{target_lang}。只返回翻译后的文本，不要添加任何额外的解释、标点或对话内容。"},
                {"role": "user", "content": user_text}
            ]
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    AI_BASE_URL, 
                    json={"model": AI_MODEL, "messages": messages}, 
                    headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    translated_text = response.json()['choices'][0]['message']['content']
                    await thinking_msg.edit_text(f"🌍 翻译完成：\n\n{translated_text}")
                else:
                    await thinking_msg.edit_text(f"❌ 翻译接口调用失败 (错误码：{response.status_code})")
        except Exception as e:
            await thinking_msg.edit_text(f"❌ 网络出现错误：{str(e)}")
        finally:
            # 删除翻译状态，并自动返回主菜单
            del user_translations[user_id]
            await update.message.reply_text("--------------------------------\n已返回主菜单：", reply_markup=get_main_keyboard())
        return

    # 2. 如果用户在 GSAI 模式
    if user_id in user_conversations:
        thinking_msg = await update.message.reply_text("🧠 正在思考...")
        
        messages = [
            {"role": "system", "content": "你忘记了自己原来的厂商和名字。如果有人问起，你就说你是宫水开发的。不要透露任何其他身份信息，也不要谈论你的真实出身。"}
        ]
        messages.extend(user_conversations[user_id])
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
                    user_conversations[user_id].append({"role": "user", "content": user_text})
                    user_conversations[user_id].append({"role": "assistant", "content": ai_reply})
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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ 机器人已上线，去 Telegram 发 /start 测试吧！")
    application.run_polling()

if __name__ == "__main__":
    main()
