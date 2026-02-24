"""Test fixtures and configuration."""
import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_seller_info():
    """Sample seller information for testing."""
    return {
        "tax_id": "0105536018253",
        "name": "ABC Company Limited",
        "address": "123 Main Road, District, Bangkok 10100",
        "branch_code": "00000"
    }


@pytest.fixture
def sample_buyer_info():
    """Sample buyer information for testing."""
    return {
        "tax_id": "0105536018254",
        "name": "XYZ Corporation Limited",
        "address": "456 Side Street, District, Bangkok 10200",
        "branch_code": "00000"
    }


@pytest.fixture
def sample_invoice_item():
    """Sample invoice item for testing."""
    return {
        "description": "Professional Consulting Service",
        "quantity": "1",
        "unit_price": "1000.00",
        "discount": "0"
    }
