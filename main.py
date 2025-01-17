from tiktok_collections import getCollectionData, getCollectionItems, getFavorites, getUncategorizedFavorites
from tiktok import getTiktokData
from download import downloadCollectionVideos
import asyncio

async def main():
  config = getTiktokData()

  # Get collections
  collections = getCollectionData(config)
  collectionData = { "collections": collections }
  collectionItems = getCollectionItems(config, collectionData)
  uncategorizedFavorites = getUncategorizedFavorites(collectionItems, config)

  # Download collections & favorites
  await downloadCollectionVideos(collectionItems, config)
  await downloadCollectionVideos(uncategorizedFavorites, config)

if __name__ == "__main__":
  asyncio.run(main())