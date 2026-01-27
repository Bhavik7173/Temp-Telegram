# streamlit_uploader_dashboard.py (with Uploads tab enabled + Mobile Upload)
import streamlit as st
import pandas as pd
import plotly.express as px
import os, asyncio, nest_asyncio, shutil, tempfile, glob, subprocess, time, calendar, tempfile, socket, random
# For folder inspection and cleaning
import hashlib, re

import seaborn as sns
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from io import BytesIO
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.types import Channel
from tqdm import tqdm
from PIL import Image

from telethon.tl.types import DocumentAttributeFilename, MessageMediaPhoto
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
from datetime import datetime, date, timedelta
from datetime import timedelta

nest_asyncio.apply()

# Telegram API setup
# TELEGRAM_ACCOUNTS = {
#     "India Account": {
#         "api_id": 28322319,
#         "api_hash": "e551f8c2022f3a3a18be4aafb80a35d6",
#         "phone": "+917096768617"
#     },
#     "Germany Account": {
#         "api_id": 27644731,
#         "api_hash": "934fe7edfed764fed5963fcac8266e85",
#         "phone": "+4915566214361"
#     }
# }

api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
phone = os.environ.get("PHONE")

# selected_account = st.sidebar.selectbox("Select Telegram Account", TELEGRAM_ACCOUNTS.keys())

# api_id = TELEGRAM_ACCOUNTS[selected_account]["api_id"]
# api_hash = TELEGRAM_ACCOUNTS[selected_account]["api_hash"]
# phone = TELEGRAM_ACCOUNTS[selected_account]["phone"]

# 🧩 Unique server instance ID (no collisions between multiple servers)
INSTANCE_ID = f"{socket.gethostname()}_{os.getpid()}_{random.randint(1000,9999)}"

# 🕒 Timestamp for file naming
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

# 📁 Log file paths (unique per instance)
# LOG_DIR = "D:/TeraBoxDownload/Telegram/Telegram Upload/Log File/"
LOG_DIR = "Log File"
os.makedirs(LOG_DIR, exist_ok=True)

temp_log_file = f"{LOG_DIR}/{INSTANCE_ID}_{timestamp}_temp_upload_log.csv"
temp_cache_file = f"{LOG_DIR}/{INSTANCE_ID}_{timestamp}_temp_uploaded_cache.txt"

# Main shared logs (common across all servers)
log_file = f"{LOG_DIR}/upload_log.csv"
cache_file = f"{LOG_DIR}/uploaded_cache.txt"
session_name = f"{LOG_DIR}/telegram_session"

# base_path = st.text_input("📁 Enter Folder Base Path", value="D:/TeraBoxDownload/Telegram/Telegram Upload/Folder Seperation/")
base_path = st.text_input("📁 Enter Folder Base Path", value="data")
os.makedirs(base_path, exist_ok=True)

# Load metrics
folders = len(os.listdir(base_path)) if os.path.exists(base_path) else 0
files = sum(len(files) for _, _, files in os.walk(base_path)) if os.path.exists(base_path) else 0
uploads = len(open(log_file).readlines()) if os.path.exists(log_file) else 0
uploads_cache = len(open(cache_file).readlines()) if os.path.exists(cache_file) else 0
channels = 0

# === FILE TYPE GROUPING ===
MEDIA_GROUP_TYPES = ('.jpg', '.jpeg', '.png', '.mp4', '.mov', '.mkv', '.pdf', '.docx', '.webm')
OTHER_TYPES = ('.zip', '.rar', '.7z', '.txt', '.xls', '.ppt', '.exe', '.heic', '.webp')
SUPPORTED_EXTENSIONS = MEDIA_GROUP_TYPES + OTHER_TYPES

theme = st.sidebar.radio("Theme", ["Light", "Dark"])

if theme == "Dark":
    st.markdown("""
        <style>
        body { background-color: #121212; color: white; }
        .metric-card { background: #1e1e1e; color: #e0e0e0; }
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <style>
        body { background-color: #ffffff; color: black; }
        .metric-card { background: #f5f5f5; color: #333; }
        </style>
    """, unsafe_allow_html=True)

if os.path.exists(log_file):
    try:
        df_log = pd.read_csv(log_file, names=["Timestamp", "File", "Channel", "FileType"])
        channels = df_log["Channel"].nunique()
    except:
        df_log = pd.DataFrame(columns=["Timestamp", "File", "Channel", "FileType"])
else:
    df_log = pd.DataFrame(columns=["Timestamp", "File", "Channel", "FileType"])

