# MPV Scraper Documentation

Welcome to the MPV Scraper documentation! This guide helps you find the right information for your needs.

## 📚 Documentation Structure

```mermaid
graph TD
    A[docs/] --> B[README.md]
    A --> C[user/]
    A --> D[technical/]
    A --> E[CHANGELOG.md]

    C --> F[QUICK_START.md]
    C --> G[FLOW_ASSESSMENT.md]

    D --> H[API_TROUBLESHOOTING.md]
    D --> I[PERFORMANCE.md]
    D --> J[error_handling.md]
    D --> K[DEVELOPMENT.md]
    D --> L[TESTING.md]
    D --> M[directory_scanner.md]
    D --> N[filename_parser.md]

    style A fill:#e3f2fd
    style C fill:#e8f5e8
    style D fill:#fff3e0
    style B fill:#f3e5f5
```

### 🎯 **For End Users**
- **[Quick Start Guide](user/QUICK_START.md)** - Get up and running in minutes
- **[Flow Assessment](user/FLOW_ASSESSMENT.md)** - Understanding how the scraper works

### 🔧 **For Developers & Advanced Users**
- **[API Troubleshooting](technical/API_TROUBLESHOOTING.md)** - Fix TVDB/TMDB authentication issues
- **[Performance Optimization](technical/PERFORMANCE.md)** - Optimize for large libraries
- **[Error Handling](technical/error_handling.md)** - Understanding retry logic and fallbacks
- **[Development Guide](technical/DEVELOPMENT.md)** - Contributing to the project
- **[Testing Guide](technical/TESTING.md)** - Running tests and quality assurance

### 🔍 **Technical Reference**
- **[Directory Scanner](technical/directory_scanner.md)** - How file discovery works
- **[Filename Parser](technical/filename_parser.md)** - Understanding filename parsing logic

## 🚀 **Quick Navigation**

### **Getting Started**
1. **New User?** → [Quick Start Guide](user/QUICK_START.md)
2. **API Issues?** → [API Troubleshooting](technical/API_TROUBLESHOOTING.md)
3. **Performance Problems?** → [Performance Guide](technical/PERFORMANCE.md)

### **Development**
1. **Contributing?** → [Development Guide](technical/DEVELOPMENT.md)
2. **Running Tests?** → [Testing Guide](technical/TESTING.md)
3. **Understanding Code?** → [Technical Reference](#technical-reference)

## 📖 **Documentation Summary**

| Document | Purpose | Audience |
|----------|---------|----------|
| [Quick Start](user/QUICK_START.md) | Basic setup and usage | End users |
| [Flow Assessment](user/FLOW_ASSESSMENT.md) | System overview | Users & developers |
| [API Troubleshooting](technical/API_TROUBLESHOOTING.md) | Fix authentication issues | Advanced users |
| [Performance](technical/PERFORMANCE.md) | Optimize large libraries | Advanced users |
| [Error Handling](technical/error_handling.md) | Understand fallbacks | Developers |
| [Development](technical/DEVELOPMENT.md) | Contributing guidelines | Developers |
| [Testing](technical/TESTING.md) | Quality assurance | Developers |
| [Directory Scanner](technical/directory_scanner.md) | File discovery logic | Developers |
| [Filename Parser](technical/filename_parser.md) | Parsing algorithms | Developers |

## 🎯 **Common Use Cases**

### **First Time Setup**
1. Read [Quick Start Guide](user/QUICK_START.md)
2. Set up API keys (see [API Troubleshooting](technical/API_TROUBLESHOOTING.md))
3. Run your first scrape

### **Troubleshooting**
1. Check [API Troubleshooting](technical/API_TROUBLESHOOTING.md) for authentication issues
2. Review [Error Handling](technical/error_handling.md) for fallback behavior
3. Consult [Performance Guide](technical/PERFORMANCE.md) for optimization

### **Development**
1. Read [Development Guide](technical/DEVELOPMENT.md) for contribution guidelines
2. Use [Testing Guide](technical/TESTING.md) for quality assurance
3. Reference technical docs for implementation details

## 📝 **Documentation Standards**

- **User docs**: Focus on practical usage and troubleshooting
- **Technical docs**: Include implementation details and code examples
- **All docs**: Use clear headings, code blocks, and examples
- **Cross-references**: Link between related documents

## 🤝 **Contributing to Documentation**

When updating documentation:
1. Place user-focused content in `/docs/user/`
2. Place technical content in `/docs/technical/`
3. Update this index when adding new documents
4. Use clear, concise language
5. Include practical examples

---

**Need help?** Start with the [Quick Start Guide](user/QUICK_START.md) or check the [API Troubleshooting](technical/API_TROUBLESHOOTING.md) for common issues.
