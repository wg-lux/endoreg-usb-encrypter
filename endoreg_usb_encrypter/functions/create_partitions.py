from .base import run_command

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
