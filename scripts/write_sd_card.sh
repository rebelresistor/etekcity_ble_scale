#!/bin/bash


# SD Card Image
IMAGE="${HOME}/Downloads/2022-01-28-raspios-bullseye-armhf-lite.img"


# get the disk to write from the command line
if [ "$1" == "" ]; then
	echo "usage: write_sd_card.sh disk [image]"
	echo ""
	echo "example: write_sd_card.sh disk4 Downloads/2022-01-28-raspios-bullseye-armhf-lite.img"
	exit 1
fi

if [ "$2" != "" ]; then
	IMAGE="$2"
fi

if [ ! -f "$IMAGE" ]; then
	echo "Error: image file does not exist: $IMAGE"
	exit 1
fi


function is_valid_disk () {
	diskutil info "$1" >/dev/null 2>/dev/null
}

# check whether the user has given us a valid block device, not a partition 
function is_whole_disk () {
	whole_disk_status=`diskutil info "$1" | grep -E "  Whole:" | sed -E 's/ *Whole: +//' | tr '[:upper:]' '[:lower:]'`
	test "$whole_disk_status" == yes
}



if ! is_valid_disk "$1"; then
	echo "Error: you must supply a valid disk ID"
	exit 1
fi

if ! is_whole_disk "$1"; then
	echo "Error: you must supply a whole disk, not a partition, i.e. disk4, not disk4s1"
	exit 1
fi

echo "Your password may be requested to run commands as root"
sudo diskutil unmountDisk "$1"
sudo dd bs=1m "if=$IMAGE" "of=/dev/r$1"


echo "Done!"