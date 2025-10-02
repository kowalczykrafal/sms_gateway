#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>

// Define USBDEVFS_RESET if not available
#ifndef USBDEVFS_RESET
#define USBDEVFS_RESET 21780
#endif

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <usb_device_path>\n", argv[0]);
        return 1;
    }
    
    const char *device_path = argv[1];
    int fd = open(device_path, O_WRONLY);
    
    if (fd < 0) {
        fprintf(stderr, "Error opening device %s: %s\n", device_path, strerror(errno));
        return 1;
    }
    
    int result = ioctl(fd, USBDEVFS_RESET, 0);
    close(fd);
    
    if (result < 0) {
        fprintf(stderr, "Error resetting device %s: %s\n", device_path, strerror(errno));
        return 1;
    }
    
    printf("USB device %s reset successfully\n", device_path);
    return 0;
}
