# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class OzonParserItem(scrapy.Item):
    # define the fields for your item here like:
    image_href = scrapy.Field()
    name = scrapy.Field()
    cost = scrapy.Field()
    discount = scrapy.Field()
    rating = scrapy.Field()
    reviews = scrapy.Field()
