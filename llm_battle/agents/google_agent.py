"""
Agent that uses Google Gemini API to make decisions.
"""

import os
import json
import asyncio
import httpx
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from .base_agent import BaseAgent


class GoogleAgent(BaseAgent):
    """Agent that uses Google Gemini API to make decisions."""

    def __init__(
        self,
        name: str = "Google Gemini",
        model: str = "gemini-1.5-pro",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 3
    ):
        """Initialize the Google Gemini agent.

        Args:
            name: The display name of the agent
            model: The model to use (e.g., "gemini-1.5-pro")
            api_key: Google API key (if None, will try to get from env)
            temperature: Temperature for generation (0.0 to 1.0)
            max_retries: Maximum number of retries on API failure
        """
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key not provided and not found in environment")

        self.temperature = temperature
        self.max_retries = max_retries
        self.move_history = []  # Track move history for better context

    async def get_move(self, board_state: Dict[str, Any]) -> Tuple[int, int]:
        """Get the next move from Google Gemini.

        Args:
            board_state: Dictionary containing game state

        Returns:
            Tuple of (row, col) for the chosen move
        """
        board = board_state["board"]
        current_player = board_state["current_player"]
        valid_moves = board_state["valid_moves"]
        player1_count = board_state["player1_count"]
        player2_count = board_state["player2_count"]

        if not valid_moves:
            raise ValueError("No valid moves available")

        # Create a prompt for the LLM
        prompt = self._create_prompt(board, current_player, valid_moves, player1_count, player2_count)

        # Get response from Google API
        for attempt in range(self.max_retries):
            try:
                response = await self._call_google_api(prompt)
                move = self._parse_response(response, valid_moves)

                # Record this move in history
                self.move_history.append({
                    "player": current_player,
                    "move": move,
                    "board_state": np.array(board).tolist(),
                    "player1_count": player1_count,
                    "player2_count": player2_count
                })

                # Keep only the last 5 moves to avoid context getting too large
                if len(self.move_history) > 5:
                    self.move_history = self.move_history[-5:]

                return move
            except Exception as e:
                if attempt == self.max_retries - 1:
                    # If we've exhausted retries, fall back to a random move
                    print(f"Error getting move from Google after {self.max_retries} attempts: {e}")
                    return valid_moves[0]  # Just use the first valid move as fallback
                await asyncio.sleep(1)  # Wait before retrying

    def _create_prompt(
        self,
        board: List[List[int]],
        current_player: int,
        valid_moves: List[Tuple[int, int]],
        player1_count: int,
        player2_count: int
    ) -> str:
        """Create a prompt for the LLM with enhanced game understanding.

        Args:
            board: 2D array representing the board
            current_player: Current player (1 or 2)
            valid_moves: List of valid moves as (row, col) tuples
            player1_count: Number of player 1 pieces
            player2_count: Number of player 2 pieces

        Returns:
            Prompt string
        """
        # Create a more visual board representation with coordinates
        board_str = "  0 1 2 3 4 5 6 7\n"
        for r, row in enumerate(board):
            board_str += f"{r} "
            for cell in row:
                if cell == 0:
                    board_str += "· "  # Empty cell (middle dot for better visibility)
                elif cell == 1:
                    board_str += "X "  # Player 1
                else:
                    board_str += "O "  # Player 2
            board_str += "\n"

        # Format valid moves with potential impact analysis
        valid_moves_analysis = []
        for r, c in valid_moves:
            # Count how many pieces would be captured by this move
            captures = self._count_potential_captures(board, r, c, current_player)
            valid_moves_analysis.append(f"({r}, {c}) - would capture {captures} pieces")

        valid_moves_str = "\n".join(valid_moves_analysis)

        # Create move history context
        move_history_str = ""
        if self.move_history:
            move_history_str = "Recent moves:\n"
            for i, move_data in enumerate(self.move_history):
                player = move_data["player"]
                r, c = move_data["move"]
                p1_count = move_data["player1_count"]
                p2_count = move_data["player2_count"]
                move_history_str += f"{i+1}. Player {player} ({'X' if player == 1 else 'O'}) placed at ({r}, {c}). Score after: X:{p1_count}, O:{p2_count}\n"

        # Create the enhanced prompt
        prompt = f"""You are playing a strategic board game similar to Othello/Reversi with the following rules:

GAME RULES:
1. The game is played on an 8x8 grid.
2. Players take turns placing pieces on empty cells.
3. When you place a piece, you capture any ADJACENT opponent pieces (up, down, left, right).
4. Adjacent means sharing an edge, not just a corner.
5. The game ends when the board is full.
6. The player with the most pieces wins.

CAPTURE MECHANICS:
- When you place a piece at position (r,c), you capture any opponent pieces at (r+1,c), (r-1,c), (r,c+1), and (r,c-1).
- You do NOT capture diagonally adjacent pieces.
- You only capture pieces that are directly adjacent to your newly placed piece.

CURRENT GAME STATE:
Board (X=player1, O=player2, ·=empty):
{board_str}

You are player {current_player} ({'X' if current_player == 1 else 'O'}).
Current score: Player 1 (X): {player1_count}, Player 2 (O): {player2_count}

{move_history_str}

VALID MOVES (with capture analysis):
{valid_moves_str}

STRATEGY TIPS:
- Capturing more pieces is generally good
- Control the center of the board when possible
- Try to block your opponent from making high-capture moves
- Think ahead about how your move sets up future positions

INSTRUCTIONS:
1. Analyze the board carefully
2. Choose the move that maximizes your advantage
3. Return ONLY a JSON object with your chosen move, like this:
{{"row": 3, "col": 4, "reasoning": "This move captures 2 pieces and controls the center"}}

Your move:"""

        return prompt

    def _count_potential_captures(self, board, row, col, player):
        """Count how many pieces would be captured by placing at (row, col)."""
        captures = 0
        opponent = 3 - player  # If player is 1, opponent is 2, and vice versa

        # Check all four adjacent directions
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]  # right, down, left, up

        for dr, dc in directions:
            r, c = row + dr, col + dc
            if (0 <= r < len(board) and 0 <= c < len(board[0]) and
                board[r][c] == opponent):
                captures += 1

        return captures

    async def _call_google_api(self, prompt: str) -> str:
        """Call the Google Gemini API to get a response.

        Args:
            prompt: The prompt to send to the API

        Returns:
            The text response from the API
        """
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        data = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": 150
            }
        }

        # Create a new client for each request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=data
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")

            result = response.json()

            # Extract the text from the response
            try:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError) as e:
                raise Exception(f"Unexpected API response format: {e}")

    def _parse_response(self, response: str, valid_moves: List[Tuple[int, int]]) -> Tuple[int, int]:
        """Parse the LLM response to extract the move.

        Args:
            response: The text response from the LLM
            valid_moves: List of valid moves to validate against

        Returns:
            Tuple of (row, col) for the chosen move
        """
        try:
            # Try to find a JSON object in the response
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                move_data = json.loads(json_str)

                row = move_data.get("row")
                col = move_data.get("col")

                if row is not None and col is not None:
                    move = (int(row), int(col))

                    # Validate the move
                    if move in valid_moves:
                        # If there's reasoning, print it for debugging
                        reasoning = move_data.get("reasoning")
                        if reasoning:
                            print(f"Google reasoning: {reasoning}")
                        return move

            # If we couldn't parse a valid move, look for coordinates in the text
            import re
            coords = re.findall(r'\((\d+)\s*,\s*(\d+)\)', response)

            for r_str, c_str in coords:
                move = (int(r_str), int(c_str))
                if move in valid_moves:
                    return move

            # If all else fails, return the move with the most captures
            best_move = valid_moves[0]
            max_captures = -1

            for move in valid_moves:
                r, c = move
                captures = self._count_potential_captures(
                    np.array(self.move_history[-1]["board_state"]) if self.move_history else np.zeros((8, 8)),
                    r, c,
                    self.move_history[-1]["player"] if self.move_history else 1
                )

                if captures > max_captures:
                    max_captures = captures
                    best_move = move

            return best_move

        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response}")

            # Choose the move with the most captures as fallback
            if valid_moves:
                return valid_moves[0]
            else:
                raise ValueError("No valid moves available")