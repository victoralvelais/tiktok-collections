from tiktok_collections import getCollectionData, getCollectionItems
from tiktok import getTiktokData
from download import downloadCollectionVideos
import asyncio

def main():
  config = getTiktokData()
  collections = getCollectionData(config)
  collectionData = { "collections": collections }
  collectionItems = getCollectionItems(config, collectionData)

  # Testing - Limit to 10 collections and first 15 videos
  collectionItems["collections"] = collectionItems["collections"][:10]
  for collection in collectionItems["collections"]:
    collection['itemList'] = collection.get('itemList', [])[:15] 
  
  asyncio.run(downloadCollectionVideos(collectionItems, config))
  return collectionItems

if __name__ == "__main__":
  main()