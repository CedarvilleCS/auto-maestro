FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive

# install common tools + Python3 + pip
RUN apt-get update \
    && apt-get -y install \
        binutils \
        curl \
        iproute2 \
        iputils-ping \
        nano \
        net-tools \
        unzip \
        arping \
        conntrack \
        dnsutils \
        iptables \
        mtr-tiny \
        netcat-openbsd \
        openbsd-inetd \
        openssh-server \
        openssh-client \
        procps \
        tcpdump \
        telnet \
        telnetd \
        python3 \
        python3-pip \
        wget \
        git \
        build-essential \
        libssl-dev \
        libffi-dev \
        ruby \
        ruby-dev \
        gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Install security/penetration testing tools (only those with agent support)
RUN apt-get update \
    && apt-get -y install \
        nmap \
        hydra \
        hashcat \
    && rm -rf /var/lib/apt/lists/*

# Note: Metasploit installation commented out due to size - uncomment if needed
# RUN curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > /tmp/msfinstall \
#     && chmod +x /tmp/msfinstall \
#     && /tmp/msfinstall \
#     && rm /tmp/msfinstall

# Note: psexec is typically used from impacket Python library (installed below)

# Install Python security libraries (Ubuntu 24.04 pip requires --break-system-packages flag)
# Using --ignore-installed to avoid conflicts with system packages
RUN pip3 install --ignore-installed scapy PySocks paramiko impacket --break-system-packages

# Create seed user and set password
RUN useradd -m -s /bin/bash seed \
    && echo "root:dees" | chpasswd \
    && echo "seed:dees" | chpasswd

# Copy custom bashrc
COPY bashrc /home/seed/.bashrc
COPY bashrc /root/.bashrc
COPY sshd_config /etc/ssh/sshd_config

CMD ["/bin/bash"]
