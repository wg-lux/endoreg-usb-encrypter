import subprocess
import json
import os
import logging
import secrets
from pathlib import Path
import shutil

# Setup logging
def setup_logging(log_file="usb_encryption.log"):
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

# Function to run a shell command and capture output
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

# Function to unmount all partitions and close LUKS devices on a device
def cleanup_device(device, logger, mount_dir):
    logger.info(f"Unmounting all partitions and closing LUKS devices on {device}")
    
    # Unmount any mounted partitions
    partitions = run_command(f"lsblk -ln -o NAME,MOUNTPOINT {device}", logger)
    for line in partitions.splitlines():
        parts = line.split()
        partition_device = f"/dev/{parts[0]}"
        mountpoint = parts[1] if len(parts) > 1 else None
        
        if mountpoint:
            logger.info(f"Unmounting {partition_device} from {mountpoint}")
            run_command(f"umount {partition_device}", logger)
        else:
            logger.info(f"{partition_device} is not mounted, skipping.")
    
    # Close any opened LUKS devices
    try:
        luks_devices = run_command("lsblk -ln -o NAME,TYPE | grep crypt", logger)
        if not luks_devices.strip():
            logger.info("No LUKS devices found, skipping LUKS cleanup.")
        else:
            for line in luks_devices.splitlines():
                luks_device = line.split()[0]
                luks_path = f"/dev/mapper/{luks_device}"

                # Check if the LUKS device is mounted
                mount_info = run_command(f"lsblk -ln -o NAME,MOUNTPOINT {luks_path}", logger)
                if mount_info:
                    mountpoint = mount_info.split()[1] if len(mount_info.split()) > 1 else None
                    if mountpoint:
                        logger.info(f"Unmounting LUKS device {luks_path} from {mountpoint}")
                        run_command(f"umount {luks_path}", logger)

                # After unmounting, attempt to close the LUKS device
                run_command(f"cryptsetup close {luks_device}", logger)

    except subprocess.CalledProcessError:
        logger.info("No LUKS devices found, skipping LUKS cleanup.")
    
    # Inform the kernel of partition changes using partprobe
    logger.info(f"Running partprobe on {device}")
    run_command(f"partprobe {device}", logger)

# Function to create partitions on the device
def create_partitions(device, partition_names, size_factors, logger):
    logger.info(f"Creating partitions on {device} with partition names: {partition_names} and size factors: {size_factors}")
    
    # Run parted to clear existing partitions
    run_command(f"parted -s {device} mklabel gpt", logger)
    
    # Inform the kernel of partition changes
    run_command(f"partprobe {device}", logger)

    start = 1  # Start partitioning at 1%
    partitions = []

    for i, (name, factor) in enumerate(zip(partition_names, size_factors)):
        end = start + factor * 100  # in percentage
        partition = f"{device}{i+1}"
        # Create the partition with proper sizes and names
        run_command(f"parted -s {device} mkpart {name} ext4 {int(start)}% {int(end)}%", logger)
        partitions.append(partition)
        start = end
    
    logger.info(f"Partitions created: {partitions}")
    return partitions

# Function to format partitions with ext4
def format_partition(partition, logger):
    logger.info(f"Formatting partition {partition} as ext4")
    run_command(f"mkfs.ext4 {partition}", logger)
    partition_uuid = run_command(f"blkid -s UUID -o value {partition}", logger)
    logger.debug(f"Formatted partition {partition}, UUID: {partition_uuid}")
    return partition_uuid

# Function to encrypt partition with LUKS
def encrypt_partition(partition, logger, mount_dir, key_dir):
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

# Function to unmount all partitions
def unmount_partitions(logger, mount_dir):
    logger.info(f"Unmounting all LUKS partitions from {mount_dir}")
    
    # Find all mounted LUKS devices in the mount directory
    luks_mounts = run_command(f"lsblk -ln -o NAME,MOUNTPOINT | grep {mount_dir}", logger)
    if not luks_mounts:
        logger.info("No LUKS partitions found to unmount.")
        return

    for line in luks_mounts.splitlines():
        parts = line.split()
        luks_device = f"/dev/{parts[0]}"
        mountpoint = parts[1] if len(parts) > 1 else None
        
        if mountpoint:
            logger.info(f"Unmounting {luks_device} from {mountpoint}")
            run_command(f"umount {mountpoint}", logger)
    
    logger.info("All partitions unmounted.")

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

# Function to test unmounting and remounting all partitions
def test_unmount_and_mount_all_partitions(device, mount_dir, logger):
    logger.info("Testing unmount and remount of all partitions")

    # Unmount all partitions
    unmount_partitions(logger, mount_dir)

    # Reuse the key files saved during encryption to remount the partitions
    partitions = run_command(f"lsblk -ln -o NAME {device} | grep -E '^[a-z]+[0-9]$'", logger).splitlines()
    for partition in partitions:
        partition_path = f"/dev/{partition}"
        key_file = f"./key-{partition}.key"
        decrypt_and_mount_partition(partition_path, key_file, mount_dir, logger)

    logger.info("Test completed: all partitions unmounted and remounted successfully.")

