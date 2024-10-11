# Setup logging
import logging

def setup_logging(log_file:str="usb_encryption.log"):
    """
    Set up logging configuration for the USBEncryption module.

    Args:
        log_file (str): The path to the log file. Defaults to "usb_encryption.log".

    Returns:
        logging.Logger: The configured logger object.
    """

    logger = logging.getLogger("USBEncryption")
    logger.setLevel(logging.DEBUG)

    # Console Handler with INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)

    # File Handler with DEBUG level
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)

    # Add both handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger