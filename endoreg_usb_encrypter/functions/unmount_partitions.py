# Function to unmount all partitions
from .base import run_command

def unmount_partitions(mount_dir, logger):
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