import requests

from datetime import datetime
from zoneinfo import ZoneInfo
import os
import sys
import asyncio

from dotenv import load_dotenv
load_dotenv()


import telegram
from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update
)

from pushover import (
    send_pushover,
    validate_pushover_key
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)



from database import (
    init_db,
    add_alert,
    get_user_alerts,
    remove_multiple_alerts,
    get_pushover_key,
    get_pushover_status,
    disable_pushover,
    enable_pushover,
    save_pushover_key,
    add_favorite,
    remove_favorite,
    get_user_favorites,
    is_favorite,
)



from fxcm import (
    get_price,
    init_fxcm
)



from crypto import (
    get_crypto_price
)



import monitor





BOT_TOKEN = os.getenv("BOT_TOKEN")

async def setpush(update, context):

    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "Send your Pushover User Key.\n\nExample:\n/setpush uQi8xxxxxxxx"
        )
        return

    pushover_key = context.args[0]

    save_pushover_key(
        user_id,
        pushover_key
    )

    enable_pushover(user_id)

    await update.message.reply_text(
        "✅ Pushover notification enabled"
    )



INDICES_SYMBOLS = {"SPX500", "NAS100", "US30", "GER30", "UK100", "JP225", "AUS200"}
COMMODITY_SYMBOLS = {"XAUUSD", "XAGUSD", "USOIL", "COPPER", "NATGAS", "COFFEE"}


def get_market_from_symbol(symbol):
    symbol = symbol.upper()
    if symbol.endswith("USDT"):
        return "crypto"
    if symbol in COMMODITY_SYMBOLS:
        return "commodity"
    if symbol in INDICES_SYMBOLS:
        return "indices"
    return "forex"


def format_market_price(symbol, price):

    symbol = symbol.upper()


    # Crypto
    if symbol.endswith("USDT"):

        return f"{price:.2f}"


    # Commodities
    if symbol in [
        "XAUUSD",
        "XAGUSD",
        "USOIL",
        "COPPER"
    ]:

        return f"{price:.2f}"


    # Indices
    if symbol in [
        "SPX500",
        "NAS100",
        "US30"
    ]:

        return f"{price:.2f}"


    # Forex
    return f"{price:.5f}"

# ==================================================
# MAIN MENU
# ==================================================


main_menu = [

    ["📈 Add Alert", "📋 My Alerts"],

    ["⭐ Favorites", "🔔 Notification Settings"],

    ["ℹ️ Status"],

]







# ==================================================
# MARKET MENU
# ==================================================


market_menu = [

    ["💱 Forex", "🪙 Crypto"],

    ["🥇 Commodities", "📊 Indices"],

    ["⬅️ Back"]

]






notification_menu_connected = [

    ["🧪 Test Alert"],

    ["🔄 Change User Key"],

    ["❌ Disable Pushover"],

    ["⬅️ Back"]

]


notification_menu_disabled = [

    ["🔑 Enter Pushover Key"],

    ["⬅️ Back"]

]


# ==================================================
# FOREX MENU
# ==================================================


forex_menu = [

    ["EURUSD", "GBPUSD"],

    ["USDJPY", "GBPJPY"],

    ["✏️ Enter Forex Pair"],

    ["⬅️ Back"]

]








# ==================================================
# CRYPTO MENU
# ==================================================


crypto_menu = [

    ["BTCUSDT", "ETHUSDT"],

    ["SOLUSDT", "XRPUSDT"],

    ["✍️ Enter Crypto Pair"],

    ["⬅️ Back"]

]








# ==================================================
# COMMODITY MENU
# ==================================================


commodity_menu = [

    ["XAUUSD", "XAGUSD"],

    ["USOIL", "COPPER"],

    ["✍️ Enter Commodity"],

    ["⬅️ Back"]

]








# ==================================================
# INDICES MENU
# ==================================================


indices_menu = [

    ["SPX500", "NAS100"],

    ["US30"],

    ["✏️ Enter Index"],

    ["⬅️ Back"]

]








# ==================================================
# HOT SYMBOLS
# ==================================================


