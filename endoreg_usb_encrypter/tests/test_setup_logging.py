import logging
import pytest
from endoreg_usb_encrypter.functions import setup_logging  # Ensure this import points to the right location

def test_setup_logging(mocker):
    """
    Test the setup_logging function to ensure that it correctly configures
    the logger, file handler, and console handler.
    """
    # Mocking the necessary components
    mock_get_logger = mocker.patch('logging.getLogger')  # Patching logging.getLogger
    mock_file_handler = mocker.patch('logging.FileHandler')  # Patching logging.FileHandler
    mock_stream_handler = mocker.patch('logging.StreamHandler')  # Patching logging.StreamHandler

    # Mock logger object returned by getLogger
    mock_logger = mocker.Mock()
    mock_get_logger.return_value = mock_logger

    # Call the setup_logging function
    logger = setup_logging("test_log.log")

    # Verify logging.getLogger was called with the correct logger name
    mock_get_logger.assert_called_once_with("USBEncryption")

    # Verify that logger's level is set to DEBUG
    mock_logger.setLevel.assert_called_once_with(logging.DEBUG)

    # Verify that StreamHandler was created and set to INFO level
    mock_stream_handler.assert_called_once()  # Ensures StreamHandler was created
    created_stream_handler = mock_stream_handler.return_value
    created_stream_handler.setLevel.assert_called_once_with(logging.INFO)

    # Verify that FileHandler was created with the correct log file
    mock_file_handler.assert_called_once_with("test_log.log")
    created_file_handler = mock_file_handler.return_value
    created_file_handler.setLevel.assert_called_once_with(logging.DEBUG)

    # Ensure that both handlers were added to the logger
    mock_logger.addHandler.assert_any_call(created_stream_handler)
    mock_logger.addHandler.assert_any_call(created_file_handler)

    # Assert that the logger returned by the function is the mock logger
    assert logger == mock_logger

