import logging
from enum import Enum
from datetime import datetime, date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)


class ApnewsPureSeleniumRobot:

    class SearchCategory(Enum):
        STORIES = "Stories"
        SUBSECTIONS = "Subsections"
        VIDEOS = "Videos"


    def __init__(self, timeout: int=10, browser_width: int=1280, browser_height: int=720, browser_log_level: int=3):
        self.starting_url = "https://apnews.com/"

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument(f"--log-level={browser_log_level}")

        self.browser = webdriver.Chrome(options=chrome_options)
        self.browser.set_window_size(browser_width, browser_height)

        self.wait = WebDriverWait(self.browser, timeout=timeout)

        self.browser.get(self.starting_url)

        self.accept_cookies()


    def stop(self):
        self.browser.quit()


    def take_screenshot(self, file_path: str):
        self.browser.get_screenshot_as_file(file_path)


    def accept_cookies(self):
        try:
            accept_cookies_button = self.wait.until(expected_conditions.presence_of_element_located(
                (By.ID, "onetrust-accept-btn-handler")
            ))
            accept_cookies_button.click()
        except NoSuchElementException as exception:
            logger.debug(f"NoSuchElementException: {exception}")
            logger.warning(f"Accept cookies button not found")


    def search(self, search_phrase: str, from_date: date) -> list:
        result_list = list()

        self.browser.get(self.starting_url)

        search_button = self.wait.until(expected_conditions.presence_of_element_located(
            (By.CSS_SELECTOR, "button.SearchOverlay-search-button")
        ))
        search_button.click()

        search_input = self.wait.until(expected_conditions.presence_of_element_located(
            (By.CSS_SELECTOR, "input.SearchOverlay-search-input")
        ))
        search_input.send_keys(search_phrase + Keys.ENTER)

        try:
            search_filter = self.wait.until(expected_conditions.presence_of_element_located(
                (By.CSS_SELECTOR, "div.SearchFilter")
            ))
        except Exception:
            logger.debug("Search results not found")
            return result_list

        search_filter_heading = search_filter.find_element(By.CSS_SELECTOR, "div.SearchFilter-heading")
        search_filter_heading.click()

        try:
            search_filter_category = search_filter.find_element(
                By.XPATH, f"//span[contains(text(), '{self.SearchCategory.STORIES.value}')]"
            )
            search_filter_category.click()
        except NoSuchElementException:
            logger.warning(f"Search category {self.SearchCategory.STORIES.value} does not exist, will ignore it")


        first_article = self.wait.until(expected_conditions.presence_of_element_located(
            (By.CSS_SELECTOR, "div.SearchResultsModule-results div.PageList-items-item")
        ))

        logger.debug("Order latest news first")

        sort_by_selectbox = self.wait.until(expected_conditions.presence_of_element_located((By.NAME, 's')))
        Select(sort_by_selectbox).select_by_visible_text('Newest')

        self.wait.until(expected_conditions.staleness_of(first_article))

        result_list = self._add_news_to_list(result_list, from_date)

        logger.debug(result_list)

        return result_list


    def _add_news_to_list(self, result_list: list, from_date: date) -> list:
        news_element_list = self.wait.until(expected_conditions.visibility_of_all_elements_located(
            (By.CSS_SELECTOR, "div.SearchResultsModule-results div.PageList-items-item")
        ))

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
            next_page_button = self.browser.find_element(By.CSS_SELECTOR, "div.Pagination-nextPage a")
            next_page_button.click()
        except NoSuchElementException:
            logger.debug("No more pages found")
            return result_list

        return self._add_news_to_list(result_list, from_date)


    @staticmethod
    def _parse_news_data(news_element: webdriver.remote.webelement.WebElement) -> dict:
        timestamp = news_element.find_element(By.CSS_SELECTOR, "bsp-timestamp").get_attribute("data-timestamp")
        timestamp_seconds = int(timestamp) / 1000
        news_time = datetime.fromtimestamp(int(timestamp_seconds))

        news_dict = {
            "title": news_element.find_element(By.CSS_SELECTOR,
                                               "div.PagePromo-title span.PagePromoContentIcons-text").text,
            "date": news_time.date(),
        }

        try:
            news_dict["description"] = news_element.find_element(
                By.CSS_SELECTOR, "div.PagePromo-description span.PagePromoContentIcons-text"
            ).text
        except NoSuchElementException:
            news_dict["description"] = ""

        try:
            news_dict["image_url"] = news_element.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
        except NoSuchElementException:
            news_dict["image_url"] = None

        return news_dict
