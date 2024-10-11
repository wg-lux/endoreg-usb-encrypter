import pytest
import subprocess
from endoreg_usb_encrypter.functions import run_command  # Adjust this import to match your module name


def test_run_command_success(mocker):
    """
    Test run_command when the shell command executes successfully.
    """
    # Mock logger
    mock_logger = mocker.Mock()

    # Mocking subprocess.run for successful execution
    mock_subprocess_run = mocker.patch('subprocess.run')
    mock_result = mocker.Mock()
    mock_result.stdout = b"Command output"
    mock_subprocess_run.return_value = mock_result

    # Call the function
    command = "echo 'hello'"
    result = run_command(command, mock_logger)

    # Assertions
    mock_subprocess_run.assert_called_once_with(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    mock_logger.debug.assert_called_once_with(f"Command '{command}' succeeded with output: Command output")
    assert result == "Command output"


def test_run_command_failure(mocker):
    """
    Test run_command when the shell command fails.
    """
    # Mock logger
    mock_logger = mocker.Mock()

    # Mocking subprocess.run for a failure case
    mock_subprocess_run = mocker.patch('subprocess.run')
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="invalid_command", stderr=b"Command not found"
    )

    # Call the function and assert exception is raised
    command = "invalid_command"
    with pytest.raises(subprocess.CalledProcessError):
        run_command(command, mock_logger)

    # Assertions
    mock_subprocess_run.assert_called_once_with(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    mock_logger.error.assert_called_once_with(f"Command '{command}' failed with error: Command not found")
