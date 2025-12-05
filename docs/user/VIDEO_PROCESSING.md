# Video Processing

## Screenshot Timing

The scraper uses intelligent timing to avoid capturing frames during intro sequences or logo displays. When generating fallback screenshots:

- **Videos longer than 2 minutes**: Captures at the specified percentage (default 25%), but ensures at least 30 seconds have elapsed to skip intro sequences.
- **Videos shorter than 2 minutes**: Skips forward by at least 30 seconds or 40% of the video duration, whichever is less, to avoid intro/logo frames.

This ensures that screenshots capture actual episode content rather than title cards or theme song sequences. Guide

The MPV Scraper includes powerful video processing capabilities to optimize your media for handheld device playback, convert formats, and crop videos for specific aspect ratios.

## 🎯 Video Optimization

### Overview

The video optimizer automatically detects and fixes problematic video files that cause playback issues on handheld devices:

- **Slow frame rates** and **audio sync problems**
- **AI-upscaled content** with complex encoding
- **High bitrate files** that overwhelm device capabilities
- **Incompatible codecs** (HEVC/H.265 on older devices)

### Smart Problem Detection

The optimizer analyzes each video file and assigns an optimization score (0.0-1.0):

| **Issue** | **Impact** | **Detection** |
|-----------|------------|---------------|
| **HEVC/H.265 codec** | CPU intensive decoding | Codec analysis |
| **10-bit color depth** | 2x more processing | Pixel format detection |
| **High bitrate** (>5 Mbps) | Memory/bandwidth stress | Bitrate calculation |
| **AI-upscaled resolution** | Complex encoding | Resolution analysis |
| **Large file size** (>1GB) | Storage/loading issues | File size check |

### Optimization Results

**Before vs After:**
- **File Size**: 1GB → ~200MB (80% reduction)
- **Codec**: HEVC → H.264 (better compatibility)
- **Resolution**: 1440x1080 → 960x720 (handheld-friendly)
- **Bitrate**: 6 Mbps → 1.5 Mbps (smooth playback)
- **Color Depth**: 10-bit → 8-bit (reduced processing)

## 🚀 Parallel Processing

### Performance Comparison

| **Method** | **Time for 192 Episodes** | **Speedup** |
|------------|---------------------------|-------------|
| **Sequential** | ~10.5 hours | 1x |
| **Parallel (6 workers)** | ~1.7 hours | **6.2x faster** |

### Hardware Acceleration

The optimizer uses hardware acceleration when available:

- **macOS**: `h264_videotoolbox` (hardware encoder)
- **Automatic Fallback**: Software encoding if hardware fails
- **Multi-threading**: Uses all available CPU cores

## 📋 Commands

### Analyze Videos

```bash
# Analyze videos for handheld compatibility
python -m mpv_scraper.cli analyze /path/to/videos

# Dry run to see what would be analyzed
python -m mpv_scraper.cli analyze /path/to/videos --dry-run
```

**Example Output:**
```
Found 192 video files to analyze
Problematic file: Teenage Mutant Ninja Turtles - 01x01 - Turtle Tracks.mp4
  Issues: HEVC/H.265 codec (CPU intensive), 10-bit color depth, High bitrate (6.0 Mbps)
  Optimization score: 1.00
```

### Optimize Videos

#### Sequential Optimization
```bash
# Basic optimization
python -m mpv_scraper.cli optimize /path/to/videos --preset handheld

# Compatibility mode (maximum compatibility)
python -m mpv_scraper.cli optimize /path/to/videos --preset compatibility

# Dry run
python -m mpv_scraper.cli optimize /path/to/videos --dry-run
```

#### Parallel Optimization (Recommended)
```bash
# Parallel optimization (6x faster!)
python -m mpv_scraper.cli optimize-parallel /path/to/videos --preset handheld

# Custom worker count
python -m mpv_scraper.cli optimize-parallel /path/to/videos --workers 8

# Replace originals (save disk space) with auto-confirm and progress bar
python -m mpv_scraper.cli optimize-parallel /path/to/videos --replace-originals -y

# Dry run with space savings estimate
python -m mpv_scraper.cli optimize-parallel /path/to/videos --replace-originals --dry-run

# Regenerate gamelist.xml after optimization completes
python -m mpv_scraper.cli optimize-parallel /path/to/videos --replace-originals -y --regen-gamelist
```

