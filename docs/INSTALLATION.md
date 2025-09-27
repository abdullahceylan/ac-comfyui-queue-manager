# ComfyUI Queue Manager - Installation Guide

## Quick Installation

### Method 1: Git Clone (Recommended)

```bash
# Navigate to ComfyUI custom nodes directory
cd ComfyUI/custom_nodes

# Clone the repository
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager

# Install dependencies
cd comfyui-queue-manager
pip install -r requirements.txt

# Restart ComfyUI
```

### Method 2: Manual Download

1. Download the latest release from GitHub
2. Extract to `ComfyUI/custom_nodes/comfyui-queue-manager`
3. Install dependencies: `pip install -r requirements.txt`
4. Restart ComfyUI

### Method 3: ComfyUI Manager (if available)

1. Open ComfyUI Manager
2. Search for "Queue Manager"
3. Click Install
4. Restart ComfyUI

## Detailed Installation

### Prerequisites

Before installing, ensure you have:

- **ComfyUI**: Working installation of ComfyUI
- **Python**: Version 3.8 or higher
- **pip**: Python package manager
- **Git**: For cloning repository (optional)

### Step-by-Step Installation

#### 1. Locate ComfyUI Directory

Find your ComfyUI installation directory:

**Windows**:
```cmd
# Usually in one of these locations:
C:\ComfyUI\
C:\Users\[username]\ComfyUI\
```

**macOS**:
```bash
# Usually in:
~/ComfyUI/
/Applications/ComfyUI/
```

**Linux**:
```bash
# Usually in:
~/ComfyUI/
/opt/ComfyUI/
```

#### 2. Navigate to Custom Nodes

```bash
cd ComfyUI/custom_nodes
```

#### 3. Install Queue Manager

**Option A: Git Clone**
```bash
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager
cd comfyui-queue-manager
```

**Option B: Download ZIP**
1. Download ZIP from GitHub
2. Extract to `custom_nodes/comfyui-queue-manager`
3. Navigate to the directory

#### 4. Install Python Dependencies

```bash
# Install required packages
pip install -r requirements.txt

# Or install manually:
pip install flask>=2.3.0
```

#### 5. Verify Installation

Check that these files exist:
```
custom_nodes/comfyui-queue-manager/
├── __init__.py
├── queue_manager_node.py
├── requirements.txt
├── web/
│   ├── index.html
│   ├── queue_manager.js
│   └── styles.css
└── [other files...]
```

#### 6. Restart ComfyUI

- Close ComfyUI completely
- Start ComfyUI again
- Wait for full initialization

#### 7. Verify Queue Manager Appears

1. Look for "Queue Manager" in ComfyUI menu
2. Click to open the interface
3. Should see empty queue interface

## Platform-Specific Instructions

### Windows Installation

#### Using Command Prompt

```cmd
# Navigate to ComfyUI directory
cd C:\ComfyUI\custom_nodes

# Clone repository
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager

# Install dependencies
cd comfyui-queue-manager
pip install -r requirements.txt
```

#### Using PowerShell

```powershell
# Navigate to ComfyUI directory
Set-Location "C:\ComfyUI\custom_nodes"

# Clone repository
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager

# Install dependencies
Set-Location comfyui-queue-manager
pip install -r requirements.txt
```

#### Common Windows Issues

**Issue**: `pip` not found
**Solution**: 
```cmd
python -m pip install -r requirements.txt
```

**Issue**: Permission denied
**Solution**: Run Command Prompt as Administrator

**Issue**: Git not found
**Solution**: Download ZIP file instead of using git clone

### macOS Installation

#### Using Terminal

```bash
# Navigate to ComfyUI directory
cd ~/ComfyUI/custom_nodes

# Clone repository
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager

# Install dependencies
cd comfyui-queue-manager
pip3 install -r requirements.txt
```

#### Using Homebrew Python

If you use Homebrew Python:
```bash
# Use pip3 instead of pip
pip3 install -r requirements.txt

# Or specify Python version
python3 -m pip install -r requirements.txt
```

#### Common macOS Issues

**Issue**: Permission denied
**Solution**: 
```bash
sudo pip3 install -r requirements.txt
```

**Issue**: Multiple Python versions
**Solution**: Use specific Python version:
```bash
python3.10 -m pip install -r requirements.txt
```

### Linux Installation

#### Ubuntu/Debian

```bash
# Install git if needed
sudo apt update
sudo apt install git python3-pip

# Navigate to ComfyUI directory
cd ~/ComfyUI/custom_nodes

# Clone repository
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager

# Install dependencies
cd comfyui-queue-manager
pip3 install -r requirements.txt
```

#### CentOS/RHEL/Fedora

```bash
# Install git if needed
sudo yum install git python3-pip  # CentOS/RHEL
sudo dnf install git python3-pip  # Fedora

# Navigate to ComfyUI directory
cd ~/ComfyUI/custom_nodes

# Clone repository
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager

# Install dependencies
cd comfyui-queue-manager
pip3 install -r requirements.txt
```

#### Arch Linux

