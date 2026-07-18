from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from lang import UI_LANGUAGES

def get_text(user_id, key, user_ui_lang):
    lang_code = user_ui_lang.get(user_id, 'zh')
    return UI_LANGUAGES[lang_code].get(key, key)

def get_main_keyboard(user_id, user_ui_lang):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'robot_dev', user_ui_lang), callback_data='custom_btn')],
        [InlineKeyboardButton(get_text(user_id, 'contact_btn', user_ui_lang), callback_data='contact')],
        [InlineKeyboardButton(get_text(user_id, 'gsai', user_ui_lang), callback_data='gsai'), InlineKeyboardButton(get_text(user_id, 'setting', user_ui_lang), callback_data='setting')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_dev_keyboard(user_id, user_ui_lang):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'dev_captcha', user_ui_lang), callback_data='dev_captcha')],
        [InlineKeyboardButton(get_text(user_id, 'back_msg', user_ui_lang), callback_data='back_home'), InlineKeyboardButton(get_text(user_id, 'dev_types', user_ui_lang), callback_data='dev_types')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_setting_keyboard(user_id, user_ui_lang):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'setting_lang', user_ui_lang), callback_data='setting_lang')],
        [InlineKeyboardButton(get_text(user_id, 'setting_back', user_ui_lang), callback_data='back_home')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_type_keyboard(user_id, user_ui_lang):
    funcs = [("双向", 'contact'), ("AI", 'gsai'), ("设置", 'setting'), ("群管", 'group_manage'), ("查询", 'query'), ("资源", 'resource'), ("签到", 'checkin'), ("AI", 'ai_sub')]
    keyboard = []
    for i in range(0, len(funcs), 2):
        row = [InlineKeyboardButton(funcs[i][0], callback_data=funcs[i][1])]
        if i + 1 < len(funcs): row.append(InlineKeyboardButton(funcs[i+1][0], callback_data=funcs[i+1][1]))
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

def get_captcha_keyboard(user_id, user_ui_lang):
    keyboard = [[InlineKeyboardButton(get_text(user_id, 'captcha_math', user_ui_lang), callback_data='captcha_math')]]
    return InlineKeyboardMarkup(keyboard)

def get_channel_keyboard(user_id, user_ui_lang, channel_link):
    keyboard = [[InlineKeyboardButton(get_text(user_id, 'join_btn', user_ui_lang), url=channel_link)], [InlineKeyboardButton(get_text(user_id, 'check_btn', user_ui_lang), callback_data='check_member')]]
    return InlineKeyboardMarkup(keyboard)

def get_lang_keyboard(user_id, user_ui_lang):
    keyboard = [[InlineKeyboardButton(get_text(user_id, 'lang_zh', user_ui_lang), callback_data='lang_zh'), InlineKeyboardButton(get_text(user_id, 'lang_en', user_ui_lang), callback_data='lang_en')], [InlineKeyboardButton(get_text(user_id, 'lang_back', user_ui_lang), callback_data='lang_back')]]
    return InlineKeyboardMarkup(keyboard)

# 底部键盘回复区域（强制【每个按钮独占一排】）
def get_bottom_keyboard(state, user_id, user_ui_lang):
    lang_home = get_text(user_id, 'back_msg', user_ui_lang)
    lang_back = get_text(user_id, 'back_dev_menu', user_ui_lang)
    lang_exit_ai = get_text(user_id, 'exit_ai', user_ui_lang)
    lang_retry_math = get_text(user_id, 'retry_math', user_ui_lang)
    
    # 每一行一个 list，严格保证全竖排
    if state == 'home' or state == 'level2':
        return ReplyKeyboardMarkup([[lang_home]], resize_keyboard=True, one_time_keyboard=False)
    elif state == 'level3':
        return ReplyKeyboardMarkup([[lang_home], [lang_back]], resize_keyboard=True, one_time_keyboard=False)
    elif state == 'ai':
        return ReplyKeyboardMarkup([[lang_home], [lang_exit_ai]], resize_keyboard=True, one_time_keyboard=False)
    elif state == 'math':
        return ReplyKeyboardMarkup([[lang_home], [lang_back], [lang_retry_math]], resize_keyboard=True, one_time_keyboard=False)
    return ReplyKeyboardMarkup([[lang_home]], resize_keyboard=True)

async def is_channel_member(bot, user_id, required_channel):
    try:
        member = await bot.get_chat_member(chat_id=f"@{required_channel}", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"⚠️ 频道检查出错 (请确保机器人是频道管理员): {e}")
        return True
