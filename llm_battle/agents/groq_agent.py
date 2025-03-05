"""
Agent that uses Groq API to make decisions.
"""

import os
import json
import asyncio
import httpx
import random
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from .base_agent import BaseAgent


class GroqAgent(BaseAgent):
    """Agent that uses Groq API to make decisions."""

    def __init__(
        self,
        name: str = "Groq llama",
        model: str = "llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 3
    ):
        """Initialize the Groq agent.

        Args:
            name: The display name of the agent
            model: The model to use (e.g., "llama-3.3-70b-versatile")
            api_key: Groq API key (if None, will try to get from env)
            temperature: Temperature for generation (0.0 to 1.0)
            max_retries: Maximum number of retries on API failure
        """
        super().__init__(name)
        self.model = model
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not provided and not found in environment")

        self.temperature = temperature
        self.max_retries = max_retries
        self.move_history = []  # Track move history for better context
        self.last_api_call = 0  # Track last API call time

    async def get_move(self, board_state: Dict[str, Any]) -> Tuple[int, int]:
        """Get the next move from Groq.

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

        # Get response from Groq API
        for attempt in range(self.max_retries):
            try:
                # Add delay to avoid resource exhaustion (min 3 seconds between calls)
                current_time = asyncio.get_event_loop().time()
                time_since_last_call = current_time - self.last_api_call
                if time_since_last_call < 3 + (attempt * 1.5):  # Add more delay with each retry
                    await asyncio.sleep(3 + (attempt * 1.5) - time_since_last_call)

                response = await self._call_groq_api(prompt)
                self.last_api_call = asyncio.get_event_loop().time()

                move = self._parse_response(response, valid_moves, board, current_player)

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
                    # If we've exhausted retries, use a strategic fallback instead of random
                    print(f"Error getting move from Groq after {self.max_retries} attempts: {e}")
                    return self._get_strategic_fallback_move(board, valid_moves, current_player)
                
                # Add increasing backoff with jitter
                backoff_time = 2 * (attempt + 1) + random.uniform(0, 2)
                print(f"API call failed, waiting {backoff_time:.2f}s before retry {attempt+1}/{self.max_retries}")
                await asyncio.sleep(backoff_time)

    def _get_strategic_fallback_move(self, board, valid_moves, current_player):
        """Get a strategic move based on heuristics when API fails."""
        if not valid_moves:
            return None
            
        # Initialize score for each move
        move_scores = {}

        for r, c in valid_moves:
            score = 0
            
            # 1. Prioritize corners (highest value)
            if (r, c) in [(0, 0), (0, 7), (7, 0), (7, 7)]:
                score += 100
                
            # 2. Avoid cells adjacent to corners
            elif (r, c) in [(0, 1), (1, 0), (1, 1), (0, 6), (1, 6), (1, 7),
                           (6, 0), (6, 1), (7, 1), (6, 6), (6, 7), (7, 6)]:
                score -= 50
                
            # 3. Edges are good
            elif r == 0 or r == 7 or c == 0 or c == 7:
                score += 30
                
            # 4. Captures are important
            captures = self._count_potential_captures(board, r, c, current_player)
            score += captures * 20
            
            # 5. Control center in early game
            empty_count = sum(row.count(0) for row in board)
            if empty_count > 40:  # Early game
                center_distance = abs(r - 3.5) + abs(c - 3.5)
                if center_distance < 2:
                    score += 15
                    
            move_scores[(r, c)] = score
            
        # Return move with highest score, or random if tied
        best_score = max(move_scores.values())
        best_moves = [move for move, score in move_scores.items() if score == best_score]
        return random.choice(best_moves)

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

        # Format valid moves with potential impact analysis and strategic value
        valid_moves_analysis = []
        for r, c in valid_moves:
            # Count how many pieces would be captured by this move
            captures = self._count_potential_captures(board, r, c, current_player)
            
            # Position analysis
            position_notes = []
            if (r, c) in [(0, 0), (0, 7), (7, 0), (7, 7)]:
                position_notes.append("CORNER (excellent strategic position)")
            elif r == 0 or r == 7 or c == 0 or c == 7:
                position_notes.append("EDGE (good strategic position)")
            elif (r, c) in [(0, 1), (1, 0), (1, 1), (0, 6), (1, 6), (1, 7),
                          (6, 0), (6, 1), (7, 1), (6, 6), (6, 7), (7, 6)]:
                position_notes.append("NEXT TO CORNER (risky, gives opponent access to corner)")
                
            center_distance = abs(r - 3.5) + abs(c - 3.5)
            if center_distance <= 1:
                position_notes.append("CENTER (good for early control)")
                
            position_analysis = ", ".join(position_notes) if position_notes else ""
            
            valid_moves_analysis.append(f"({r}, {c}) - would capture {captures} pieces {position_analysis}")

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

        # Determine game phase for strategic guidance
        total_pieces = player1_count + player2_count
        empty_spaces = 64 - total_pieces
        
        if total_pieces < 20:
            phase = "OPENING PHASE"
            strategy_tips = """
