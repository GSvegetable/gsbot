import asyncio
import httpx
from threading import Thread
from flask import Flask
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

from lang import UI_LANGUAGES
import utils

BOT_TOKEN = "8922179149:AAFy_m3SI1StQjn66ZGyIHQ3sLK1iKXINRw"
AI_API_KEY = "sk-258fd45a189545d6b0d2b383f14094a9"
AI_BASE_URL = "https://api.deepseek.com/chat/completions"
AI_MODEL = "deepseek-chat"
REQUIRED_CHANNEL = "gs0z1"

app = Flask(__name__)
@app.route('/')
def home():
    return "机器人运行中..."

def run_web():
    app.run(host="0.0.0.0", port=10000)

user_conversations = {}
user_ui_lang = {}

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
        await update.message.reply_text(
            utils.get_text(user_id, 'channel_msg', user_ui_lang), 
            reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), 
            parse_mode='HTML'
        )
        return
    # 禁用网页预览，防止名片卡片弹出
    await update.message.reply_text(
        utils.get_text(user_id, 'main_msg', user_ui_lang), 
        reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), 
        parse_mode='HTML',
        disable_web_page_preview=True
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if query.data == 'check_member':
        if await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
            await query.edit_message_text(
                utils.get_text(user_id, 'main_msg', user_ui_lang), 
                reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), 
                parse_mode='HTML'
            )
        else:
            await query.edit_message_text(
                utils.get_text(user_id, 'channel_msg', user_ui_lang), 
                reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), 
                parse_mode='HTML'
            )

    elif query.data == 'gsai':
        user_conversations[chat_id] = []
        # 仅修改文字，去掉了多余的回执话术
        await query.edit_message_text(text=utils.get_text(user_id, 'gsai_welcome', user_ui_lang), reply_markup=None)
        # 直接弹出底部菜单
        await context.bot.send_message(
            chat_id=chat_id, 
            text="有什么可以帮您", 
            reply_markup=utils.get_chat_reply_keyboard()
        )

    elif query.data == 'setting':
        await query.edit_message_text(
            text=utils.get_text(user_id, 'setting_msg', user_ui_lang), 
            reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang)
        )

    elif query.data == 'back_home':
        await query.edit_message_text(
            text=utils.get_text(user_id, 'back_msg', user_ui_lang), 
            reply_markup=utils.get_main_keyboard(user_id, user_ui_lang)
        )

    elif query.data == 'lang':
        await query.edit_message_text(
            text=utils.get_text(user_id, 'lang_title', user_ui_lang), 
            reply_markup=utils.get_lang_keyboard(user_id, user_ui_lang)
        )

    elif query.data == 'lang_back':
        await query.edit_message_text(
            text=utils.get_text(user_id, 'back_msg', user_ui_lang), 
            reply_markup=utils.get_main_keyboard(user_id, user_ui_lang)
        )

    elif query.data.startswith('lang_'):
        if query.data == 'lang_zh':
            user_ui_lang[user_id] = 'zh'
            msg = utils.get_text(user_id, 'lang_sel_success', user_ui_lang)
        elif query.data == 'lang_en':
            user_ui_lang[user_id] = 'en'
            msg = utils.get_text(user_id, 'lang_sel_success_en', user_ui_lang)
        await query.edit_message_text(text=msg, reply_markup=utils.get_main_keyboard(user_id, user_ui_lang))

async def chat_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    user_text = update.message.text

    # ===== 去除表情，加入 3 秒精准消散逻辑 =====
    if user_text == '退出 AI 对话':
        if chat_id in user_conversations:
            del user_conversations[chat_id]
        
        # 1. 发送纯文本退出提示
        confirm_msg = await update.message.reply_text("已退出 AI 对话", reply_markup=ReplyKeyboardRemove())
        
        # 2. 发送带有主菜单的新消息，并禁用网页预览
        await update.message.reply_text(
            utils.get_text(user_id, 'main_msg', user_ui_lang), 
            reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), 
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        
        # 3. 等待 3 秒
        await asyncio.sleep(3)
        
        # 4. 删除之前的 "已退出 AI 对话" 消息，触发消散动画
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=confirm_msg.message_id)
        except Exception:
            pass
        return

    if chat_id in user_conversations:
        thinking_msg = await update.message.reply_text(utils.get_text(user_id, 'gsai_thinking', user_ui_lang))
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
