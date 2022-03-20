# Etekcity BLE Scale

The Etekcity BLE Scale works great, but the app situation is horrendous. Before you ever use the scale, you need to get your phone, open the app, click into the scale, and only then can you weight yourself...

This repo is everything you need to get a Raspberry Pi up and running to log all measurements from the scale. No app or phone required, whatsoever!

I used a Raspberry Pi Zero 2, and will be provisioning the SD card from macOS. 

## Caveats

The following is a list of things you should know before diving into using this guide.

- To make the Raspberry Pi as reliable as possible, it will be run with a read-only root filesystem. This reduces the risk of corruption on power outages. To save data and logs, though, a writable partition is required. For this reason, the partition re-sizing will be done manually.

- The Pi Zero 2 Wifi Adaptor and BLE module share an antenna. This means they cannot transmit or recieve at the same time. While running BLE scans, I was seeing ~10 sec. network dropouts consistently. This is fixed by purchasing a *TP-Link Archer T3U AC1300 USB WLAN Stick Adapter*, and connecting to a 5GHz-only wifi network. The built-in Wifi adaptor will be disabled.


If you're happy with this, proceed to the [Setup Guide](SETUP.md).