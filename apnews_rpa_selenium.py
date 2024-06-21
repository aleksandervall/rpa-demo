import logging
from enum import Enum
from datetime import datetime, date, timedelta
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebElement
from selenium.common.exceptions import ElementNotInteractableException, ElementClickInterceptedException
from SeleniumLibrary.errors import ElementNotFound

from RPA.Browser.Selenium import Selenium

logger = logging.getLogger(__name__)


class ApnewsRpaSeleniumRobot:

    class SearchCategory(Enum):
        STORIES = "Stories"
        SUBSECTIONS = "Subsections"
        VIDEOS = "Videos"


    def __init__(self, timeout: int=10, browser_width: int=1280, browser_height: int=720):
        self.starting_url = "https://apnews.com/"

        self.browser = Selenium()
        self.browser.open_available_browser(self.starting_url)

        self.browser.set_selenium_timeout(timedelta(seconds=timeout))
        self.browser.set_window_size(browser_width, browser_height)

        self.accept_cookies()


    def stop(self):
        self.browser.close_all_browsers()


    def take_screenshot(self, file_path: str):
        self.browser.capture_page_screenshot(file_path)


    def accept_cookies(self):
        try:
            self.browser.click_button("I Accept")
        except ElementNotFound:
            logger.warning(f"Accept cookies button not found")


    def search(self, search_phrase: str, from_date: date) -> list:
        result_list = list()

        self.browser.go_to(self.starting_url)

        self.browser.click_button("css:button.SearchOverlay-search-button")
        self.browser.input_text("css:input.SearchOverlay-search-input", search_phrase + Keys.ENTER)

        self.browser.wait_until_element_is_visible("css:div.SearchFilter", error="Search results not found")

        try:
            self.browser.click_element("css:div.SearchFilter div.SearchFilter-heading")
            self.browser.click_element(f"xpath://span[contains(text(), '{self.SearchCategory.STORIES.value}')]")
            self.browser.wait_until_page_does_not_contain_element("css:div.SearchFilter")
            self.browser.wait_until_page_contains_element("css:div.SearchFilter")
        except ElementNotFound:
            logger.warning(f"Search category {self.SearchCategory.STORIES.value} does not exist, will ignore it")
        except AssertionError:
            self.browser.wait_until_page_contains_element("css:div.SearchFilter")

        logger.debug("Order latest news first")
        self.browser.select_from_list_by_label("name:s", "Newest")

        try:
            self.browser.wait_until_page_does_not_contain_element("css:div.SearchFilter")
            self.browser.wait_until_page_contains_element("css:div.SearchFilter")
        except AssertionError:
            self.browser.wait_until_page_contains_element("css:div.SearchFilter")

        result_list = self._add_news_to_list(result_list, from_date)

        logger.debug(result_list)

        return result_list


    def _add_news_to_list(self, result_list: list, from_date: date) -> list:
        news_element_list = self.browser.find_elements("css:div.SearchResultsModule-results div.PageList-items-item")

        first_news_dict = self._parse_news_data(news_element_list[0])
        if first_news_dict.get("date") < from_date:
            return result_list

        for news_element in news_element_list:
            try:
                news_dict = self._parse_news_data(news_element)

                if news_dict.get("date") < from_date:
                    continue

                result_list.append(news_dict)

            except Exception as error:
                logger.debug(f"Parsing data error: {error}")
                logger.warning(f"Problem when parsing news data, will continue with next news")

        try:
            self.browser.click_element("css:div.Pagination-nextPage a")
        except ElementNotFound:
            logger.debug("No more pages found")
            return result_list

        return self._add_news_to_list(result_list, from_date)


    def _parse_news_data(self, news_element: WebElement) -> dict:
        timestamp = self.browser.find_element("css:bsp-timestamp", news_element).get_attribute("data-timestamp")
        timestamp_seconds = int(timestamp) / 1000
        news_time = datetime.fromtimestamp(int(timestamp_seconds))

        news_dict = {
            "title": self.browser.find_element(
                "css:div.PagePromo-title span.PagePromoContentIcons-text",
                news_element
            ).text,
            "date": news_time.date(),
        }

        try:
            news_dict["description"] = self.browser.find_element(
                "css:div.PagePromo-description span.PagePromoContentIcons-text",
                news_element
            ).text
        except ElementNotFound:
            news_dict["description"] = ""

        try:
            news_dict["image_url"] = self.browser.find_element("css:img", news_element).get_attribute("src")
        except ElementNotFound:
            news_dict["image_url"] = None

        return news_dict
