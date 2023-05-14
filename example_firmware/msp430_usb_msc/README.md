The M1_FileSystemEmulation example from the TI CCS IDE, with sleep mode disabled in `mscFse.c:124`.

Change 

    if (USBMSC_pollCommand() == USBMSC_OK_TO_SLEEP){
        __bis_SR_register(LPM0_bits + GIE);
    }

to

    USBMSC_pollCommand();

Sleep mode is great for saving energy, but bad for fuzzing ;)