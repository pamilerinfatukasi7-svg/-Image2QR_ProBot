import os
import sys
import io
import logging
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer, CircleModuleDrawer
from qrcode.image.styles.colormasks import RadialGradiantColorMask, SolidFillColorMask  # FIXED: RadialGradiantColorMask (with 'a')
from PIL import Image, ImageDraw
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    logger.error("TELEGRAM_TOKEN environment variable not set!")
    sys.exit(1)

ENVIRONMENT = os.environ.get('ENVIRONMENT', 'production')

# Color presets
COLORS = {
    'black': '#000000',
    'red': '#FF0000',
    'blue': '#0066FF',
    'green': '#00CC00',
    'purple': '#800080',
    'orange': '#FF6600',
    'pink': '#FF1493',
    'cyan': '#00CED1',
    'teal': '#008080',
    'gold': '#FFD700',
    'magenta': '#FF00FF'
}

STYLES = {
    'default': 'Default (Square)',
    'rounded': 'Rounded Corners',
    'circle': 'Circle Modules',
    'gradient': 'Gradient'
}

# User preferences storage
user_prefs = {}

def generate_qr_code(data, fill_color='#000000', back_color='#FFFFFF', style='default', size=10):
    """Generate QR code with styling."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        if style == 'rounded':
            module_drawer = RoundedModuleDrawer()
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=module_drawer,
                color_mask=SolidFillColorMask(
                    back_color=back_color,
                    front_color=fill_color
                )
            )
        elif style == 'circle':
            module_drawer = CircleModuleDrawer()
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=module_drawer,
                color_mask=SolidFillColorMask(
                    back_color=back_color,
                    front_color=fill_color
                )
            )
        elif style == 'gradient':
            img = qr.make_image(
                image_factory=StyledPilImage,
                color_mask=RadialGradiantColorMask(  # FIXED: RadialGradiantColorMask (with 'a')
                    back_color=back_color,
                    center_color=fill_color,
                    edge_color=fill_color
                )
            )
        else:  # default
            img = qr.make_image(fill_color=fill_color, back_color=back_color)
        
        return img
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        return None

def add_logo_to_qr(qr_img, logo_bytes):
    """Add logo to center of QR code."""
    try:
        qr_img = qr_img.convert('RGBA')
        qr_width, qr_height = qr_img.size
        
        logo_size = int(qr_width * 0.20)
        
        logo = Image.open(logo_bytes).convert('RGBA')
        logo.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
        
        mask = Image.new('L', (logo.width, logo.height), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, logo.width, logo.height), fill=255)
        
        pos = ((qr_width - logo.width) // 2, (qr_height - logo.height) // 2)
        qr_img.paste(logo, pos, mask)
        
        return qr_img
    except Exception as e:
        logger.error(f"Logo adding error: {e}")
        return qr_img

def create_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎨 Customize", callback_data='customize'),
            InlineKeyboardButton("💡 Help", callback_data='help')
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data='settings'),
            InlineKeyboardButton("ℹ️ About", callback_data='about')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_style_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⬛ Default", callback_data='style_default'),
            InlineKeyboardButton("⭕ Rounded", callback_data='style_rounded')
        ],
        [
            InlineKeyboardButton("🔵 Circle", callback_data='style_circle'),
            InlineKeyboardButton("🌈 Gradient", callback_data='style_gradient')
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_color_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("⚫ Black", callback_data='color_black'),
            InlineKeyboardButton("🔴 Red", callback_data='color_red')
        ],
        [
            InlineKeyboardButton("🔵 Blue", callback_data='color_blue'),
            InlineKeyboardButton("🟢 Green", callback_data='color_green')
        ],
        [
            InlineKeyboardButton("🟣 Purple", callback_data='color_purple'),
            InlineKeyboardButton("🟠 Orange", callback_data='color_orange')
        ],
        [
            InlineKeyboardButton("🩷 Pink", callback_data='color_pink'),
            InlineKeyboardButton("🩵 Cyan", callback_data='color_cyan')
        ],
        [
            InlineKeyboardButton("💛 Gold", callback_data='color_gold'),
            InlineKeyboardButton("🟪 Magenta", callback_data='color_magenta')
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='back_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome = f"""
🌟 **Welcome {user.first_name}!** 