HOT_SYMBOLS = [

    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "GBPJPY",


    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",


    "XAUUSD",
    "XAGUSD",
    "USOIL",
    "COPPER",


    "SPX500",
    "NAS100",
    "US30",

]








# ==================================================
# FAVORITES MENU BUILDER
# ==================================================


async def _send_favorites_menu(update, favorites):

    if not favorites:

        await update.message.reply_text(

            "⭐ No favorites yet.\n\n"
            "Select any symbol and tap\n"
            "'☆ Save to Favorites' to build your list.",

            reply_markup=ReplyKeyboardMarkup(
                [["⬅️ Back"]],
                resize_keyboard=True
            )

        )

        return

    # Build rows of 2 symbols
    keyboard = []

    for i in range(0, len(favorites), 2):

        keyboard.append(favorites[i:i + 2])

    keyboard.append(["✏️ Edit Favorites"])
    keyboard.append(["⬅️ Back"])

    await update.message.reply_text(

        "⭐ Your Favorites\n\nSelect a symbol to set an alert:",

        reply_markup=ReplyKeyboardMarkup(
            keyboard,
            resize_keyboard=True
        )

    )


# ==================================================
# START COMMAND
# ==================================================


async def start(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):


    context.user_data.clear()



    await update.message.reply_text(

        "🚀 Universal Trading Alert Platform",

        reply_markup=ReplyKeyboardMarkup(

            main_menu,

            resize_keyboard=True

        )

    )
# ==================================================
# SYSTEM STATUS CHECK
# ==================================================

async def system_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # ==========================
    # BOT STATUS
    # ==========================

    bot_status = "🟢 Bot: Online"



    # ==========================
    # FXCM LIVE CHECK
    # ==========================

    try:

        fxcm_check = get_price("EURUSD")


        if fxcm_check:

            eurusd_price = fxcm_check["bid"]

            fxcm_status = (
                "🟢 FXCM: Connected\n"
                f"💱 EURUSD: {format_market_price('EURUSD', eurusd_price)}"
            )

        else:

            fxcm_status = (
                "🔴 FXCM: Disconnected"
            )


    except Exception:


        fxcm_status = (
            "🔴 FXCM: Disconnected"
        )





    # ==========================
    # BINANCE LIVE CHECK
    # ==========================

    try:
        response = requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            timeout=10
        )

        response.raise_for_status()

        data = response.json()
        btc_price = float(data["price"])

        binance_status = (
            "🟢 Binance: Connected\n"
            f"₿ BTCUSDT: ${btc_price:,.2f}"
        )

    except Exception as error:
        print(
            f"Binance status check failed: "
            f"{type(error).__name__}: {error}",
            flush=True
        )

        binance_status = "🔴 Binance: Disconnected"





    # ==========================
    # TIME (IST)
    # ==========================

    ist_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    current_time = ist_time.strftime(
        "%d-%m-%Y %H:%M:%S"
    )





    message = f"""
ℹ️ System Status


{bot_status}


{fxcm_status}


{binance_status}


🕒 Last Update:
{current_time}
"""





    await update.message.reply_text(

        message,

        reply_markup=ReplyKeyboardMarkup(

            main_menu,

            resize_keyboard=True

        )

    )
# ==================================================
# MENU HANDLER
# ==================================================


