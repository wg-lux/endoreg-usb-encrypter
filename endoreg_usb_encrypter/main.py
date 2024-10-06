import subprocess
import json
import os
import logging
from pathlib import Path

DEFAULT_UUID = "E4DF-3B19"

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

# Function to create partitions on the device
def create_partitions(device, size_factors, logger):
    logger.info(f"Creating partitions on {device} with size factors: {size_factors}")
    run_command(f"parted -s {device} mklabel gpt", logger)
    start = 0
    partitions = []

    for i, factor in enumerate(size_factors):
        end = start + factor * 100  # in percentage
        partition = f"{device}{i+1}"
        run_command(f"parted -s {device} mkpart primary {start}% {end}%", logger)
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
def encrypt_partition(partition, key_file, logger):
    logger.info(f"Encrypting partition {partition} with LUKS")
    run_command(f"cryptsetup luksFormat {partition} --key-file={key_file} -q", logger)
    run_command(f"cryptsetup open {partition} luks-{os.path.basename(partition)} --key-file={key_file}", logger)
    
    luks_partition_uuid = run_command(f"cryptsetup luksUUID {partition}", logger)
    luks_mapping = f"/dev/mapper/luks-{os.path.basename(partition)}"
    logger.debug(f"Encrypted partition {partition}, LUKS UUID: {luks_partition_uuid}, mapping: {luks_mapping}")
    return luks_mapping, luks_partition_uuid

# Main function
def main(device_uuid, size_factors=[0.33, 0.33, 0.33], output_json="output.json", log_file="usb_encryption.log"):
    # Set up logging
    logger = setup_logging(log_file)
    
    # Step 1: Find the device path from the UUID
    logger.info(f"Finding device with UUID: {device_uuid}")
    try:
        device = run_command(f"blkid -U {device_uuid}", logger)
        logger.info(f"Found device: {device}")
    except Exception as e:
        logger.error(f"Error finding device with UUID {device_uuid}: {e}")
        return

    # Step 2: Create partitions
    partitions = create_partitions(device, size_factors, logger)
    
    # Initialize storage for results
    result = {
        "partitions": [],
        "luks_partitions": [],
        "keys": []
    }
    
    # Step 3: Format partitions and encrypt with LUKS
    for partition in partitions:
        partition_uuid = format_partition(partition, logger)
        
        # Generate a random key for LUKS
        key_file = f"/tmp/key-{os.path.basename(partition)}.key"
        logger.info(f"Generating random key for partition {partition}")
        run_command(f"dd if=/dev/urandom of={key_file} bs=512 count=4", logger)
        
        luks_mapping, luks_uuid = encrypt_partition(partition, key_file, logger)
        
        # Store results
        result["partitions"].append({
            "partition": partition,
            "uuid": partition_uuid
        })
        result["luks_partitions"].append({
            "partition": luks_mapping,
            "luks_uuid": luks_uuid
        })
        result["keys"].append({
            "partition": partition,
            "key_file": key_file
        })
    
    # Step 4: Save output to JSON
    with open(output_json, "w") as json_file:
        json.dump(result, json_file, indent=4)
    logger.info(f"Results written to {output_json}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Format, partition, and encrypt a USB device.")
    parser.add_argument("--uuid", default = "E4DF-3B19", help="UUID of the USB device")
    parser.add_argument("--factors", nargs=3, type=float, default=[0.33, 0.33, 0.33], help="Size factors for the partitions")
    parser.add_argument("--output", default="output.json", help="Output JSON file")
    parser.add_argument("--logfile", default="usb_encryption.log", help="Log file location")
    args = parser.parse_args()
    
    main(args.uuid, args.factors, args.output, args.logfile)
