from tiktok_collections import getCollectionData, getCollectionItems
from tiktok import getTiktokData
from download import downloadCollectionVideos
import asyncio

def main():
  config = getTiktokData()
  collections = getCollectionData(config)
  collectionData = { "collections": collections }
  collectionItems = getCollectionItems(config, collectionData)

  # Testing - Limit to first collection and first 5 videos
  collectionItems["collections"] = collectionItems["collections"][:1]
  collectionItems["collections"][0]['itemList'] = collectionItems['collections'][0].get('itemList', [])[:5]
  
  asyncio.run(downloadCollectionVideos(collectionItems, config))
  return collectionItems

if __name__ == "__main__":
  main()