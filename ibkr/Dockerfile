FROM ubuntu:20.04

# Environment variables for configuration
ENV GATEWAY_VERSION=latest-standalone
ENV IBC_VERSION=3.12.0
ENV DISPLAY=:1
ENV TWS_PORT=4002
ENV VNC_PORT=5900
ENV TRADING_MODE=paper

# Install dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    libxrender1 \
    libxtst6 \
    libxi6 \
    x11vnc \
    socat \
    wget \
    unzip \
    openjdk-8-jre \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /opt/ibgateway

# Download and install IB Gateway
RUN wget -q https://download2.interactivebrokers.com/installers/ibgateway/${GATEWAY_VERSION}/ibgateway-${GATEWAY_VERSION}-linux-x64.sh
RUN chmod +x ibgateway-${GATEWAY_VERSION}-linux-x64.sh
RUN ./ibgateway-${GATEWAY_VERSION}-linux-x64.sh -q -dir /opt/ibgateway

# Setup IBC (Interactive Brokers Controller)
WORKDIR /opt/ibc
RUN wget -q https://github.com/IbcAlpha/IBC/releases/download/${IBC_VERSION}/IBCLinux-${IBC_VERSION}.zip
RUN unzip IBCLinux-${IBC_VERSION}.zip
RUN chmod +x *.sh

# Create necessary directories
RUN mkdir -p /root/Jts

# Copy configuration files
COPY config.ini /opt/ibc/config.ini
COPY jts.ini /root/Jts/jts.ini

# Create startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Healthcheck to ensure the gateway is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD netstat -an | grep ${TWS_PORT} | grep LISTEN || exit 1

# Expose the API port and VNC port
EXPOSE ${TWS_PORT} ${VNC_PORT}

# Start IB Gateway with IBC
ENTRYPOINT ["/start.sh"]