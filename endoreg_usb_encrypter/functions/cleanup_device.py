from .base import run_command
import subprocess

# Function to unmount all partitions and close LUKS devices on a device
def cleanup_device(device, mount_dir, logger):
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