from playwright.sync_api import sync_playwright
import json
import time

def getOrCreateConfig():
  configFile = 'tiktok_config.json'
  config = { 'cookies': [], 'app_context': {} }
  
  try:
    with open(configFile, 'r') as f:
      return json.load(f)
  except (FileNotFoundError, json.JSONDecodeError):
    with open(configFile, 'w') as f:
      json.dump(config, f, indent=2)
    return config

def saveConfig(config):
    with open('tiktok_config.json', 'w') as f:
      json.dump(config, f, indent=2)

def getAuthTokens(cookies):
  msToken = next((cookie['value'] for cookie in cookies if cookie['name'] == 'msToken'), '')
  sessionId = next((cookie['value'] for cookie in cookies if cookie['name'] == 'sessionid'), '')
  return msToken, sessionId

def captureTiktokData(config):
  print("No cookies found in config, login to TikTok to continue")
  with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    timeout = 60000 * 5

    page.goto("https://www.tiktok.com/login/phone-or-email/email")

    page.wait_for_selector('a[href*="/upload"]', timeout=timeout) or \
    page.wait_for_selector('.avatar-anchor', timeout=timeout) or \
    page.wait_for_selector('[data-e2e="profile-icon"]', timeout=timeout)

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
    browser.close()

def getTiktokData():
  config = getOrCreateConfig()

  # Add token validation
  if not config.get('cookies'):
    msToken, sessionId = getAuthTokens(config['cookies'])
    if msToken and sessionId: print("Session cookies found, skipping login")
    else: captureTiktokData(config)
  return config

if __name__ == "__main__":
  getTiktokData()