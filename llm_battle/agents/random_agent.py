"""
Random agent that makes random valid moves.
"""

import random
from typing import Dict, List, Tuple, Any
import asyncio
from .base_agent import BaseAgent


class RandomAgent(BaseAgent):
    """Agent that makes random valid moves. Useful as a baseline."""
    
    def __init__(self, name: str = "Random Agent"):
        """Initialize the random agent.
        
        Args:
            name: The display name of the agent
        """
        super().__init__(name)
    
    async def get_move(self, board_state: Dict[str, Any]) -> Tuple[int, int]:
        """Get a random valid move.
        
        Args:
            board_state: Dictionary containing game state
        
        Returns:
            Tuple of (row, col) for the chosen move
        """
        # Add a small delay to simulate "thinking"
        await asyncio.sleep(0.5)
        
        valid_moves = board_state["valid_moves"]
        if not valid_moves:
            raise ValueError("No valid moves available")
        
        return random.choice(valid_moves)