import pytest

def pytest_addoption(parser):
    parser.addoption("--verbose_logging", action='store_true')
    parser.addoption("--auto_apply_down", action='store_true')
    parser.addoption('--strict_digest_check', action='store_false')


@pytest.fixture
def verbose(request):
    return request.config.getoption('--verbose_logging')


@pytest.fixture
def auto_apply_down(request):
    return request.config.getoption('--auto_apply_down')


@pytest.fixture
def strict_digest_check(request):
    return request.config.getoption('--strict_digest_check')
