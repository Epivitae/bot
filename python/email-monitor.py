import imaplib
import email
from email.header import decode_header
import requests
import os
import urllib.parse
import sys

# ================= 🔐 解密区域 =================
raw_secrets = os.environ.get("ION_MAIL_SECRET")
config = {}
if raw_secrets:
    for line in raw_secrets.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            config[key.strip()] = value.strip()

BARK_KEY = config.get("BARK_KEY")
EMAIL_USER = config.get("EMAIL_USER")
EMAIL_PASS = config.get("EMAIL_PASS")
IMAP_SERVER = 'mail.cstnet.cn'
UID_FILE = "python/seen_uids.txt" # ⚠️ 注意路径，我们要存到 python 文件夹里

def log(msg):
    print(msg)
    sys.stdout.flush()

def clean_text(text):
    if not text: return ""
    decoded_list = decode_header(text)
    header_str = ""
    for content, charset in decoded_list:
        if isinstance(content, bytes):
            try:
                header_str += content.decode(charset if charset else 'utf-8', errors='ignore')
            except:
                header_str += content.decode('gbk', errors='ignore')
        else:
            header_str += str(content)
    return header_str

def send_bark(title, content):
    log(f"🚀 触发推送: {title}")
    enc_title = urllib.parse.quote(title)
    enc_content = urllib.parse.quote(content)
    url = f"https://api.day.app/{BARK_KEY}/{enc_title}/{enc_content}?level=critical&volume=3"
    try:
        requests.get(url, timeout=30)
    except Exception as e:
        log(f"推送失败: {e}")

def get_seen_uids():
    """从文件加载已读 UID"""
    if not os.path.exists(UID_FILE):
        return None # 返回 None 表示这是第一次运行
    
    with open(UID_FILE, "r") as f:
        # 读取所有非空行
        return set(line.strip() for line in f if line.strip())

def save_seen_uids(uids):
    """保存 UID 到文件"""
    with open(UID_FILE, "w") as f:
        for uid in uids:
            f.write(f"{uid}\n")
    log(f"💾 记录已更新，当前共记录 {len(uids)} 条 UID")

def check_email():
    try:
        log(f"1. 连接邮箱: {IMAP_SERVER} ...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # 使用 UID search 搜索所有邮件
        status, response = mail.uid('search', None, 'ALL')
        all_uids_bytes = response[0].split()
        # 转为字符串列表
        current_server_uids = set(x.decode('utf-8') for x in all_uids_bytes)

        if not current_server_uids:
            log("📭 邮箱是空的。")
            return

        # 加载本地记录
        local_seen_uids = get_seen_uids()

        # === 🛡️ 初始化保护逻辑 ===
        if local_seen_uids is None:
            log("⚠️ 未找到记录文件，视为【第一次运行】。")
            log(f"📊 当前邮箱共有 {len(current_server_uids)} 封邮件，将全部标记为已读，不发送通知。")
            log("👉 下一次运行起，如果有新 ID 才会通知。")
            save_seen_uids(current_server_uids)
            return

        # 找出新邮件 (服务器有，但本地没有的)
        new_uids = current_server_uids - local_seen_uids
        
        # 排序，从小到大处理
        sorted_new_uids = sorted(list(new_uids), key=lambda x: int(x))

        if sorted_new_uids:
            log(f"🔍 发现 {len(sorted_new_uids)} 封新邮件 (UID 比对)")
            
            for uid in sorted_new_uids:
                # 获取内容
                _, msg_data = mail.uid('fetch', uid, '(BODY.PEEK[])')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = clean_text(msg["Subject"])
                        sender = clean_text(msg["From"])
                        
                        log(f"✅ [新邮件 UID:{uid}] {subject}")
                        send_bark(f"新邮件: {subject}", f"发件人: {sender}")
                
                # 加入已读集合
                local_seen_uids.add(uid)
            
            # 全部发送完后，保存文件
            save_seen_uids(local_seen_uids)
        else:
            log("📭 没有新 UID，一切正常。")

        mail.close()
        mail.logout()

    except Exception as e:
        log(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    check_email()