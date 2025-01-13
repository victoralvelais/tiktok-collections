from TikTokApi import TikTokApi
from tiktok import getAuthTokens
from tiktok_collections import loadConfig
import os
import json
from tqdm import tqdm
import time
from datetime import datetime

def truncateDescription(desc, max_words=12):
  words = [word.replace('@', '(a)').replace(':', ' - ') for word in desc.split()]
  truncated = ' '.join(words[:max_words])
  if len(words[max_words:]) > 0:
    truncated += ' ...'
  return truncated

async def downloadCollectionVideos(collectionData, config=None):
  if not config:
    config = loadConfig()
  msToken, _s = getAuthTokens(config.cookies)
  id = config.app_context.user.uniqueId
  print(f"Downloading {id}'s collections")

  async with TikTokApi() as api:
    await api.create_sessions(ms_tokens=[msToken], num_sessions=1, sleep_after=3)
    # Create output directory
    outputDir = f"{id}-tiktok-collection"
    os.makedirs(outputDir, exist_ok=True)
    os.makedirs(os.path.join(outputDir, "logs"), exist_ok=True)

    failures = {}
    for collection in collectionData['collections']:
      collectionName = collection['name']
      collectionPath = os.path.join(outputDir, 'Collections', collectionName)
      os.makedirs(collectionPath, exist_ok=True)
      print(f"\nProcessing collection: {collectionName}")

      for item in tqdm(collection.get('itemList', [])):
        videoId = item['id']
        authorId = item['author']['uniqueId']
        desc = truncateDescription(item['desc'])
        createTime = datetime.fromtimestamp(item['createTime']).strftime('%m-%d-%Y')
        filenameBase = f"{authorId} - {desc} - {createTime}"
        url = f"https://www.tiktok.com/@{authorId}/video/{videoId}"

        try:
          # Save video file
          videoPath = os.path.join(collectionPath, f"{filenameBase}.mp4")
          print(f"\nSaving video - {videoPath}")
          video = api.video(url=url)
          info = await video.info()

          if not info["video"]["downloadAddr"]:
            info["video"]["downloadAddr"] = info["video"]["playAddr"]

          videoBytes = await video.bytes()

          if os.path.exists(videoPath):
            existingSize = os.path.getsize(videoPath)
            if existingSize == len(videoBytes):
              print(f"Skipping duplicate")
              continue

          with open(videoPath, "wb") as output:
            output.write(videoBytes)

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
            "metadata": item
          }

    # Save failures log
    if failures:
      failuresPath = os.path.join(outputDir, "logs", "download_failures.json")
      with open(failuresPath, "w", encoding='utf-8') as f:
        json.dump(failures, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
  import asyncio
  import sys
  import json

  if len(sys.argv) < 2 or len(sys.argv) > 3:
    print("Usage: python download.py <collection_json_file> <output_directory>")
    sys.exit(1)

  collectionFile = sys.argv[1]
  config = sys.argv[2] if len(sys.argv) == 3 else None

  with open(collectionFile, 'r', encoding='utf-8') as f:
    collectionData = json.load(f)

  asyncio.run(downloadCollectionVideos(collectionData, config))