import os
from .base import run_command

# Function to decrypt and mount a partition using the key file
def decrypt_and_mount_partition(partition, key_file, mount_dir, logger):
    luks_partition_name = f"luks-{os.path.basename(partition)}"
    luks_mapped_device = f"/dev/mapper/{luks_partition_name}"

    # Check if the LUKS device is already open and close it if necessary
    if os.path.exists(luks_mapped_device):
        logger.info(f"LUKS device {luks_partition_name} is already open. Closing it first.")
        run_command(f"cryptsetup close {luks_partition_name}", logger)

    logger.info(f"Decrypting and mounting {partition} using key file {key_file}")
    
    # Open the LUKS partition
    run_command(f"cryptsetup open {partition} {luks_partition_name} --key-file={key_file}", logger)

    # Ensure the mount directory exists
    mount_path = os.path.join(mount_dir, luks_partition_name)
    if not os.path.exists(mount_path):
        logger.info(f"Creating mount directory: {mount_path}")
        os.makedirs(mount_path)

    # Mount the LUKS partition to the specified directory
    run_command(f"mount {luks_mapped_device} {mount_path}", logger)
    logger.info(f"LUKS partition {partition} mounted at {mount_path}")
    
    return mount_path