### Optimization Presets

#### Handheld Preset
- **Target Codec**: H.264 High
- **Resolution**: 1280x720 (720p)
- **Bitrate**: 1.5 Mbps
- **Quality**: CRF 23 (good quality)
- **Use Case**: Balanced quality and compatibility

#### Compatibility Preset
- **Target Codec**: H.264 Baseline
- **Resolution**: 854x480 (480p)
- **Bitrate**: 1.0 Mbps
- **Quality**: CRF 28 (smaller files)
- **Use Case**: Maximum compatibility, smaller files

## 🔄 Video Format Conversion

### MKV to MP4 Conversion

Convert MKV files to web-optimized MP4 format with significant file size reduction.

#### Convert with Subtitles
```bash
# Convert MKV to MP4 with soft subtitles
python -m mpv_scraper.cli convert-with-subs /path/to/mkv/files

# Dry run
python -m mpv_scraper.cli convert-with-subs /path/to/mkv/files --dry-run
```

#### Convert without Subtitles
```bash
# Convert MKV to MP4 without subtitles
python -m mpv_scraper.cli convert-without-subs /path/to/mkv/files

# Dry run
python -m mpv_scraper.cli convert-without-subs /path/to/mkv/files --dry-run
```

### Conversion Presets

Both presets provide:
- **Web optimization** (`movflags +faststart`)
- **H.264 video codec** (`libx264`)
- **AAC audio** (copied from source)
- **~2/3 file size reduction**

#### With Subtitles Preset
- **Subtitle Codec**: `mov_text` (soft subtitles)
- **Tune**: `film` (optimized for film content)
- **Use Case**: Preserve subtitle tracks

#### Without Subtitles Preset
- **Subtitle Codec**: None (subtitles removed)
- **Tune**: `animation` (optimized for animation)
- **Use Case**: Smaller files, no subtitle support needed

## ✂️ Video Cropping

### 4:3 Aspect Ratio Cropping

Automatically crop 16:9 videos with letterboxing to 4:3 aspect ratio for display on 4:3 devices.

```bash
# Crop videos to 4:3 aspect ratio
python -m mpv_scraper.cli crop /path/to/videos --quality medium

# High quality cropping
python -m mpv_scraper.cli crop /path/to/videos --quality high

# Fast cropping (lower quality)
python -m mpv_scraper.cli crop /path/to/videos --quality fast

# Dry run
python -m mpv_scraper.cli crop /path/to/videos --dry-run
```

### How It Works

1. **Letterboxing Detection**: Uses FFprobe to detect black bars
2. **Crop Calculation**: Calculates optimal crop area for 4:3 content
3. **FFmpeg Processing**: Applies crop filter with hardware acceleration
4. **Output**: Creates `_4x3` suffixed files

### Quality Options

| **Quality** | **Encoding Speed** | **File Size** | **Use Case** |
|-------------|-------------------|---------------|--------------|
| **Fast** | Very fast | Larger | Quick processing |
| **Medium** | Balanced | Medium | Default choice |
| **High** | Slower | Smaller | Best quality |

## 💾 Space Management

### Replace Originals Feature

The `--replace-originals` flag automatically removes original files after successful optimization:

```bash
# Optimize and replace originals (save disk space)
python -m mpv_scraper.cli optimize-parallel /path/to/videos --replace-originals
```

**Safety Features:**
- **Verification**: Only removes originals if optimized file is valid (>1MB)
- **Warning**: Clear warnings about permanent deletion
- **Space Calculation**: Shows estimated space savings
- **Dry Run**: Test with `--dry-run` first

**Example Output:**
```
⚠️  WARNING: --replace-originals flag is enabled!
   Original files will be PERMANENTLY DELETED after successful optimization.
   This action cannot be undone!
   Estimated space savings: 123.4GB
```

### Manual Space Management

