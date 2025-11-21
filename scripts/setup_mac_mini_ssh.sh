#!/bin/bash
# Atlas Mac Mini SSH Setup Script
# Run this script to set up passwordless SSH authentication to Mac Mini

set -e

echo "🔧 Setting up SSH authentication to Mac Mini..."

# Check if we already have SSH keys
if [ ! -f ~/.ssh/id_rsa ]; then
    echo "📋 Generating SSH key pair..."
    ssh-keygen -t rsa -b 4096 -C "atlas-server@$(hostname)" -f ~/.ssh/id_rsa -N ""
    echo "✅ SSH key pair generated"
else
    echo "✅ SSH key pair already exists"
fi

# Get Mac Mini connection details
echo ""
echo "🔍 Mac Mini Connection Setup"
echo "Please provide the following information:"
read -p "Mac Mini IP address: " MAC_MINI_IP
read -p "Mac Mini username: " MAC_MINI_USER

echo ""
echo "📋 Setting up SSH config..."

# Create SSH config entry
cat >> ~/.ssh/config << EOF

# Atlas Mac Mini Configuration
Host macmini
    HostName $MAC_MINI_IP
    User $MAC_MINI_USER
    Port 22
    IdentityFile ~/.ssh/id_rsa
    ServerAliveInterval 60
    ServerAliveCountMax 3
EOF

echo "✅ SSH config updated"

# Display the public key for manual copying
echo ""
echo "🔑 Copy this public key to your Mac Mini:"
echo "Run this command ON THE MAC MINI:"
echo ""
echo "mkdir -p ~/.ssh && echo '$(cat ~/.ssh/id_rsa.pub)' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"
echo ""

echo "After copying the key, test the connection:"
echo "ssh macmini \"echo 'SSH connection successful'\""

# Create connection test script
cat > /home/ubuntu/dev/atlas/scripts/test_mac_mini_connection.sh << 'EOF'
#!/bin/bash
# Test Mac Mini SSH connection

echo "🧪 Testing Mac Mini SSH connection..."

# Test basic SSH connection
if ssh -o ConnectTimeout=10 macmini "echo 'SSH connection successful'" 2>/dev/null; then
    echo "✅ SSH connection working"
else
    echo "❌ SSH connection failed"
    exit 1
fi

# Test file transfer
echo "test_file_$(date +%s)" > /tmp/atlas_test.txt
if scp /tmp/atlas_test.txt macmini:/tmp/ 2>/dev/null; then
    echo "✅ File transfer working"
    rm /tmp/atlas_test.txt
    ssh macmini "rm /tmp/atlas_test.txt" 2>/dev/null
else
    echo "❌ File transfer failed"
    exit 1
fi

# Test directory creation
if ssh macmini "mkdir -p ~/atlas_worker && echo 'Directory creation successful'" 2>/dev/null; then
    echo "✅ Remote directory operations working"
else
    echo "❌ Remote directory operations failed"
    exit 1
fi

echo "🎉 All Mac Mini connection tests passed!"
EOF

chmod +x /home/ubuntu/dev/atlas/scripts/setup_mac_mini_ssh.sh
chmod +x /home/ubuntu/dev/atlas/scripts/test_mac_mini_connection.sh

echo ""
echo "🎯 Setup Instructions:"
echo "1. Run: ./scripts/setup_mac_mini_ssh.sh"
echo "2. Copy the public key to your Mac Mini (shown in output)"
echo "3. Test connection: ./scripts/test_mac_mini_connection.sh"