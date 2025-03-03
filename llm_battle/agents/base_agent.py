"""
Base class for all LLM agents.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import asyncio


class BaseAgent(ABC):
    """Abstract base class that all LLM agents must implement."""
    
    def __init__(self, name: str):
        """Initialize the agent with a name.
        
        Args:
            name: The display name of the agent
        """
        self.name = name
        self.wins = 0
        self.losses = 0
        self.ties = 0
        self.games_played = 0
    
    @abstractmethod
    async def get_move(self, board_state: Dict[str, Any]) -> Tuple[int, int]:
        """Get the next move from the agent.
        
        Args:
            board_state: Dictionary containing:
                - board: 2D numpy array of the current board
                - current_player: The current player (1 or 2)
                - valid_moves: List of valid (row, col) tuples
                - player1_count: Number of player 1 pieces
                - player2_count: Number of player 2 pieces
        
        Returns:
            Tuple of (row, col) for the chosen move
        """
        pass
    
    def record_result(self, result: str) -> None:
        """Record the result of a game.
        
        Args:
            result: "win", "loss", or "tie"
        """
        self.games_played += 1
        if result == "win":
            self.wins += 1
        elif result == "loss":
            self.losses += 1
        elif result == "tie":
            self.ties += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get the agent's statistics.
        
        Returns:
            Dictionary of statistics
        """
        win_rate = self.wins / self.games_played if self.games_played > 0 else 0
        return {
            "name": self.name,
            "wins": self.wins,
            "losses": self.losses,
            "ties": self.ties,
            "games_played": self.games_played,
            "win_rate": win_rate
        }
    
    def __str__(self) -> str:
        """String representation of the agent."""
        stats = self.get_stats()
        return f"{self.name} (W: {stats['wins']}, L: {stats['losses']}, T: {stats['ties']}, WR: {stats['win_rate']:.2f})"