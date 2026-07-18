import asyncio
import httpx
import random
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes

from config import REQUIRED_CHANNEL, ADMIN_CHAT_ID, AI_API_KEY, AI_BASE_URL, AI_MODEL
from lang import UI_LANGUAGES
import utils

# ===== 核心状态变量 =====
user_conversations = {}
user_ui_lang = {}
user_math_state = {}
user_pwd_state = {}
user_nav_state = {}  # 记录用户当前的菜单层级状态：home, level2, level3, ai, math

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    # 1. 如果用户正在等待输密码，直接打断并删除密码提示消息（伴随两秒动画）
    if chat_id in user_pwd_state:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=user_pwd_state[chat_id]['msg_id'])
        except Exception:
            pass
        del user_pwd_state[chat_id]

    # 2. 频道检测逻辑
    if not await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
        await update.message.reply_text(
            utils.get_text(user_id, 'channel_msg', user_ui_lang), 
            reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), 
            parse_mode='HTML'
        )
        return
        
    # 3. 重置状态并发主页菜单
    user_nav_state[chat_id] = 'home'
    await update.message.reply_text(
        utils.get_text(user_id, 'main_msg', user_ui_lang), 
        reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), 
        parse_mode='HTML',
        disable_web_page_preview=True
    )
    # 弹出底部键盘：初始状态只有 [主菜单]
    await update.message.reply_text("▫️", reply_markup=utils.get_bottom_keyboard('home', user_id, user_ui_lang))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    chat_id = query.message.chat_id

    # 密码锁请求 (AI, 开发, 双向, 设置)
    if query.data in ['custom_btn', 'contact', 'gsai', 'setting']:
        if chat_id in user_pwd_state:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=user_pwd_state[chat_id]['msg_id'])
            except Exception:
                pass
            del user_pwd_state[chat_id]
        pwd_msg = await query.edit_message_text(text="请输入密码：")
        user_pwd_state[chat_id] = {'target': query.data, 'msg_id': pwd_msg.message_id}
        return

    if query.data == 'check_member':
        if await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
            await query.edit_message_text(utils.get_text(user_id, 'main_msg', user_ui_lang), reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), parse_mode='HTML', disable_web_page_preview=True)
        else:
            await query.edit_message_text(utils.get_text(user_id, 'channel_msg', user_ui_lang), reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), parse_mode='HTML')
        return

    # 机器人开发菜单
    if query.data == 'dev_captcha':
        user_nav_state[chat_id] = 'level3'
        await query.edit_message_text(text=utils.get_text(user_id, 'captcha_title', user_ui_lang), reply_markup=utils.get_captcha_keyboard(user_id, user_ui_lang))
        await context.bot.send_message(chat_id=chat_id, text="▫️", reply_markup=utils.get_bottom_keyboard('level3', user_id, user_ui_lang))
        return

    if query.data == 'dev_types':
        user_nav_state[chat_id] = 'level3'
        await query.edit_message_text(text=utils.get_text(user_id, 'back_msg', user_ui_lang), reply_markup=utils.get_type_keyboard(user_id, user_ui_lang))
        await context.bot.send_message(chat_id=chat_id, text="▫️", reply_markup=utils.get_bottom_keyboard('level3', user_id, user_ui_lang))
        return

    # 数学题触发
    if query.data == 'captcha_math':
        user_nav_state[chat_id] = 'math'
        await query.edit_message_text(text="▫️", reply_markup=None)
        await start_math_game(update, context)
        return

    if query.data == 'back_home':
        user_nav_state[chat_id] = 'home'
        await query.edit_message_text(text=utils.get_text(user_id, 'main_msg', user_ui_lang), reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), parse_mode='HTML', disable_web_page_preview=True)
        await context.bot.send_message(chat_id=chat_id, text="▫️", reply_markup=utils.get_bottom_keyboard('home', user_id, user_ui_lang))
        return

    if query.data == 'setting':
        user_nav_state[chat_id] = 'level2'
        await query.edit_message_text(text=utils.get_text(user_id, 'setting_title', user_ui_lang), reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang))
        await context.bot.send_message(chat_id=chat_id, text="▫️", reply_markup=utils.get_bottom_keyboard('level2', user_id, user_ui_lang))
        return

    if query.data == 'setting_lang':
        await query.edit_message_text(text=utils.get_text(user_id, 'lang_title', user_ui_lang), reply_markup=utils.get_lang_keyboard(user_id, user_ui_lang))
        return

    if query.data == 'lang_back':
        user_nav_state[chat_id] = 'level2'
        await query.edit_message_text(text=utils.get_text(user_id, 'setting_title', user_ui_lang), reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang))
        return
    
    if query.data.startswith('lang_'):
        if query.data == 'lang_zh': user_ui_lang[user_id] = 'zh'
        elif query.data == 'lang_en': user_ui_lang[user_id] = 'en'
        await query.edit_message_text(
            text=utils.get_text(user_id, 'lang_sel_success_en' if query.data == 'lang_en' else 'lang_sel_success', user_ui_lang), 
            reply_markup=utils.get_main_keyboard(user_id, user_ui_lang)
        )
        await context.bot.send_message(chat_id=chat_id, text="▫️", reply_markup=utils.get_bottom_keyboard('home', user_id, user_ui_lang))

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
    await context.bot.send_message(chat_id=chat_id, text=f"请计算：{a} + {b} = ?", reply_markup=utils.get_bottom_keyboard('math', user_id, user_ui_lang))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    user_text = update.message.text

    # ===== 处理密码验证流程 =====
    if chat_id in user_pwd_state:
        target = user_pwd_state[chat_id]['target']
        expected_pwd = "121100" if target == 'gsai' else "012110"
        if user_text == expected_pwd:
            target_info = user_pwd_state.pop(chat_id)
            try: 
                await context.bot.delete_message(chat_id=chat_id, message_id=target_info['msg_id'])
            except Exception: 
                pass
            
            if target == 'gsai':
                user_conversations[chat_id] = []
                user_nav_state[chat_id] = 'ai'
                await update.message.reply_text(utils.get_text(user_id, 'gsai_welcome', user_ui_lang), reply_markup=utils.get_bottom_keyboard('ai', user_id, user_ui_lang))
            elif target == 'custom_btn':
                user_nav_state[chat_id] = 'level2'
                await update.message.reply_text(utils.get_text(user_id, 'dev_title', user_ui_lang), reply_markup=utils.get_dev_keyboard(user_id, user_ui_lang))
                await update.message.reply_text("▫️", reply_markup=utils.get_bottom_keyboard('level2', user_id, user_ui_lang))
            elif target == 'contact':
                await update.message.reply_text("请输入您想要联系开发者的内容：")
            elif target == 'setting':
                user_nav_state[chat_id] = 'level2'
                await update.message.reply_text(utils.get_text(user_id, 'setting_title', user_ui_lang), reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang))
                await update.message.reply_text("▫️", reply_markup=utils.get_bottom_keyboard('level2', user_id, user_ui_lang))
        else:
            await update.message.reply_text("输入错误")
        return

    # ===== 底部键盘全局导航 =====
    if user_text == '主菜单':
        await show_menu(update, context)
        return
        
    if user_text == '返回上一级':
        user_nav_state[chat_id] = 'level2'
        await update.message.reply_text(utils.get_text(user_id, 'dev_title', user_ui_lang), reply_markup=utils.get_dev_keyboard(user_id, user_ui_lang))
        await update.message.reply_text("▫️", reply_markup=utils.get_bottom_keyboard('level2', user_id, user_ui_lang))
        return

    # ===== 数学题验证 =====
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

    # ===== AI 对话逻辑 =====
    if user_text == '退出 AI 对话':
        if chat_id in user_conversations: 
            del user_conversations[chat_id]
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