async def menu_handler(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):


    text = update.message.text

    user_id = update.message.from_user.id



    # ==================================================
    # PUSHOVER KEY INPUT
    # ==================================================

    if context.user_data.get("waiting_for_pushover_key"):

        if text == "⬅️ Back":
            context.user_data.pop("waiting_for_pushover_key", None)
            status = get_pushover_status(user_id)
            keyboard = notification_menu_connected if status == 1 else notification_menu_disabled
            await update.message.reply_text(
                "🔔 Notification Settings",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
            return

        key = text.strip()


        await update.message.reply_text(
            "🔄 Validating Pushover key..."
        )


        valid = validate_pushover_key(key)



        if valid:


            save_pushover_key(
                user_id,
                key
            )


            enable_pushover(
                user_id
            )



            context.user_data.pop(
                "waiting_for_pushover_key",
                None
            )



            await update.message.reply_text(

                "✅ Pushover Connected\n\n"
                "🚨 Emergency alerts enabled",

                reply_markup=ReplyKeyboardMarkup(
                    main_menu,
                    resize_keyboard=True
                )

            )



        else:


            await update.message.reply_text(

                "❌ Invalid Pushover User Key\n\n"
                "Please check your key and try again."

            )


        return






    # ==================================================
    # ADD ALERT
    # ==================================================


    if text == "📈 Add Alert":


        context.user_data.clear()



        await update.message.reply_text(

            "🌍 Select Market",

            reply_markup=ReplyKeyboardMarkup(

                market_menu,

                resize_keyboard=True

            )

        )







    # ==================================================
    # REGULAR BACK BUTTON
    # ==================================================

    elif text == "⬅️ Back":

        in_favorites = context.user_data.get("in_favorites")
        market = context.user_data.get("market")
        symbol = context.user_data.get("symbol")
        custom_symbol = context.user_data.get("custom_symbol")

        # From price input screen inside favorites → back to favorites menu
        if in_favorites and symbol:

            context.user_data.pop("symbol", None)
            context.user_data.pop("market", None)

            favorites = get_user_favorites(user_id)
            await _send_favorites_menu(update, favorites)
            return

        # From favorites menu → back to main menu
        if in_favorites:

            context.user_data.clear()

            await update.message.reply_text(

                "🚀 Universal Trading Alert Platform",

                reply_markup=ReplyKeyboardMarkup(
                    main_menu,
                    resize_keyboard=True
                )

            )

            return

        # From selected symbol / target-price screen
        # Back to the relevant symbol menu
        if symbol or custom_symbol:

            context.user_data.pop("symbol", None)
            context.user_data.pop("custom_symbol", None)

            if market == "forex":

                await update.message.reply_text(

                    "💱 Select Forex Pair",

                    reply_markup=ReplyKeyboardMarkup(
                        forex_menu,
                        resize_keyboard=True
                    )

                )

            elif market == "crypto":

                await update.message.reply_text(

                    "🪙 Select Crypto Pair",

                    reply_markup=ReplyKeyboardMarkup(
                        crypto_menu,
                        resize_keyboard=True
                    )

                )

            elif market == "commodity":

                await update.message.reply_text(

                    "🥇 Select Commodity",

                    reply_markup=ReplyKeyboardMarkup(
                        commodity_menu,
                        resize_keyboard=True
                    )

                )

            elif market == "indices":

                await update.message.reply_text(

                    "📊 Select Index",

                    reply_markup=ReplyKeyboardMarkup(
                        indices_menu,
                        resize_keyboard=True
                    )

                )

            return

        # From a symbol menu
        # Back to Select Market
        elif market:

            context.user_data.clear()

            await update.message.reply_text(

                "🌍 Select Market",

                reply_markup=ReplyKeyboardMarkup(
                    market_menu,
                    resize_keyboard=True
                )

            )

            return

        # From Select Market
        # Back to the main menu
        else:

            context.user_data.clear()

            await update.message.reply_text(

                "🚀 Universal Trading Alert Platform",

                reply_markup=ReplyKeyboardMarkup(
                    main_menu,
                    resize_keyboard=True
                )

            )

            return







    # ==================================================
    # FOREX
    # ==================================================


    elif text == "💱 Forex":


        context.user_data["market"] = "forex"



        await update.message.reply_text(

            "💱 Select Forex Pair",

            reply_markup=ReplyKeyboardMarkup(

                forex_menu,

                resize_keyboard=True

            )

        )








    # ==================================================
    # CRYPTO
    # ==================================================


    elif text == "🪙 Crypto":


        context.user_data["market"] = "crypto"



        await update.message.reply_text(

            "🪙 Select Crypto Pair",

            reply_markup=ReplyKeyboardMarkup(

                crypto_menu,

                resize_keyboard=True

            )

        )








    # ==================================================
    # COMMODITIES
    # ==================================================


    elif text == "🥇 Commodities":


        context.user_data["market"] = "commodity"



        await update.message.reply_text(

            "🥇 Select Commodity",

            reply_markup=ReplyKeyboardMarkup(

                commodity_menu,

                resize_keyboard=True

            )

        )








    # ==================================================
    # INDICES
    # ==================================================


    elif text == "📊 Indices":


        context.user_data["market"] = "indices"



        await update.message.reply_text(

            "📊 Select Index",

            reply_markup=ReplyKeyboardMarkup(

                indices_menu,

                resize_keyboard=True

            )

        )








    # ==================================================
    # SYMBOL SELECTED
    # ==================================================

    elif text in HOT_SYMBOLS or (
        context.user_data.get("in_favorites")
        and text in get_user_favorites(user_id)
    ):

        context.user_data["symbol"] = text
        context.user_data["market"] = get_market_from_symbol(text)

        already_fav = is_favorite(user_id, text)

        fav_label = "⭐ Remove Favorite" if already_fav else "☆ Save to Favorites"

        price_keyboard = [

            [fav_label],

            ["⬅️ Back"]

        ]


        # ==========================
        # SHOW CURRENT PRICE
        # ==========================

        try:

            if text.endswith("USDT"):

                data = get_crypto_price(text)
                current_price = float(data["price"])

                price_message = (
                    f"📊 {text} Selected\n\n"
                    f"💰 Current Price:\n"
                    f"{format_market_price(text, current_price)}\n\n"
                    "Enter target price:"
                )

            else:

                data = get_price(text)
                bid = float(data['bid'])
                ask = float(data['ask'])

                price_message = (
                    f"📊 {text} Selected\n\n"
                    f"📈 Current Bid:\n"
                    f"{format_market_price(text, bid)}\n\n"
                    f"📉 Current Ask:\n"
                    f"{format_market_price(text, ask)}\n\n"
                    "Enter target price:"
                )

            await update.message.reply_text(
                price_message,
                reply_markup=ReplyKeyboardMarkup(
                    price_keyboard,
                    resize_keyboard=True
                )
            )

        except Exception as _price_err:

            print(
                f"Price fetch error for {text}: {_price_err}",
                flush=True,
            )

            context.user_data.pop("symbol", None)

            await update.message.reply_text(
                f"⚠️ Could not fetch {text} price\n\n"
                "The price feed is temporarily unavailable. "
                "Please try again in a moment.",
                reply_markup=ReplyKeyboardMarkup(
                    main_menu,
                    resize_keyboard=True,
                )
            )








    # ==================================================
    # FAVORITES TOGGLE (Save / Remove)
    # ==================================================

    elif text in ["☆ Save to Favorites", "⭐ Remove Favorite"]:

        symbol = context.user_data.get("symbol")

        if not symbol:
            return

        if text == "☆ Save to Favorites":

            add_favorite(user_id, symbol)

            new_label = "⭐ Remove Favorite"

            await update.message.reply_text(

                f"⭐ {symbol} saved to favorites",

                reply_markup=ReplyKeyboardMarkup(
                    [[new_label], ["⬅️ Back"]],
                    resize_keyboard=True
                )

            )

        else:

            remove_favorite(user_id, symbol)

            new_label = "☆ Save to Favorites"

            await update.message.reply_text(

                f"🗑 {symbol} removed from favorites",

                reply_markup=ReplyKeyboardMarkup(
                    [[new_label], ["⬅️ Back"]],
                    resize_keyboard=True
                )

            )


    # ==================================================
    # FAVORITES MENU
    # ==================================================

    elif text == "⭐ Favorites":

        context.user_data.clear()
        context.user_data["in_favorites"] = True

        favorites = get_user_favorites(user_id)

        await _send_favorites_menu(update, favorites)


    # ==================================================
    # EDIT FAVORITES (remove via inline buttons)
    # ==================================================

    elif text == "✏️ Edit Favorites":

        favorites = get_user_favorites(user_id)

        if not favorites:

            await update.message.reply_text(
                "⭐ No favorites to edit."
            )
            return

        buttons = [
            [InlineKeyboardButton(
                f"❌ {sym}",
                callback_data=f"fav_remove_{sym}"
            )]
            for sym in favorites
        ]

        await update.message.reply_text(

            "✏️ Tap to remove a favorite:",

            reply_markup=InlineKeyboardMarkup(buttons)

        )


    # ==================================================
    # MANUAL INPUT BUTTONS
    # ==================================================

    elif text in [

        "✏️ Enter Forex Pair",

        "✍️ Enter Crypto Pair",

        "✍️ Enter Commodity",

        "✏️ Enter Index"

    ]:


        context.user_data["custom_symbol"] = True



        market = context.user_data.get(

            "market"

        )



        if market == "crypto":


            await update.message.reply_text(

                "🪙 Enter Crypto Symbol\n\n"
                "Example:\n"
                "BNBUSDT\nDOGEUSDT\nADAUSDT"

            )



        elif market == "commodity":


            await update.message.reply_text(

                "🥇 Enter Commodity Symbol\n\n"
                "Example:\n"
                "NATGAS\nCOFFEE"

            )



        elif market == "indices":


            await update.message.reply_text(

                "📊 Enter Index Symbol\n\n"
                "Example:\n"
                "GER30\nUK100"

            )



        else:


            await update.message.reply_text(

                "💱 Enter Forex Pair\n\n"
                "Example:\n"
                "AUDUSD\nEURJPY"

            )
    # ==================================================
    # CUSTOM SYMBOL INPUT
    # ==================================================

    elif context.user_data.get("custom_symbol"):

        symbol = text.upper().replace("/", "").replace(" ", "")

        try:

            context.user_data["symbol"] = symbol
            context.user_data.pop("custom_symbol", None)

            if symbol.endswith("USDT"):

                data = get_crypto_price(symbol)
                current_price = float(data["price"])

                price_message = (
                    f"📊 {symbol} Selected\n\n"
                    f"💰 Current Price:\n"
                    f"{format_market_price(symbol, current_price)}\n\n"
                    "Enter target price:"
                )

            else:

                data = get_price(symbol)

                bid = float(data["bid"])
                ask = float(data["ask"])

                price_message = (
                    f"📊 {symbol} Selected\n\n"
                    f"📈 Current Bid:\n"
                    f"{format_market_price(symbol, bid)}\n\n"
                    f"📉 Current Ask:\n"
                    f"{format_market_price(symbol, ask)}\n\n"
                    "Enter target price:"
                )

            already_fav = is_favorite(user_id, symbol)
            fav_label = "⭐ Remove Favorite" if already_fav else "☆ Save to Favorites"

            await update.message.reply_text(
                price_message,
                reply_markup=ReplyKeyboardMarkup(
                    [[fav_label], ["⬅️ Back"]],
                    resize_keyboard=True
                )
            )

        except Exception:

            context.user_data.pop("symbol", None)

            await update.message.reply_text(
                f"❌ Symbol not available: {symbol}\n\n"
                "Please check the symbol and try again."
            )
            
# ==================================================
# MY ALERTS
# ==================================================


    elif text == "📋 My Alerts":

        alerts = get_user_alerts(user_id)

        if not alerts:
            await update.message.reply_text("📋 No active alerts.")
            return

        msg = "📋 Your Active Alerts\n\nTap an alert to select it, then press Delete.\n\n"
        for alert in alerts:
            msg += f"📊 {alert[2]}  |  🎯 {format_market_price(alert[2], float(alert[3]))}  |  {alert[4]}\n"

        buttons = []
        for alert in alerts:
            buttons.append([
                InlineKeyboardButton(
                    f"\u2610 {alert[2]}  {format_market_price(alert[2], float(alert[3]))}  {alert[4]}",
                    callback_data=f"toggle_{alert[0]}"
                )
            ])
        buttons.append([
            InlineKeyboardButton("\U0001f5d1 Delete Selected", callback_data="delete_selected")
        ])

        context.user_data["delete_list"] = []

        await update.message.reply_text(
            msg,
            reply_markup=InlineKeyboardMarkup(buttons)
        )






    # ==================================================
    # NOTIFICATION SETTINGS
    # ==================================================

    elif text == "🔔 Notification Settings":

        status = get_pushover_status(user_id)


        if status == 1:

            message = """
🔔 Notification Settings


Pushover:
✅ Connected


Emergency Alerts:
🚨 Enabled


Choose an option:
"""


            keyboard = notification_menu_connected


        else:

            message = """
🔔 Notification Settings


Pushover:
❌ Not Connected


Emergency Alerts:
OFF


Choose an option:
"""


            keyboard = notification_menu_disabled



        await update.message.reply_text(

            message,

            reply_markup=ReplyKeyboardMarkup(

                keyboard,

                resize_keyboard=True

            )

        )

# ==================================================
# NOTIFICATION MENU ACTIONS
# ==================================================

    elif text == "🧪 Test Alert":

        key = get_pushover_key(user_id)

        if not key:

            await update.message.reply_text(
                "❌ Pushover is not connected.\nPlease enter your Pushover Key from Notification Settings."
            )
            return


        from pushover import send_pushover


        send_pushover(
            key,
            "🧪 Test Alert",
            "✅ Your Trading Alert notifications are working!"
        )


        await update.message.reply_text(
            "✅ Test notification sent"
        )



    elif text == "❌ Disable Pushover":

        disable_pushover(user_id)


        await update.message.reply_text(

            "🔴 Pushover Disabled",

            reply_markup=ReplyKeyboardMarkup(
                main_menu,
                resize_keyboard=True
            )

        )



    elif text in [
           "🔑 Enter Pushover Key",
           "🔄 Change User Key"
    ]:

           context.user_data["waiting_for_pushover_key"] = True

           await update.message.reply_text(
               "🔑 Enter your Pushover User Key:\n\n"
               "Paste the key here.",
               reply_markup=ReplyKeyboardMarkup(
                   [["⬅️ Back"]],
                   resize_keyboard=True,
               )
           )





# ==================================================
# STATUS BUTTON
# ==================================================


    elif text == "ℹ️ Status":

            await system_status(
                update,
                context
            )








# ==================================================
# REMOVE UNUSED BUTTON
# ==================================================



# ==================================================
# INLINE CALLBACK HANDLER
# ==================================================


async def delete_callback(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):


    query = update.callback_query


    await query.answer()



    data = query.data





    # ======================================
    # SELECT / UNSELECT ALERT
    # ======================================


    if data.startswith("toggle_"):



        alert_id = int(

            data.split("_")[1]

        )



        selected = context.user_data.get(

            "delete_list",

            []

        )





        if alert_id in selected:


            selected.remove(alert_id)



        else:


            selected.append(alert_id)





        context.user_data["delete_list"] = selected





        alerts = get_user_alerts(

            query.from_user.id

        )



        buttons = []





        for alert in alerts:



            mark = "✅ " if alert[0] in selected else ""



            buttons.append(

                [

                    InlineKeyboardButton(

                        f"{mark}{alert[2]} | {alert[3]}",

                        callback_data=f"toggle_{alert[0]}"

                    )

                ]

            )







        buttons.append(

            [

                InlineKeyboardButton(

                    "🗑 Delete Selected",

                    callback_data="delete_selected"

                )

            ]

        )






        await query.edit_message_reply_markup(

            reply_markup=InlineKeyboardMarkup(

                buttons

            )

        )







    # ======================================
    # REMOVE FAVORITE
    # ======================================

    elif data.startswith("fav_remove_"):

        symbol = data[len("fav_remove_"):]

        user_id = query.from_user.id

        remove_favorite(user_id, symbol)

        favorites = get_user_favorites(user_id)

        if not favorites:

            await query.edit_message_text(

                "⭐ No favorites remaining.\n\n"
                "Go back and select a symbol to add one."

            )

        else:

            buttons = [
                [InlineKeyboardButton(
                    f"❌ {sym}",
                    callback_data=f"fav_remove_{sym}"
                )]
                for sym in favorites
            ]

            await query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(buttons)
            )


    elif data == "delete_selected":



        selected = context.user_data.get(

            "delete_list",

            []

        )





        if not selected:



            await query.answer(

                "Select alerts first",

                show_alert=True

            )

            return







        remove_multiple_alerts(

            selected

        )





        context.user_data.clear()






        await query.edit_message_text(

            "✅ Selected alerts removed."

        )

