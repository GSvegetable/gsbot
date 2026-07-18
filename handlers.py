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
user_pwd_state = {} # 记录正在进行密码验证的用户

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # ===== 中断状态判断：如果用户在等待密码，清空并删除提示消息 =====
    if chat_id in user_pwd_state:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=user_pwd_state[chat_id]['msg_id'])
        except Exception:
            pass
        del user_pwd_state[chat_id]

    if not await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
        await update.message.reply_text(
            utils.get_text(user_id, 'channel_msg', user_ui_lang), 
            reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), 
            parse_mode='HTML'
        )
        return
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

    # ===== 如果用户点击了密码锁保护的菜单按钮 =====
    if query.data in ['custom_btn', 'contact', 'gsai', 'setting']:
        # 如果之前有旧的在等待密码，立刻删除旧消息并清空
        if chat_id in user_pwd_state:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=user_pwd_state[chat_id]['msg_id'])
            except Exception:
                pass
            del user_pwd_state[chat_id]
        
        # 弹出密码输入要求
        pwd_msg = await query.edit_message_text(text="请输入密码：")
        # 记录当前用户等待的目标和消息ID
        user_pwd_state[chat_id] = {
            'target': query.data,
            'msg_id': pwd_msg.message_id
        }
        return

    # ===== 以下是其他的原有逻辑 =====
    if query.data == 'check_member':
        if await utils.is_channel_member(context.bot, user_id, REQUIRED_CHANNEL):
            await query.edit_message_text(
                utils.get_text(user_id, 'main_msg', user_ui_lang), 
                reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), 
                parse_mode='HTML', disable_web_page_preview=True
            )
        else:
            await query.edit_message_text(
                utils.get_text(user_id, 'channel_msg', user_ui_lang), 
                reply_markup=utils.get_channel_keyboard(user_id, user_ui_lang, f"https://t.me/{REQUIRED_CHANNEL}"), 
                parse_mode='HTML'
            )

    elif query.data == 'dev_types':
        await query.edit_message_text(text=utils.get_text(user_id, 'back_msg', user_ui_lang), reply_markup=utils.get_type_keyboard(user_id, user_ui_lang))

    elif query.data == 'dev_captcha':
        await query.edit_message_text(text=utils.get_text(user_id, 'captcha_title', user_ui_lang), reply_markup=utils.get_captcha_keyboard(user_id, user_ui_lang))

    elif query.data == 'captcha_math':
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
        await query.edit_message_text(text=f"请计算：{a} + {b} = ?")

    elif query.data == 'back_dev_menu':
        user_math_state.pop(chat_id, None)
        await query.edit_message_text(text=utils.get_text(user_id, 'dev_title', user_ui_lang), reply_markup=utils.get_dev_keyboard(user_id, user_ui_lang))

    elif query.data == 'back_home':
        user_math_state.pop(chat_id, None)
        await query.edit_message_text(text=utils.get_text(user_id, 'main_msg', user_ui_lang), reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), parse_mode='HTML', disable_web_page_preview=True)

    elif query.data in ['group_manage', 'query', 'resource', 'checkin', 'ai_sub']:
        pass

    elif query.data == 'setting':
        await query.edit_message_text(text=utils.get_text(user_id, 'setting_title', user_ui_lang), reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang))

    elif query.data == 'setting_lang':
        await query.edit_message_text(text=utils.get_text(user_id, 'lang_title', user_ui_lang), reply_markup=utils.get_lang_keyboard(user_id, user_ui_lang))

    elif query.data == 'lang_back':
        await query.edit_message_text(text=utils.get_text(user_id, 'back_msg', user_ui_lang), reply_markup=utils.get_main_keyboard(user_id, user_ui_lang))

    elif query.data.startswith('lang_'):
        if query.data == 'lang_zh': user_ui_lang[user_id] = 'zh'
        elif query.data == 'lang_en': user_ui_lang[user_id] = 'en'
        await query.edit_message_text(
            text=utils.get_text(user_id, 'lang_sel_success_en' if query.data == 'lang_en' else 'lang_sel_success', user_ui_lang), 
            reply_markup=utils.get_main_keyboard(user_id, user_ui_lang)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    user_text = update.message.text

    # ===== 处理密码验证流程 =====
    if chat_id in user_pwd_state:
        target = user_pwd_state[chat_id]['target']
        # AI 是 121100，其他（开发、双向、设置）都是 012110
        expected_pwd = "121100" if target == 'gsai' else "012110"
        
        if user_text == expected_pwd:
            # 密码正确，清除状态，原地修改为对应的菜单（无任何提示词）
            target_info = user_pwd_state.pop(chat_id)
            if target == 'gsai':
                user_conversations[chat_id] = []
                await context.bot.edit_message_text(
                    text=utils.get_text(user_id, 'gsai_welcome', user_ui_lang),
                    chat_id=chat_id,
                    message_id=target_info['msg_id'],
                    reply_markup=utils.get_chat_reply_keyboard()
                )
            elif target == 'custom_btn':
                await context.bot.edit_message_text(
                    text=utils.get_text(user_id, 'dev_title', user_ui_lang),
                    chat_id=chat_id,
                    message_id=target_info['msg_id'],
                    reply_markup=utils.get_dev_keyboard(user_id, user_ui_lang)
                )
            elif target == 'contact':
                await context.bot.edit_message_text(
                    text="请输入您想要联系开发者的内容：",
                    chat_id=chat_id,
                    message_id=target_info['msg_id']
                )
            elif target == 'setting':
                await context.bot.edit_message_text(
                    text=utils.get_text(user_id, 'setting_title', user_ui_lang),
                    chat_id=chat_id,
                    message_id=target_info['msg_id'],
                    reply_markup=utils.get_setting_keyboard(user_id, user_ui_lang)
                )
        else:
            # 密码错误，仅提示输入错误
            await update.message.reply_text("输入错误")
        return

    # 数学题验证
    if chat_id in user_math_state:
        correct_answer = user_math_state.pop(chat_id)
        try:
            if int(user_text) == correct_answer:
                msg = utils.get_text(user_id, 'correct_msg', user_ui_lang)
            else:
                msg = utils.get_text(user_id, 'incorrect_msg', user_ui_lang)
        except ValueError:
            msg = utils.get_text(user_id, 'incorrect_msg', user_ui_lang)
        await update.message.reply_text(text=msg, reply_markup=utils.get_math_result_keyboard(user_id, user_ui_lang))
        return

    # AI 退出
    if user_text == '退出 AI 对话':
        if chat_id in user_conversations: del user_conversations[chat_id]
        confirm_msg = await update.message.reply_text("已退出 AI 对话", reply_markup=ReplyKeyboardRemove())
        await update.message.reply_text(utils.get_text(user_id, 'main_msg', user_ui_lang), reply_markup=utils.get_main_keyboard(user_id, user_ui_lang), parse_mode='HTML', disable_web_page_preview=True)
        await asyncio.sleep(2)
        try: await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=confirm_msg.message_id)
        except Exception: pass
        return

    # AI 对话
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