- Focus on controlling the center of the board
- Avoid placing pieces next to corners (they give your opponent access to corners)
- Build a solid foundation for mid-game
- Mobility is more important than maximizing immediate captures
"""
        elif empty_spaces < 15:
            phase = "ENDGAME PHASE"
            strategy_tips = """
- Focus on maximizing piece count
- Secure corners and edges
- Look for moves that lead to multiple captures
- Consider how the board will be filled by the end of the game
"""
        else:
            phase = "MIDGAME PHASE"
            strategy_tips = """
- Balance between position and captures
- Limit your opponent's mobility
- Secure corners when possible
- Build strong edge formations
- Avoid giving away corner access
"""

        # Create the enhanced prompt with advanced strategy
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
Game phase: {phase}

{move_history_str}

VALID MOVES (with capture analysis):
{valid_moves_str}

ADVANCED STRATEGY TIPS:
{strategy_tips}

SPECIAL POSITIONS:
- CORNERS (0,0), (0,7), (7,0), (7,7): Most valuable positions, should be prioritized
- EDGES: Second most valuable, hard for opponent to capture
- NEAR CORNERS: Avoid placing pieces adjacent to empty corners, as they give opponent access to corners
- CENTER CONTROL: Important in early game to establish position

INSTRUCTIONS:
1. Analyze the board carefully
2. Choose the move that maximizes your long-term advantage
3. Return ONLY a JSON object with your chosen move, like this:
{{"row": 3, "col": 4, "reasoning": "This move captures 2 pieces and controls a strategic position"}}

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

    async def _call_groq_api(self, prompt: str) -> str:
        """Call the Groq API to get a response.

        Args:
            prompt: The prompt to send to the API

        Returns:
            The text response from the API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 150
        }

        # Create a new client for each request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data
            )

            if response.status_code != 200:
                raise Exception(f"API error: {response.status_code} - {response.text}")

            result = response.json()
            return result["choices"][0]["message"]["content"]

    def _parse_response(self, response: str, valid_moves: List[Tuple[int, int]], board=None, current_player=None) -> Tuple[int, int]:
        """Parse the LLM response to extract the move.

        Args:
            response: The text response from the LLM
            valid_moves: List of valid moves to validate against
            board: Current board state (optional)
            current_player: Current player (1 or 2) (optional)

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
                            print(f"Groq reasoning: {reasoning}")
                        return move

            # If we couldn't parse a valid move, look for coordinates in the text
            import re
            coords = re.findall(r'\((\d+)\s*,\s*(\d+)\)', response)

            for r_str, c_str in coords:
                move = (int(r_str), int(c_str))
                if move in valid_moves:
                    return move

            # If all else fails, use the strategic fallback
            if board is not None and current_player is not None:
                return self._get_strategic_fallback_move(board, valid_moves, current_player)
            else:
                # Fall back to original capture-based selection
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

            # Use strategic fallback if available
            if board is not None and current_player is not None:
                return self._get_strategic_fallback_move(board, valid_moves, current_player)
            # Otherwise use first valid move
            elif valid_moves:
                return valid_moves[0]
            else:
                raise ValueError("No valid moves available")