import json
import os
import requests
import time
from types import SimpleNamespace
from tiktok import getAuthTokens

def buildUrl(appContext, cursor=0, collectionId=None, type="list"):
  baseUrls = {
    "list": "https://www.tiktok.com/api/user/collection_list/",
    "items": "https://www.tiktok.com/api/collection/item_list/",
    "favorites": "https://www.tiktok.com/api/user/collect/item_list/",
  }

  queryParams = {
    "aid": "1988",
    "count": "30",
    "cursor": str(cursor),
    "secUid": appContext['user']['secUid']
  }
  
  if collectionId:
    queryParams["collectionId"] = collectionId
    queryParams["sourceType"] = "113"
    type = "items"

  return baseUrls[type] + "?" + "&".join(f"{k}={v}" for k, v in queryParams.items())

def loadConfig():
  with open('tiktok_config.json', 'r') as f:
    return json.load(f)
  return config

def makeRequest(url, headers):
  session = requests.Session()
  retries = 3
  for attempt in range(retries):
    try:
      response = session.get(
        url,
        headers=headers,
        verify=True,
        timeout=10
      )
      return response.json()
    except requests.exceptions.SSLError:
      if attempt == retries - 1:
        raise
      time.sleep(2 * (attempt + 1))  # Exponential backoff
    except requests.exceptions.RequestException:
      if attempt == retries - 1:
        raise
      time.sleep(2 * (attempt + 1))


def buildHeaders(appContext, msToken, sessionId):
  return {
    "Accept": "*/*",
    "User-Agent": appContext['userAgent'],
    "Content-Type": "application/json",
    "Cookie": f"sessionid={sessionId}; msToken={msToken}"
  }

def saveToJson(data, fileName):
  with open(fileName, 'w') as f:
    json.dump(data, f, indent=2)
    f.flush()
  print(f"\nData saved to {fileName}")

def recentSave(filename):
  return os.path.exists(filename) and time.time() - os.path.getmtime(filename) < 12 * 3600

def recentlyCollected(dataFilePath, collections):
  recent = recentSave(dataFilePath)
  itemsCollected = all('itemList' in collection and collection['itemList'] and len(collection['itemList']) > 0 for collection in collections)
  return (recent and itemsCollected)

def map_collection_item(item):
  return {
    'author': {
      'id': item['author']['id'],
      'nickname': item['author']['nickname'],
      'secUid': item['author']['secUid'],
      'signature': item['author']['signature'],
      'uniqueId': item['author']['uniqueId'],
      'verified': item['author']['verified']
    },
    'contents': item.get('contents', []),
    'createTime': item['createTime'],
    'desc': item['desc'],
    'id': item['id'],
    'music': {
      'authorName': item['music'].get('authorName', ''),
      'duration': item['music'].get('duration', 0),
      'id': item['music'].get('id', ''),
      'original': item['music'].get('original', False),
      'playUrl': item['music'].get('playUrl', ''),
      'title': item['music'].get('title', '')
    },
    'stats': {
      'collectCount': item['stats'].get('collectCount', 0),
      'commentCount': item['stats'].get('commentCount', 0),
      'diggCount': item['stats'].get('diggCount', 0),
      'playCount': item['stats'].get('playCount', 0),
      'shareCount': item['stats'].get('shareCount', 0)
    },
    'video': {
      'duration': item['video'].get('duration', 0),
      'format': item['video'].get('format', 'mp4'),
      'width': item['video'].get('width', 0),
      'height': item['video'].get('height', 0),
      'id': item['video']['id'],
      'ratio': item['video'].get('ratio', '')
    }
}

def getCollectionData(config=None):
  if not config:
    config = loadConfig()
  msToken, sessionId = getAuthTokens(config['cookies'])
  dataFilePath = f"collection_data_{config['app_context']['user']['uniqueId']}.json"
  
  cursor = 0
  # hasMore = not recentSave(dataFilePath) # Bugged - first run
  hasMore = True
  collections = [] if hasMore else json.load(open(dataFilePath))['collections']
  
  while hasMore:
    reqUrl = buildUrl(config['app_context'], cursor)
    headers = buildHeaders(config['app_context'], msToken, sessionId)
    data = makeRequest(reqUrl, headers)

    if 'collectionList' in data:
      collections.extend(data['collectionList'])
      hasMore = data.get('hasMore', False)
      cursor = data.get('cursor', 0)
      print(f"Fetched {len(data['collectionList'])} items. Total: {len(collections)}")
    else:
      hasMore = False

    time.sleep(1)

  outputData = {
    'total': len(collections),
    'user': config['app_context']['user'],
    'collections': collections
  }

  saveToJson(outputData, dataFilePath)
  return collections

