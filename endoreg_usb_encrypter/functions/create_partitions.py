from .base import run_command

# Function to create partitions on the device
def create_partitions(device, partition_names, size_factors, logger):
    logger.info(f"Creating partitions on {device} with partition names: {partition_names} and size factors: {size_factors}")
    
    # Run parted to clear existing partitions
    run_command(f"parted -s {device} mklabel gpt", logger)
    
    # Inform the kernel of partition changes
    run_command(f"partprobe {device}", logger)

    start = 1  # Start partitioning at 1% to avoid reserved space
    partitions = []

    for i, (name, factor) in enumerate(zip(partition_names, size_factors)):
        end = start + factor * 100  # in percentage
        partition = f"{device}{i+1}"
        
        # Create the partition with specified sizes
        run_command(f"parted -s {device} mkpart {name} ext4 {int(start)}% {int(end)}%", logger)
        
        # Wait for the partition table to be updated
        run_command(f"partprobe {device}", logger)

        # Format the partition as ext4
        run_command(f"mkfs.ext4 {partition}", logger)

        # Label the partition with the provided name
        run_command(f"e2label {partition} {name}", logger)

        partitions.append(partition)
        start = end
    
    logger.info(f"Partitions created, formatted, and labeled: {partitions}")
    return partitions
