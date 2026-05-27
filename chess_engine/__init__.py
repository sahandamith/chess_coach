"""
Chess Engine Analysis Module

This module provides classes for analyzing chess games using Stockfish engine.
"""

from .analyzer import ChessAnalyzer

# GUI module requires matplotlib - make it optional for web deployments
try:
    from .gui import ChessGui
    __all__ = ['ChessAnalyzer', 'ChessGui']
except ImportError:
    # GUI not available (e.g., in web environment without matplotlib)
    __all__ = ['ChessAnalyzer']
