# Changelog

All notable changes to the ComfyUI Queue Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive integration test suite
- Performance benchmarking tools
- Detailed user documentation
- API documentation with examples
- Installation guide for all platforms
- Example scripts and use cases

### Changed
- Improved error handling throughout the system
- Enhanced API response formats
- Better database schema design
- Optimized performance for large queues

### Fixed
- Archive functionality for running workflows
- API response format consistency
- Database connection handling
- Memory usage optimization

## [1.0.0] - 2025-09-27

### Added
- Initial release of ComfyUI Queue Manager
- Persistent queue storage with SQLite database
- Web-based management interface
- REST API for programmatic access
- Workflow status tracking (pending, running, completed, failed)
- Archive system for completed workflows
- Import/export functionality
- Advanced filtering and search capabilities
- Real-time status updates
- Queue control (pause/resume)
- Bulk operations support
- Error handling and logging
- Performance monitoring
- Configuration management

### Core Features
- **Queue Management**: Automatic workflow tracking with persistent storage
- **Web Interface**: Modern, responsive interface accessible from ComfyUI menu
- **Filtering & Search**: Advanced filtering by status, date, name, and full-text search
- **Archive System**: Archive old workflows to keep queue clean
- **Import/Export**: Share workflows and backup queue configuration
- **REST API**: Complete programmatic access to all features
- **Real-time Monitoring**: Track workflow execution status and performance

### Technical Implementation
- SQLite database for reliable data persistence
- Flask web server for API and interface
- Modular architecture with clear separation of concerns
- Comprehensive error handling and logging
- Performance optimization for large queues
- Thread-safe operations for concurrent access

### Documentation
- User guide with complete usage instructions
- Installation guide for all platforms
- API documentation with examples
- Example scripts and automation tools
- Troubleshooting guide

### Testing
- Unit tests for all core components
- Integration tests for end-to-end workflows
- Performance tests for large queues
- API tests for all endpoints
- Error handling tests

## Development History

### Pre-1.0.0 Development Phases

#### Phase 1: Core Infrastructure (2025-09-01 to 2025-09-10)
- Database design and implementation
- Basic queue service functionality
- Initial web interface
- ComfyUI integration

#### Phase 2: Advanced Features (2025-09-11 to 2025-09-20)
- Archive system implementation
- Import/export functionality
- Advanced filtering and search
- API development

#### Phase 3: Polish and Testing (2025-09-21 to 2025-09-27)
- Comprehensive testing suite
- Documentation creation
- Performance optimization
- Bug fixes and improvements

## Migration Guide

### From Development Versions

If you were using development versions of the Queue Manager:

1. **Backup your data**: Export your queue before updating
2. **Update installation**: Pull latest changes and restart ComfyUI
3. **Database migration**: The system will automatically migrate your database
4. **Verify functionality**: Test that all features work as expected

### Breaking Changes

#### v1.0.0
- Initial stable release - no breaking changes from development versions
- Database schema finalized
- API endpoints stabilized

## Known Issues

### v1.0.0
- Large queues (10,000+ items) may experience slower filtering performance
- WebSocket support not yet implemented (polling used for real-time updates)
- Multi-user support not available in this version

### Workarounds
- **Performance**: Enable auto-archiving to keep active queue size manageable
- **Real-time Updates**: Interface polls every 5 seconds for updates
- **Multi-user**: Each ComfyUI instance maintains its own queue

## Upgrade Instructions

### From v1.0.0 to Future Versions

When new versions are released:

1. **Backup**: Always export your queue data before upgrading
2. **Update**: Pull latest changes or download new release
3. **Dependencies**: Run `pip install -r requirements.txt --upgrade`
4. **Restart**: Restart ComfyUI completely
5. **Verify**: Check that all features work correctly

## Support and Feedback

### Reporting Issues
- Use GitHub Issues for bug reports
- Include system information and error logs
- Provide steps to reproduce the issue

### Feature Requests
- Use GitHub Discussions for feature requests
- Describe the use case and expected behavior
- Consider contributing if you can implement the feature

### Community
- Join the ComfyUI Discord for community support
- Share your workflows and automation scripts
- Help other users with questions

## Acknowledgments

### Contributors
- Abdullah Ceylan - Initial development and maintenance
- ComfyUI Community - Feedback and testing
- Beta testers - Early feedback and bug reports

### Dependencies
- Flask - Web framework for API and interface
- SQLite - Database for persistent storage
- ComfyUI - The amazing tool this extends

### Inspiration
- ComfyUI's built-in queue system
- Community requests for persistent queues
- Workflow management best practices

---

For more information, see the [documentation](docs/) or visit the [GitHub repository](https://github.com/abdullahceylan/ac-comfyui-queue-manager).