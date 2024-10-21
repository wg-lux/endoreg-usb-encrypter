
from .base import run_command
from .unmount_partitions import unmount_partitions
from .decrypt_and_mount_partition import decrypt_and_mount_partition


# Function to test unmounting and remounting all partitions
def unmount_and_mount_all_partitions(
        device, mount_dir, 
        logger,
        key_dir
    ):
    logger.info("Testing unmount and remount of all partitions")

    # Unmount all partitions
    unmount_partitions(mount_dir, logger)

    # Reuse the key files saved during encryption to remount the partitions
    partitions = run_command(f"lsblk -ln -o NAME {device} | grep -E '^[a-z]+[0-9]$'", logger).splitlines()
    for partition in partitions:
        partition_path = f"/dev/{partition}"
        key_file = f"{key_dir}/key-{partition}.key"
        decrypt_and_mount_partition(partition_path, key_file, mount_dir, logger)

    logger.info("Test completed: all partitions unmounted and remounted successfully.")