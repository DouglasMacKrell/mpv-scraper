# MPV-Scraper Text User Interface (TUI)

The MPV-Scraper TUI provides a comprehensive, user-friendly interface for managing MPV libraries and scraping metadata. This document covers all TUI features, workflows, and usage patterns.

## 🎯 Overview

The TUI is a full-featured alternative to CLI-only usage, providing:
- **Visual Interface**: Buttons and keyboard shortcuts for all operations
- **Real-Time Monitoring**: Live status updates and system monitoring
- **Library Management**: Multi-library support with history
- **Advanced Settings**: Provider configuration and system preferences
- **Comprehensive Help**: Context-sensitive help and documentation

## 🚀 Quick Start

### First-Time Setup
1. **Initialize Library**: Press `i` or click "Init" button
   - Enter your library path (e.g., `/Volumes/SD Card/roms/mpv`)
   - Creates proper directory structure and configuration files

2. **Verify Setup**: Press `t` or click "Test" button
   - Tests connectivity to all API endpoints
   - Ensures your system is ready for scraping

3. **Run Pipeline**: Press `r` or click "Run" button
   - Executes complete scan → scrape → generate workflow
   - Processes all shows and movies in your library

### Library Management
- **List Libraries**: Press `l` to see recent libraries
- **New Library**: Press `n` to create and switch to new library
- **Change Library**: Press `c` to switch between existing libraries

## ⌨️ Keyboard Shortcuts

### Core Operations
| Key | Action | Description |
|-----|--------|-------------|
| `i` | Init Library | Initialize new library with proper structure |
| `s` | Scan Library | Scan current library for shows/movies |
| `r` | Run Pipeline | Execute full scan→scrape→generate workflow |
| `o` | Optimize Videos | Crop videos to 4:3 aspect ratio |
| `u` | Undo Last | Revert most recent operation |

### Library Management
| Key | Action | Description |
|-----|--------|-------------|
| `l` | List Libraries | Show recent library history |
| `n` | New Library | Create and switch to new library |
| `c` | Change Library | Switch to different library |

### Settings & Monitoring
| Key | Action | Description |
|-----|--------|-------------|
| `p` | Provider Settings | Configure metadata provider preferences |
| `v` | System Info | View comprehensive system information |
| `t` | Test Connectivity | Test network and API connectivity |

### Help & Navigation
| Key | Action | Description |
|-----|--------|-------------|
| `?` | Help | Toggle comprehensive help guide |
| `F1` | Context Help | Show context-sensitive help |
| `q` | Quit | Exit the application |

## 🎮 Interface Layout

### Left Panel
- **Command Buttons**: Core operations (Init, Scan, Run, Optimize, Undo)
- **Library Buttons**: Library management (List, New, Change)
- **Settings Buttons**: Configuration and monitoring (Provider, System, Test)
- **Jobs Panel**: Recent job activity and status

### Right Panel
- **Logs Panel**: Recent log entries with color-coded messages
- **Commands Panel**: Real-time command execution status
- **Libraries Panel**: Current library information
- **Settings Panel**: System status and monitoring

## 🔧 Command Operations

### Initialize Library (`i`)
**Purpose**: Set up a new MPV library with proper structure

**What it does**:
- Creates `/Movies` directory for movies
- Creates `/images` directory for artwork
- Generates `mpv-scraper.toml` configuration file
- Creates `.env` file for API keys

**Usage**: Press `i` or click "Init" button, then enter library path

**Example**: `/Volumes/SD Card/roms/mpv`

### Scan Library (`s`)
**Purpose**: Discover shows and movies in the current library

**What it does**:
- Counts TV show folders
- Counts movie files
- Validates library structure
- Shows summary in jobs panel

**Usage**: Press `s` or click "Scan" button

**Output**: "Found 5 show folders and 12 movies"

### Run Pipeline (`r`)
**Purpose**: Execute the complete metadata scraping workflow

**What it does**:
1. Scans library for shows/movies
2. Scrapes metadata from APIs (TVDB/TMDB)
3. Downloads artwork and images
4. Generates `gamelist.xml` files

**Usage**: Press `r` or click "Run" button

**Time**: Can take several minutes depending on library size

### Optimize Videos (`o`)
**Purpose**: Crop videos to 4:3 aspect ratio

