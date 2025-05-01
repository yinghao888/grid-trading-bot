#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_color() {
    printf "${1}%s${NC}\n" "${2}"
}

# Verify script is being downloaded correctly
if [ "$(head -n1 $0)" = "404: Not Found" ]; then
    print_color $RED "Error: Unable to download installation script. Please check the repository URL."
    exit 1
fi

# Check Python
print_color $YELLOW "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_color $RED "Python3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create working directory
INSTALL_DIR="$HOME/backpack-grid-bot"
print_color $GREEN "Creating installation directory at $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR" || exit 1

# Create and activate virtual environment
print_color $GREEN "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
print_color $GREEN "Installing dependencies..."
pip install --upgrade pip
pip install aiohttp==3.9.1 python-dotenv==1.0.0 websockets==12.0 pandas==2.1.4 numpy==1.26.2 loguru==0.7.2

# Download bot script
print_color $GREEN "Downloading bot script..."
BOT_URL="https://raw.githubusercontent.com/yinghao888/grid-trading-bot/main/bot.py"
if ! curl -f -s "$BOT_URL" -o bot.py; then
    print_color $RED "Failed to download bot script from $BOT_URL"
    print_color $RED "Please check if the repository exists and is public."
    exit 1
fi

# Verify bot.py was downloaded successfully
if [ ! -s bot.py ]; then
    print_color $RED "Downloaded bot.py is empty. Installation failed."
    exit 1
fi

print_color $GREEN "Installation completed successfully!"
print_color $GREEN "Starting the bot..."
python bot.py 
