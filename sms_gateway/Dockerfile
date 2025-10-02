ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:latest
FROM $BUILD_FROM

ENV LANG=C.UTF-8
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install requirements for add-on
RUN apk add --no-cache python3 py3-pip python3-dev usbutils gcc musl-dev linux-headers
RUN pip3 install --no-cache-dir argparse pyserial requests paho-mqtt xmltodict

# Load USB modules for usbreset functionality
RUN modprobe usb-storage || true
RUN modprobe usb-serial || true
RUN modprobe cdc-acm || true

# Compile usbreset tool
COPY usbreset.c /
RUN gcc -Wall -Wextra -o /usr/local/bin/usbreset usbreset.c && chmod +x /usr/local/bin/usbreset

# Verify usbreset installation
RUN which usbreset && echo "usbreset compiled successfully" || echo "usbreset compilation failed"

# Copy data for add-on
COPY CHANGELOG.md /
COPY gsm_core.py /
COPY gsm_commands.py /
COPY gsm_sms.py /
COPY gsm_diagnostics.py /
COPY gsm_reset.py /
COPY gsm_io.py /
COPY gsm_serial.py /
COPY gsm_io_thread.py /
COPY gsm_io_main.py /
# gsm_text_decoder.py removed - no longer needed
COPY LICENSE /
COPY README.md /
COPY run.sh /
COPY sms_manager.py /
COPY sms_launcher.py /
COPY sms_mqtt_handler.py /
# sms_status_manager.py removed - no longer needed
# sms_diagnostics.py removed - no longer needed

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
