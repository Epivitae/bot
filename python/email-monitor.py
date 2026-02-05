import imaplib
import email
from email.header import decode_header
import requests
import os
import urllib.parse
import datetime
from email.utils import parsedate_to_datetime

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
    print(f"🚀 触发推送: {title}")
    enc_title = urllib.parse.quote(title)
    enc_content = urllib.parse.quote(content)
    url = f"https://api.day.app/{BARK_KEY}/{enc_title}/{enc_content}?group=Work&icon=https://www.cas.cn/images/cas_logo.png"
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

def check_email():
    try:
        print(f"正在连接邮箱: {EMAIL_USER} ...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # 1. 依然搜索未读邮件 (UNSEEN)
        # 这样能过滤掉已读的
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if not email_ids:
            print("📭 没有未读邮件。")
            return

        print(f"🔍 发现 {len(email_ids)} 封未读邮件，正在检查时间...")

        # 获取当前 UTC 时间
        now_time = datetime.datetime.now(datetime.timezone.utc)
        
        # 设定时间窗口：只推送过去 20 分钟内到达的邮件
        # (因为 GitHub Action 每 15 分钟跑一次，留 5 分钟缓冲)
        time_window = datetime.timedelta(minutes=20)

        # 2. 遍历检查每一封未读邮件的时间
        for e_id in email_ids:
            # 只获取邮件头 (BODY.PEEK[HEADER])，速度快且不标记为已读
            _, msg_data = mail.fetch(e_id, '(BODY.PEEK[HEADER])')
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # === ⏰ 核心逻辑：解析时间 ===
                    email_date_str = msg.get("Date")
                    if email_date_str:
                        try:
                            # 将邮件时间字符串转为 datetime 对象
                            email_dt = parsedate_to_datetime(email_date_str)
                            
                            # 统一转为 UTC 进行比较
                            if email_dt.tzinfo is None:
                                # 如果邮件时间没有时区信息，假设它是 UTC (防止报错)
                                email_dt = email_dt.replace(tzinfo=datetime.timezone.utc)
                            else:
                                # 转为 UTC
                                email_dt = email_dt.astimezone(datetime.timezone.utc)

                            # 计算时间差
                            time_diff = now_time - email_dt
                            
                            # === ⚖️ 判断：是否在 20 分钟内？ ===
                            if time_diff <= time_window and time_diff.total_seconds() >= 0:
                                # 获取完整内容来解析标题
                                _, full_data = mail.fetch(e_id, '(BODY.PEEK[])')
                                full_msg = email.message_from_bytes(full_data[0][1])
                                subject = clean_text(full_msg["Subject"])
                                sender = clean_text(full_msg["From"])
                                
                                print(f"✅ [新邮件] {subject} (到达于 {int(time_diff.total_seconds()/60)} 分钟前)")
                                send_bark(f"新邮件: {subject}", f"发件人: {sender}")
                            else:
                                # 旧邮件，跳过
                                # print(f"⏹️ [忽略旧邮件] 到达于 {time_diff} 前，跳过。")
                                pass
                                
                        except Exception as e:
                            print(f"⚠️ 时间解析错误: {e}")

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"❌ 运行出错: {e}")

if __name__ == "__main__":
    if not BARK_KEY or not EMAIL_PASS:
        print("错误：未设置 Secrets 环境变量")
    else:
        check_email()