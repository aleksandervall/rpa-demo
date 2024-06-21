import os
import re
import io
import uuid
import logging
import requests
from PIL import Image
from datetime import datetime
from dateutil.relativedelta import relativedelta

from apnews_rpa_selenium import ApnewsRpaSeleniumRobot as ApnewsRobot

from robocorp.tasks import task
from RPA.Excel.Files import Files as Excel


logger = logging.getLogger(__name__)

SEARCH_PHRASE = os.getenv("SEARCH_PHRASE", "automation")
NUMBER_OF_MONTHS = os.getenv("NUMBER_OF_MONTHS", 1)
OUTPUT_PATH = os.getenv("ROBOT_ARTIFACTS", "output")
NEWS_EXCEL_PATH = os.path.join(OUTPUT_PATH, os.getenv("NEWS_EXCEL_FILENAME", "news.xlsx"))
DOWNLOAD_IMAGE_PATH = os.path.join(OUTPUT_PATH, os.getenv("DOWNLOAD_IMAGE_DIR", ""))


@task
def search_news():
    logging.basicConfig(level=logging.INFO)

    starting_date = (datetime.now() - relativedelta(months=max(0, (int(NUMBER_OF_MONTHS) - 1)))).replace(day=1).date()

    logger.info(f"Started searching news for phrase '{SEARCH_PHRASE}' from {starting_date}")

    apnews_robot = ApnewsRobot()

    try:
        result_list = apnews_robot.search(SEARCH_PHRASE, starting_date)

        logger.info(f"News found: {len(result_list)}")

        if result_list:
            save_excel(result_list)

    except Exception as error:
        apnews_robot.take_screenshot(os.path.join("output", "error.png"))
        logger.error(error)

    finally:
        logger.info("Searching news completed")
        apnews_robot.stop()


def save_excel(result_list: list):
    excel_data = {
        "title": [],
        "date": [],
        "description": [],
        "picture_filename": [],
        "count_of_search_phrases": [],
        "has_money_amount": []
    }

    logger.info("Preparing news data for Excel")

    for news_dict in result_list:
        excel_data["title"].append(news_dict.get("title", ""))
        excel_data["date"].append(news_dict.get("date", ""))
        excel_data["description"].append(news_dict.get("description", ""))

        news_dict["image_file"] = None
        if news_dict.get("image_url"):
            try:
                image_file = download_image(news_dict.get("image_url"), DOWNLOAD_IMAGE_PATH)
                excel_data["picture_filename"].append(image_file)
            except Exception as error:
                excel_data["picture_filename"].append(f"PICTURE DOWNLOAD FROM {news_dict.get('image_url')} FAILED")
                logger.warning(f"Problem when downloading image: {error}")
        else:
            excel_data["picture_filename"].append("")

        count_of_search_phrases = count_search_phrases(
            SEARCH_PHRASE, news_dict.get("title", ""), news_dict.get("description", "")
        )
        excel_data["count_of_search_phrases"].append(count_of_search_phrases)

        has_money_amount_value = has_money_amount(
            news_dict.get("title", ""), news_dict.get("description", "")
        )
        excel_data["has_money_amount"].append(has_money_amount_value)

    logger.info("Adding data to Excel file")

    excel = Excel()
    excel.create_workbook(path=NEWS_EXCEL_PATH, fmt="xlsx")
    excel.append_rows_to_worksheet(excel_data, header=True)
    excel.save_workbook()


def download_image(url: str, download_path: str) -> str:
    response = requests.get(url)
    response.raise_for_status()

    image = Image.open(io.BytesIO(response.content))

    if download_path:
        os.makedirs(download_path, exist_ok=True)

    filename = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(download_path, filename)

    image.save(file_path, format="JPEG")

    return filename


def count_search_phrases(search_phrase: str, *args) -> int:
    return " ".join(args).count(search_phrase)


def has_money_amount(*args) -> bool:
    regex_pattern = r"(\$\d{1,3}(,\d{3})*(\.\d{1,2})?(?=\s)|(\d+(\.\d{1,2})?( dollars| USD)))"
    result = re.search(regex_pattern, " ".join(args))
    return bool(result)
