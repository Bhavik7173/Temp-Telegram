import os, shutil, glob

LOG_DIR = "D:/TeraBoxDownload/Telegram/Telegram Upload/Log File/"
main_log = os.path.join(LOG_DIR, "upload_log.csv")
main_cache = os.path.join(LOG_DIR, "uploaded_cache.txt")

def recover_unmerged_logs(log_dir, main_log, main_cache):
    temp_logs = glob.glob(os.path.join(log_dir, "*_temp_upload_log.csv"))
    temp_caches = glob.glob(os.path.join(log_dir, "*_temp_uploaded_cache.txt"))

    print(f"🔍 Found {len(temp_logs)} temp logs and {len(temp_caches)} temp caches")

    for tlog in temp_logs:
        try:
            with open(tlog, "r", encoding="utf-8", errors="ignore") as src, open(main_log, "a", encoding="utf-8") as dest:
                shutil.copyfileobj(src, dest)
            os.remove(tlog)
            print(f"✅ Merged and deleted log: {tlog}")
        except Exception as e:
            print(f"⚠️ Failed to merge {tlog}: {e}")

    for tcache in temp_caches:
        try:
            with open(tcache, "r", encoding="utf-8", errors="ignore") as src, open(main_cache, "a", encoding="utf-8") as dest:
                shutil.copyfileobj(src, dest)
            os.remove(tcache)
            print(f"✅ Merged and deleted cache: {tcache}")
        except Exception as e:
            print(f"⚠️ Failed to merge {tcache}: {e}")

if __name__ == "__main__":
    recover_unmerged_logs(LOG_DIR, main_log, main_cache)