```bash
# Install git if needed
sudo pacman -S git python-pip

# Navigate to ComfyUI directory
cd ~/ComfyUI/custom_nodes

# Clone repository
git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager

# Install dependencies
cd comfyui-queue-manager
pip install -r requirements.txt
```

## Virtual Environment Installation

For isolated installation, use a virtual environment:

### Create Virtual Environment

```bash
# Navigate to custom node directory
cd ComfyUI/custom_nodes/comfyui-queue-manager

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Using with Virtual Environment

Each time you start ComfyUI, ensure the virtual environment is activated:

```bash
# Navigate to queue manager directory
cd ComfyUI/custom_nodes/comfyui-queue-manager

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Start ComfyUI from parent directory
cd ../../
python main.py
```

## Docker Installation

If running ComfyUI in Docker:

### Dockerfile Addition

Add to your ComfyUI Dockerfile:

```dockerfile
# Install Queue Manager
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/abdullahceylan/ac-comfyui-queue-manager.git comfyui-queue-manager && \
    cd comfyui-queue-manager && \
    pip install -r requirements.txt
```

### Docker Compose

Add to your docker-compose.yml:

```yaml
services:
  comfyui:
    # ... existing configuration
    volumes:
      - ./custom_nodes/comfyui-queue-manager:/ComfyUI/custom_nodes/comfyui-queue-manager
    ports:
      - "8188:8188"  # ComfyUI
      - "5000:5000"  # Queue Manager API
```

## Troubleshooting Installation

### Common Issues

#### 1. Queue Manager Not Appearing in Menu

**Symptoms**: No "Queue Manager" option in ComfyUI menu

**Possible Causes**:
- Installation incomplete
- Dependencies not installed
- ComfyUI not restarted properly

**Solutions**:
```bash
# Verify files exist
ls ComfyUI/custom_nodes/comfyui-queue-manager/

# Reinstall dependencies
cd ComfyUI/custom_nodes/comfyui-queue-manager
pip install -r requirements.txt --force-reinstall

# Check ComfyUI console for errors
# Restart ComfyUI completely
```

#### 2. Import Errors

**Symptoms**: Python import errors in ComfyUI console

**Common Errors**:
```
ModuleNotFoundError: No module named 'flask'
ImportError: cannot import name 'QueueService'
```

**Solutions**:
```bash
# Install missing dependencies
pip install flask>=2.3.0

# Check Python path
python -c "import sys; print(sys.path)"

# Verify installation
python -c "import flask; print(flask.__version__)"
```

#### 3. Permission Issues

**Symptoms**: Permission denied errors during installation

**Solutions**:
```bash
# Linux/macOS: Use sudo
sudo pip install -r requirements.txt

# Windows: Run as Administrator
# Or use user installation:
pip install --user -r requirements.txt
```

#### 4. Port Conflicts

**Symptoms**: Queue Manager interface not accessible

**Error**: "Port 5000 already in use"

**Solutions**:
1. Change port in configuration
2. Stop conflicting application
3. Use different port: `python -m flask run --port 5001`

#### 5. Database Issues

**Symptoms**: Queue not persisting, database errors

**Solutions**:
```bash
# Check permissions
ls -la ComfyUI/custom_nodes/comfyui-queue-manager/

# Reset database
rm ComfyUI/custom_nodes/comfyui-queue-manager/queue_manager.db

# Restart ComfyUI
```

### Verification Steps

After installation, verify everything works:

1. **Check Files**:
   ```bash
   ls ComfyUI/custom_nodes/comfyui-queue-manager/
   # Should show: __init__.py, queue_manager_node.py, web/, etc.
   ```

2. **Check Dependencies**:
   ```bash
   pip list | grep -i flask
   # Should show: Flask 2.3.0 or higher
   ```

3. **Check ComfyUI Console**:
   - Start ComfyUI
   - Look for Queue Manager initialization messages
   - No error messages related to queue manager

4. **Check Menu**:
   - "Queue Manager" appears in ComfyUI menu
   - Clicking opens web interface

5. **Test Functionality**:
   - Create simple workflow
   - Execute it
   - Check if it appears in Queue Manager

### Getting Help

If installation fails:

1. **Check Logs**:
   - ComfyUI console output
   - `logs/queue_manager.log` (if created)

2. **Gather Information**:
   - Operating system and version
   - Python version: `python --version`
   - ComfyUI version
   - Error messages

3. **Report Issues**:
   - GitHub Issues: Include system info and error logs
   - ComfyUI Discord: Community support
   - Include installation method used

## Updating

### Update from Git

```bash
cd ComfyUI/custom_nodes/comfyui-queue-manager
git pull origin main
pip install -r requirements.txt --upgrade
```

### Manual Update

1. Download latest release
2. Replace files (backup database first)
3. Install/update dependencies
4. Restart ComfyUI

### Database Migration

Updates may include database schema changes:
- Automatic migration on first run
- Backup created before migration
- Check logs for migration status

---

**Next Steps**: After successful installation, see the [User Guide](USER_GUIDE.md) for usage instructions.