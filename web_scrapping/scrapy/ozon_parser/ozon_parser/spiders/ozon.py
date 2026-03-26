import scrapy
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
import re
import json

from ..items import OzonParserItem

class OzonSpider(scrapy.Spider):
    name = "ozon"
    allowed_domains = ["ozon.ru", "www.ozon.ru"]
    # start_urls = ["https://www.ozon.ru/category/"]   # Стартовая страница каталога

    # Ограничение на количество страниц в категории (можно убрать или увеличить)
    max_pages = 8

    with open('/mnt/c/Users/leous/.vscode/2_course/web_scrapping/scrapy/ozon_parser/ozon_parser/spiders/headers.json', 'r', encoding='utf-8') as file:
        headers = json.load(file)

    # XPath для поиска ссылок на категории
    category_xpath = (
        '//a[contains(@href, "/category/") '
        'and not(contains(@href, "/brand/")) '
        'and not(contains(@href, "?")) '
        'and not(starts-with(@href, "http"))]'
    )

    # XPath для поиска блоков товаров на странице категории
    product_xpath = "//div[contains(@class, 'qi0_24')]/div[contains(@class, 'tile-root')]"

    # Относительные XPath для полей внутри блока товара
    field_xpaths = {
        "image_href": ".//a[contains(@class, 'q4b1_4_0-a tile-clickable-element ki1_24')]/@href",
        "name": ".//span[contains(@class, 'tsBody500Medium')]/text()",
        "cost": ".//span[contains(@class, 'c35_3_13-a1 tsHeadline500Medium')]/text()",
        "discount": ".//span[contains(@class, 'tsBodyControl400Small c35_3_13-a6 c35_3_13-b4')]/text()",
        "rating": ".//div[contains(@class, 'i4k_24 ik5_24 p6b3_2_0-a p6b3_2_0-a0 p6b3_2_0-a1 tsBodyMBold')]/span[contains(@class, 'p6b3_2_0-a4')][1]/span/text()",
        "reviews": ".//div[contains(@class, 'i4k_24 ik5_24 p6b3_2_0-a p6b3_2_0-a0 p6b3_2_0-a1 tsBodyMBold')]/span[contains(@class, 'p6b3_2_0-a4')][2]/span/text()",
    }

    def start_requests(self):
        # Стартовый запрос с заданными заголовками
        yield scrapy.Request(
            url="https://www.ozon.ru/category/",
            headers=self.headers,
            callback=self.parse
        )

    # Функции обработки полей 
    def clean_price(self, value):
        """Удаляет тонкие пробелы и знак рубля, преобразует в число."""
        if value is None:
            return None
        cleaned = value.replace('\u2009', '').replace('₽', '').strip()
        try:
            return float(cleaned) if '.' in cleaned else int(cleaned)
        except ValueError:
            return cleaned

    def extract_number(self, value):
        """Извлекает первое число из строки."""
        if value is None:
            return None
        match = re.search(r'\d+', value)
        return int(match.group()) if match else None

    def clean_str(self, value):
        """Удаляет лишние пробелы и знак рубля."""
        if value is None:
            return None
        return value.replace('\u2009', '').replace('₽', '').strip()

    def parse(self, response):
        """Извлекает категории со стартовой страницы."""
        category_links = response.xpath(self.category_xpath)
        for link in category_links:
            href = link.xpath('@href').get()
            name = link.xpath('text()').get()
            if href and name:
                full_url = response.urljoin(href)
                yield scrapy.Request(
                    url=full_url,
                    headers=self.headers,
                    callback=self.parse_category,
                    meta={'category_name': name.strip()}
                )

    def parse_category(self, response):
        """Парсит страницу категории: извлекает товары и обрабатывает пагинацию."""
        category_name = response.meta.get('category_name', 'Unknown')
        product_nodes = response.xpath(self.product_xpath)

        if not product_nodes:
            self.logger.info(f"В категории '{category_name}' на странице {response.url} товаров не найдено.")
            return

        for node in product_nodes:
            item = OzonParserItem()
            for field_name, xpath_expr in self.field_xpaths.items():
                value = node.xpath(xpath_expr).get()
                if value is not None:
                    if field_name in ('cost', 'rating'):
                        value = self.clean_price(value)
                    elif field_name in ('discount', 'reviews'):
                        value = self.extract_number(value)
                    elif field_name == 'image_href':
                        value = response.urljoin(value)   # абсолютный URL изображения
                    else:
                        value = self.clean_str(value)
                item[field_name] = value
            yield item

        # Пагинация: формируем URL следующей страницы через параметр page
        parsed = urlparse(response.url)
        query = parse_qs(parsed.query)
        current_page = int(query.get('page', ['1'])[0])
        next_page = current_page + 1

        if next_page <= self.max_pages:
            query['page'] = [str(next_page)]
            new_query = urlencode(query, doseq=True)
            next_url = urlunparse(parsed._replace(query=new_query))
            yield scrapy.Request(
                url=next_url,
                headers=self.headers,
                callback=self.parse_category,
                meta={'category_name': category_name}
            )