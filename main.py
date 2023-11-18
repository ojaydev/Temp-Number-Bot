import time
import requests
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler

TELEGRAM_TOKEN = '' # Telegram Token
API_KEY = '' #5sim's API Key
ADMIN_USER_IDS = []  # Replace with the actual admin's user ID

# Dictionary to store authorized users and their expiration times
authorized_users = {}
BANNED_USER_IDS = []

# Global variables
rented_number = ""
rent_id = ""
product = ""
otp = ""
user_activity = {}  # user_id: timestamp


def ban_user(update: Update, context: CallbackContext):
    if update.message.from_user.id not in ADMIN_USER_IDS:
        update.message.reply_text("You are not authorized to ban users.")
        return

    args = context.args
    if len(args) != 1:
        update.message.reply_text("Usage: /ban_user user_id")
        return

    user_id = int(args[0])
    BANNED_USER_IDS.append(user_id)
    update.message.reply_text(f"User {user_id} has been banned.")



def unban_user(update: Update, context: CallbackContext):
    if update.message.from_user.id not in ADMIN_USER_IDS:
        update.message.reply_text("You are not authorized to unban users.")
        return

    args = context.args
    if len(args) != 1:
        update.message.reply_text("Usage: /unban_user user_id")
        return

    user_id = int(args[0])
    if user_id in BANNED_USER_IDS:
        BANNED_USER_IDS.remove(user_id)
        update.message.reply_text(f"User {user_id} has been unbanned.")
    else:
        update.message.reply_text(f"User {user_id} is not banned.")

def is_authorized(user_id):
    if user_id in BANNED_USER_IDS:
        return False
    if user_id in authorized_users:
        expiration_time = authorized_users[user_id]
        if time.time() < expiration_time:
        if user_id in ADMIN_USER_IDS:
            return True
    return False

def grant_access(update: Update, context: CallbackContext):
    if update.message.from_user.id not in ADMIN_USER_IDS:
        update.message.reply_text("You are not authorized to grant access. contact the admins https://t.me/hydrasmsupdates/3")
        return


    # Extract the user ID and time limit from the command
    args = context.args
    if len(args) != 2:
        update.message.reply_text("Usage: /grant_access user_id time_limit (5, 10, or 30 minutes)")
        return

    user_id = int(args[0])
    time_limit = int(args[1])
    if time_limit not in [5, 10, 30]:
        update.message.reply_text("Time limit must be 5, 10, or 30 minutes.")
        return

    # Add or update the user in the authorized_users dictionary
    expiration_time = time.time() + time_limit * 60
    authorized_users[user_id] = expiration_time
    update.message.reply_text(f"Access granted to user {user_id} for {time_limit} minutes. Use /start to use the bot")


def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_activity[user_id] = time.time()  # Record the activity timestamp
    if not is_authorized(user_id):
        update.message.reply_text("You do not have access to this bot. contact any one of the admins to get access https://t.me/hydrasmsupdates/3")
        return

    user = update.message.from_user
    update.message.reply_text(f"Hello, {user.first_name}! Welcome to Hydra OTP Bot. How can I assist you today?",
                              reply_markup=get_main_keyboard())

def users_active_24h(update: Update, context: CallbackContext):
    if update.message.from_user.id not in ADMIN_USER_IDS:
        update.message.reply_text("You are not authorized to view this information.")
        return

    active_users = [user for user, timestamp in user_activity.items() if time.time() - timestamp < 24 * 60 * 60]
    response = "Users active in the past 24 hours:\n" + "\n".join(map(str, active_users))
    update.message.reply_text(response)

def users_with_subscriptions(update: Update, context: CallbackContext):
    if update.message.from_user.id not in ADMIN_USER_IDS:
        update.message.reply_text("You are not authorized to view this information.")
        return

    active_subscriptions = [user for user, expiration_time in authorized_users.items() if time.time() < expiration_time]
    response = "Users with active subscriptions:\n" + "\n".join(map(str, active_subscriptions))
    update.message.reply_text(response)

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Rent Number")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def ama_ca(update: Update, context: CallbackContext):
    global rented_number, rent_id, product
    token = API_KEY  # Use your actual API key
    country = 'usa'  # Replace with the desired country
    operator = 'any'  # Replace with the desired operator
    product = 'amazon'  # Replace with the desired product name
    
    headers = {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
    }
    
    url = f'https://5sim.net/v1/user/buy/activation/{country}/{operator}/{product}'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        data = response.json()
        if 'phone' in data:
            rented_number = data['phone']
            rent_id = data['id']
            update.message.reply_text(f"Rented number for {product}: {rented_number}")
            
            # Display the inline keyboard
            keyboard = [[InlineKeyboardButton("Check Activation", callback_data="check_otp")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text("What would you like to do next?", reply_markup=reply_markup)
            
        else:
            update.message.reply_text(f"Failed to rent a number for {product}.")
      
    except requests.exceptions.RequestException as e:
        update.message.reply_text(f"An error occurred while making the request: {e}")


def button_handler(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "Rent Number":
        ama_ca(update, context)


def check_otp(update: Update, context: CallbackContext):
    global otp, rent_id
    token = API_KEY  # Use your actual API key
      
    headers = {
        'Authorization': 'Bearer ' + token,
        'Accept': 'application/json',
    }
    
    url = f'https://5sim.net/v1/user/check/{rent_id}'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        data = response.json()
        if 'sms' in data and len(data['sms']) > 0:
            first_sms = data['sms'][0]
            if 'text' in first_sms:
                otp = first_sms['text']
            else:
                otp = f"No OTP code found in the SMS."
        else:
            otp = f"No OTP code messages available."
      
    except requests.exceptions.RequestException as e:
        otp = f"An error occurred while making the request: {e}"


def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    callback_data = query.data
    
    if callback_data == "check_otp":
        check_otp(update, context)  # Call the check_otp function here
        
        # Respond with the output from check_otp function
        response_text = f"OTP code: {otp}" if otp else "No OTP code available."
        query.message.reply_text(response_text)

# Set up handlers
updater = Updater(token=TELEGRAM_TOKEN)
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('grant_access', grant_access, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('ban_user', ban_user, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('unban_user', unban_user, pass_args=True))
updater.dispatcher.add_handler(CommandHandler('users_active_24h', users_active_24h))
updater.dispatcher.add_handler(CommandHandler('users_with_subscriptions', users_with_subscriptions))
updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, button_handler))
updater.dispatcher.add_handler(CallbackQueryHandler(button_callback))


# Start the bot
updater.start_polling()
updater.idle()