**What it does**:
- Removes letterboxing (black bars)
- Optimizes for 4:3 displays
- Useful for older content like cartoons

**Usage**: Press `o` or click "Optimize" button

**Target**: Classic TV shows and cartoons

### Undo Last Operation (`u`)
**Purpose**: Revert the most recent scraper operation

**What it does**:
- Restores original files
- Removes generated metadata
- Uses `transaction.log` for safety

**Usage**: Press `u` or click "Undo" button

**Note**: Only works if `transaction.log` exists

## 📁 Library Management

### List Libraries (`l`)
**Purpose**: Show recently used libraries

**What it does**:
- Displays up to 5 recent library paths
- Stored in `~/.mpv-scraper/library_history.json`
- Shows in libraries panel

**Usage**: Press `l` or click "List" button

### New Library (`n`)
**Purpose**: Create and switch to new library

**What it does**:
- Prompts for library path
- Runs init command automatically
- Switches to the new library

**Usage**: Press `n` or click "New" button

### Change Library (`c`)
**Purpose**: Switch to different library

**What it does**:
- Shows library selection modal
- Lists recent libraries
- Validates library structure

**Usage**: Press `c` or click "Change" button

## ⚙️ Settings & Monitoring

### Provider Settings (`p`)
**Purpose**: Configure metadata provider preferences

**Options**:
- **Primary**: Use TVDB/TMDB when keys are set
- **Prefer Fallback**: Try TVmaze/OMDb first
- **Fallback Only**: Only use TVmaze/OMDb
- **Offline**: No network calls; use cache only

**Usage**: Press `p` or click "Provider" button

### System Information (`v`)
**Purpose**: View comprehensive system details

**Information**:
- Operating system and version
- Python version
- Architecture
- Disk space (total and free)
- ffmpeg version

**Usage**: Press `v` or click "System" button

### Test Connectivity (`t`)
**Purpose**: Test network and API connectivity

**Tests**:
- Internet connection (8.8.8.8)
- TVDB API (api4.thetvdb.com)
- TMDB API (api.themoviedb.org)
- TVmaze API (api.tvmaze.com)
- OMDb API (www.omdbapi.com)

**Usage**: Press `t` or click "Test" button

## 🎯 Workflow Examples

### New SD Card Setup
1. **Initialize**: Press `n` → Enter path → Auto-initialize
2. **Verify**: Press `t` → Verify connectivity
3. **Process**: Press `r` → Run full pipeline

### Switch Between Libraries
1. **List**: Press `l` → See recent libraries
2. **Change**: Press `c` → Select from recent libraries
3. **Verify**: Press `s` → Verify content is found
4. **Process**: Press `r` → Process if needed

### Troubleshooting
1. **Check System**: Press `v` → Check system status
2. **Test Network**: Press `t` → Test connectivity
3. **Get Help**: Press `?` → Get comprehensive help

## 🆘 Troubleshooting

### Common Issues

#### No shows/movies found during scan
**Symptoms**: Scan shows "Found 0 show folders and 0 movies"

**Solutions**:
- Check library structure (needs `/Movies` or show folders)
- Verify file extensions (.mp4, .mkv, etc.)
- Ensure library path is correct

#### Scrape operations failing
**Symptoms**: Commands fail with network or API errors

**Solutions**:
- Press `t` to test connectivity
- Check API keys in `.env` file
- Verify network connection
- Try different provider mode

#### Low disk space warnings
**Symptoms**: System status shows disk space warnings

**Solutions**:
- Check system status panel
- Free up space on target drive
- Consider using external storage

#### TUI not responding
**Symptoms**: Interface becomes unresponsive

**Solutions**:
- Press `q` to quit and restart
- Check if commands are running in background
- Verify Python and dependencies are installed

### Advanced Troubleshooting

#### Check Logs
- Look at the logs panel for error messages
- Check `mpv-scraper.log` in your library directory
- Look for ERROR and WARNING messages

#### Network Issues
- Press `t` to test connectivity
- Check firewall settings
- Try different network connection
- Use 'offline' provider mode if needed

#### Disk Issues
- Check available disk space
- Ensure write permissions to library directory
- Try different storage location

#### Reset Operations
- Use `u` (undo) to revert last operation
- Delete `.mpv-scraper` directory to reset completely
- Re-initialize library with `i` command

