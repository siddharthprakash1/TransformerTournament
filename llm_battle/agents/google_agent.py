"""
Agent that uses Google Gemini API to make decisions.
"""

import os
import json
import asyncio
import httpx
import random
import time
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from .base_agent import BaseAgent


class GoogleAgent(BaseAgent):
    """Agent that uses Google Gemini API to make decisions."""

    # Class-level variable to track last game completion time
    last_game_completion = 0
    cooldown_period = 30  # 30 seconds cooldown between games

    def __init__(
        self,
        name: str = "Google Gemini",
        model: str = "gemini-2.0-flash-thinking-exp-01-21",  # Updated model
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_retries: int = 3
    ):
        """Initialize the Google Gemini agent.

        Args:
            name: The display name of the agent
            model: The model to use (e.g., "gemini-2.0-flash-thinking-exp-01-21")
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
        self.last_api_call = 0  # Track last API call time
        self.first_move_of_game = True  # Track if this is the first move of a game

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

        # Check if this is a new game and enforce cooldown if needed
        current_time = time.time()
        if self.first_move_of_game:
            time_since_last_game = current_time - GoogleAgent.last_game_completion
            if time_since_last_game < GoogleAgent.cooldown_period:
                cooldown_needed = GoogleAgent.cooldown_period - time_since_last_game
                print(f"Cooling down between games: waiting {cooldown_needed:.2f}s")
                await asyncio.sleep(cooldown_needed)
            self.first_move_of_game = False

        # Check if this is the last move of the game
        empty_cells = sum(row.count(0) for row in board)
        if empty_cells <= 1:
            # Update the class-level last game completion time
            GoogleAgent.last_game_completion = time.time()
            self.first_move_of_game = True

        if not valid_moves:
            raise ValueError("No valid moves available")

        # Create a prompt for the LLM
        prompt = self._create_prompt(board, current_player, valid_moves, player1_count, player2_count)

        # Get response from Google API
        for attempt in range(self.max_retries):
            try:
                # Add more aggressive delay to avoid resource exhaustion
                current_time = asyncio.get_event_loop().time()
                time_since_last_call = current_time - self.last_api_call

                # Increased base delay with exponential backoff
                base_delay = 8.0  # Increased from 2 seconds
                current_delay = base_delay * (2 ** attempt)  # Exponential backoff

                if time_since_last_call < current_delay:
                    wait_time = current_delay - time_since_last_call
                    print(f"API rate limiting: waiting {wait_time:.2f}s before next call")
                    await asyncio.sleep(wait_time)

                response = await self._call_google_api(prompt)
                self.last_api_call = asyncio.get_event_loop().time()

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
                    # If we've exhausted retries, select the best strategic move
                    print(f"Error getting move from Google after {self.max_retries} attempts: {e}")
                    return self._get_best_strategic_move(board, valid_moves, current_player)

                # Add increasing delay between retries with much stronger backoff
                backoff_time = 15 * (2 ** attempt) + random.uniform(0, 5)  # Much stronger backoff
                print(f"API call failed, waiting {backoff_time:.2f}s before retry {attempt+1}/{self.max_retries}")
                await asyncio.sleep(backoff_time)

    def _get_best_strategic_move(self, board, valid_moves, current_player):
        """Get the best strategic move based on heuristics when API fails."""
        # Initialize score for each move
        move_scores = {}

        for r, c in valid_moves:
            score = 0

            # 1. Prioritize corners (highest value)
            if (r, c) in [(0, 0), (0, 7), (7, 0), (7, 7)]:
                score += 100

            # 2. Avoid cells adjacent to corners (they give opponent access to corners)
            elif (r, c) in [(0, 1), (1, 0), (1, 1), (0, 6), (1, 6), (1, 7),
                           (6, 0), (6, 1), (7, 1), (6, 6), (6, 7), (7, 6)]:
                score -= 50

            # 3. Edges are good
            elif r == 0 or r == 7 or c == 0 or c == 7:
                score += 30

            # 4. Count captures (important factor)
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

        # Format valid moves with potential impact analysis and enhanced strategic analysis
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
                position_notes.append("NEXT TO CORNER (risky, could give opponent access to corner)")

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
- Control the center of the board
- Avoid placing pieces next to corners (they give your opponent access to corners)
- Build a solid foundation for mid-game
- Focus on mobility rather than maximizing immediate captures
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

        # Create the enhanced prompt with improved strategic guidance
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
{{"row": 3, "col": 4, "reasoning": "This move captures 2 pieces and controls an important strategic position"}}

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

            # If all else fails, use strategic fallback
            return self._get_best_strategic_move(
                np.array(self.move_history[-1]["board_state"]) if self.move_history else np.zeros((8, 8)),
                valid_moves,
                self.move_history[-1]["player"] if self.move_history else 1
            )

        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            print(f"Response was: {response}")

            # Choose a strategic move as fallback
            if valid_moves:
                return self._get_best_strategic_move(
                    np.array(self.move_history[-1]["board_state"]) if self.move_history else np.zeros((8, 8)),
                    valid_moves,
                    self.move_history[-1]["player"] if self.move_history else 1
                )
            else:
                raise ValueError("No valid moves available")