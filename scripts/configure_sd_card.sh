#!/bin/bash

# this script is intended for use after the Raspian OctoPrint 
# has been burned to the SD card, to configure it before first
# boot.

CARD_ROOT="/Volumes/boot"

# a file that gets created after the config to track cards that were configured.
CONFIG_FILE=".configured"

if [ -f "$CARD_ROOT/$CONFIG_FILE" ]; then
	echo "Error: this card has already been configured:"
	echo -n "    "
	cat "$CARD_ROOT/$CONFIG_FILE"
	exit 1
fi


# remove the automatic resizing of the main partition, and boot logging to the serial console
sed -E 's/ init=[^ ]*\/init_resize.sh//' "$CARD_ROOT/cmdline.txt" >/tmp/cmdline_clean.txt
sed -E 's/console=serial0,115200//' /tmp/cmdline_clean.txt >/tmp/cmdline_clean2.txt
cat /tmp/cmdline_clean2.txt > "$CARD_ROOT/cmdline.txt"   # cat, not move, preserves file ownership/permissions.
rm /tmp/cmdline_clean.txt
rm /tmp/cmdline_clean2.txt


# add the new bits
echo '
country=DE  # Deutschland
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev

# my network information
network={
  ssid="WifiName"
  psk="WifiPassword"
}
' >> "$CARD_ROOT/wpa_supplicant.conf"

# enable ssh for first contact
touch "$CARD_ROOT/ssh"

# tag the card as configured
echo "Configured at `date -j '+%Y-%m-%d %H:%M:%S'` by `whoami`@`uname -n`" >"$CARD_ROOT/$CONFIG_FILE"


echo -n "Done configuring! Eject? (y/n) "
read -n 1 answer

if [ "$answer" == "Y" -o "$answer" == "y" ]; then
	echo ""
	echo ""
	diskutil eject "$CARD_ROOT"
fi