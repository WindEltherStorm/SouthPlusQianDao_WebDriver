import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Config
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
MAX_RETRIES = 3

# Chrome setup
chrome_options = Options()
if not DEBUG:
    chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
wait = WebDriverWait(driver, 10)

def load_cookies():
    cookie_str = os.getenv('COOKIE')
    if not cookie_str:
        print("ERROR: COOKIE env var not set")
        return False
    try:
        cookies = json.loads(cookie_str)
        driver.get("https://www.south-plus.net/")
        for cookie in cookies:
            driver.add_cookie(cookie)
        print("SUCCESS: Cookies loaded")
        return True
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid COOKIE JSON: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Cookie loading failed: {e}")
        return False

def sign_in():
    for attempt in range(MAX_RETRIES):
        try:
            driver.get("https://www.south-plus.net/plugin.php?id=eb9e6_tasks:actions:newtasks")
            time.sleep(3)
            
            # Wait for and click sign-in link
            sign_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "每日签到")))
            sign_link.click()
            time.sleep(2)
            
            # Click claim button (updated XPath for robustness)
            claim_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '立即领取') or contains(text(), 'Sign in')]")))
            claim_btn.click()
            time.sleep(2)
            
            print("SUCCESS: Sign-in completed")
            return True
        except TimeoutException:
            print(f"WARNING: Element not found on attempt {attempt + 1}")
        except NoSuchElementException as e:
            print(f"ERROR: Sign-in element missing: {e}")
        except Exception as e:
            print(f"ERROR: Sign-in failed on attempt {attempt + 1}: {e}")
        time.sleep(5)  # Backoff
    print("ERROR: All sign-in retries failed")
    return False

def notify_via_serverchan(title, message):
    key = os.getenv('serverKey')
    if not key:
        print("INFO: serverKey not set, skipping notification")
        return
    url = f"https://sctapi.ftqq.com/{key}.send"
    params = {"title": title, "desp": message}
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            print("SUCCESS: Notification sent")
        else:
            print(f"WARNING: Notification failed: {resp.status_code}")
    except Exception as e:
        print(f"ERROR: Notification error: {e}")

# Main execution
try:
    if load_cookies():
        if sign_in():
            msg = "SouthPlus Daily Sign-in: SUCCESS"
            notify_via_serverchan(msg, f"Completed at {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            msg = "SouthPlus Daily Sign-in: Already Done or Failed"
            notify_via_serverchan(msg, "Check logs for details")
    else:
        print("FATAL: Aborting due to cookie error")
finally:
    driver.quit()