def getCollectionItems(config=None, collectionData=None):
  if not config:
    config = loadConfig()
  msToken, sessionId = getAuthTokens(config['cookies'])
  dataFilePath = f"collection_data_{config['app_context']['user']['uniqueId']}.json"

  if not collectionData:
    with open(dataFilePath, 'r') as f:
      collectionData = json.load(f)
  
  # Bugged
  # if recentlyCollected(dataFilePath, collectionData['collections']):
  #   print("All collections were recently fetched - skipping update")
  #   return collectionData

  else:
    totalItems = 0
    for collection in collectionData['collections']:
      collectionItems = []
      cursor = 0
      hasMore = True

      try:
        print(f"\nFetching collection: {collection['name']} - Total: {collection['total']}")
        while hasMore:
          reqUrl = buildUrl(config['app_context'], cursor, collection['collectionId'])
          headers = buildHeaders(config['app_context'], msToken, sessionId)
          data = makeRequest(reqUrl, headers)
          
          
          if 'itemList' in data:
            collectionItems.extend([map_collection_item(item) for item in data['itemList']])
            hasMore = data.get('hasMore', False)
            cursor = data.get('cursor', 0)
            print(f"Got {len(data['itemList'])} items. Total: {len(collectionItems)}")
          else:
            hasMore = False
          
          time.sleep(1)
      except Exception as e:
        print(f"\nError fetching collection {collection['name']}: {str(e)}")
        print("Saving progress and continuing to next collection...")

      # Directly add items to the collection in collectionDict
      for idx, collectionStore in enumerate(collectionData['collections']):
        if collectionStore['collectionId'] == collection['collectionId']:
          collectionData['collections'][idx]['itemList'] = collectionItems
          items_in_collection = len(collectionItems)
          print(f"Collection '{collectionStore['name']}': {items_in_collection} items")
          totalItems += items_in_collection
          break
      
      print(f"\nTotal items across all collections: {totalItems}")

    saveToJson(collectionData, dataFilePath)
    return collectionData

def getFavorites(config=None):
  if not config:
    config = loadConfig()
  msToken, sessionId = getAuthTokens(config['cookies'])
  dataFilePath = f"favorites_data_{config['app_context']['user']['uniqueId']}.json"

  cursor = 0
  hasMore = not recentSave(dataFilePath)
  favorites = [] if hasMore else json.load(open(dataFilePath))['favorites']

  try:
    while hasMore:
      reqUrl = buildUrl(config['app_context'], cursor, None, "favorites")
      headers = buildHeaders(config['app_context'], msToken, sessionId)
      data = makeRequest(reqUrl, headers)

      if 'itemList' in data:
        favorites.extend([map_collection_item(item) for item in data['itemList']])
        hasMore = data.get('hasMore', False)
        cursor = data.get('cursor', 0)
        print(f"Got {len(data['itemList'])} items. Total: {len(favorites)}")
      time.sleep(1)
  except Exception as e:
    print(f"\nError fetching favorites: {str(e)}")
    print("Saving progress and continuing to next collection...")

  outputData = {
    'total': len(favorites),
    'user': config['app_context']['user'],
    'favorites': favorites
  }

  saveToJson(outputData, dataFilePath)
  return favorites

def getUncategorizedFavorites(collectionItems, config=None):
  if not config:
    config = loadConfig()
  
  # Get all video IDs from collections
  collectedIds = set()
  for collection in collectionItems["collections"]:
    collectedIds.update(item['id'] for item in collection.get('itemList', []))
  print(f"Total unique videos found in collections: {len(collectedIds)}")
  
  # Get favorites and filter out already collected ones
  favorites = getFavorites(config)
  uncategorized = [
    item 
    for item in favorites 
    if item['id'] not in collectedIds
  ]
  
  return {
    "collections": [{ "name": "Uncategorized", "itemList": uncategorized }]
  }

if __name__ == "__main__":
  pass