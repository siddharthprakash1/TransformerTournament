"""
Utility functions for LLM Battle.
"""

import os
import json
import time
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from datetime import datetime


def load_env_variables():
    """Load environment variables from .env file."""
    # Try to load from .env file
    load_dotenv()

    # Check if API keys are available
    groq_key = os.environ.get("GROQ_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if not groq_key:
        print("Warning: GROQ_API_KEY not found in environment variables.")
        print("Groq agent will fall back to random moves.")

    if not google_key:
        print("Warning: GOOGLE_API_KEY not found in environment variables.")
        print("Google agent will fall back to random moves.")

    if not groq_key and not google_key:
        print("No API keys found. Consider using run_battle_demo.py instead.")


def convert_numpy(obj):
    """Convert numpy arrays to lists recursively."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list) or isinstance(obj, tuple):
        return [convert_numpy(i) for i in obj]
    else:
        return obj


def save_game_record(
    game_id: int,
    board_history: List[List[List[int]]],
    moves_history: List[tuple],
    winner: Optional[int],
    agent1_name: str,
    agent2_name: str,
    output_dir: str = "game_records"
) -> str:
    """Save a record of a game.

    Args:
        game_id: Unique identifier for the game
        board_history: List of board states
        moves_history: List of moves made
        winner: Winner of the game (1, 2, or None for tie)
        agent1_name: Name of agent 1
        agent2_name: Name of agent 2
        output_dir: Directory to save the record

    Returns:
        Path to the saved record file
    """
    os.makedirs(output_dir, exist_ok=True)

    record = {
        "game_id": game_id,
        "timestamp": time.time(),
        "agent1": agent1_name,
        "agent2": agent2_name,
        "winner": winner,
        "winner_name": agent1_name if winner == 1 else agent2_name if winner == 2 else "Tie",
        "board_history": board_history,
        "moves_history": moves_history
    }

    # Convert any NumPy arrays to lists before saving
    record_converted = convert_numpy(record)

    filename = os.path.join(output_dir, f"game_{game_id}.json")
    with open(filename, "w") as f:
        json.dump(record_converted, f, indent=2)

    return filename


def visualize_game_stats(stats: Dict[str, Any], output_file: str = "tournament_stats.png"):
    """Visualize game statistics.

    Args:
        stats: Dictionary of statistics
        output_file: File to save the visualization
    """
    # Extract agent names and win rates
    agent_names = [agent["name"] for agent in stats["agents"]]
    win_rates = [agent["win_rate"] for agent in stats["agents"]]
    wins = [agent["wins"] for agent in stats["agents"]]
    losses = [agent["losses"] for agent in stats["agents"]]
    ties = [agent["ties"] for agent in stats["agents"]]

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))

    # Plot win rates
    bars = ax1.bar(agent_names, win_rates, color='skyblue')
    ax1.set_title('Win Rates')
    ax1.set_ylabel('Win Rate')
    ax1.set_ylim(0, 1.0)

    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{height:.2f}', ha='center', va='bottom')

    # Plot wins, losses, ties
    x = np.arange(len(agent_names))
    width = 0.25

    ax2.bar(x - width, wins, width, label='Wins', color='green')
    ax2.bar(x, losses, width, label='Losses', color='red')
    ax2.bar(x + width, ties, width, label='Ties', color='gray')

    ax2.set_title('Game Results')
    ax2.set_xticks(x)
    ax2.set_xticklabels(agent_names)
    ax2.legend()

    # Add title and adjust layout
    fig.suptitle('Tournament Results', fontsize=16)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    # Save figure
    plt.savefig(output_file)
    plt.close()