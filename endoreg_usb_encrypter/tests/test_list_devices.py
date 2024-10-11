from endoreg_usb_encrypter.functions import list_devices  # Adjust this import to match your module name
import pytest
import subprocess

# TODO - how to test independent of host system

def test_list_devices_success(mocker, capsys):
    """
    Test list_devices when the command returns a valid list of devices.
    """
    # Mock logger
    mock_logger = mocker.Mock()

    # # Mocking run_command to return a list of devices
    # mock_run_command = mocker.patch('endoreg_usb_encrypter.run_command')
    # mock_run_command.return_value = "sda 500G disk\nsdb 1T disk"

    # # Call the function
    # devices = list_devices(mock_logger)

    # # Assertions
    # mock_logger.info.assert_called_once_with("Listing available devices...")
    # mock_run_command.assert_called_once_with("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT -dn | grep 'disk'", mock_logger)


    # # Verifying print output (with capsys)
    # captured = capsys.readouterr()


def test_list_devices_with_empty_lines(mocker, capsys):
    """
    Test list_devices when the command returns devices with empty lines.
    """
    # Mock logger
    mock_logger = mocker.Mock()

    # Mocking run_command to return a list with empty lines
    # mock_run_command = mocker.patch('endoreg_usb_encrypter.run_command')
    # mock_run_command.return_value = "sda 500G disk\n\nsdb 1T disk\n"

    # # Call the function
    # devices = list_devices(mock_logger)

    # # Assertions
    # mock_logger.info.assert_called_once_with("Listing available devices...")
    # mock_run_command.assert_called_once_with("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT -dn | grep 'disk'", mock_logger)
    
    # # Ensure the empty lines are preserved in output

    # # Verifying print output (with capsys)
    # captured = capsys.readouterr()


def test_list_devices_permission_error(mocker):
    """
    Test list_devices when there is a permission error.
    """
    # Mock logger
    mock_logger = mocker.Mock()

    # Mocking run_command to raise a CalledProcessError due to permission issue
    # mock_run_command = mocker.patch('endoreg_usb_encrypter.run_command')
    # mock_run_command.side_effect = subprocess.CalledProcessError(
    #     returncode=1, cmd="lsblk -o NAME,SIZE,TYPE,MOUNTPOINT -dn | grep 'disk'", stderr=b"Permission denied"
    # )

    # # Call the function and assert exception is raised
    # with pytest.raises(subprocess.CalledProcessError):
    #     list_devices(mock_logger)

    # Assertions
    # mock_logger.info.assert_called_once_with("Listing available devices...")
    # mock_run_command.assert_called_once_with("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT -dn | grep 'disk'", mock_logger)
    # mock_logger.error.assert_called_once_with("Command 'lsblk -o NAME,SIZE,TYPE,MOUNTPOINT -dn | grep 'disk'' failed with error: Permission denied")