```bash
# Remove original files for already optimized episodes
find /path/to/videos -name "*_optimized.mp4" -size +1M | while read optimized; do
    original="${optimized%_optimized.mp4}.mp4"
    if [ -f "$original" ]; then
        rm "$original"
        echo "Removed: $original"
    fi
done
```

## 🎬 Real-World Examples

### Optimizing AI-Upscaled Content

**Problem**: TMNT episodes are AI-upscaled with HEVC/H.265, causing playback issues.

```bash
# 1. Analyze the problem
python -m mpv_scraper.cli analyze "/Volumes/SD/roms/mpv/Teenage Mutant Ninja Turtles (1987)"

# 2. Parallel optimization with space savings
python -m mpv_scraper.cli optimize-parallel "/Volumes/SD/roms/mpv/Teenage Mutant Ninja Turtles (1987)" --replace-originals
```

**Results**:
- **192 episodes** processed in ~1.7 hours (vs 10.5 hours sequential)
- **80% space savings** (1GB → 200MB per episode)
- **Perfect playback** on handheld devices

### Converting MKV Collections

**Problem**: Large MKV files need web-optimized MP4 format.

```bash
# Convert with subtitles preserved
python -m mpv_scraper.cli convert-with-subs "/path/to/mkv/collection"

# Convert without subtitles (smaller files)
python -m mpv_scraper.cli convert-without-subs "/path/to/mkv/collection"
```

**Results**:
- **~2/3 file size reduction**
- **Web-optimized** for streaming
- **Maintained quality** with H.264 encoding

### Cropping for 4:3 Displays

**Problem**: 16:9 Scooby-Doo episodes have letterboxing for 4:3 display.

```bash
# Crop to 4:3 aspect ratio
python -m mpv_scraper.cli crop "/path/to/scooby-doo" --quality medium
```

**Results**:
- **Full-screen display** on 4:3 devices
- **No black bars** in final output
- **Maintained aspect ratio** of original content

## 🔧 Troubleshooting

### Common Issues

#### "No space left on device"
```bash
# Check available space
df -h /path/to/videos

# Use replace-originals to save space
python -m mpv_scraper.cli optimize-parallel /path/to/videos --replace-originals
```

#### "Conversion failed"
```bash
# Check FFmpeg installation
ffmpeg -version

# Try compatibility preset
python -m mpv_scraper.cli optimize-parallel /path/to/videos --preset compatibility
```

#### "Hardware acceleration failed"
```bash
# Check hardware support
ffmpeg -encoders | grep videotoolbox

# Automatic fallback to software encoding is built-in
```

### Performance Optimization

#### For Large Collections
```bash
# Use maximum workers (adjust based on CPU cores)
python -m mpv_scraper.cli optimize-parallel /path/to/videos --workers 8

# Monitor progress
watch -n 30 'find /path/to/videos -name "*_optimized.mp4" -size +1M | wc -l'
```

#### For Limited Disk Space
```bash
# Always use replace-originals for space-constrained devices
python -m mpv_scraper.cli optimize-parallel /path/to/videos --replace-originals

# Monitor disk usage
watch -n 30 'df -h /path/to/videos'
```

## 📊 Performance Benchmarks

### Processing Speed

| **Method** | **Time per Episode** | **192 Episodes** |
|------------|---------------------|------------------|
| **Sequential Software** | ~3-5 minutes | ~10.5 hours |
| **Sequential Hardware** | ~1-2 minutes | ~4 hours |
| **Parallel (6 workers)** | ~1-2 minutes | ~1.7 hours |

### File Size Reduction

| **Content Type** | **Original Size** | **Optimized Size** | **Reduction** |
|------------------|-------------------|-------------------|---------------|
| **AI-upscaled HEVC** | 1GB | 200MB | 80% |
| **Standard H.264** | 500MB | 150MB | 70% |
| **MKV with subs** | 800MB | 250MB | 69% |

### Hardware vs Software

| **Platform** | **Hardware Encoder** | **Speedup** |
|--------------|---------------------|-------------|
| **macOS** | h264_videotoolbox | 2-3x faster |
| **Linux** | VAAPI (if available) | 1.5-2x faster |
| **Windows** | NVENC (if available) | 2-3x faster |
