from pathlib import Path

from endoreg_usb_encrypter.functions import (
    cleanup_device,
    create_partitions,
    encrypt_partition,
    setup_logging,
    list_devices,
    format_partition,
    unmount_and_mount_all_partitions
)
import json

###################
test_run=False
###################

default_factors=[0.33, 0.33, 0.33]
output_json="output.json"
log_file="prod_usb_encryption.log"
hdd_info_json="hdd-info.json"
nix_output_file="sensitive-hdd.nix"  # New argument for Nix file
default_mount_dir="/mnt/sensitive-hdd-mount"
default_key_dir="./sensitive-hdd-keys"
user = "endoreg-service-user"
group = "endoreg-service"
TEST_DEVICE = "/dev/sdb"

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
        default_mount_dir="/mnt/endoreg-sensitive-data",
        default_key_dir="./sensitive-hdd-keys",
        user = "admin",
        group = "endoreg-service",
        test_run=False,
        partition_names = ['dropoff', 'processing', 'processed']
    ):
    # Set up logging
    logger = setup_logging(log_file)
    size_factors = default_factors
    mount_dir = Path(default_mount_dir)
    key_dir = Path(default_key_dir)

    # raise exception if mount_dir does not exist
    if not mount_dir.exists():
        logger.error(f"Mount directory {mount_dir} does not exist")
        raise FileNotFoundError(f"Mount directory {mount_dir} does not exist")
    

    # assert that mount dir owner is admin and group is endoreg-service
    if mount_dir.owner() != user or mount_dir.group() != group:
        logger.error(f"Mount directory {mount_dir} must be owned by {user} and group {group}")
        raise PermissionError(f"Mount directory {mount_dir} must be owned by {user} and group {group}")
    
    if not key_dir.exists():
        logger.warning(f"Key directory {key_dir} does not exist. Creating it now.") 
        key_dir.mkdir(parents=True, exist_ok=True)

        # set permissions for key_dir:
        key_dir.chmod(0o700)



    # List available devices and ask for user input
    devices = list_devices(logger)
    
    if not test_run:
        device = input("Please enter the full path of the device you wish to format (e.g., /dev/sdb): ").strip()
    else:
        device = TEST_DEVICE
    
    confirm = input(f"Are you sure you want to format and partition {device}? This will destroy all data on the device. (yes/no): ").strip().lower()
    if confirm != 'yes':
        logger.info("Operation canceled by the user.")
        return

    # Step 1: Cleanup device before partitioning
    cleanup_device(device, mount_dir, logger)

    # Step 2: Create partitions on the device
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
    main(test_run=test_run)
    # import argparse
    # parser = argparse.ArgumentParser(description="List devices, format, partition, and encrypt a USB drive.")
    # parser.add_argument("--factors", nargs=3, type=float, default=[0.33, 0.33, 0.33], help="Size factors for the partitions")
    # parser.add_argument("--output", default="output.json", help="Output JSON file")
    # parser.add_argument("--logfile", default="usb_encryption.log", help="Log file location")
    # parser.add_argument("--hddinfo", default="hdd-info.json", help="HDD info JSON file location")
    # parser.add_argument("--nixfile", default="sensitive-hdd.nix", help="Output Nix file location")  # Added Nix file option
    # parser.add_argument("--mountdir", default="/mnt/endoreg-sensitive", help="Target directory for mounting LUKS partitions")
    # parser.add_argument("--keydir", default="./sensitive-hdd-keys/", help="Directory to store encryption keys")
    # args = parser.parse_args()
    
    # main(args.factors, args.output, args.logfile, args.hddinfo, args.nixfile, args.mountdir)

