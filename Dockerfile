# Use Debian 9 because it's da best
FROM debian:9

# Establish environment variables/paths
ENV APP_DIR=/srv

# Work in app directory
WORKDIR $APP_DIR

# Install system packages required for building app
RUN apt-get update && apt-get install -y python-pip transmission-daemon

# Add application user so we're not running as root
RUN useradd -m swashbuckler

# Copy python library requirements
COPY requirements.txt .

# Install application dependencies
RUN pip install -r requirements.txt

# Drop transmission config
COPY settings.json /etc/transmission-daemon/settings.json


CMD /usr/bin/transmission-daemon --config-dir /etc/transmission-daemon/settings.json