## 💡 Tips & Tricks

### Efficient Workflows
- **Use F1**: Get context-sensitive help on any element
- **Monitor Status**: Check system status for disk space and API keys
- **Test First**: Test connectivity before running scrape operations
- **Use Undo**: Use undo (`u`) if something goes wrong

### Best Practices
- **Backup First**: Always backup your library before major operations
- **Check Space**: Monitor disk space before large operations
- **Verify Keys**: Ensure API keys are set before scraping
- **Test Connectivity**: Run connectivity tests on new systems

### Keyboard Shortcuts
- **Quick Access**: Learn keyboard shortcuts for faster operation
- **Context Help**: Use F1 for specific element help
- **Escape**: Use `q` to quit quickly if needed

## 🔧 Configuration

### TUI Preferences
Stored in `~/.mpv-scraper/tui_preferences.json`:
- **Refresh Rate**: Panel refresh interval (0.5s, 1.0s, 2.0s)
- **Theme**: Dark/Light/Auto theme preference

### Library Settings
Stored in `mpv-scraper.toml` in each library:
- **Provider Mode**: Metadata provider preferences
- **Workers**: Number of parallel workers
- **Preset**: Video processing preset

### API Keys
Stored in `.env` file in each library:
- **TVDB_API_KEY**: TheTVDB API key
- **TMDB_API_KEY**: The Movie Database API key
- **OMDB_API_KEY**: Open Movie Database API key (optional)

## 📊 Status Indicators

### System Status Panel
- **💾 Disk**: Available disk space
- **🌐 Network**: Internet connectivity
- **🔑 API Keys**: TVDB/TMDB key status
- **⚠️ Warnings**: System warnings
- **❌ Errors**: System errors
- **✅ Success**: Successful operations

### Job Status
- **completed**: Operation finished successfully
- **running**: Operation in progress
- **failed**: Operation failed

### Log Messages
- **ERROR** (red): Critical errors requiring attention
- **WARNING** (yellow): Non-critical warnings
- **INFO** (normal): General information messages

## 🎨 User Experience Features

### Real-Time Updates
- **Auto-refresh**: Panels update automatically
- **Live Status**: Command execution status in real-time
- **System Monitoring**: Continuous system health monitoring

### Visual Feedback
- **Emoji Indicators**: Clear visual status indicators
- **Color Coding**: Error/warning colors in logs
- **Progress Indicators**: Success/failure indicators for commands

### Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Context Help**: F1 for context-sensitive help
- **Clear Labels**: Descriptive button and panel labels

## 🔄 Integration with CLI

The TUI is designed to work seamlessly with the CLI:
- **Same Commands**: TUI executes the same CLI commands
- **Shared Configuration**: Uses same configuration files
- **Compatible Output**: Generates same gamelist.xml files
- **Logging**: Uses same logging system

Users can switch between TUI and CLI as needed, with full compatibility between both interfaces.

## 📈 Performance Considerations

### Large Libraries
- **Scan Time**: Large libraries may take longer to scan
- **Scrape Time**: Many shows/movies increase processing time
- **Memory Usage**: Monitor system resources during operations

### Network Usage
- **API Calls**: Scraping requires network connectivity
- **Image Downloads**: Artwork downloads use bandwidth
- **Rate Limiting**: APIs may have rate limits

### Storage Requirements
- **Metadata**: JSON metadata files for each show/movie
- **Images**: Poster and artwork files
- **Logs**: Transaction and error logs

## 🚀 Future Enhancements

The TUI is actively developed with planned enhancements:
- **Batch Operations**: Process multiple libraries
- **Advanced Filtering**: Filter shows/movies by criteria
- **Custom Themes**: Additional theme options
- **Plugin System**: Extensible functionality
- **Mobile Support**: Touch-friendly interface

## 📞 Getting Help

### In-App Help
- **Comprehensive Help**: Press `?` for complete guide
- **Context Help**: Press F1 for element-specific help
- **Status Information**: Check system status with `v`

### External Resources
- **Documentation**: Check project documentation
- **Logs**: Review log files for detailed information
- **Community**: Join user community for support

The TUI provides comprehensive help and documentation to ensure users can effectively manage their MPV libraries and metadata scraping operations.
