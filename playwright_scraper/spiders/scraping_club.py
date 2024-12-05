import scrapy
from scrapy.http import HtmlResponse
from playwright_scraper.items import PlaywrightScraperItem
from urllib.parse import urljoin

class ScrapingClubSpider(scrapy.Spider):
    name = "scraping_club"
    allowed_domains = ["emag.ro"]

    def start_requests(self):
        url = "https://www.emag.ro/laptopuri/c"
        yield scrapy.Request(
            url,
            meta={
                "playwright": True,
                "playwright_include_page": True,
                "playwright_wait_for": "div#card_grid"  # Wait for the div with the id 'card_grid'
            }
        )

    async def parse(self, response):
        # Access the page from the response meta
        page = response.meta["playwright_page"]

        # Wait for the div with the id 'card_grid' to be present on the page
        await page.wait_for_selector('div#card_grid')

        # Now that the element is available, extract the page content
        html = await page.content()

        # Use Scrapy to parse the HTML content
        response = HtmlResponse(url=response.url, body=html, encoding='utf-8')

        # Log the response for debugging
        self.logger.info(f"Parsing page: {response.url}")

        # Iterate over the product elements inside the 'card_grid' div
        for product in response.css("div#card_grid div.card-v2"):
            # Select the child div with class 'card-v2-wrapper js-section-wrapper' inside 'card-v2'
            card_wrapper_info = product.css("div.card-v2 div.card-v2-wrapper.js-section-wrapper div.card-v2-info")
            card_wrapper_price = product.css("div.card-v2 div.card-v2-wrapper.js-section-wrapper div.card-v2-content")

            # Extract product data from 'card-v2-wrapper js-section-wrapper'
            url = card_wrapper_info.css("a::attr(href)").get()
            name = card_wrapper_info.css("div.px-2 h2 a::text").get()
            price = card_wrapper_price.css("p.product-new-price::text").get() + "." + str(card_wrapper_price.css("p.product-new-price sup::text").get())

            # Create an item instance
            item = PlaywrightScraperItem()
            item['link'] = url
            item['name'] = name
            item['price'] = price

            # Yield the item
            yield item

        # Find the next page link (relative path)
        next_page = response.css('a.js-change-page[aria-label="Next"]::attr(href)').get()

        # Log the next page link for debugging
        self.logger.info(f"Next page should be: {next_page}")

        if next_page:
            # Use urljoin to handle both relative and absolute URLs correctly
            next_page_url = urljoin(response.url, next_page)

            # Yield the next page request
            yield scrapy.Request(
                url=next_page_url,
                callback=self.parse,  # Parse the next page
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_wait_for": "div#card_grid"  # Wait for the div with the id 'card_grid' again
                }
            )
        else:
            self.logger.info("No next page found or got some captcha")
    
    def get_playwright_browser(self):
        """Override the browser initialization to launch in headless mode."""
        from playwright.async_api import async_playwright

        async def launch_browser():
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)  # Ensure headless mode is enabled
                return browser

        return launch_browser()