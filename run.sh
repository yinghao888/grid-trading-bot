#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

print_color() {
    printf "${1}%s${NC}\n" "${2}"
}

# Check Python
if ! command -v python3 &> /dev/null; then
    print_color $RED "Python3 is required but not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Create and activate virtual environment
print_color $GREEN "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
print_color $GREEN "Installing dependencies..."
pip install aiohttp==3.9.1 python-dotenv==1.0.0 websockets==12.0 pandas==2.1.4 numpy==1.26.2 loguru==0.7.2

# Download bot script
print_color $GREEN "Downloading bot script..."
curl -s https://raw.githubusercontent.com/your-username/grid-trading-bot/main/bot.py -o bot.py

if [ $? -ne 0 ]; then
    print_color $RED "Failed to download bot script!"
    exit 1
fi

# Start the bot
print_color $GREEN "Starting the bot..."
python bot.py 
