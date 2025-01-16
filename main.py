from tiktok_collections import getCollectionData, getCollectionItems
from tiktok import getTiktokData
from download import downloadCollectionVideos
import asyncio

def main():
  config = getTiktokData()
  collections = getCollectionData(config)
  collectionData = { "collections": collections }
  collectionItems = getCollectionItems(config, collectionData)

  asyncio.run(downloadCollectionVideos(collectionItems, config))
  return collectionItems

if __name__ == "__main__":
  main()