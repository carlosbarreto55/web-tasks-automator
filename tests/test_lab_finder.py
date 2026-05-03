import pytest
from unittest.mock import MagicMock

from selenium.webdriver.common.by import By

from src.lab_finder import LabFinder


class TestLabFinderLocatorType:
    def test_defaults_to_css_selector(self):
        driver = MagicMock()
        finder = LabFinder(driver)
        assert finder._by == By.CSS_SELECTOR

    def test_xpath_locator_type(self):
        driver = MagicMock()
        finder = LabFinder(driver, locator_type="xpath")
        assert finder._by == By.XPATH

    def test_invalid_locator_type_raises_value_error(self):
        driver = MagicMock()
        with pytest.raises(ValueError, match="Invalid locator_type"):
            LabFinder(driver, locator_type="invalid")


class TestLabFinderFindLabLinks:
    def test_returns_elements_matching_selector(self):
        driver = MagicMock()
        mock_links = [MagicMock(), MagicMock(), MagicMock()]
        driver.find_elements.return_value = mock_links

        finder = LabFinder(driver)
        result = finder.find_lab_links("a.lab-link")

        assert result == mock_links
        driver.find_elements.assert_called_once_with(By.CSS_SELECTOR, "a.lab-link")

    def test_returns_empty_list_when_no_match(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        finder = LabFinder(driver)
        result = finder.find_lab_links(".none")

        assert result == []

    def test_uses_xpath_when_configured(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        finder = LabFinder(driver, locator_type="xpath")
        finder.find_lab_links("//a[@class='lab']")

        driver.find_elements.assert_called_once_with(By.XPATH, "//a[@class='lab']")


class TestLabFinderGetLastLab:
    def test_returns_last_element_in_list(self):
        driver = MagicMock()
        mock_links = [MagicMock(), MagicMock(), MagicMock()]
        driver.find_elements.return_value = mock_links

        finder = LabFinder(driver)
        result = finder.get_last_lab("a")

        assert result is mock_links[-1]

    def test_returns_none_when_no_labs_found(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        finder = LabFinder(driver)
        result = finder.get_last_lab("a")

        assert result is None

    def test_uses_xpath_when_configured(self):
        driver = MagicMock()
        driver.find_elements.return_value = [MagicMock()]

        finder = LabFinder(driver, locator_type="xpath")
        finder.get_last_lab("//a")

        driver.find_elements.assert_called_once_with(By.XPATH, "//a")


class TestLabFinderClickLastLab:
    def test_clicks_last_lab_element(self):
        driver = MagicMock()
        mock_link = MagicMock()
        driver.find_elements.return_value = [MagicMock(), mock_link]

        finder = LabFinder(driver)
        result = finder.click_last_lab("a.lab-link")

        assert result is True
        mock_link.click.assert_called_once()

    def test_returns_false_when_no_labs_found(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        finder = LabFinder(driver)
        result = finder.click_last_lab("a")

        assert result is False

    def test_returns_false_when_no_labs_found_with_verbose(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        finder = LabFinder(driver)
        result = finder.click_last_lab("a", verbose=True)

        assert result is False

    def test_uses_xpath_when_configured(self):
        driver = MagicMock()
        mock_link = MagicMock()
        driver.find_elements.return_value = [mock_link]

        finder = LabFinder(driver, locator_type="xpath")
        finder.click_last_lab("//a[@class='lab']")

        driver.find_elements.assert_called_once_with(By.XPATH, "//a[@class='lab']")
        mock_link.click.assert_called_once()


class TestLabFinderGetLastLabUrl:
    def test_returns_href_when_last_lab_found(self):
        driver = MagicMock()
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = "https://example.com/lab/7"
        driver.find_elements.return_value = [MagicMock(), mock_link]

        finder = LabFinder(driver)
        result = finder.get_last_lab_url("a.lab-link")

        assert result == "https://example.com/lab/7"
        mock_link.get_attribute.assert_called_once_with("href")

    def test_returns_none_when_no_labs_found(self):
        driver = MagicMock()
        driver.find_elements.return_value = []

        finder = LabFinder(driver)
        result = finder.get_last_lab_url("a")

        assert result is None

    def test_uses_xpath_when_configured(self):
        driver = MagicMock()
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = "https://example.com/lab/xpath"
        driver.find_elements.return_value = [mock_link]

        finder = LabFinder(driver, locator_type="xpath")
        result = finder.get_last_lab_url("//a[@class='lab']")

        assert result == "https://example.com/lab/xpath"
        driver.find_elements.assert_called_once_with(By.XPATH, "//a[@class='lab']")
