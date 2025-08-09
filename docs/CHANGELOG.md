## [Unreleased]

### Added
- `optimize-parallel`: `-y/--yes` to auto-confirm destructive actions
- `optimize`/`optimize-parallel`: `--regen-gamelist` to regenerate gamelist.xml after optimization
- Progress bar with ETA for `optimize-parallel`

### Changed
- Parallel optimizer now deletes originals incrementally (post-validation) and uses atomic replace to preserve filenames

### Docs
- Updated README and user/technical docs for new options and UI
# Documentation Changelog

## 2024-12-19 - Documentation Reorganization & Visual Enhancements

### 🗂️ **Structure Changes**
- **Reorganized documentation** into user-focused and technical sections
- **Created `/docs/user/`** for end-user documentation
- **Created `/docs/technical/`** for developer and advanced user documentation
- **Added comprehensive documentation index** at `/docs/README.md`

### 📁 **New Organization**

#### **User Documentation** (`/docs/user/`)
- `QUICK_START.md` - Basic setup and usage guide
- `FLOW_ASSESSMENT.md` - System overview and workflow

#### **Technical Documentation** (`/docs/technical/`)
- `API_TROUBLESHOOTING.md` - Fix TVDB/TMDB authentication issues
- `PERFORMANCE.md` - Optimize for large libraries
- `error_handling.md` - Understanding retry logic and fallbacks
- `DEVELOPMENT.md` - Contributing to the project
- `TESTING.md` - Running tests and quality assurance
- `directory_scanner.md` - File discovery implementation
- `filename_parser.md` - Filename parsing algorithms

### 🗑️ **Removed Files**
- `MPV_ENHANCEMENT_PROPOSAL.md` - Outdated, functionality now implemented
- `MPV_ENHANCEMENT_GUIDE.md` - Outdated, covered in main documentation
- `DOCUMENTATION_SUMMARY.md` - Replaced with better index

### 🔗 **Updated References**
- **Fixed all internal links** to point to correct documentation locations
- **Updated README.md** to reference new documentation structure
- **Added cross-references** between related documents

### 📊 **Visual Enhancements**
- **Added Mermaid diagrams** to all major documentation files
- **System Architecture diagram** in root README.md
- **Workflow Overview flowchart** in root README.md
- **Documentation Structure diagram** in docs/README.md
- **Quick Start flowchart** in user/QUICK_START.md
- **Complete Workflow diagram** in user/FLOW_ASSESSMENT.md
- **Troubleshooting flowchart** in technical/API_TROUBLESHOOTING.md
- **Performance Optimization flowchart** in technical/PERFORMANCE.md
- **Error Handling flowchart** in technical/error_handling.md
- **Directory Scanning flowchart** in technical/directory_scanner.md
- **Filename Parsing flowchart** in technical/filename_parser.md

### 📋 **Benefits**
- **Clear separation** between user and technical content
- **Better navigation** with comprehensive index
- **Reduced duplication** by removing outdated files
- **Improved readability** with organized structure
- **Easier maintenance** with logical grouping
- **Visual clarity** with diagrams and flowcharts
- **Better user experience** with visual guides

### 🎯 **Navigation**
- **New users**: Start with `/docs/user/QUICK_START.md`
- **Troubleshooting**: Check `/docs/technical/API_TROUBLESHOOTING.md`
- **Performance**: See `/docs/technical/PERFORMANCE.md`
- **Development**: Read `/docs/technical/DEVELOPMENT.md`
- **Overview**: Browse `/docs/README.md` for complete guide

### 📝 **README Structure Decision**
- **Root README.md**: Project overview, installation, architecture diagrams
- **docs/README.md**: Documentation navigation and structure
- **Rationale**: Clear separation of concerns - landing page vs. internal navigation
