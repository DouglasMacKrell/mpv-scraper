# Performance Optimization Guide

This guide provides tips and best practices for optimizing the MPV Metadata Scraper for large libraries and improving overall performance.

## Understanding Performance Factors

### Network Operations
The scraper's performance is primarily limited by:
- **API Rate Limits**: TVDB and TMDB have rate limits that affect speed
- **Image Downloads**: Large artwork files can slow down processing
- **Network Latency**: Internet connection speed affects download times

### Local Operations
- **File I/O**: Writing images and XML files
- **Image Processing**: Resizing and compressing artwork
- **XML Generation**: Creating gamelist.xml files

## Optimization Strategies

### 1. **Large Library Management**

#### Break Down Large Libraries
For libraries with 100+ shows or movies, consider processing in batches:

```bash
# Process shows first
python -m mpv_scraper.cli scrape /mpv --shows-only

# Then process movies
python -m mpv_scraper.cli scrape /mpv --movies-only

# Or process specific directories
python -m mpv_scraper.cli scrape /mpv/Shows/A
python -m mpv_scraper.cli scrape /mpv/Shows/B
```

#### Use Selective Scraping
```bash
# Scrape only specific shows
python -m mpv_scraper.cli scrape /mpv --show "Darkwing Duck"

# Skip already processed items
python -m mpv_scraper.cli scrape /mpv --skip-existing
```

### 2. **Network Optimization**

#### Optimal Timing
- **Off-Peak Hours**: Run during low-traffic periods (early morning, late night)
- **Weekend Processing**: Less network congestion
- **Batch Processing**: Process multiple libraries during the same session

#### Connection Optimization
```bash
# Use faster DNS servers
export DNS_SERVERS="8.8.8.8,1.1.1.1"

# Increase connection timeouts if needed
export REQUESTS_TIMEOUT="30"
```

### 3. **Caching Strategy**

#### Leverage Built-in Caching
The scraper automatically caches:
- **API Responses**: TVDB and TMDB data cached locally
- **Image Downloads**: Prevents re-downloading existing artwork
- **Metadata**: Scrape cache preserves processed data

#### Cache Management
```bash
# Check cache size
ls -lh ~/.mpv_scraper_cache.json

# Clear cache if needed (forces fresh downloads)
rm ~/.mpv_scraper_cache.json

# Backup cache before clearing
cp ~/.mpv_scraper_cache.json ~/.mpv_scraper_cache.json.backup
```

### 4. **Image Processing Optimization**

#### Image Size Limits
The scraper automatically optimizes images:
- **Maximum Width**: 500px (reduces file size)
- **Maximum File Size**: 600KB (meets EmulationStation requirements)
- **Format**: PNG with compression

#### Custom Image Optimization
For manual optimization:
```bash
# Use ImageMagick for batch optimization
find /mpv -name "*.png" -exec convert {} -resize 500x -quality 85 {} \;

# Or use Pillow for custom processing
python -c "
from PIL import Image
import os
for root, dirs, files in os.walk('/mpv'):
    for file in files:
        if file.endswith('.png'):
            path = os.path.join(root, file)
            with Image.open(path) as img:
                if img.width > 500:
                    img.thumbnail((500, 500), Image.Resampling.LANCZOS)
                    img.save(path, optimize=True)
"
```

### 5. **Memory Management**

#### Large Library Considerations
- **Process in Chunks**: Don't process entire 1000+ item libraries at once
- **Monitor Memory**: Watch system resources during processing
- **Restart Between Batches**: Clear memory between large operations

#### Python Memory Optimization
```bash
# Use Python with garbage collection
python -X dev -m mpv_scraper.cli run /mpv

# Monitor memory usage
python -c "
import psutil
import os
process = psutil.Process(os.getpid())
print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.1f} MB')
"
```

## Performance Monitoring

### Built-in Progress Tracking
The scraper provides progress feedback:
```bash
# Watch progress in real-time
python -m mpv_scraper.cli run /mpv 2>&1 | tee scraping.log

# Monitor with timestamps
python -m mpv_scraper.cli run /mpv 2>&1 | while IFS= read -r line; do
    echo "$(date '+%H:%M:%S') $line"
done
```

### Performance Metrics
Track these metrics for optimization:
- **Items per minute**: Processing speed
- **Download success rate**: Network reliability
- **Cache hit rate**: Efficiency of caching
- **Memory usage**: System resource utilization

## Advanced Optimization Techniques

### 1. **Parallel Processing (Future Enhancement)**
While not currently supported, future versions may include:
- **Concurrent API calls**: Multiple requests simultaneously
- **Parallel image downloads**: Download multiple images at once
- **Background processing**: Non-blocking operations

### 2. **Custom Workflows**
```bash
# Create a custom processing script
#!/bin/bash
# process_library.sh

LIBRARY_PATH="/mpv"
LOG_FILE="scraping_$(date +%Y%m%d_%H%M%S).log"

echo "Starting library processing at $(date)" | tee -a "$LOG_FILE"

# Process in batches
for letter in {A..Z}; do
    echo "Processing shows starting with $letter..." | tee -a "$LOG_FILE"
    python -m mpv_scraper.cli scrape "$LIBRARY_PATH" --show-prefix "$letter" 2>&1 | tee -a "$LOG_FILE"
    sleep 30  # Rate limiting pause
done

echo "Library processing completed at $(date)" | tee -a "$LOG_FILE"
```

### 3. **Scheduled Processing**
```bash
# Add to crontab for automated processing
# Process library every Sunday at 2 AM
0 2 * * 0 cd /path/to/mpv-scraper && source .venv/bin/activate && python -m mpv_scraper.cli run /mpv >> /var/log/mpv-scraper.log 2>&1
```

## Troubleshooting Performance Issues

### Common Performance Problems

#### 1. **Slow Processing**
**Symptoms**: Very slow progress, long delays
**Solutions**:
- Check network speed: `speedtest-cli`
- Verify API rate limits aren't being hit
- Process smaller batches
- Use faster internet connection

#### 2. **High Memory Usage**
**Symptoms**: System becomes slow, out of memory errors
**Solutions**:
- Process in smaller chunks
- Restart between large operations
- Monitor with `htop` or `top`
- Increase system swap space

#### 3. **Failed Downloads**
**Symptoms**: Many placeholder images, network errors
**Solutions**:
- Check network stability
- Verify firewall settings
- Use different DNS servers
- Try during off-peak hours

### Performance Testing

#### Benchmark Your Setup
```bash
# Test processing speed
time python -m mpv_scraper.cli run /mpv

# Test network performance
curl -w "@-" -o /dev/null -s "https://api.thetvdb.com" <<'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF
```

## Best Practices Summary

1. **Start Small**: Test with a few items before processing large libraries
2. **Monitor Resources**: Watch CPU, memory, and network usage
3. **Use Caching**: Leverage built-in caching mechanisms
4. **Process in Batches**: Break large libraries into manageable chunks
5. **Optimize Timing**: Run during off-peak hours
6. **Backup Data**: Always backup before large operations
7. **Monitor Logs**: Keep track of performance metrics

## Future Performance Enhancements

The scraper team is working on:
- **Parallel processing**: Concurrent API calls and downloads
- **Progress bars**: Visual progress indicators
- **Resume capability**: Continue interrupted operations
- **Smart batching**: Automatic optimal batch sizing
- **Performance profiling**: Built-in performance analysis

---

**Need help with performance issues?** Check the [API Troubleshooting Guide](API_TROUBLESHOOTING.md) for network-related problems or the [main troubleshooting section](QUICK_START.md#troubleshooting) in the Quick Start Guide.
