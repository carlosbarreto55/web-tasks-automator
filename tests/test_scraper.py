import pytest
from unittest.mock import MagicMock

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from src.scraper import Scraper


class TestScraperExtractSingle:
    def test_returns_stripped_text_when_element_found(self):
        driver = MagicMock()
        mock_el = MagicMock()
        mock_el.text = "  Hello World  "
        driver.find_element.return_value = mock_el

        scraper = Scraper(driver)
        result = scraper._extract_single(".header")

        assert result == "Hello World"
        driver.find_element.assert_called_once_with(By.CSS_SELECTOR, ".header")

    def test_returns_none_when_element_not_found(self):
        driver = MagicMock()
        driver.find_element.side_effect = NoSuchElementException()

        scraper = Scraper(driver)
        result = scraper._extract_single(".missing")

        assert result is None

    def test_returns_none_when_text_is_empty_or_whitespace(self):
        driver = MagicMock()
        mock_el = MagicMock()

        scraper = Scraper(driver)
        mock_el.text = ""
        driver.find_element.return_value = mock_el
        assert scraper._extract_single(".empty") == ""

        mock_el.text = "   "
        driver.find_element.return_value = mock_el
        assert scraper._extract_single(".blank") == ""


class TestScraperExtractMulti:
    def test_returns_list_of_stripped_texts(self):
        driver = MagicMock()
        mock_el1 = MagicMock()
        mock_el1.text = "Item 1"
        mock_el2 = MagicMock()
        mock_el2.text = "  Item 2  "
        mock_el3 = MagicMock()
        mock_el3.text = "   "
        driver.find_elements.return_value = [mock_el1, mock_el2, mock_el3]

        scraper = Scraper(driver)
        result = scraper._extract_multi(".items")

        assert result == ["Item 1", "Item 2"]
        driver.find_elements.assert_called_once_with(By.CSS_SELECTOR, ".items")

    def test_returns_empty_list_when_no_elements_found(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        scraper = Scraper(driver)
        result = scraper._extract_multi(".none")

        assert result == []

    def test_returns_empty_list_on_exception(self):
        driver = MagicMock()
        driver.find_elements.side_effect = Exception("DOM error")

        scraper = Scraper(driver)
        result = scraper._extract_multi(".error")

        assert result == []

    def test_filters_out_all_empty_and_whitespace_texts(self):
        driver = MagicMock()
        mocks = [MagicMock() for _ in range(4)]
        mocks[0].text = ""
        mocks[1].text = "   "
        mocks[2].text = "\n\t"
        mocks[3].text = "Valid"
        driver.find_elements.return_value = mocks

        scraper = Scraper(driver)
        result = scraper._extract_multi(".mixed")

        assert result == ["Valid"]


class TestScraperScrape:
    def test_with_string_selectors(self):
        driver = MagicMock()
        mock_el = MagicMock()
        mock_el.text = "Welcome"
        driver.find_element.return_value = mock_el

        scraper = Scraper(driver)
        cfg = {"data_selectors": {"greeting": ".greeting"}}
        result = scraper.scrape(cfg)

        assert result == {"greeting": "Welcome"}

    def test_returns_none_for_missing_string_selector(self):
        driver = MagicMock()
        driver.find_element.side_effect = NoSuchElementException()

        scraper = Scraper(driver)
        cfg = {"data_selectors": {"greeting": ".missing"}}
        result = scraper.scrape(cfg)

        assert result == {"greeting": None}

    def test_with_list_selectors(self):
        driver = MagicMock()
        mock_el1 = MagicMock()
        mock_el1.text = "Course A"
        mock_el2 = MagicMock()
        mock_el2.text = "Course B"
        driver.find_elements.return_value = [mock_el1, mock_el2]

        scraper = Scraper(driver)
        cfg = {"data_selectors": {"courses": [".course", ".class-name"]}}
        result = scraper.scrape(cfg)

        assert result == {"courses": ["Course A", "Course B", "Course A", "Course B"]}
        assert driver.find_elements.call_count == 2

    def test_with_list_selectors_returns_none_when_all_empty(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        scraper = Scraper(driver)
        cfg = {"data_selectors": {"items": [".none", ".also-none"]}}
        result = scraper.scrape(cfg)

        assert result == {"items": None}

    def test_mixed_string_and_list_selectors(self):
        driver = MagicMock()
        mock_single = MagicMock()
        mock_single.text = "Header"
        driver.find_element.return_value = mock_single

        mock_multi = [MagicMock(), MagicMock()]
        mock_multi[0].text = "A"
        mock_multi[1].text = "B"
        driver.find_elements.return_value = mock_multi

        scraper = Scraper(driver)
        cfg = {"data_selectors": {
            "title": "h1",
            "items": [".item a", ".item span"],
        }}
        result = scraper.scrape(cfg)

        assert result == {
            "title": "Header",
            "items": ["A", "B", "A", "B"],
        }

    def test_navigates_to_target_url_before_scraping(self):
        driver = MagicMock()
        mock_el = MagicMock()
        mock_el.text = "Dashboard"
        driver.find_element.return_value = mock_el

        scraper = Scraper(driver)
        cfg = {
            "target_url": "https://example.com/dashboard",
            "data_selectors": {"title": "h1"},
        }
        result = scraper.scrape(cfg)

        assert result == {"title": "Dashboard"}
        driver.get.assert_called_once_with("https://example.com/dashboard")

    def test_empty_selectors_returns_empty_dict(self):
        driver = MagicMock()

        scraper = Scraper(driver)
        result = scraper.scrape({})
        assert result == {}

        result = scraper.scrape({"data_selectors": {}})
        assert result == {}

    def test_no_target_url_does_not_navigate(self):
        driver = MagicMock()
        driver.find_element.return_value = MagicMock()

        scraper = Scraper(driver)
        cfg = {"data_selectors": {"key": ".selector"}}
        scraper.scrape(cfg)

        driver.get.assert_not_called()


class TestScraperNavigate:
    def test_calls_driver_get_with_url(self):
        driver = MagicMock()
        scraper = Scraper(driver)

        scraper.navigate("https://example.com/page")
        driver.get.assert_called_once_with("https://example.com/page")
