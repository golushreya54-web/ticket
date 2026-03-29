import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from flask import Flask
from threading import Thread

# ✅ Token env variable se aayega — kabhi hardcode mat karo
TOKEN = os.environ.get("DISCORD_TOKEN")  # ✅
CATEGORY_ID = 1424984701814181961
ADMIN_USER_ID = 777857263548497920
COUNTER_FILE = "ticket_counter.json"

# ─── Keep-Alive Server (Render free tier ke liye) ────────────────────────────
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive! 🟢"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# ─── Bot Setup ────────────────────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

def get_next_ticket_number():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            data = json.load(f)
            num = data.get("count", 0) + 1
    else:
        num = 1
    with open(COUNTER_FILE, "w") as f:
        json.dump({"count": num}, f)
    return str(num).zfill(3)

class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.grey, emoji="🔒", custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket band ho raha hai...", ephemeral=True)
        current_name = interaction.channel.name
        new_name = current_name.replace("ticket-", "closed-")
        await interaction.channel.edit(name=new_name)

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.red, emoji="⛔", custom_id="delete_ticket")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != ADMIN_USER_ID:
            await interaction.response.send_message("❌ Only admin can delete.", ephemeral=True)
            return
        await interaction.response.send_message("Deleting...", ephemeral=True)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Buy", style=discord.ButtonStyle.green, emoji="🛒", custom_id="buy_ticket")
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        category = guild.get_channel(CATEGORY_ID)
        if category is None:
            await interaction.response.send_message("❌ Category nahi mili.", ephemeral=True)
            return

        for channel in category.channels:
            if channel.topic and str(user.id) in channel.topic:
                await interaction.response.send_message(
                    f"⚠️ Tumhara ticket already exist karta hai: {channel.mention}",
                    ephemeral=True
                )
                return

        admin = guild.get_member(ADMIN_USER_ID)
        ticket_num = get_next_ticket_number()

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if admin:
            overwrites[admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_num}",
            category=category,
            overwrites=overwrites,
            topic=str(user.id)
        )

        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_num}",
            description=f"Support will assist you shortly.\n\n**User:** {user.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Ticket ID: {ticket_num}")

        await channel.send(
            content=f"{user.mention} <@{ADMIN_USER_ID}>",
            embed=embed,
            view=TicketControls()
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

@bot.tree.command(name="setup", description="Ticket panel send karo")
async def setup(interaction: discord.Interaction):
    if interaction.user.id != ADMIN_USER_ID:
        await interaction.response.send_message(
            "❌ Tujhe yeh command use karne ki permission nahi hai.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Blaze Xiters",
        description=(
            "Welcome to the Blaze Xiters Store.\n"
            "Experience the power of Blaze Xiters. Secure your\n"
            "access now and dominate the competition.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🛒 **How to Purchase**\n"
            "Click the **Buy** button below to open a purchase ticket. "
            "Our team will guide you through the secure payment process.\n\n"
            "📜 **Rules**\n"
            "• Tickets are for purchases and pre-sale inquiries only.\n"
            "• Time-wasters may be banned without warning.\n"
            "• Respect our staff and community guidelines."
        ),
        color=discord.Color.dark_grey()
    )
    embed.set_thumbnail(
        url="https://media.discordapp.net/attachments/1485850069629665365/1486013666800435215/ChatGPT_Image_Mar_24_2026_07_39_40_AM.png?ex=69c93b92&is=69c7ea12&hm=b2b16e6ff774eec2d1e67041ebe57099333ab0d14284a0042937054f2f124048&=&format=webp&quality=lossless&width=1376&height=917"
    )
    embed.set_footer(text="Blaze Xiters • Secure • Instant • Premium")

    await interaction.response.send_message("✅ Panel bheja gaya!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=TicketView())

@bot.command()
async def sync(ctx):
    if ctx.author.id != ADMIN_USER_ID:
        return
    synced = await bot.tree.sync()
    await ctx.send(f"✅ {len(synced)} commands synced!")

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TicketControls())
    await bot.tree.sync()
    print(f"✅ Bot Ready: {bot.user}")

# ─── Start ────────────────────────────────────────────────────────────────────
keep_alive()
bot.run(TOKEN)
