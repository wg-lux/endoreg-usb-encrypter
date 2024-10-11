# Function to run a shell command and capture output
import subprocess


def run_command(command, logger):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.debug(f"Command '{command}' succeeded with output: {result.stdout.decode('utf-8').strip()}")
        return result.stdout.decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Command '{command}' failed with error: {e.stderr.decode('utf-8')}")
        raise

# Function to list available devices
def list_devices(logger):
    logger.info("Listing available devices...")
    devices = run_command("lsblk -o NAME,SIZE,TYPE,MOUNTPOINT -dn | grep 'disk'", logger)
    print("Available devices:")
    print(devices)
    return devices

# Function to format partitions with ext4
def format_partition(partition, logger):
    logger.info(f"Formatting partition {partition} as ext4")
    run_command(f"mkfs.ext4 {partition}", logger)
    partition_uuid = run_command(f"blkid -s UUID -o value {partition}", logger)
    logger.debug(f"Formatted partition {partition}, UUID: {partition_uuid}")
    return partition_uuid