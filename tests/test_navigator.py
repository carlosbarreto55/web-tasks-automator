import pytest
from unittest.mock import MagicMock, patch, call

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementNotInteractableException

from src.scraping.navigator import Navigator


class TestNavigatorClick:
    def test_finds_element_and_clicks(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        nav = Navigator(driver, [{"click": ".menu"}])
        nav.run()

        driver.find_element.assert_called_once_with(By.CSS_SELECTOR, ".menu")
        mock_el.click.assert_called_once()

    def test_raises_no_such_element_when_not_found(self):
        driver = MagicMock()
        driver.find_element.side_effect = NoSuchElementException()

        nav = Navigator(driver, [{"click": ".missing"}])
        with pytest.raises(NoSuchElementException):
            nav.run()

    def test_raises_element_not_interactable_on_click(self):
        driver = MagicMock()
        mock_el = MagicMock()
        mock_el.click.side_effect = ElementNotInteractableException()
        driver.find_element.return_value = mock_el

        nav = Navigator(driver, [{"click": ".hidden"}])
        with pytest.raises(ElementNotInteractableException):
            nav.run()


class TestNavigatorNavigate:
    def test_calls_driver_get_with_url(self):
        driver = MagicMock()

        nav = Navigator(driver, [{"url": "https://example.com/page"}])
        nav.run()

        driver.get.assert_called_once_with("https://example.com/page")


class TestNavigatorWaitFor:
    def test_waits_for_element_after_click(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        nav = Navigator(driver, [{"click": ".btn", "wait_for": ".loaded"}])
        nav.run()

        mock_el.click.assert_called_once()

    def test_default_wait_timeout_is_10(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [{"click": ".btn", "wait_for": ".result"}]
        nav = Navigator(driver, steps)

        with patch("src.scraping.navigator.WebDriverWait") as mock_wait:
            nav.run()
            mock_wait.assert_called_once_with(driver, 10)

    def test_custom_wait_timeout(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [{"click": ".btn", "wait_for": ".result", "wait_timeout": 15}]
        nav = Navigator(driver, steps)

        with patch("src.scraping.navigator.WebDriverWait") as mock_wait:
            nav.run()
            mock_wait.assert_called_once_with(driver, 15)

    def test_wait_for_raises_timeout_exception_when_timed_out(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [{"click": ".btn", "wait_for": ".never-appears"}]
        nav = Navigator(driver, steps)

        with patch("src.scraping.navigator.WebDriverWait") as mock_wait_cls:
            mock_wait = MagicMock()
            mock_wait.until.side_effect = TimeoutException()
            mock_wait_cls.return_value = mock_wait

            with pytest.raises(TimeoutException):
                nav.run()


class TestNavigatorWaitAfter:
    def test_sleeps_after_click_when_wait_after_set(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [{"click": ".btn", "wait_after": 2}]
        nav = Navigator(driver, steps)

        with patch("time.sleep") as mock_sleep:
            nav.run()
            mock_sleep.assert_called_once_with(2)

    def test_no_sleep_when_wait_after_not_set(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [{"click": ".btn"}]
        nav = Navigator(driver, steps)

        with patch("time.sleep") as mock_sleep:
            nav.run()
            mock_sleep.assert_not_called()


class TestNavigatorRun:
    def test_executes_multiple_steps_in_order(self):
        driver = MagicMock()
        el1 = MagicMock()
        el2 = MagicMock()
        driver.find_element.side_effect = [el1, el2]

        steps = [
            {"click": ".first"},
            {"click": ".second"},
            {"url": "https://example.com/final"},
        ]
        nav = Navigator(driver, steps)
        nav.run()

        assert driver.find_element.call_count == 2
        driver.find_element.assert_has_calls([
            call(By.CSS_SELECTOR, ".first"),
            call(By.CSS_SELECTOR, ".second"),
        ])
        driver.get.assert_called_once_with("https://example.com/final")

    def test_click_with_wait_for_and_wait_after(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [{"click": ".btn", "wait_for": ".loaded", "wait_after": 1}]
        nav = Navigator(driver, steps)

        with patch("time.sleep") as mock_sleep, \
             patch("src.scraping.navigator.WebDriverWait") as mock_wait:
            nav.run()
            mock_el.click.assert_called_once()
            mock_wait.assert_called_once()
            mock_sleep.assert_called_once_with(1)

    def test_empty_steps_does_nothing(self):
        driver = MagicMock()
        nav = Navigator(driver, [])
        nav.run()
        driver.find_element.assert_not_called()
        driver.get.assert_not_called()

    def test_raises_value_error_on_invalid_step(self):
        driver = MagicMock()
        nav = Navigator(driver, [{"invalid": ".foo"}])
        with pytest.raises(ValueError, match="must contain 'click' or 'url'"):
            nav.run()

    def test_url_step_takes_precedence_over_click(self):
        """When a step has a 'url' key, navigate instead of clicking."""
        driver = MagicMock()

        steps = [{"url": "https://example.com/page", "click": ".btn"}]
        nav = Navigator(driver, steps)
        nav.run()

        driver.get.assert_called_once_with("https://example.com/page")
        driver.find_element.assert_not_called()

    def test_url_step_ignores_wait_for_and_wait_after(self):
        """URL steps do not support wait_for or wait_after — they are ignored."""
        driver = MagicMock()

        steps = [{"url": "https://example.com/page", "wait_for": ".loaded", "wait_after": 2}]
        nav = Navigator(driver, steps)

        with patch("time.sleep") as mock_sleep, \
             patch("src.scraping.navigator.WebDriverWait") as mock_wait:
            nav.run()
            driver.get.assert_called_once_with("https://example.com/page")
            mock_sleep.assert_not_called()
            mock_wait.assert_not_called()

    def test_wait_for_without_wait_after(self):
        """wait_for should work without wait_after being set."""
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [{"click": ".btn", "wait_for": ".loaded"}]
        nav = Navigator(driver, steps)

        with patch("time.sleep") as mock_sleep, \
             patch("src.scraping.navigator.WebDriverWait") as mock_wait:
            nav.run()
            mock_wait.assert_called_once()
            mock_sleep.assert_not_called()


class TestNavigatorVerbose:
    def test_prints_steps_to_stderr_when_verbose(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        steps = [
            {"click": ".menu"},
            {"url": "https://example.com/page"},
        ]
        nav = Navigator(driver, steps)

        with patch("sys.stderr.write") as mock_write:
            nav.run(verbose=True)
            output = "".join(call_args[0][0] for call_args in mock_write.call_args_list
                             if call_args[0])
            assert "step 1/2" in output
            assert "clicking: .menu" in output
            assert "step 2/2" in output
            assert "navigating to: https://example.com/page" in output

    def test_prints_nothing_when_not_verbose(self):
        driver = MagicMock()
        mock_el = MagicMock()
        driver.find_element.return_value = mock_el

        nav = Navigator(driver, [{"click": ".btn"}])

        with patch("sys.stderr.write") as mock_write:
            nav.run(verbose=False)
            mock_write.assert_not_called()
