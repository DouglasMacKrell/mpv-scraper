"""Unit tests for retry logic (Sprint 10.5)."""

from __future__ import annotations

import time
from unittest.mock import Mock

import pytest

from mpv_scraper.utils import retry_with_backoff
from mpv_scraper.images import download_image, download_marquee


def test_retry_logic():
    """Test that retry decorator works with exponential backoff."""
    # Create a mock function that fails twice then succeeds
    mock_func = Mock()
    mock_func.side_effect = [
        Exception("First failure"),
        Exception("Second failure"),
        "Success",
    ]

    # Apply retry decorator
    retry_func = retry_with_backoff(max_attempts=3, base_delay=0.1)(mock_func)

    # Call the function
    start_time = time.time()
    result = retry_func("test_arg")
    end_time = time.time()

    # Verify the function was called 3 times
    assert mock_func.call_count == 3
    assert result == "Success"

    # Verify exponential backoff timing (should take at least 0.1 + 0.2 = 0.3 seconds)
    elapsed_time = end_time - start_time
    assert elapsed_time >= 0.3, f"Expected at least 0.3s delay, got {elapsed_time}s"


def test_retry_logic_max_attempts_exceeded():
    """Test that retry decorator gives up after max attempts."""
    # Create a mock function that always fails
    mock_func = Mock()
    mock_func.side_effect = Exception("Always fails")

    # Apply retry decorator
    retry_func = retry_with_backoff(max_attempts=3, base_delay=0.01)(mock_func)

    # Call the function - should raise the last exception
    with pytest.raises(Exception, match="Always fails"):
        retry_func("test_arg")

    # Verify the function was called exactly 3 times
    assert mock_func.call_count == 3


def test_retry_logic_success_on_first_try():
    """Test that retry decorator doesn't retry on success."""
    # Create a mock function that succeeds immediately
    mock_func = Mock()
    mock_func.return_value = "Success"

    # Apply retry decorator
    retry_func = retry_with_backoff(max_attempts=3, base_delay=0.1)(mock_func)

    # Call the function
    result = retry_func("test_arg")

    # Verify the function was called only once
    assert mock_func.call_count == 1
    assert result == "Success"


def test_retry_logic_with_specific_exceptions():
    """Test that retry decorator only retries on specified exceptions."""
    # Create a mock function that raises different exceptions
    mock_func = Mock()
    mock_func.side_effect = [
        ValueError("Value error"),
        RuntimeError("Runtime error"),
        "Success",
    ]

    # Apply retry decorator that only retries on ValueError
    retry_func = retry_with_backoff(
        max_attempts=3, base_delay=0.01, exceptions=(ValueError,)
    )(mock_func)

    # Call the function - should fail on RuntimeError (not retried)
    with pytest.raises(RuntimeError, match="Runtime error"):
        retry_func("test_arg")

    # Verify the function was called only twice (ValueError retried, RuntimeError not)
    assert mock_func.call_count == 2


def test_download_functions_have_retry_decorator():
    """Test that download functions are decorated with retry logic."""
    # Verify that the functions have the retry decorator applied
    assert hasattr(
        download_image, "__wrapped__"
    ), "download_image should have retry decorator"
    assert hasattr(
        download_marquee, "__wrapped__"
    ), "download_marquee should have retry decorator"

    # Verify the function names are preserved
    assert download_image.__name__ == "download_image"
    assert download_marquee.__name__ == "download_marquee"