# Main function
def main(
        default_factors=[0.33, 0.33, 0.33],
        output_json="output.json",
        log_file="usb_encryption.log",
        hdd_info_json="hdd-info.json",
        default_mount_dir="/home/agl-admin/Desktop/sensitive-hdd-mount",
        default_key_dir="/home/agl-admin/Desktop/sensitive-hdd-keys"
    ):

    # Set up logging
    logger = setup_logging(log_file)

    # List available devices and ask for user input
    devices = list_devices(logger)
    device = input("Please enter the full path of the device you wish to format (e.g., /dev/sdb): ").strip()

    # Get partition names from the user, with default values
    partition_names = input("Enter partition names separated by commas (default: dropoff,pseudo,processed): ").strip().split(",")
    if len(partition_names) != 3:
        partition_names = ['dropoff', 'pseudo', 'processed']
    else:
        partition_names = [name.strip() for name in partition_names]

    # Get partition sizes from the user, with default factors
    size_input = input(f"Enter partition sizes as percentages (default: 33,33,33): ").strip()
    if size_input:
        size_factors = [float(s)/100 for s in size_input.split(',')]
        if len(size_factors) != 3 or sum(size_factors) != 1.0:
            logger.error("Invalid partition size percentages. Using default values.")
            size_factors = default_factors
    else:
        size_factors = default_factors

    # Get the mount directory from the user (or use the default)
    mount_dir = input(f"Enter a target directory for mounting LUKS partitions (default: {default_mount_dir}): ").strip()
    if not mount_dir:
        mount_dir = default_mount_dir

        # Check if the default mount directory exists
        if not os.path.exists(mount_dir):
            logger.info(f"Creating default mount directory: {mount_dir}")
            os.makedirs(mount_dir)

    # Check / set directory permissions
    logger.info(f"Setting permissions for mount directory: {mount_dir}")
    shutil.chown(mount_dir, user="agl-admin", group="service-user")
    os.chmod(mount_dir, 0o770)
    logger.info(f"Permissions set for {mount_dir}: user=agl-admin, group=service-user")

    # Get the key directory from the user
    _key_dir = input("Enter a directory to store encryption keys (default: /home/agl-admin/Desktop/sensitive-hdd-keys): ").strip()
    if not _key_dir:
        key_dir = default_key_dir

    else:
        key_dir = _key_dir

    logger.info(f"Key directory: {key_dir}")

    # check if key directory exists
    if not os.path.exists(key_dir):
        logger.info(f"Creating key directory: {key_dir}")
        os.makedirs(key_dir)
        logger.info(f"Key directory created: {key_dir}")

        logger.info(f"Setting permissions for key directory: {key_dir}")
        shutil.chown(key_dir, user="agl-admin", group="service-user")

        os.chmod(key_dir, 0o770)
        logger.info(f"Permissions (0770) set for {key_dir}: user=agl-admin, group=service-user")

    # Confirm with the user before proceeding
    confirm = input(f"Are you sure you want to format and partition {device}? This will destroy all data on the device. (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("Operation canceled by the user.")
        return

    # Step 1: Cleanup device before partitioning
    cleanup_device(device, logger, mount_dir)

    # Step 2: Create partitions
    partitions = create_partitions(device, partition_names, size_factors, logger)

    # Initialize storage for results
    result = {
        "partitions": [],
    }
    hdd_info = {
        "device": device,
        "partitions": []
    }

    # List to hold all key file paths
    key_files = []

    # Step 3: Format partitions with ext4 and encrypt them with LUKS
    for partition in partitions:
        partition_uuid = format_partition(partition, logger)
        luks_uuid, key_file = encrypt_partition(partition, logger, mount_dir, key_dir)
        key_files.append(key_file)
        result["partitions"].append({"partition": partition, "uuid": partition_uuid})
        hdd_info["partitions"].append({
            "partition": partition,
            "uuid": partition_uuid,
            "luks_uuid": luks_uuid,
            "encryption_key": key_file
        })

    # Step 4: Save partition output to JSON
    with open(output_json, "w") as json_file:
        json.dump(result, json_file, indent=4)
    logger.info(f"Results written to {output_json}")

    # Step 5: Save HDD info (including encryption details) to JSON
    with open(hdd_info_json, "w") as hdd_json_file:
        json.dump(hdd_info, hdd_json_file, indent=4)
    logger.info(f"HDD Info written to {hdd_info_json}")

    # Step 6: Test unmount and remount functionality
    test_unmount_and_mount_all_partitions(device, mount_dir, logger)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="List devices, format, partition, and encrypt a USB drive.")
    parser.add_argument("--factors", nargs=3, type=float, default=[0.33, 0.33, 0.33], help="Size factors for the partitions")
    parser.add_argument("--output", default="output.json", help="Output JSON file")
    parser.add_argument("--logfile", default="usb_encryption.log", help="Log file location")
    parser.add_argument("--hddinfo", default="hdd-info.json", help="HDD info JSON file location")
    parser.add_argument("--mountdir", default="/home/agl-admin/Desktop/sensitive-hdd-mount", help="Target directory for mounting LUKS partitions")
    parser.add_argument("--keydir", default="/home/agl-admin/Desktop/sensitive-hdd-keys", help="Directory to store encryption keys")
    args = parser.parse_args()
    
    main(args.factors, args.output, args.logfile, args.hddinfo, args.mountdir)
