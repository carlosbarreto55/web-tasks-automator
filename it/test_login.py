import pytest

from src.login.login import do_login


THE_INTERNET_CONFIG = {
    "name": "the-internet",
    "url": "https://the-internet.herokuapp.com/login",
    "credentials": {
        "username": "tomsmith",
        "password": "SuperSecretPassword!",
    },
    "selectors": {
        "username_input": "#username",
        "password_input": "#password",
        "submit_button": "button[type='submit']",
        "success_indicator": ".flash.success",
        "failure_indicator": ".flash.error",
    },
}


@pytest.mark.integration
class TestLoginIntegration:
    def test_successful_login(self, driver):
        ok, msg = do_login(driver, THE_INTERNET_CONFIG, verbose=False)
        assert ok is True
        assert msg is None

    def test_failed_login_bad_password(self, driver):
        config = {
            **THE_INTERNET_CONFIG,
            "credentials": {"username": "tomsmith", "password": "wrongpassword"},
        }
        ok, msg = do_login(driver, config, verbose=False)
        assert ok is False
        assert msg is not None
        assert "invalid" in msg.lower() or "password" in msg.lower()