# Page config
st.set_page_config(page_title="Telegram Dashboard", layout="wide")
st.markdown("""
    <style>
    .block-container {
        padding-top: rem;
    }
    .metrics-row {
        position: sticky;
        top: 0;
        z-index: 999;
        background-color: #ffffff;
        padding: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2111/2111646.png", width=64)
    st.title("Telegram Dashboard")
    st.markdown("---")
    nav = st.radio("Menu", ["Dashboard", "Uploads", "Mobile Upload", "Create Folders", "My Channels", "Separate Files", "Download Media", "Google Drive Import", "Folder Inspector", "📄 Excel Sheet Manager", "Analytics", "Logs"])
    st.markdown("---")
    st.button("Settings")
    st.button("Help")
    st.button("Logout")

def convert_to_jpg(path):
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in [".webp", ".heic"]:
            with Image.open(path) as im:
                rgb_im = im.convert("RGB")
                # Replace extension with .jpg but keep original name
                new_path = os.path.splitext(path)[0] + ".jpg"
                rgb_im.save(new_path, format="JPEG")
                return new_path
    except Exception as e:
        print(f"Error converting {path} to JPG: {e}")
    return path

def safe_delete(path, logs):
    path = os.path.normpath(path)  # ✅ fix slashes automatically
    if os.path.exists(path):
        try:
            os.remove(path)
            logs.append(f"🗑️ Deleted: {path}")
        except Exception as e:
            logs.append(f"❌ Could not delete {path}: {e}")
    else:
        logs.append(f"⚠️ File already deleted or missing: {path}")

def recover_unmerged_logs(log_dir, main_log, main_cache):
    
    # Merge only temp files belonging to this instance.
    # Each server instance keeps its own isolated logs.

    # Match only files for THIS instance
    temp_logs = glob.glob(os.path.join(log_dir, f"{INSTANCE_ID}_*_temp_upload_log.csv"))
    temp_caches = glob.glob(os.path.join(log_dir, f"{INSTANCE_ID}_*_temp_uploaded_cache.txt"))
    # print(temp_logs,":::",temp_caches)
    for tlog in temp_logs:
        try:
            with open(tlog, "r", encoding="utf-8", errors="ignore") as src, open(main_log, "a", encoding="utf-8") as dest:
                shutil.copyfileobj(src, dest)
            os.remove(tlog)
            print(f"✅ Recovered and merged log: {tlog}")
        except Exception as e:
            print(f"⚠️ Could not merge {tlog}: {e}")

    for tcache in temp_caches:
        try:
            with open(tcache, "r", encoding="utf-8", errors="ignore") as src, open(main_cache, "a", encoding="utf-8") as dest:
                shutil.copyfileobj(src, dest)
            os.remove(tcache)
            print(f"✅ Recovered and merged cache: {tcache}")
        except Exception as e:
            print(f"⚠️ Could not merge {tcache}: {e}")

# --------------------------
# Helper: Fetch recent files
# --------------------------
async def fetch_recent_files(channel, search_query=None, limit=20):
    """Fetch recent files from a Telegram channel with optional search filter."""
    # # client = TelegramClient(session_name, api_id, api_hash)
    # await client.start(phone=phone)
    st.success("✅ Logged into Telegram")
    try:
        messages = client.get_messages(channel, limit=limit)
        files = [msg for msg in messages if msg.media]

        if search_query:
            files = [
                f for f in files
                if search_query.lower() in (f.file.name or "").lower()
            ]
        return files
    except Exception as e:
        st.error(f"⚠️ Error fetching files from {channel.title}: {e}")
        return []


async def upload_files(upload_df, mode):
    logs = []
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start(phone=phone)
    st.success("✅ Logged into Telegram")
    recover_unmerged_logs(LOG_DIR, log_file, cache_file)
    
    uploaded = set()
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            uploaded = set(line.strip() for line in f.readlines())

    try:
        for index, row in upload_df.iterrows():
            channel = str(row['Channel Link']).strip()
            folder_raw = str(row['Actress']).strip()

            if not folder_raw or folder_raw.lower() == "nan":
                logs.append(f"❌ Invalid folder name at row {index + 2}")
                continue

            folder = folder_raw if os.path.isabs(folder_raw) else os.path.join(base_path, folder_raw)
            if not os.path.exists(folder):
                logs.append(f"❌ Folder not found: {folder}")
                continue

            try:
                entity = await client.get_entity(channel)
            except Exception as e:
                error_msg = str(e)
                wait_match = re.search(r"wait of (\d+) seconds", error_msg)
                
                if wait_match:
                    wait_time = int(wait_match.group(1))
                    logs.append(f"⏳ Telegram rate limit: waiting {wait_time} seconds before retrying {channel}")
                    st.warning(f"⏳ Flood wait detected {folder}  -----> retrying {channel} in {wait_time} seconds...")
                    await asyncio.sleep(wait_time + 5)  # Add 5s buffer
                    try:
                        entity = await client.get_entity(channel)
                    except Exception as e2:
                        logs.append(f"❌ Retried but still failed: {folder}  ----->   {channel} | {e2}")
                        continue
                else:
                    logs.append(f"❌ Cannot access channel: {folder}  ----->   {channel} | {e}")
                    continue

            # Filter files
            all_files = os.listdir(folder)
            files = [
                f for f in all_files
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
                and os.path.join(folder_raw, f) not in uploaded
            ]
            if not files:
                logs.append(f"📁 No new files found in: {folder}")
                continue

            st.write(f"📤 Uploading {len(files)} files from: {folder}")
            progress_text = st.empty()
            bar = st.progress(0)
            totalfile = len(files)
            media_paths = [convert_to_jpg(os.path.join(folder, f)) for f in files]

            # === Upload Mode Handling ===
            if mode == "Media Group":
                batch_size = 10
                for i in range(0, len(media_paths), batch_size):
                    batch = media_paths[i:i+batch_size]
                    uploaded_this_batch = False
                    while not uploaded_this_batch:
                        try:
                            await client.send_file(
                                entity,
                                batch,
                                caption=f"📤 Batch Upload on {date.today().strftime('%d/%m/%Y')}",
                                attributes=[DocumentAttributeFilename(os.path.basename(f)) for f in batch]
                            )
                            for f in batch:
                                filename = os.path.basename(f)
                                with open(temp_cache_file, 'a') as fc:
                                    fc.write(filename + '\n')
                                with open(temp_log_file, 'a') as fl:
                                    fl.write(f"{datetime.now().isoformat()},{filename},{channel},Media\n")
                                safe_delete(f, logs)
                            uploaded_this_batch = True
                            bar.progress(min((i + batch_size) / len(media_paths), 1.0))
                            progress_text.text(f"📤 Uploaded {min(i + batch_size, len(media_paths))}/{len(media_paths)} files")
                        except FloodWaitError as e:
                            logs.append(f"⏳ FloodWait: Sleeping for {e.seconds} seconds")
                            await asyncio.sleep(e.seconds)
                        except Exception as e:
                            logs.append(f"❌ Media group batch upload failed: {e}")
                            uploaded_this_batch = True
            else:
                # === One-by-One Upload ===
                for i, file in enumerate(files):
                    original_path = os.path.join(folder, file)
                    path = convert_to_jpg(original_path)
                    uploaded_this_file = False
                    while not uploaded_this_file:
                        try:
                            await client.send_file(
                                entity,
                                path,
                                caption=f"📤 Uploaded on {date.today().strftime('%d/%m/%Y')}",
                                attributes=[DocumentAttributeFilename(file)]
                            )
                            with open(temp_cache_file, 'a') as f:
                                f.write(file + '\n')
                            with open(temp_log_file, 'a') as f:
                                f.write(f"{datetime.now().isoformat()},{file},{channel},Uploaded\n")
                            safe_delete(path, logs)
                            if path.endswith(".jpg") and not file.endswith(".jpg"):
                                safe_delete(path, logs)
                            bar.progress((i + 1) / len(files))
                            progress_text.text(f"📤 Uploaded {i+1}/{len(files)} files")
                            uploaded_this_file = True
                        except FloodWaitError as e:
                            logs.append(f"⏳ FloodWait: Sleeping for {e.seconds} seconds")
                            await asyncio.sleep(e.seconds)
                        except Exception as e:
                            logs.append(f"❌ Upload failed: {file} | {e}")
                            uploaded_this_file = True

            logs.append(f"✅ Completed upload for:  {folder}  ----->   {channel}")

    finally:
        # ✅ Always merge logs, even on crash or stop
        if os.path.exists(temp_log_file):
            try:
                existing = set()
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding="utf-8", errors="ignore") as main_log:
                        for line in main_log:
                            parts = line.strip().split(",")
                            if len(parts) > 1:
                                existing.add(parts[1])
                with open(log_file, 'a', encoding="utf-8") as main_log, open(temp_log_file, 'r', encoding="utf-8") as temp_log:
                    for line in temp_log:
                        parts = line.strip().split(",")
                        if len(parts) > 1 and parts[1] not in existing:
                            main_log.write(line + "\n")
                os.remove(temp_log_file)
                logs.append(f"✅ Merged and cleaned temp log file.")
            except Exception as e:
                logs.append(f"⚠️ Could not merge temp log: {e}")

        if os.path.exists(temp_cache_file):
            try:
                with open(cache_file, 'a', encoding="utf-8") as main_cache, open(temp_cache_file, 'r', encoding="utf-8") as temp_cache:
                    main_cache.writelines(temp_cache.readlines())
                os.remove(temp_cache_file)
                logs.append(f"✅ Merged and cleaned temp cache file.")
            except Exception as e:
                logs.append(f"⚠️ Could not merge temp cache: {e}")

        await client.disconnect()

    return logs


# Upload from mobile
async def send_mobile_files(channel_link, uploaded_files):
    logs = []
    client = TelegramClient(session_name + str(int(time.time())), api_id, api_hash)
    await client.start(phone=phone)
    try:
        entity = await client.get_entity(channel_link)
    except Exception as e:
        st.error(f"❌ Failed to access channel:  {folder}  ----->   {channel} | {e}")
        return
    for file in uploaded_files:
        try:
            await client.send_file(entity, file, caption=filename)
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()},{file},{channel_link},mobile\n")
            logs.append(f"✅ Uploaded: {file}")
        except Exception as e:
            logs.append(f"❌ Failed: {file} | {e}")
        finally:
            os.remove(file)
    await client.disconnect()
    return logs

# === Download Media from Channel ===
async def download_media_from_channel(channel_username, save_path):
    os.makedirs(save_path, exist_ok=True)
    downloaded = 0
    client = TelegramClient(session_name + '_dl', api_id, api_hash)
    await client.start(phone=phone)
    entity = await client.get_entity(channel_username)
    async for message in client.iter_messages(entity):
        if message.media:
            try:
                filename = None
                if message.file and message.file.name:
                    filename = message.file.name
                elif isinstance(message.media, MessageMediaPhoto):
                    filename = f"photo_{message.id}.jpg"
                elif message.document:
                    for attr in message.document.attributes:
                        if isinstance(attr, DocumentAttributeFilename):
                            filename = attr.file_name
                if not filename:
                    ext = message.file.ext or ".bin"
                    filename = f"file_{message.id}{ext}"
                save_file = os.path.join(save_path, filename)
                if not os.path.exists(save_file):
                    await message.download_media(file=save_file)
                    downloaded += 1
            except Exception as e:
                st.warning(f"❌ Error downloading media: {e}")
    await client.disconnect()
    return downloaded


# recover_unmerged_logs(LOG_DIR, log_file, cache_file)
# st.success("✅ Recovered all unmerged temp logs and caches")

# DASHBOARD
if nav == "Dashboard":
    
    st.markdown("# 📊 Dashboard")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.markdown(f"<div class='metric-card'><span class='big-font'>📁 {folders}</span><br>Total Folders</div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-card'><span class='big-font'>📂 {files}</span><br>Total Files</div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-card'><span class='big-font'>✅ {uploads}</span><br>Files Uploaded</div>", unsafe_allow_html=True)
    col4.markdown(f"<div class='metric-card'><span class='big-font'>✅ {uploads_cache}</span><br>Telegram Channels</div>", unsafe_allow_html=True)
    col5.markdown(f"<div class='metric-card'><span class='big-font'>🔗 {channels}</span><br>Telegram Channels</div>", unsafe_allow_html=True)

    st.markdown("---")
    chart1, chart2 = st.columns(2)
    if not df_log.empty:
        df_log["Timestamp"] = pd.to_datetime(df_log["Timestamp"], errors="coerce")
        df_chart = df_log[df_log["Timestamp"].notnull()]
        chart_data = df_chart.groupby(df_chart["Timestamp"].dt.date).size().reset_index(name="Uploads")
        chart1.subheader("📈 Uploads Over Time")
        chart1.plotly_chart(px.line(chart_data, x="Timestamp", y="Uploads", markers=True), use_container_width=True)
        chart2.subheader("📎 File Types")
        filetype_counts = df_chart["FileType"].value_counts().reset_index()
        filetype_counts.columns = ["FileType", "Count"]
        chart2.plotly_chart(px.pie(filetype_counts, names="FileType", values="Count"), use_container_width=True)
    else:
        chart1.info("No log data.")
        chart2.info("No file type data.")

    st.markdown("---")
    st.subheader("🏆 Top Channels by Uploads")
    if not df_log.empty:
        top_df = df_log["Channel"].value_counts().reset_index()
        top_df.columns = ["Channel", "Uploads"]
        st.dataframe(top_df.head(5), use_container_width=True)

# UPLOADS
elif nav == "Uploads":
    st.title("📤 Upload Manager")
    mode_select = st.radio("Choose upload mode", ["Excel Upload", "Manual Upload"])
    upload_type = st.radio("Upload Type", ["Media Group", "One-by-One"])

    if mode_select == "Excel Upload":
        excel_file = st.file_uploader("Upload Excel File (Channel Link + Actress)", type=["xlsx"])
        upload_btn = st.button("Start Upload")
        if excel_file and upload_btn:
            df_upload = pd.read_excel(excel_file)
            if "Channel Link" in df_upload.columns and "Actress" in df_upload.columns:
                logs = asyncio.run(upload_files(df_upload, mode=upload_type))
                for log in logs:
                    st.write(log)
            else:
                st.error("Missing required columns in Excel: 'Channel Link' and 'Actress'")
    else:
        channel = st.text_input("Telegram Channel Link or Username")
        actress = st.text_input("Folder Name (Actress)")
        upload_btn2 = st.button("Upload Manually")
        if channel and actress and upload_btn2:
            df_upload = pd.DataFrame([{"Channel Link": channel, "Actress": actress}])
            logs = asyncio.run(upload_files(df_upload, mode=upload_type))
            for log in logs:
                st.write(log)

# 📱 Upload From Mobile
elif nav == "Mobile Upload":
    
    st.title("📱 Upload Files from Mobile")
    channel = st.text_input("Telegram Channel Username or Link")
    files = st.file_uploader("Select files to upload", accept_multiple_files=True)
    if st.button("🚀 Upload Now") and channel and files:
        logs = asyncio.run(send_mobile_files(channel, files))
        for log in logs:
            st.success(log)

elif nav == "Create Folders":
    st.subheader("Create Folders from Excel")
    with st.form("create_form"):
        excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
        create_base = st.text_input("Base Path", value=base_path)
        column_name = st.text_input("Column Name for Folder Names")
        submitted = st.form_submit_button("Create Folders")
        if submitted and excel_file and create_base and column_name:
            df = pd.read_excel(excel_file)
            if column_name in df.columns:
                for name in df[column_name]:
                    if pd.notna(name):
                        folder_path = os.path.join(create_base, str(name).strip())
                        os.makedirs(folder_path, exist_ok=True)
                        st.success(f"Created folder: {folder_path}")
            else:
                st.error("❌ Column name not found in Excel")

elif nav == "Separate Files":
    st.subheader("Separate Files into Folders")
    def clean_folder_name(name):
        import re
        return re.sub(r'[<>:"/\\|?*\n\r\t]', '', name).strip()

    with st.form("separate_form"):
        excel_file = st.file_uploader("Upload Excel File", type=["xlsx"])
        source_path = st.text_input("Source Folder Path")
        dest_path = st.text_input("Destination Base Folder")
        submitted = st.form_submit_button("Separate Files")
        if submitted and excel_file and source_path and dest_path:
            df = pd.read_excel(excel_file, header=None)
            username_to_folder = {}
            for _, row in df.iterrows():
                row = row.dropna().astype(str).tolist()
                if len(row) < 3:
                    continue
                folder_name = clean_folder_name(row[2])
                for cell in row[1:]:
                    cell = cell.strip().lower()
                    if cell.startswith("http") or cell.isdigit():
                        continue
                    if len(cell) >= 3:
                        username_to_folder[cell] = folder_name

            for folder in set(username_to_folder.values()):
                os.makedirs(os.path.join(dest_path, folder), exist_ok=True)
            os.makedirs(os.path.join(dest_path, "Other"), exist_ok=True)

            for filename in os.listdir(source_path):
                file_path = os.path.join(source_path, filename)
                if not os.path.isfile(file_path):
                    continue
                matched = False
                for username, folder_name in username_to_folder.items():
                    if filename.lower().startswith(username):
                        shutil.copy2(file_path, os.path.join(dest_path, folder_name, filename))
                        matched = True
                        break
                if not matched:
                    shutil.copy2(file_path, os.path.join(dest_path, "Other", filename))
            st.success("✅ Files separated and copied.")


            
# === Download Media ===
elif nav == "Download Media":
    st.header("📥 Download Files from Telegram Channel")
    channel_link = st.text_input("Enter Telegram Channel Username or Link")
    save_path = st.text_input("Enter Download Folder Path", value="D:/TelegramDownloads")

    if channel_link and st.button("🔍 Fetch Channel Files"):
        client = TelegramClient(session_name + "_dl", api_id, api_hash)
        client.start(phone=phone)

        async def fetch_and_show():
            entity = await client.get_entity(channel_link)
            media_msgs = []
            async for msg in client.iter_messages(entity):
                if msg.media:
                    media_msgs.append(msg)

            total_files = len(media_msgs)

            per_page = 20
            total_pages = (total_files + per_page - 1) // per_page
            page = st.number_input("Page", 1, total_pages, 1)
            start = (page - 1) * per_page
            end = start + per_page
            page_msgs = media_msgs[start:end]

            for msg in page_msgs:
                filename = msg.file.name if msg.file and msg.file.name else f"file_{msg.id}.bin"
                with st.expander(filename):
                    # Display photo
                    if isinstance(msg.media, MessageMediaPhoto):
                        bio = BytesIO()
                        await msg.download_media(file=bio)
                        bio.seek(0)
                        st.image(Image.open(bio))
                    # Display video
                    elif isinstance(msg.media, MessageMediaDocument) and msg.document.mime_type.startswith("video"):
                        bio = BytesIO()
                        await msg.download_media(file=bio)
                        bio.seek(0)
                        st.video(bio.read())
                    else:
                        st.write("📎 Document or other media")

                    # Download button
                    if st.button(f"⬇️ Download {filename}", key=f"dl_{msg.id}"):
                        os.makedirs(save_path, exist_ok=True)
                        save_file = os.path.join(save_path, filename)
                        if not os.path.exists(save_file):
                            await msg.download_media(file=save_file)
                            st.success(f"✅ Downloaded: {filename}")
                        else:
                            st.info(f"Already exists: {filename}")

            return total_files

        total_files = asyncio.get_event_loop().run_until_complete(fetch_and_show())
        st.success(f"📂 Found {total_files} media files in {channel_link}")

        client.disconnect()


elif nav == "Google Drive Import":
    st.header("📥 Import Files from Google Drive")

    # Step 1: User pastes shared folder link
    shared_link = st.text_input("Paste Google Drive Shared Folder Link")

    # Optional: Button to authenticate Google account (for better access)
    if st.button("Authenticate Google Account"):
        gauth = GoogleAuth()
        gauth.LocalWebserverAuth()
        st.success("✅ Google account authenticated")

    # Parse folder ID from shared link helper function
    def get_folder_id(link):
        import re
        # Pattern to extract folder ID from typical shared folder link
        m = re.search(r"/folders/([a-zA-Z0-9_-]+)", link)
        return m.group(1) if m else None

    if shared_link:
        folder_id = get_folder_id(shared_link)
        if not folder_id:
            st.error("Invalid Google Drive folder link.")
        else:
            try:
                # Authenticate (reuse or create new auth)
                gauth = GoogleAuth()
                gauth.LocalWebserverAuth()
                drive = GoogleDrive(gauth)

                # List files inside folder
                file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
                st.write(f"Found {len(file_list)} files/folders:")

                file_titles = [f['title'] for f in file_list]
                selected_files = st.multiselect("Select files to download", file_titles)

                if st.button("Download Selected Files to Temp Folder"):
                    with tempfile.TemporaryDirectory() as tmpdir:
                        for file in file_list:
                            if file['title'] in selected_files:
                                filepath = os.path.join(tmpdir, file['title'])
                                file.GetContentFile(filepath)
                                st.write(f"Downloaded: {file['title']}")

                        st.success(f"✅ Downloaded {len(selected_files)} files to temp directory")
                        # Here you can call your Telegram upload functions on files in tmpdir
            except Exception as e:
                st.error(f"Google Drive access error: {e}")

elif nav == "Folder Inspector":
    st.header("🗂️ Folder Inspector & Cleaner")

    folder_path = st.text_input("Enter Folder Path to Inspect")

    def get_folder_stats(folder_path):
        total_size = 0
        total_files = 0
        for root, dirs, files in os.walk(folder_path):
            total_files += len(files)
            for f in files:
                fp = os.path.join(root, f)
                total_size += os.path.getsize(fp)
        return total_files, total_size

    def find_duplicates(folder_path):
        hashes = {}
        duplicates = []
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                fp = os.path.join(root, f)
                with open(fp, 'rb') as file:
                    filehash = hashlib.md5(file.read()).hexdigest()
                if filehash in hashes:
                    duplicates.append((fp, hashes[filehash]))
                else:
                    hashes[filehash] = fp
        return duplicates

    def delete_old_files(folder_path, days_old=30):
        now = datetime.now()
        cutoff = now - timedelta(days=days_old)
        deleted_files = []
        for root, dirs, files in os.walk(folder_path):
            for f in files:
                fp = os.path.join(root, f)
                mtime = datetime.fromtimestamp(os.path.getmtime(fp))
                if mtime < cutoff:
                    os.remove(fp)
                    deleted_files.append(fp)
        return deleted_files

    def zip_folder(folder_path, output_path):
        shutil.make_archive(output_path, 'zip', folder_path)

    if folder_path and os.path.exists(folder_path):
        total_files, total_size = get_folder_stats(folder_path)
        st.write(f"Total files: {total_files}")
        st.write(f"Total size: {total_size / (1024*1024):.2f} MB")

        if st.button("Find Duplicate Files"):
            dups = find_duplicates(folder_path)
            if dups:
                st.warning(f"Found {len(dups)} duplicate files:")
                for dup in dups:
                    st.write(f"Duplicate: {dup[0]}  <--->  {dup[1]}")
            else:
                st.success("No duplicates found.")

        days_old = st.number_input("Delete files older than days", min_value=1, max_value=365, value=30)
        if st.button("Delete Old Files"):
            deleted = delete_old_files(folder_path, days_old)
            st.success(f"Deleted {len(deleted)} files older than {days_old} days.")

        if st.button("Zip Folder"):
            zip_output = folder_path.rstrip(os.sep) + "_zipped"
            zip_folder(folder_path, zip_output)
            st.success(f"Folder zipped to {zip_output}.zip")
    else:
        st.info("Enter a valid existing folder path.")


elif nav == "📄 Excel Sheet Manager":
    st.header("📄 Excel Sheet Viewer & Manager")

    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
    if uploaded_file:
        df_excel = pd.read_excel(uploaded_file)
        st.dataframe(df_excel, use_container_width=True)

        if "Instagram Name" in df_excel.columns and "Actress" in df_excel.columns and "Channel Link" in df_excel.columns:
            st.success("✅ Sheet has required columns.")
        else:
            st.warning("⚠️ Required columns not found. Expected: 'Instagram', 'Folder', 'Channel Link'.")

        st.download_button(
            label="📥 Download Excel",
            data=df_excel.to_csv(index=False),
            file_name="insta_channel_map.csv",
            mime="text/csv"
        )
    else:
        st.info("📎 Upload your Excel file to view it here.")

elif nav == "My Channels":
    st.header("📋 Your Private & Public Channels")
    # --------------------------
    # List only user-created channels
    # --------------------------
    client = TelegramClient(session_name, api_id, api_hash)
    client.start(phone=phone)   
    dialogs = client.loop.run_until_complete(client.get_dialogs())

    channels = [
        d.entity for d in dialogs
        if isinstance(d.entity, Channel) and getattr(d.entity, "creator", False)
    ]

    if not channels:
        st.info("No channels found that you created.")
    else:
        for channel in channels:
            with st.container():
                st.markdown(f"### {channel.title}")

                # Open popup modal for channel details
                if st.button(f"📂 View Details – {channel.title}", key=f"popup_{channel.id}"):
                    with st.modal(f"📂 Channel: {channel.title}"):

                        # Channel Info
                        st.write(f"**Channel ID:** `{channel.id}`")
                        st.write(f"**Type:** {'Private' if channel.megagroup else 'Public'}")
                        st.write(f"**Members:** {getattr(channel, 'participants_count', 'N/A')}")
                        st.write(f"**Created:** {channel.date.strftime('%Y-%m-%d')}")

                        st.divider()

                        # Search/filter bar
                        search_query = st.text_input("🔎 Search files by name", key=f"search_{channel.id}")

                        # Fetch recent files with helper function
                        files = fetch_recent_files(channel, search_query, limit=20)

                        if not files:
                            st.info("No recent files found.")
                        else:
                            st.write("### 📑 Recent Files")
                            for msg in files:
                                file_name = msg.file.name or "Unnamed File"
                                file_size = (
                                    round(msg.file.size / 1024 / 1024, 2)
                                    if msg.file and msg.file.size else "?"
                                )
                                st.write(f"📄 **{file_name}** ({file_size} MB)")

                                # Download button
                                if st.button(f"⬇ Download {file_name}", key=f"dl_{msg.id}"):
                                    save_path = os.path.join("downloads", file_name)
                                    os.makedirs("downloads", exist_ok=True)
                                    client.download_media(msg, file=save_path)
                                    st.success(f"✅ Downloaded: {save_path}")
# Analytics (placeholder)
elif nav == "Analytics":
    st.header("📊 Upload Analytics Dashboard")

    if not os.path.exists(log_file):
        st.warning("⚠️ No logs found yet. Please upload some files first.")
    else:
        # Load logs
        df = pd.read_csv(log_file, names=["Timestamp", "File", "Channel", "FileType"])
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        df.dropna(subset=["Timestamp"], inplace=True)
        df["Date"] = df["Timestamp"].dt.date
        df["Hour"] = df["Timestamp"].dt.hour
        df["Weekday"] = df["Timestamp"].dt.day_name()
        df["Month"] = df["Timestamp"].dt.to_period("M").astype(str)

        # === Filters ===
        with st.expander("🔍 Filters", expanded=True):
            col1, col2, col3 = st.columns(3)
            start = col1.date_input("📅 Start Date", df["Date"].min())
            end = col2.date_input("📅 End Date", df["Date"].max())
            channel_filter = col3.multiselect("📺 Channel Filter", df["Channel"].unique())
            type_filter = st.multiselect("🗂 File Type Filter", df["FileType"].unique())

        # Apply filters
        filtered = df[(df["Date"] >= start) & (df["Date"] <= end)]
        if channel_filter:
            filtered = filtered[filtered["Channel"].isin(channel_filter)]
        if type_filter:
            filtered = filtered[filtered["FileType"].isin(type_filter)]

        # === Summary Metrics ===
        total_uploads = len(filtered)
        total_channels = filtered["Channel"].nunique()
        total_filetypes = filtered["FileType"].nunique()
        latest_upload = filtered["Date"].max() if not filtered.empty else "N/A"

        st.markdown("### 📊 Summary Metrics")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Uploads", f"{total_uploads}")
        c2.metric("Channels", f"{total_channels}")
        c3.metric("File Types", f"{total_filetypes}")
        c4.metric("Last Upload Date", str(latest_upload))

        st.divider()

        # === Charts Layout ===
        col1, col2 = st.columns(2)

        # 📆 Daily Upload Volume
        daily = filtered.groupby("Date").size().reset_index(name="Uploads")
        col1.plotly_chart(
            px.line(
                daily, x="Date", y="Uploads",
                title="📆 Daily Upload Volume",
                markers=True, template="plotly_dark", line_shape="spline",
            ),
            use_container_width=True,
        )

        # 🥧 File Type Distribution
        ftypes = filtered["FileType"].value_counts().reset_index()
        ftypes.columns = ["FileType", "Count"]
        col2.plotly_chart(
            px.pie(
                ftypes, names="FileType", values="Count",
                title="🗂 File Type Distribution",
                color_discrete_sequence=px.colors.qualitative.Set2,
            ),
            use_container_width=True,
        )

        # === Uploads per Channel ===
        st.subheader("📺 Uploads per Channel")
        ch_count = filtered["Channel"].value_counts().reset_index()
        ch_count.columns = ["Channel", "Uploads"]
        st.plotly_chart(
            px.bar(
                ch_count, x="Channel", y="Uploads",
                title="Uploads per Channel",
                color="Uploads", color_continuous_scale="Blues",
                template="plotly_white",
            ),
            use_container_width=True,
        )

        # --- 📊 Trend Comparison Stats ---
        st.subheader("📈 Weekly Upload Trends")

        # Ensure Timestamp is datetime
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        df.dropna(subset=["Timestamp"], inplace=True)
        df["Date"] = df["Timestamp"].dt.date

        # Group by Date
        daily_uploads = df.groupby("Date").size().reset_index(name="Uploads")
        today = pd.Timestamp.now().normalize().date()
        last_7 = today - pd.Timedelta(days=6)
        prev_7 = last_7 - pd.Timedelta(days=7)

        # Calculate recent 7-day and previous 7-day totals
        current_week = daily_uploads[(daily_uploads["Date"] >= last_7) & (daily_uploads["Date"] <= today)]["Uploads"].sum()
        previous_week = daily_uploads[(daily_uploads["Date"] >= prev_7) & (daily_uploads["Date"] < last_7)]["Uploads"].sum()

        # Calculate change %
        if previous_week > 0:
            change = ((current_week - previous_week) / previous_week) * 100
        else:
            change = 0

        # Color and emoji based on trend
        if change > 0:
            trend_icon = "📈"
            trend_color = "green"
        elif change < 0:
            trend_icon = "📉"
            trend_color = "red"
        else:
            trend_icon = "➖"
            trend_color = "gray"

        col1, col2, col3 = st.columns(3)
        col1.metric("Uploads (Last 7 Days)", f"{current_week:,}")
        col2.metric("Uploads (Prev 7 Days)", f"{previous_week:,}")
        col3.markdown(
            f"<h5 style='color:{trend_color};text-align:center'>{trend_icon} {abs(change):.1f}% change</h5>",
            unsafe_allow_html=True
        )


        # === Heatmap (Day vs Hour) ===
        st.subheader("🕒 Upload Frequency Heatmap")

        # Create heatmap pivot table
        heat_df = filtered.groupby(["Weekday", "Hour"]).size().reset_index(name="Count")
        weekdays_order = list(calendar.day_name)
        heat_df["Weekday"] = pd.Categorical(heat_df["Weekday"], categories=weekdays_order, ordered=True)
        heat_pivot = heat_df.pivot(index="Weekday", columns="Hour", values="Count").fillna(0)

        # Function to format large numbers (e.g. 1K, 2.3M)
        def format_short(n):
            if n >= 1_000_000:
                return f"{n/1_000_000:.1f}M"
            elif n >= 1_000:
                return f"{n/1_000:.1f}K"
            elif n == 0:
                return ""
            else:
                return str(int(n))

        # Apply formatting to each cell
        annot_labels = heat_pivot.applymap(format_short)

        # Plot heatmap with custom annotation labels
        fig, ax = plt.subplots(figsize=(12, 5))
        sns.heatmap(
            heat_pivot,
            cmap="YlOrBr",
            linewidths=0.3,
            annot=annot_labels,
            fmt="",
            cbar_kws={"label": "Uploads"},
            ax=ax
        )

        ax.set_title("Upload Frequency Heatmap (Day vs Hour)", fontsize=13, pad=10)
        st.pyplot(fig)



        # === Monthly Uploads ===
        st.subheader("📅 Monthly Upload Trends")
        monthly = filtered.groupby("Month").size().reset_index(name="Uploads")
        st.plotly_chart(
            px.bar(
                monthly, x="Month", y="Uploads",
                title="Monthly Upload Volume",
                color="Uploads", color_continuous_scale="Blues",
                text="Uploads", template="plotly_white"
            ),
            use_container_width=True,
        )

        # === Download Logs ===
        st.download_button(
            "📥 Download Filtered Logs as CSV",
            filtered.to_csv(index=False),
            file_name=f"filtered_uploads_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

# Logs tab
elif nav == "Logs":
    st.title("🧾 Upload Logs")
    if not df_log.empty:
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("No upload log found.")