I'm **Image2QR Pro Bot** - your QR code creator with style! 🎨

**✨ Features:**
• Convert any text to QR code
• Upload images as logos
• 4 different styles
• 11 color options
• High quality output

**📌 How to Use:**
1️⃣ Send me any **text or URL**
2️⃣ Upload an **image** then send text for logo
3️⃣ Use buttons to **customize** colors & styles

**💡 Try it now!** Send me a link or text! 🚀
"""
    await update.message.reply_text(
        welcome,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=create_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 **Image2QR Pro Bot - Help Guide**

**📋 Commands:**
• `/start` - Welcome message
• `/help` - Show this guide
• `/settings` - View your preferences
• `/reset` - Reset to defaults

**🎨 How to Use:**

**1. Text to QR Code:**
Just send any text or URL
Example: `https://github.com`

**2. Image + Text = QR with Logo:**
1. Upload an image (photo)
2. Then send your text/URL
3. Logo appears in QR center

**3. Customize Appearance:**
• Click "Customize" button
• Choose style (Default/Rounded/Circle/Gradient)
• Choose color (11 options)
• Changes saved automatically

💡 **Pro Tips:**
• Use high contrast colors for best scanning
• Logos work best with simple shapes
• Keep text under 300 characters for best results
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prefs = user_prefs.get(user_id, {})
    style = prefs.get('style', 'default')
    color = prefs.get('color', 'black')
    
    settings_text = f"""
⚙️ **Your Current Settings**

🎨 **Style:** {STYLES.get(style, 'Default')}
🌈 **Color:** {color.capitalize()}
📏 **Size:** Standard

**Customize your QR codes using the buttons below!**
"""
    keyboard = [
        [
            InlineKeyboardButton("🎨 Change Style", callback_data='customize'),
            InlineKeyboardButton("🌈 Change Color", callback_data='color_menu')
        ],
        [InlineKeyboardButton("🔙 Main Menu", callback_data='back_main')]
    ]
    await update.message.reply_text(
        settings_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_prefs[user_id] = {'style': 'default', 'color': 'black'}
    await update.message.reply_text(
        "✅ **Settings Reset!**\n\n"
        "Style: Default\n"
        "Color: Black\n\n"
        "Send me some text to test! 🚀",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = update.message.text
        user_id = update.effective_user.id
        
        if text.startswith('/'):
            return
        
        await update.message.chat.send_action(action="upload_photo")
        
        prefs = user_prefs.get(user_id, {})
        style = prefs.get('style', 'default')
        color = prefs.get('color', 'black')
        
        qr_img = generate_qr_code(
            text,
            fill_color=COLORS.get(color, '#000000'),
            back_color='#FFFFFF',
            style=style
        )
        
        if not qr_img:
            await update.message.reply_text("❌ Failed to generate QR code. Please try with shorter text.")
            return
        
        if 'logo_data' in context.user_data:
            try:
                logo_bytes = context.user_data['logo_data']
                qr_img = add_logo_to_qr(qr_img, logo_bytes)
                context.user_data.pop('logo_data', None)
                has_logo = "✅ With logo!"
            except:
                context.user_data.pop('logo_data', None)
                has_logo = ""
        else:
            has_logo = ""
        
        img_byte_arr = io.BytesIO()
        qr_img.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        
        caption = f"""
✅ **QR Code Generated!**

📝 **Content:** `{text[:40]}{'...' if len(text) > 40 else ''}`
🎨 **Style:** {STYLES.get(style, 'Default')}
🌈 **Color:** {color.capitalize()}
{has_logo}

