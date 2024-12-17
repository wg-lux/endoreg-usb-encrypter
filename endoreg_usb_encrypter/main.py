import json
import os
import shutil

from functions import (
    cleanup_device,
    create_partitions,
    encrypt_partition,
    setup_logging,
    list_devices,
    format_partition,
    unmount_and_mount_all_partitions
)


# Function to write the Nix configuration file
def write_nix_configuration(hdd_info, partition_names, nix_file="sensitive-hdd.nix"):
    nix_content = []
    
    nix_content.append("{ ... }:\n")
    nix_content.append("let\n")
    nix_content.append("  sensitive-hdd = {\n")
    
    for i, partition in enumerate(hdd_info["partitions"]):
        p_name = partition_names[i]
        nix_content.append(f"    # Partition {p_name}\n")
        nix_content.append(f"    \"{p_name}\" = {{\n")
        nix_content.append(f"      label = \"{p_name}\";\n")
        nix_content.append(f"      device = \"/dev/disk/by-uuid/{partition['uuid']}\";\n")
        nix_content.append(f"      device-by-label = \"/dev/disk/by-label/{p_name}\";\n")
        nix_content.append(f"      mountPoint = \"/mnt/sensitive-hdd-mount/{p_name}\";\n")
        nix_content.append(f"      uuid = \"{partition['uuid']}\";\n")
        nix_content.append(f"      luks-uuid = \"{partition['luks_uuid']}\";\n")
        nix_content.append(f"      luks-device = \"/dev/disk/by-uuid/{partition['luks_uuid']}\";\n")
        nix_content.append(f"      fsType = \"ext4\";\n")
        nix_content.append("    };\n")

    nix_content.append("  };\n")
    nix_content.append("in sensitive-hdd")

    # Write to file
    with open(nix_file, "w") as nix_file_obj:
        nix_file_obj.write("".join(nix_content))

    print(f"Nix configuration file written to {nix_file}")


# Main function
def main(
        default_factors=[0.33, 0.33, 0.33],
        output_json="output.json",
        log_file="prod_usb_encryption.log",
        hdd_info_json="hdd-info.json",
        nix_output_file="sensitive-hdd.nix",   # New argument for Nix file
        default_mount_dir="/mnt/sensitive-hdd-mount",
        default_key_dir="./sensitive-hdd-keys",
        user = "endoreg-service-user",
        group = "endoreg-service"
    ):

    # Set up logging
    logger = setup_logging(log_file)

    # List available devices and ask for user input
    devices = list_devices(logger)
    device = input("Please enter the full path of the device you wish to format (e.g., /dev/sdb): ").strip()

    # Get partition names from the user, with default values
    partition_names = input("Enter partition names separated by commas (default: dropoff,processing,processed): ").strip().split(",")
    if len(partition_names) != 3:
        partition_names = ['dropoff', 'processing', 'processed']
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
    shutil.chown(mount_dir, user="{user}", group="endoreg-service")
    os.chmod(mount_dir, 0o770)
    logger.info(f"Permissions set for {mount_dir}: user={user}, group=endoreg-service")

    # Get the key directory from the user
    _key_dir = input(f"Enter a directory to store encryption keys (default: {default_key_dir}): ").strip()
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
        shutil.chown(key_dir, user="{user}", group="endoreg-service")
        os.chmod(key_dir, 0o770)
        logger.info(f"Permissions (0770) set for {key_dir}: user={user}, group=endoreg-service")

    # Confirm with the user before proceeding
    confirm = input(f"Are you sure you want to format and partition {device}? This will destroy all data on the device. (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("Operation canceled by the user.")
        return

    # Step 1: Cleanup device before partitioning
    cleanup_device(device, mount_dir, logger)

    # Step 2: Create partitions
    ov_partition_names = ['dropoff', 'processing', 'processed']
    partitions = create_partitions(device, ov_partition_names, size_factors, logger)

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
        luks_uuid, key_file = encrypt_partition(partition, mount_dir, key_dir, logger)
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

    # Step 6: Write Nix configuration file
    write_nix_configuration(hdd_info, partition_names, nix_output_file)

    # Step 7: Test unmount and remount functionality
    unmount_and_mount_all_partitions(device, mount_dir, logger, key_dir)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="List devices, format, partition, and encrypt a USB drive.")
    parser.add_argument("--factors", nargs=3, type=float, default=[0.33, 0.33, 0.33], help="Size factors for the partitions")
    parser.add_argument("--output", default="output.json", help="Output JSON file")
    parser.add_argument("--logfile", default="usb_encryption.log", help="Log file location")
    parser.add_argument("--hddinfo", default="hdd-info.json", help="HDD info JSON file location")
    parser.add_argument("--nixfile", default="sensitive-hdd.nix", help="Output Nix file location")  # Added Nix file option
    parser.add_argument("--mountdir", default="/mnt/endoreg-sensitive", help="Target directory for mounting LUKS partitions")
    parser.add_argument("--keydir", default="./sensitive-hdd-keys/", help="Directory to store encryption keys")
    args = parser.parse_args()
    
    main(args.factors, args.output, args.logfile, args.hddinfo, args.nixfile, args.mountdir)