# ==================================================
# SAVE ALERT
# ==================================================


async def save_alert(

    update: Update,

    context: ContextTypes.DEFAULT_TYPE

):


    user_id = update.message.from_user.id


    try:


        target = float(

            update.message.text

        )



        symbol = context.user_data.get(

            "symbol"

        )



        if not symbol:


            return






        # ==========================
        # GET CURRENT PRICE
        # ==========================


        if symbol.endswith("USDT"):


            data = get_crypto_price(symbol)


            current_price = float(

                data["price"]

            )


        else:


            data = get_price(symbol)


            bid = float(data["bid"])
            ask = float(data["ask"])

            current_price = (bid + ask) / 2

        








        # ==========================
        # DETERMINE DIRECTION
        # ==========================


        if current_price >= target:


            direction = "BELOW"



        else:


            direction = "ABOVE"








        add_alert(

            user_id,

            symbol,

            target,

            direction

        )








        await update.message.reply_text(


            "✅ Alert Saved\n\n"
            f"📊 Symbol: {symbol}\n"
            f"💵 Current: {format_market_price(symbol, current_price)}\n"
            f"🎯 Target: {format_market_price(symbol, target)}\n"
            f"📈 Direction: {direction}\n\n"
            "🚀 Monitoring Started",


            reply_markup=ReplyKeyboardMarkup(

                main_menu,

                resize_keyboard=True

            )


        )







        context.user_data.clear()






    except Exception as e:



        await update.message.reply_text(

            f"❌ Error creating alert\n\n{e}"

        )








