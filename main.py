from tiktok_collections import getCollectionData, getCollectionItems, getUncategorizedFavorites
from tiktok import getTiktokData
from download import downloadCollectionVideos
import asyncio

def main():
  config = getTiktokData()

  # Get collections
  collections = getCollectionData(config)
  collectionData = { "collections": collections }
  collectionItems = getCollectionItems(config, collectionData)
  uncategorizedFavorites = getUncategorizedFavorites(collectionItems, config)

  # Download collections & favorites
  asyncio.run(downloadCollectionVideos(collectionItems, config))
  asyncio.run(downloadCollectionVideos(uncategorizedFavorites, config))

if __name__ == "__main__":
  main()