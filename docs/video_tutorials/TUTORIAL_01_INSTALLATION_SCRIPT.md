# Atlas Tutorial 1: Installation and Setup Script

## Introduction
Hello and welcome to the first tutorial in the Atlas series. In this video, I'll show you how to download, install, and configure Atlas on your system. By the end of this tutorial, you'll have a fully functional Atlas installation ready to process your content.

Before we begin, make sure you have Python 3.9 or higher installed on your system. Let's get started!

## Section 1: System Requirements and Prerequisites
First, let's check that we have the necessary prerequisites installed.

[Screen recording: Terminal showing Python version check]
```bash
python3 --version
git --version
```

If you don't have Python or Git installed, you'll need to install them first. For Ubuntu:
```bash
sudo apt update
sudo apt install python3 git
```

For macOS with Homebrew:
```bash
brew install python3 git
```

## Section 2: Downloading Atlas
Now let's download the Atlas repository from GitHub.

[Screen recording: Terminal showing git clone command]
```bash
git clone https://github.com/your-username/atlas.git
cd atlas
```

## Section 3: Setting Up Virtual Environment
It's best practice to use a virtual environment for Python projects. Let's create one for Atlas.

[Screen recording: Terminal showing virtual environment setup]
```bash
python3 -m venv venv
source venv/bin/activate
```

## Section 4: Installing Dependencies
Now we'll install all the required dependencies for Atlas.

[Screen recording: Terminal showing pip install command]
```bash
pip install -r requirements.txt
```

## Section 5: Initial Configuration
Let's copy the sample configuration file and customize it with our API keys.

[Screen recording: Terminal and text editor showing .env setup]
```bash
cp .env.template .env
nano .env
```

We need to add our API keys for the services we want to use:
- OpenRouter API key for AI features
- YouTube API key for YouTube content ingestion
- Instapaper credentials for Instapaper import

## Section 6: Running Initial Setup
Let's run the initial setup script to verify our installation.

[Screen recording: Terminal showing setup script]
```bash
python scripts/setup_wizard.py --automated
```

## Section 7: Verifying Installation
Finally, let's verify that our installation is working correctly.

[Screen recording: Terminal showing health check]
```bash
python atlas_status.py --detailed
```

If everything is set up correctly, you should see a status report showing that all systems are healthy.

## Conclusion
That's it for the installation and setup tutorial. You should now have a fully functional Atlas installation ready to process your content.

In the next tutorial, we'll cover adding your first content to Atlas and processing it. If you found this helpful, please like and subscribe for more Atlas tutorials. Thanks for watching, and see you next time!