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

async def downloadWithRetries(video, maxRetries=3):
  for attempt in range(maxRetries):
    try:
      return await video.bytes()
    except Exception as e:
      if attempt == maxRetries - 1:
        raise
      await asyncio.sleep(2 ** attempt)

def skipDuplicateVideos(file):
  if os.path.exists(file):
    existingSize = os.path.getsize(file)
    return existingSize > 300 * 1024  # 300KB
  
def skipDuplicatePhotos(path, photoCount):
  PHOTO_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif')
  return len([f for f in os.listdir(path)
    if f.lower().endswith(PHOTO_EXTENSIONS)]) >= photoCount

async def fetchVideo(api, url):
  video = api.video(url=url)
  info = await video.info()

  if "video" in info:
    videoInfo = info["video"]
    videoInfo["downloadAddr"] = (
      videoInfo.get("downloadAddr") or 
      videoInfo.get("playAddr") or 
      ""
    )

  return video, info

async def saveVideo(video, videoPath, saveLog):
  videoBytes = await downloadWithRetries(video)
  print(saveLog)
  with open(videoPath, "wb") as output:
    output.write(videoBytes)

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
        break
      except Exception:
        continue

async def downloadCollectionVideos(collectionData, config=None):
  if not config:
    config = loadConfig()
  msToken, _s = getAuthTokens(config['cookies'])
  id = config['app_context']['user']['uniqueId']
  print(f"Downloading {id}'s collections")

  async with TikTokApi() as api:
    await api.create_sessions(ms_tokens=[msToken], num_sessions=1, sleep_after=3)
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
        video, info = await fetchVideo(api, url)

        try:
          videoPath = os.path.join(collectionPath, f"{filenameBase}.mp4")
          imagePost = info.get('imagePost')

          if imagePost:
            # Save photo
            photoPath = os.path.splitext(videoPath)[0]
            if skipDuplicatePhotos(photoPath, len(imagePost['images'])):
              print(f"\nAlready saved - {collectionName}/{filenameBase[:40]}")
              continue
            saveLog = f"\nSaving slideshow {index}/{total} - {collectionName}/{filenameBase[:40]}"
            savePhotos(imagePost, photoPath, saveLog)
          else:
            # Save video
            if skipDuplicateVideos(videoPath):
              print(f"\nAlready saved - {collectionName}/{filenameBase[:40]}")
              continue
            saveLog = f"\nSaving video {index}/{total} - {collectionName}/{filenameBase[:40]}"
            saveVideo(video, videoPath, saveLog)

          # Save metadata
          metaPath = os.path.join(collectionPath, f"{filenameBase}.json")
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

          time.sleep(1)  # Rate limiting

        except Exception as e:
          print(f"Error downloading video {url}: {str(e)}")
          failures[videoId] = {
            "collection": collectionName,
            "error": str(e),
            "metadata": item,
            "video": info
          }

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