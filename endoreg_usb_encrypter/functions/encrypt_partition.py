import os
import secrets
from .base import run_command

# Function to encrypt partition with LUKS
def encrypt_partition(partition, mount_dir, key_dir, logger):
    logger.info(f"Encrypting partition {partition} with LUKS")    

    # Generate a unique key file name for each partition
    key_file = f"{key_dir}/key-{os.path.basename(partition)}.key"
    with open(key_file, "wb") as keyf:
        key = secrets.token_bytes(32)  # 32 bytes = 256-bit key
        keyf.write(key)

    # Encrypt the partition with LUKS
    run_command(f"cryptsetup luksFormat {partition} {key_file} -q", logger)
    
    # Open the LUKS partition
    luks_partition_name = f"luks-{os.path.basename(partition)}"
    run_command(f"cryptsetup open {partition} {luks_partition_name} --key-file={key_file}", logger)

    # Format the LUKS-mapped device with ext4
    luks_mapped_device = f"/dev/mapper/{luks_partition_name}"
    logger.info(f"Formatting LUKS-mapped device {luks_mapped_device} as ext4")
    run_command(f"mkfs.ext4 {luks_mapped_device}", logger)

    # Ensure the mount directory exists
    mount_path = os.path.join(mount_dir, luks_partition_name)
    if not os.path.exists(mount_path):
        logger.info(f"Creating mount directory: {mount_path}")
        os.makedirs(mount_path)
    
    # Mount the LUKS partition to the specified directory
    run_command(f"mount {luks_mapped_device} {mount_path}", logger)
    logger.info(f"LUKS partition {partition} mounted at {mount_path}")

    # Get the LUKS UUID
    luks_uuid = run_command(f"cryptsetup luksUUID {partition}", logger)
    logger.info(f"LUKS partition {partition} opened as {luks_partition_name}, LUKS UUID: {luks_uuid}")
    
    return luks_uuid, key_file