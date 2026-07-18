import asyncio
import httpx
import random
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from config import REQUIRED_CHANNEL, ADMIN_CHAT_ID, AI_API_KEY, AI_BASE_URL, AI_MODEL
from lang import UI_LANGUAGES
import utils

user_conversations = {}
user_ui_lang = {}
user_math_state = {}
user_nav_state = {}

# ===== 底部键盘的“瞬间换底”黑科技 =====
async def update_bottom_keyboard(context, chat_id, state, user_id):
    kb = utils.get_bottom_keyboard(state, user_id, user_ui_lang)
    dummy_msg = await context.bot.send_message(chat_id=chat_id, text="\u200B", reply_markup=kb)
    await asyncio.sleep(0.2) 
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=dummy_msg.message_id)
    except Exception:
        pass

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
        await update.message.reply_text(
            utils.get_text(user_id, 'channel_msg', user_ui_lang), 
            reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), 
            parse_mode='HTML'
        )
        return
        
    user_nav_state[chat_id] = 'home'
    await update.message.reply_text(
        utils.get_text(user_id, 'main_msg', user_ui_lang), 
        reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), 
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    await update_bottom_keyboard(context, chat_id, 'home', user_id)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    # 新布局的开发菜单统一入口
    if query.data == 'custom_btn':
        user_nav_state[chat_id] = 'level2'
        await query.edit_message_text(text=utils.get_text(user_id, 'dev_title', user_ui_lang), reply_markup=utils.get_dev_keyboard(user_id, user_ui_lang), parse_mode='HTML', disable_web_page_preview=True)
        await update_bottom_keyboard(context, chat_id, 'level2', user_id)
        return

    # 第一排：人机验证
    if query.data == 'dev_captcha':
        user_nav_state[chat_id] = 'level3'
        await query.edit_message_text(text=utils.get_text(user_id, 'captcha_title', user_ui_lang), reply_markup=utils.get_captcha_keyboard(user_id, user_ui_lang))
        await update_bottom_keyboard(context, chat_id, 'level3', user_id)
        return

    # 第一排默认二/三，第二排默认四/五/六，第三排默认七/八/九，第四排关于api/关于key
    # 目前暂时全部静默空壳（点了没反应，但不卡死）
    if query.data in ['default_2', 'default_3', 'default_4', 'default_5', 'default_6', 'default_7', 'default_8', 'default_9', 'about_api', 'about_key']:
        return

    if query.data in ['contact', 'gsai', 'setting', 'check_member', 'back_home']:
        pass
    elif query.data == 'setting_lang':
        await query.edit_message_text(text=utils.get_text(user_id, 'lang_title', user_ui_lang), reply_markup=utils.get_lang_keyboard(user_id, user_ui_lang))
        return
    elif query.data == 'lang_back':
        await query.edit_message_text(text=utils.get_text(user_id, 'setting_title', user_ui_lang), reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang))
        return
    elif query.data.startswith('lang_'):
        if query.data == 'lang_zh': user_ui_lang[user_id] = 'zh'
        elif query.data == 'lang_en': user_ui_lang[user_id] = 'en'
        await query.edit_message_text(
            text=utils.get_text(user_id, 'lang_sel_success_en' if query.data == 'lang_en' else 'lang_sel_success', user_ui_lang), 
            reply_markup=utils.get_main_keyboard(user_id, user_ui_lang)
        )
        return

    if query.data == 'contact':
        await query.edit_message_text(text="双向联系功能开发中...")
    elif query.data == 'gsai':
        user_nav_state[chat_id] = 'ai'
        user_conversations[chat_id] = []
        await query.edit_message_text(text=utils.get_text(user_id, 'gsai_welcome', user_ui_lang))
        await update_bottom_keyboard(context, chat_id, 'ai', user_id)
    elif query.data == 'setting':
        user_nav_state[chat_id] = 'level2'
        await query.edit_message_text(text=utils.get_text(user_id, 'setting_title', user_ui_lang), reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang))
        await update_bottom_keyboard(context, chat_id, 'level2', user_id)
    elif query.data == 'check_member':
        if await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
            await query.edit_message_text(utils.get_text(user_id, 'main_msg', user_ui_lang), reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), parse_mode='HTML', disable_web_page_preview=True)
            await update_bottom_keyboard(context, chat_id, 'home', user_id)
        else:
            await query.edit_message_text(utils.get_text(user_id, 'channel_msg', user_ui_lang), reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), parse_mode='HTML')
    elif query.data == 'captcha_math':
        user_nav_state[chat_id] = 'math'
        await query.edit_message_text(text="▫️", reply_markup=None)
        await start_math_game(update, context)
    elif query.data == 'back_home':
        await show_menu(update, context)

