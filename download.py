from TikTokApi import TikTokApi
from tiktok import getAuthTokens
from tiktok_collections import loadConfig
import os
import json
from tqdm import tqdm
import time
from datetime import datetime
import asyncio
import httpx

def cleanFilename(text, maxWords=12, maxLength=60):
  # Max Words
  text = text.replace(':', '--')
  words = text.split()[:maxWords]
  cleaned = ' '.join(words)

  # Invalid characters
  invalidChars = '<>:"/\\|?*'
  for char in invalidChars:
    cleaned = cleaned.replace(char, '')

  # Max string length
  if len(cleaned) > maxLength:
    cleaned = cleaned[:maxLength-3] + '...' 
  
  return cleaned

def getIdFromUrl(url): return url.split('/')[-1]

def getDownloadAddr(info):
  if "video" in info:
    videoInfo = info["video"]
    videoInfo["downloadAddr"] = (
      videoInfo.get("downloadAddr") or 
      videoInfo.get("playAddr") or
      ""
    )

async def withRetries(operation, maxRetries=3):
  for attempt in range(maxRetries):
    try:
      return await operation()
    except Exception as e:
      if attempt == maxRetries - 1:
        print(f"Max retries reached. Error: {str(e)}")
        print(f"\nError from operation: {operation}")
        raise
      # Exponential backoff: 2^0=1, 2^1=2, 2^2=4 seconds, etc.
      await asyncio.sleep(2 ** attempt)

def skipDuplicateVideos(file):
  if os.path.exists(file):
    existingSize = os.path.getsize(file)
    return existingSize > 300 * 1024  # 300KB
  
def skipDuplicatePhotos(path, photoCount):
  if not os.path.exists(path):
    return False
  PHOTO_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif')
  return len([f for f in os.listdir(path)
    if f.lower().endswith(PHOTO_EXTENSIONS)]) >= photoCount

async def fetchVideo(api, url):
  try:
    video = api.video(url=url)
    info = await video.info()
    if info.get('isContentClassified') == True:
      print(f"\nisClassified: {url}")
      info = manualFetch(url)
    getDownloadAddr(info)
    return video, info
  except Exception as e:
    print(f"\nFETCHVIDEO ERROR: {url} - {e}")
    # Log the response details
    if hasattr(e, 'response'):
      print(f"\nError from URL: {url}")
      print(f"\nResponse Status: {e.response.status_code}")
      print(f"\nResponse Headers: {e.response.headers}")
      print(f"\nResponse Body: {e.response.text}")
      print(f"\nResponse Full: {str(e)}")
    raise

async def saveVideo(video, videoPath, info, saveLog):
  try:
    print("Trying videobytes")
    videoBytes = await withRetries(lambda: video.bytes())
  except Exception as e:
    print("Trying downloadAddr manually")
    downloadAddr = info["video"]["downloadAddr"]
    challengeToken = info.get('tt_chain_token')
    videoBytes = await manuallySaveVideo(downloadAddr, challengeToken)
  print(saveLog)
  with open(videoPath, "wb") as output:
    output.write(videoBytes)

async def manuallySaveVideo(url, challengeToken=None):
  config = loadConfig()
  msToken, sessionId = getAuthTokens(config['cookies'])
  cookieString = f"sessionid={sessionId}; msToken={msToken}"
  if challengeToken: cookieString += f"; tt_chain_token={challengeToken}"

  headers = {
    "Accept": "*/*",
    "User-Agent": config['app_context']['userAgent'],
    "Cookie": cookieString,
    "Range": "bytes=0-",
    "Accept-Encoding": 'identity;q=1, *;q=0',
    "Referer": 'https://www.tiktok.com/'
  }

  response = httpx.get(url, headers=headers)
  response.raise_for_status()
  return response.content

async def savePhotos(imagePost, slideShowPath, saveLog):
  images = imagePost['images']
  os.makedirs(slideShowPath, exist_ok=True)

  for i, image in enumerate(images):
    imagePath = os.path.join(slideShowPath, f"image-{i+1}.jpg")
    if skipDuplicatePhotos(imagePath, 1):
      print(f"\nAlready saved - {imagePath}")
      continue

    # Download photos
    print(saveLog)
    urls = image['imageURL']['urlList']
    for url in urls:
      try:
        response = httpx.get(url)
        response.raise_for_status()
        with open(imagePath, "wb") as f:
          f.write(response.content)
        await asyncio.sleep(0.5)
        break
      except Exception:
        continue

