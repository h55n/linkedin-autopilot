import os
import json
import base64
import sqlite3
import win32crypt
from Crypto.Cipher import AES
import shutil

def get_encryption_key():
    local_state_path = os.path.join(os.environ["USERPROFILE"],
                                    "AppData", "Local", "Google", "Chrome",
                                    "User Data", "Local State")
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.loads(f.read())

    # Get the encrypted key
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    # Remove DPAPI prefix
    key = key[5:]
    # Decrypt with DPAPI
    decrypted_key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
    return decrypted_key

def decrypt_data(data, key):
    try:
        # get the initialization vector
        iv = data[3:15]
        data = data[15:]
        # generate cipher
        cipher = AES.new(key, AES.MODE_GCM, iv)
        # decrypt password
        return cipher.decrypt(data)[:-16].decode()
    except Exception as e:
        try:
            return str(win32crypt.CryptUnprotectData(data, None, None, None, 0)[1])
        except:
            return ""

def main():
    key = get_encryption_key()
    print("Got encryption key!")
    
    db_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local",
                            "Google", "Chrome", "User Data", "Default", "Network", "Cookies")
    filename = "Cookies_copy.db"
    if not os.path.isfile(filename):
        shutil.copyfile(db_path, filename)
    
    db = sqlite3.connect(filename)
    cursor = db.cursor()
    
    cursor.execute("SELECT host_key, name, value, encrypted_value FROM cookies WHERE host_key LIKE '%linkedin.com%'")
    
    li_at = None
    csrf = None
    for host_key, name, value, encrypted_value in cursor.fetchall():
        if not value:
            decrypted_value = decrypt_data(encrypted_value, key)
        else:
            decrypted_value = value
            
        if name == "li_at":
            li_at = decrypted_value
        elif name == "JSESSIONID":
            csrf = decrypted_value.strip('"')
            
    print(f"li_at: {li_at[:10] if li_at else 'Not found'}...")
    print(f"JSESSIONID: {csrf[:10] if csrf else 'Not found'}...")
    
    if li_at:
        with open("linkedin_cookies.json", "w") as f:
            json.dump({"li_at": li_at, "JSESSIONID": csrf}, f)

if __name__ == "__main__":
    main()
