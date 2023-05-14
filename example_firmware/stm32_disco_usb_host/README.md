Fuzz STM32 USB Host Middleware by using a fuzzing harness

The firmware images included in this directory are derived from [here](https://github.com/STMicroelectronics/STM32CubeL4/tree/v1.17.1/Projects/B-L475E-IOT01A/Applications/USB_Host/MSC_Standalone) and are prepared with appropriate harnesses to fuzz the device descriptor and config descriptor parser routines, as presumable done in the [µAFL Paper](https://github.com/mcusec/microafl).
For fuzzing, a USB flash drive must be plugged into the USB Host port of the board. The fuzzing data is then red via the virtual serial from the host PC.

