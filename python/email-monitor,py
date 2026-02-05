import imaplib
import email
from email.header import decode_header
import requests
import os
import urllib.parse

# ================= 🔐 解密区域 (适配 ION_MAIL) =================
# 注意：这里读取的环境变量名必须和 YAML 里定义的一致
raw_secrets = os.environ.get("ION_MAIL_SECRET")

config = {}
if raw_secrets:
    for line in raw_secrets.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            config[key.strip()] = value.strip()

# 从字典中提取配置
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
    print(f"准备推送: {title}")
    enc_title = urllib.parse.quote(title)
    enc_content = urllib.parse.quote(content)
    # GitHub 在海外，直连 Bark 即可，不需要代理
    url = f"https://api.day.app/{BARK_KEY}/{enc_title}/{enc_content}?group=Work&icon=https://www.cas.cn/images/cas_logo.png"
    try:
        requests.get(url, timeout=10)
    except Exception as e:
        print(f"推送失败: {e}")

def check_email():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # 计算 15 分钟前的时间
        # GitHub 服务器通常是 UTC 时间，注意时区
        # CSTNET 很多时候识别内部时间，稳妥起见我们只搜 UNSEEN (未读)
        # 然后在代码里过滤时间，或者简单点：只推未读的
        
        # 搜索所有未读邮件
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()

        if email_ids:
            print(f"发现 {len(email_ids)} 封未读邮件")
            for e_id in email_ids:
                _, msg_data = mail.fetch(e_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = clean_text(msg["Subject"])
                        sender = clean_text(msg["From"])
                        
                        # 解析邮件时间，避免推送太久以前的旧未读邮件 (可选优化)
                        # 这里简单处理：只要是未读的就推
                        send_bark(f"新邮件: {subject}", f"发件人: {sender}")
                        
                        # ⚠️ 关键：GitHub Action 是无状态的。
                        # 如果不标记为已读，下次运行脚本还会再推一次！
                        # 所以这里必须标记为已读，或者你需要用数据库记录 ID (太麻烦)
                        # 如果你不想标记为已读，这个方案在 GitHub Action 上很难完美实现
                        # mail.store(e_id, '+FLAGS', '\\Seen') 
        else:
            print("没有新邮件")

        mail.close()
        mail.logout()

    except Exception as e:
        print(f"运行出错: {e}")

if __name__ == "__main__":
    if not BARK_KEY or not EMAIL_PASS:
        print("错误：未设置 Secrets 环境变量")
    else:
        check_email()