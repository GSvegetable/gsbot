from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from lang import UI_LANGUAGES

def get_text(user_id, key, user_ui_lang):
    lang_code = user_ui_lang.get(user_id, 'zh')
    return UI_LANGUAGES[lang_code].get(key, key)

# 主页键盘
def get_main_keyboard(user_id, user_ui_lang):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'custom_btn', user_ui_lang), callback_data='custom_btn')],
        [InlineKeyboardButton(get_text(user_id, 'contact_btn', user_ui_lang), callback_data='contact')],
        [InlineKeyboardButton(get_text(user_id, 'gsai', user_ui_lang), callback_data='gsai'), InlineKeyboardButton(get_text(user_id, 'setting', user_ui_lang), callback_data='setting')]
    ]
    return InlineKeyboardMarkup(keyboard)

# 定制子菜单键盘
def get_custom_keyboard(user_id, user_ui_lang):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'group_manage', user_ui_lang), callback_data='group_manage'), InlineKeyboardButton(get_text(user_id, 'contact_sub', user_ui_lang), callback_data='contact_sub')],
        [InlineKeyboardButton(get_text(user_id, 'query', user_ui_lang), callback_data='query'), InlineKeyboardButton(get_text(user_id, 'resource', user_ui_lang), callback_data='resource')],
        [InlineKeyboardButton(get_text(user_id, 'checkin', user_ui_lang), callback_data='checkin'), InlineKeyboardButton(get_text(user_id, 'ai_sub', user_ui_lang), callback_data='ai_sub')],
        [InlineKeyboardButton(get_text(user_id, 'back_btn', user_ui_lang), callback_data='back_home')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_setting_keyboard(user_id, user_ui_lang):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'setting_lang', user_ui_lang), callback_data='setting_lang')],
        [InlineKeyboardButton(get_text(user_id, 'setting_back', user_ui_lang), callback_data='back_home')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_lang_keyboard(user_id, user_ui_lang):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'lang_zh', user_ui_lang), callback_data='lang_zh'), InlineKeyboardButton(get_text(user_id, 'lang_en', user_ui_lang), callback_data='lang_en')],
        [InlineKeyboardButton(get_text(user_id, 'lang_back', user_ui_lang), callback_data='lang_back')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_channel_keyboard(user_id, user_ui_lang, channel_link):
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, 'join_btn', user_ui_lang), url=channel_link)],
        [InlineKeyboardButton(get_text(user_id, 'check_btn', user_ui_lang), callback_data='check_member')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_chat_reply_keyboard():
    return ReplyKeyboardMarkup([['退出 AI 对话']], resize_keyboard=True)

async def is_channel_member(bot, user_id, required_channel):
    try:
        member = await bot.get_chat_member(chat_id=f"@{required_channel}", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"⚠️ 频道检查出错 (请确保机器人是频道管理员): {e}")
        return True
