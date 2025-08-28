# Overview

PingeraCLI is a Python command-line interface tool that provides a beautiful terminal experience for network monitoring through the Pingera SDK. Built with modern CLI frameworks Typer and Rich, it offers colorful, formatted output and intuitive command-line interactions. The tool is distributed as a pip package and serves as a wrapper around the Pingera SDK for network monitoring capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## CLI Framework Architecture
The application is built on Typer, a modern Python framework for building CLI applications. Typer provides automatic help generation, type validation, and shell completion. The main entry point (`main.py`) defines the core Typer app with rich markup support and structured command organization.

## Output and Presentation Layer
Rich library powers the visual presentation layer, providing:
- Colorful terminal output with custom themes
- Formatted panels, tables, and text styling
- Console abstraction for both standard output and error streams
- ASCII art banners and visual elements for enhanced user experience

## Configuration Management
The application implements a hierarchical configuration system:
- Environment variables for API keys and sensitive data
- JSON-based configuration files stored in XDG-compliant directories (`~/.config/pingera-cli/`)
- Default configuration fallbacks for all settings
- Support for customizable base URLs, timeouts, output formats, and display preferences

## Command Structure
Commands are organized using a modular pattern:
- Base command class provides common functionality and validation
- Command modules inherit from the base class for consistent behavior
- API key validation and SDK availability checks are centralized
- Error handling and console output are standardized across commands

## SDK Integration Layer
The CLI acts as a wrapper around the Pingera SDK:
- Runtime validation ensures the SDK is installed and importable
- API authentication is handled through environment variables
- SDK functionality is exposed through CLI commands with enhanced formatting

## Package Distribution
The application is packaged for PyPI distribution:
- setuptools-based packaging with dynamic version management
- Cross-platform support (Windows, macOS, Linux)
- Python 3.7+ compatibility
- Entry points for both `pingera` and `pingera-cli` commands

# External Dependencies

## Core CLI Dependencies
- **Typer**: Modern CLI framework with automatic help generation and type validation
- **Rich**: Terminal formatting library for colored output, tables, and panels
- **Click**: Low-level CLI utilities (dependency of Typer)

## Pingera Integration
- **Pingera SDK**: Core networking and monitoring functionality (runtime dependency)

## Development Dependencies
- **pytest**: Testing framework with coverage support
- **Black**: Code formatting
- **Flake8**: Code linting
- **MyPy**: Static type checking

## System Integration
- **Environment Variables**: API key management through `PINGERA_API_KEY`
- **XDG Base Directory**: Configuration file storage following Linux standards
- **Cross-platform File System**: Configuration management across Windows, macOS, and Linux