from threading import Thread
from flask import Flask
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# 引入配置和处理逻辑
import config
import handlers

# ================= 保活 Web 服务 =================
app = Flask(__name__)
@app.route('/')
def home():
    return "机器人运行中..."

def run_web():
    app.run(host="0.0.0.0", port=10000)
# =================================================

def main():
    # 1. 启动保活服务
    Thread(target=run_web).start()
    
    # 2. 启动机器人服务 (通过 config 引入密钥)
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # 3. 绑定 handlers 里的处理函数
    application.add_handler(CommandHandler("start", handlers.show_menu))
    application.add_handler(CallbackQueryHandler(handlers.button_click))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    
    print("✅ 机器人已上线，去 Telegram 发 /start 测试吧！")
    application.run_polling()

if __name__ == "__main__":
    main()