def saveMetadata(metaPath, item):
  metadata = {
    "author": item['author'],
    "contents": item['contents'],
    "createTime": item['createTime'],
    "desc": item['desc'],
    "id": item['id'],
    "music": item['music'],
    "stats": item['stats'],
    "video": item['video']
  }

  with open(metaPath, "w", encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

def parseVideoInfo(response, id):
  # Try SIGI_STATE first
  sigiData = extractJsonFromScript(response.text, "SIGI_STATE")
  if sigiData: return sigiData["ItemModule"][id]

  # Fall back to UNIVERSAL_DATA
  universalData = extractJsonFromScript(response.text, "__UNIVERSAL_DATA_FOR_REHYDRATION__")
  if universalData:
    defaultScope = universalData.get("__DEFAULT_SCOPE__", {})
    videoDetail = defaultScope.get("webapp.video-detail", {})

    if videoDetail.get("statusCode", 0) != 0:
      raise ValueError(f"Invalid video detail response. Status code: {response.status_code}")

    return videoDetail.get("itemInfo", {}).get("itemStruct")

  raise ValueError(f"No valid video data found. Status code: {response.status_code}")

def extractJsonFromScript(htmlText, scriptId):
  start = htmlText.find(f'<script id="{scriptId}" type="application/json">')
  if start == -1: return None

  start += len(f'<script id="{scriptId}" type="application/json">')
  end = htmlText.find("</script>", start)

  if end == -1: return None
  return json.loads(htmlText[start:end])

def getSessionCookie(cookies):
  for cookie in cookies:
    if cookie['name'] == 'sessionid':
      return cookie
  return None

def manualFetch(url):
  # Try manual fetch as fallback
  config = loadConfig()
  msToken, sessionId = getAuthTokens(config['cookies'])

  headers = {
    "Accept": "*/*",
    "User-Agent": config['app_context']['userAgent'],
    "Cookie": f"sessionid={sessionId}; msToken={msToken}"
    }
  
  response = httpx.get(url, headers=headers)
  response.raise_for_status()
  challengeToken = response.cookies.get('tt_chain_token')
  videoId = getIdFromUrl(url)
  videoInfo = parseVideoInfo(response, videoId)
  videoInfo['tt_chain_token'] = challengeToken
  return videoInfo

async def downloadCollectionVideos(collectionData, config=None):
  if not config:
    config = loadConfig()
  cookies = config['cookies']
  msToken, _s = getAuthTokens(cookies)
  id = config['app_context']['user']['uniqueId']
  print(f"Downloading {id}'s collections")

  async with TikTokApi() as api:
    await api.create_sessions(ms_tokens=[msToken], num_sessions=1, sleep_after=5)
    # Create output directory
    outputDir = f"{id}-tiktok-collection"
    os.makedirs(outputDir, exist_ok=True)
    os.makedirs(os.path.join(outputDir, "logs"), exist_ok=True)

    index = 0
    failures = {}
    total = sum(len(collection.get('itemList', []))
      for collection in collectionData['collections'])

    for collection in collectionData['collections']:
      collectionName = collection['name']
      collectionPath = os.path.join(outputDir, 'Collections', collectionName)
      os.makedirs(collectionPath, exist_ok=True)
      print(f"\nSaving {collectionName} collection")

      for item in tqdm(collection.get('itemList', [])):
        index += 1
        videoId = item['id']
        authorId = item['author']['uniqueId']
        desc = cleanFilename(item['desc'])
        createTime = datetime.fromtimestamp(item['createTime']).strftime('%m-%d-%Y')
        filenameBase = f"{authorId} - {desc} - {createTime}"
        url = f"https://www.tiktok.com/@{authorId}/video/{videoId}"

        try:
          video, info = await withRetries(lambda: fetchVideo(api, url))
          videoPath = os.path.join(collectionPath, f"{filenameBase}.mp4")
          imagePost = info.get('imagePost')

          if imagePost:
            # Save photo
            photoPath = os.path.splitext(videoPath)[0]
            if skipDuplicatePhotos(photoPath, len(imagePost['images'])):
              print(f"\nAlready saved - {collectionName}/{filenameBase[:40]}")
              continue
            saveLog = f"\nSaving slideshow {index}/{total} - {collectionName}/{filenameBase[:40]}"
            await savePhotos(imagePost, photoPath, saveLog)
          else:
            # Save video
            if skipDuplicateVideos(videoPath):
              print(f"\nAlready saved - {collectionName}/{filenameBase[:40]}")
              continue
            saveLog = f"\nSaving video {index}/{total} - {collectionName}/{filenameBase[:40]}"
            await saveVideo(video, videoPath, info, saveLog)

          # Save metadata
          metaPath = os.path.join(collectionPath, f"{filenameBase}.json")
          saveMetadata(metaPath, item)
          time.sleep(1)  # Rate limiting

        except Exception as e:
          print(f"Error downloading video {url}: {str(e)}")
          failures[videoId] = { "collection": collectionName, "error": str(e), "metadata": item }
          if 'info' in locals(): failures[videoId]["video"] = info  # Only add info if it exists

    # Save failures log
    if failures:
      failuresPath = os.path.join(outputDir, "logs", "download_failures.json")
      with open(failuresPath, "w", encoding='utf-8') as f:
        json.dump(failures, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
  import sys

  if len(sys.argv) < 2 or len(sys.argv) > 3:
    print("Usage: python download.py <collection_json_file> <output_directory>")
    sys.exit(1)

  collectionFile = sys.argv[1]
  config = sys.argv[2] if len(sys.argv) == 3 else None

  with open(collectionFile, 'r', encoding='utf-8') as f:
    collectionData = json.load(f)

  asyncio.run(downloadCollectionVideos(collectionData, config))