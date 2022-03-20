# Setup Guide

## Write Your SD Card

Use `diskutil list` to determine your SD block device, something like `disk4`.

Using `scripts/write_sd_card.sh`, write the image to the card.

```
./scripts/write_sd_card.sh disk4 Downloads/2022-01-28-raspios-bullseye-armhf-lite.img
```

## Configure the SD Card

First, open `scripts/configure_sd_card.sh`, and input your region and Wifi Details in lines 30, 35 and 36. Then:

```
./scripts/configure_sd_card.sh
```

Eject the SD card, put it into your Pi, and then boot the pi. 


## Provision Login to the Pi

Firstly, clean any previous raspberry pi's from your known hosts file, just in case:

```
grep -v '^raspberrypi.local' ~/.ssh/known_hosts >  ~/.ssh/known_hosts_clean; mv -f ~/.ssh/known_hosts_clean ~/.ssh/known_hosts
```

Install your public key to the RPi. 
If you get an error here, use `ssh-keygen` to generate a public/private key pair.
The password, when prompted, is `raspberry`.

```
ssh-copy-id pi@raspberrypi.local
```

Login to the pi:

```
ssh pi@raspberrypi.local
```

## Configure the Pi

Change the password to something unique, default is `raspberry`.

```
passwd
```

Modify the ssh server config file to make connection stay alive, even when idle for long periods.

```
sudo nano /etc/ssh/sshd_config
```

...and then add the following two lines, or uncomment and change the lines already in that file.

```
ClientAliveInterval 15
ClientAliveCountMax 4
```

To save changes and exit: `Ctrl + X`, `Y`, and `Enter`.

## Configure the Partitions 

This will add 2 GBs to the Root partition, and then create another partition from the left over free space.

```
echo ", +2G" | sudo sfdisk -N 2 /dev/mmcblk0 --force
sudo reboot
```

Wait for the reboot, reconnect with the `ssh` command, and continue.

```
sudo resize2fs /dev/mmcblk0p2
```

Check that worked, the root partition should be ~4GB.

```
df -h
```

### Optional Step - SD card check

Only do this if you think your SD card might be bad, takes about 10 mins. Make sure that `mmcblk0p2` is the correct block device for the root parition (it usually is).

```
sudo badblocks -s /dev/mmcblk0p2
```

If no errors are found, it'll just say: `Checking for bad blocks (read-only test): done`.


## Make partition from Free Space

> **WARNING**: there's 2MB of free space allocated before the first FAT32 volume is allocated on the SD card. Creating a new partition defaults to making this free space into a partition. Make sure you follow the instructions below to avoid this -- you don't want that!

```
sudo fdisk /dev/mmcblk0
```

Type `print`, and take note of the `End` sector number of the second partition, the number in the second column.
Type `n` for a new partition, `p` for primary, and `Enter` to accept the default number. 
Add 1 to the `End` sector number you recorded above, and input that as the start sector for the new partition. 
`Enter` to accept the default `End` sector. `w` to write the new partition table to disk.

```
sudo reboot
```

After the reboot is completed, create a new partition:

```
sudo mkfs.ext4 /dev/mmcblk0p3
```

Mount it, make it read/write for everyone, and test you can write to the partition.

```
sudo mkdir /mnt/data
sudo mount /dev/mmcblk0p3 /mnt/data
sudo chmod -R a+rw /mnt/data
touch /mnt/data/hello
```

Get the full UUID of the new parition:

```
sudo blkid -o list
```

Copy the full UUID string, and paste it into the following line, instead of the `xxxx`'s.

```
UUID=xxxx-xxxx-xxxx	/mnt/data	ext4	defaults	0
```

Write this line to the bottom of the `fstab`.

```
sudo nano /etc/fstab
```

Reboot, and the same file should be writable again.

```
sudo reboot
```

```
touch /mnt/data/hello
```

If this touch command fails, stop, and investigate why your partition didn't auto-mount on a reboot.


## Full System Update

```
sudo apt-get update && sudo apt-get --yes upgrade
```

Make sure the update didn't break anything, do a reboot to be sure everything is OK!

```
sudo reboot
```

## Dependancies

Install Bluetooth dependencies:

```
sudo apt-get install -y libbluetooth-dev libglib2.0-dev libboost-python-dev libboost-thread-dev
sudo apt-get install -y python3-pip
sudo apt-get install -y git
sudo pip3 install bluepy
```

If you're installing support for the **TP-Link** Wifi Dongle, you'll also need:

```
sudo apt install -y raspberrypi-kernel-headers bc build-essential dkms
```

## Compile **TP-Link** Wifi Driver

```
cd /home/pi
git clone https://github.com/morrownr/88x2bu-20210702.git
cd ./88x2bu-20210702

# Assuming we're using the 32-bit OS! Don't bother trying to compile this if you're on 64-bit
./ARM_RPI.sh

# this will compile and install the driver (this takes some time) - make sure you reboot when asked here!
sudo ./install-driver.sh
```

If that all worked, modify the WPA supplicant file, changing the wifi network to the 5GHz one:

```
sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
```

Disable on-board Wifi support by editing the `/boot/cmdline.txt` file, and adding:

```
dtoverlay=disable-wifi
```

Make sure there's spaces between everything there and this new string you pasted in.

Do a reboot, and make sure you still have access to the Pi over Wifi!

```
sudo reboot
```

## Final Adjustments

```
sudo raspi-config
```

Then: 

```
1. -> 4. -> Change the host name
5. -> 2. -> Change your localisation
```

Exit and Reboot.

Validate the new hostname works:

```
ssh pi@new-hostname.local
```

## Do a test BLE Scan

```
sudo hcitool lescan
```

You should see Mac Addresses and names of BLE devices.


## Clone This Repo on the Pi

```
cd /home/pi
git clone https://github.com/rebelresistor/etekcity_ble_scale.git
```


## Install the `systemd` Service

```
sudo python etekcity_ble_scale/src/EtekcityESF37.py --install
```

Tail the log file, and run a test of the scale.

```
tail -f /mnt/data/etekcity_scale/logs/application.log 
```

Turn on the scale, wait for the Bluetooth symbol on the display of the scale, and then stand on it. 
You should see a lot of logging of messages in the log file.

Check your weight was recorded to the CSV file.

```
cat /mnt/data/etekcity_scale/measurements.csv
```

## Make the root partition read only

```
sudo raspi-config
```

Choose `4` -> `P3`, make both partitions read only and reboot on exit!


## Remove the service

To remove the service, make the root partitions readable again, and run:

```
sudo python etekcity_ble_scale/src/EtekcityESF37.py --remove
```