💡 **Save image** - Tap to view & download
"""
        
        await update.message.reply_photo(
            photo=img_byte_arr,
            caption=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Text handling error: {e}")
        await update.message.reply_text("⚠️ Error generating QR code. Please try again.")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        img_bytes = await file.download_as_bytearray()
        context.user_data['logo_data'] = io.BytesIO(img_bytes)
        
        await update.message.reply_text(
            "✅ **Image received!** 📸\n\n"
            "Now send me the **text or URL** to make into a QR code.\n"
            "I'll embed your image as a logo! 🎨\n\n"
            "💡 Tip: Use simple, clear images for best results.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=create_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Image handling error: {e}")
        await update.message.reply_text("❌ Failed to process image. Please try again with a smaller image.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    try:
        if query.data == 'back_main':
            await query.edit_message_text(
                "🏠 **Main Menu**\n\n"
                "Send me any text to create a QR code!\n"
                "Upload an image for a logo! ✨",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_main_keyboard()
            )
        
        elif query.data == 'customize':
            await query.edit_message_text(
                "🎨 **Select QR Code Style**\n\n"
                "Choose your preferred design:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_style_keyboard()
            )
        
        elif query.data == 'color_menu':
            await query.edit_message_text(
                "🌈 **Select QR Code Color**\n\n"
                "Choose the main color:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_color_keyboard()
            )
        
        elif query.data == 'settings':
            prefs = user_prefs.get(user_id, {})
            style = prefs.get('style', 'default')
            color = prefs.get('color', 'black')
            
            await query.edit_message_text(
                f"⚙️ **Your Settings**\n\n"
                f"🎨 Style: {STYLES.get(style, 'Default')}\n"
                f"🌈 Color: {color.capitalize()}\n\n"
                f"Use /reset to restore defaults.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎨 Change Style", callback_data='customize')],
                    [InlineKeyboardButton("🌈 Change Color", callback_data='color_menu')],
                    [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
                ])
            )
        
        elif query.data == 'about':
            about = """
🤖 **Image2QR Pro Bot v2.0**

**Features:**
• 4 QR styles
• 11 color options
• Logo embedding
• High quality

**Tech:**
• Python 3.12
• python-telegram-bot
• QRCode + Pillow
• Railway

Made with ❤️
"""
            await query.edit_message_text(
                about,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
                ])
            )
        
        elif query.data == 'help':
            await query.edit_message_text(
                "📋 **Quick Help**\n\n"
                "1. Send text/URL → QR code\n"
                "2. Upload image then text → QR with logo\n"
                "3. Use buttons to customize\n"
                "4. /settings to view preferences\n"
                "5. /reset to restore defaults",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data='back_main')]
                ])
            )
        
        elif query.data.startswith('style_'):
            style = query.data.replace('style_', '')
            if user_id not in user_prefs:
                user_prefs[user_id] = {}
            user_prefs[user_id]['style'] = style
            
            await query.edit_message_text(
                f"✅ **Style set to {STYLES.get(style, style.capitalize())}!**\n\n"
                f"Send me some text to see it in action! 🚀",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_main_keyboard()
            )
        
        elif query.data.startswith('color_'):
            color = query.data.replace('color_', '')
            if user_id not in user_prefs:
                user_prefs[user_id] = {}
            user_prefs[user_id]['color'] = color
            
            await query.edit_message_text(
                f"✅ **Color set to {color.capitalize()}!**\n\n"
                f"Send me some text to try it out! 🎨",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=create_main_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.edit_message_text(
            "❌ Error. Please try again.",
            reply_markup=create_main_keyboard()
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Sorry, something went wrong. Please try again later."
        )

def main():
    logger.info("🚀 Starting Image2QR Pro Bot...")
    logger.info(f"📊 Environment: {ENVIRONMENT}")
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('settings', settings_command))
    application.add_handler(CommandHandler('reset', reset_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.PHOTO, handle_image))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot is running!")
    application.run_polling(allowed_updates=None)

if __name__ == '__main__':
    main()