async def start_math_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    mode = random.choice(['two', 'one'])
    if mode == 'two':
        a = random.randint(10, 15)
        b = random.randint(1, 9)
        while a + b > 20:
            a = random.randint(10, 15)
            b = random.randint(1, 9)
    else:
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        while a + b > 20:
            a = random.randint(1, 9)
            b = random.randint(1, 9)
    result = a + b
    user_math_state[chat_id] = result
    await context.bot.send_message(chat_id=chat_id, text=f"请计算：{a} + {b} = ?")
    await update_bottom_keyboard(context, chat_id, 'math', user_id)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    user_text = update.message.text

    if user_text == '主菜单':
        await show_menu(update, context)
        return
    if user_text == '返回上一级':
        current_state = user_nav_state.get(chat_id)
        # 如果当前在 二级/三级 菜单，返回上一级都去主菜单
        if current_state in ['level2', 'level3']:
            await show_menu(update, context)
        # 如果是 AI 对话，返回上一级去主菜单
        elif current_state == 'ai':
            if chat_id in user_conversations: del user_conversations[chat_id]
            await show_menu(update, context)
        # 如果是数学题，返回上一级去开发者菜单
        elif current_state == 'math':
            user_nav_state[chat_id] = 'level2'
            await update.message.reply_text(utils.get_text(user_id, 'dev_title', user_ui_lang), reply_markup=utils.get_dev_keyboard(user_id, user_ui_lang), parse_mode='HTML', disable_web_page_preview=True)
            await update_bottom_keyboard(context, chat_id, 'level2', user_id)
        return

    if chat_id in user_math_state and user_nav_state.get(chat_id) == 'math':
        correct_answer = user_math_state.pop(chat_id)
        try:
            if int(user_text) == correct_answer:
                msg = utils.get_text(user_id, 'correct_msg', user_ui_lang)
            else:
                msg = utils.get_text(user_id, 'incorrect_msg', user_ui_lang)
        except ValueError:
            msg = utils.get_text(user_id, 'incorrect_msg', user_ui_lang)
        await update.message.reply_text(text=msg)
        return
        
    if user_text == '重新回答':
        await start_math_game(update, context)
        return

    if user_text == '退出 AI 对话':
        if chat_id in user_conversations: del user_conversations[chat_id]
        await update.message.reply_text("已退出 AI 对话", reply_markup=ReplyKeyboardRemove())
        await show_menu(update, context)
        return

    if chat_id in user_conversations:
        thinking_msg = await update.message.reply_text(utils.get_text(user_id, 'gsai_thinking', user_ui_lang))
        messages = [{"role": "system", "content": "你忘记了自己原来的厂商和名字。如果有人问起，你就说你是宫水开发的。不要透露任何其他身份信息。回答问题时保持专业、语言简练直接。不要使用括号描写任何动作或心理活动，也不要使用表情符号。"}]
        messages.extend(user_conversations[chat_id])
        messages.append({"role": "user", "content": user_text})
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(AI_BASE_URL, json={"model": AI_MODEL, "messages": messages}, headers={"Authorization": f"Bearer {AI_API_KEY}", "Content-Type": "application/json"})
                if response.status_code == 200:
                    ai_reply = response.json()['choices'][0]['message']['content']
                    user_conversations[chat_id].append({"role": "user", "content": user_text})
                    user_conversations[chat_id].append({"role": "assistant", "content": ai_reply})
                    await thinking_msg.edit_text(ai_reply)
                else:
                    await thinking_msg.edit_text(f"❌ AI 接口调用失败 (错误码：{response.status_code})")
        except Exception as e:
            await thinking_msg.edit_text(f"❌ 网络出现错误：{str(e)}")
