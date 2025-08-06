# MPV Enhancement Implementation Guide

## Quick Start

### 1. Create the System Configuration
Copy the provided `es_systems_mpv.cfg` to your KNULLI device:
```bash
# Copy to your SD card
cp es_systems_mpv.cfg /Volumes/BLANK/System/configs/emulationstation/
```

### 2. Test the Enhancement
1. **Restart KNULLI** to load the new system configuration
2. **Verify MPV appears** as a proper EmulationStation system
3. **Test basic playback** - files should still play normally
4. **Check for metadata support** - gamelist.xml files should now be recognized

### 3. Generate Metadata
Use the MPV scraper to generate rich metadata:
```bash
# Run the scraper on your MPV directory
python -m mpv_scraper.cli run /Volumes/BLANK/roms/mpv
```

### 4. Verify Results
- Check that `gamelist.xml` files are created
- Verify images are downloaded and placed correctly
- Confirm metadata displays in the EmulationStation UI

## Troubleshooting

### MPV System Not Appearing
- Ensure `es_systems_mpv.cfg` is in the correct location
- Check file permissions (should be readable)
- Restart KNULLI completely

### Metadata Not Displaying
- Verify gamelist.xml files are created
- Check image paths are correct
- Ensure XML encoding is UTF-8
- Test with a simple file first

### Playback Issues
- Verify the `emulatorlauncher` command works
- Check that MPV is still accessible
- Test with different video formats

## Advanced Configuration

### Custom Themes
Create a custom theme for MPV:
```
/System/configs/emulationstation/themes/mpv/
├── theme.xml
├── background.jpg
└── assets/
    ├── logo.png
    └── icon.png
```

### Custom Scraping
Modify the scraper configuration:
```python
# In your scraper settings
TVDB_API_KEY = "your_api_key"
TMDB_API_KEY = "your_api_key"
```

### Performance Optimization
For large media libraries:
- Use SSD storage for faster access
- Optimize image sizes (keep under 600KB)
- Consider using compressed video formats

## Rollback Plan
If issues occur, you can easily revert:
1. **Remove the system config**: Delete `es_systems_mpv.cfg`
2. **Restart KNULLI**: System will return to basic MPV mode
3. **Clean up files**: Remove generated gamelist.xml files if desired

## Support
- Check the main documentation for detailed information
- Test with a small subset of files first
- Report issues with specific error messages
- Provide feedback on the enhancement proposal

This enhancement transforms KNULLI's basic MPV player into a full-featured media management system while maintaining backward compatibility and performance.
