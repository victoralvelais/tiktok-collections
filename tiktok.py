from playwright.sync_api import sync_playwright
import json
import os
import time

def getOrCreateConfig():
  configFile = 'tiktok_config.json'
  if not os.path.exists(configFile):
    config = {
      'cookies': [],
      'app_context': {},
    }
    with open(configFile, 'w') as f:
      json.dump(config, f, indent=2)
  with open(configFile, 'r') as f:
    return json.load(f)

def saveConfig(config):
    with open('tiktok_config.json', 'w') as f:
      json.dump(config, f, indent=2)

def captureTiktokData():
  config = getOrCreateConfig()
  
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto("https://www.tiktok.com/login/phone-or-email/email")
    page.fill('input[name="username"]', config['credentials']['username'])
    page.fill('input[type="password"]', config['credentials']['password'])
    page.click('button[type="submit"]')

    page.wait_for_selector('a[href*="/upload"]', timeout=60000) or \
    page.wait_for_selector('.avatar-anchor', timeout=60000) or \
    page.wait_for_selector('[data-e2e="profile-icon"]', timeout=60000)

    config['cookies'] = context.cookies()
    
    appContext = page.evaluate('JSON.parse(document.querySelector("#__UNIVERSAL_DATA_FOR_REHYDRATION__").innerHTML).__DEFAULT_SCOPE__["webapp.app-context"]')
    config['app_context'] = {
      "appId": appContext["appId"],
      "appType": appContext["appType"],
      "csrfToken": appContext["csrfToken"],
      "user": {
          "nickName": appContext["user"]["nickName"],
          "secUid": appContext["user"]["secUid"],
          "uid": appContext["user"]["uid"],
          "uniqueId": appContext["user"]["uniqueId"]
      },
      "userAgent": appContext["userAgent"],
      "wid": appContext["wid"]
    }

    username = config['app_context']['user']['uniqueId']
    page.goto(f"https://www.tiktok.com/@{username}/")
    page.wait_for_selector('p[role="tab"]:has-text("Favorites")')

    page.click('p[role="tab"]:has-text("Favorites")')
    page.wait_for_selector('p[role="tab"][aria-selected="true"]:has-text("Favorites")')
    page.click("button#collections")

    saveConfig(config)
    time.sleep(10)
    input("Press Enter to close browser...")
    browser.close()

if __name__ == "__main__":
  captureTiktokData()