# ==================================================
# MONITOR START
# ==================================================


async def start_monitor(app):


    print(

        "📡 Starting monitor...",

        flush=True

    )



    monitor.set_bot(

        app.bot

    )



    asyncio.create_task(

        monitor.monitor_loop()

    )








# ==================================================
# MAIN
# ==================================================


def main():



    print(

        "STEP 1",

        flush=True

    )



    if not BOT_TOKEN:


        raise Exception(

            "BOT_TOKEN missing"

        )






    print(

        "STEP 2",

        flush=True

    )



    init_db()



    print(

        "Connecting FXCM...",

        flush=True

    )

    try:
        init_fxcm()
    except Exception as e:
        print(
            f"⚠️  FXCM init failed (FXCM instruments disabled): {e}",
            flush=True,
        )






    print(

        "STEP 3",

        flush=True

    )





    app = (

        Application

        .builder()

        .token(BOT_TOKEN)

        .post_init(start_monitor)

        .build()

    )






    print(

        "STEP 4",

        flush=True

    )






    # ==========================
    # COMMAND
    # ==========================


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )
    app.add_handler(
        CommandHandler(
            "setpush",
            setpush
        )
    )








    # ==========================
    # INLINE BUTTONS
    # ==========================


    app.add_handler(

        CallbackQueryHandler(

            delete_callback

        )

    )







    # ==========================
    # PRICE INPUT
    # MUST BE ABOVE MENU
    # ==========================


    app.add_handler(

        MessageHandler(

            filters.Regex(

                r"^\d+(\.\d+)?$"

            ),

            save_alert

        )

    )








    # ==========================
    # NORMAL BUTTONS
    # ==========================


    app.add_handler(

        MessageHandler(

            filters.TEXT & ~filters.COMMAND,

            menu_handler

        )

    )







    print(

        "🚀 Bot Started",

        flush=True

    )





    # Exit when another instance is already polling so Railway restarts cleanly.
    async def _conflict_error_handler(update, context):
        if isinstance(context.error, telegram.error.Conflict):
            print(
                "\u274c Conflict: another bot instance is running. Exiting.",
                flush=True,
            )
            sys.exit(1)
        print(f"Bot error: {context.error}", flush=True)

    app.add_error_handler(_conflict_error_handler)

    app.run_polling(

        drop_pending_updates=True,

        allowed_updates=Update.ALL_TYPES

    )







# ==================================================
# RUN
# ==================================================


if __name__ == "__main__":


    main()
