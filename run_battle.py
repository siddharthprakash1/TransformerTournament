#!/usr/bin/env python3
"""
LLM Battle - Main script to run battles between language models.
"""

import os
import sys
import asyncio
import argparse
from typing import List, Dict, Any, Optional
import pygame
import numpy as np

# Add the parent directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_battle.agents.base_agent import BaseAgent
from llm_battle.agents.random_agent import RandomAgent
from llm_battle.agents.groq_agent import GroqAgent
from llm_battle.agents.google_agent import GoogleAgent
from llm_battle.tournament import Tournament, run_quick_battle
from llm_battle.utils import load_env_variables, visualize_game_stats

# Import the battle UI
import battle_ui


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run battles between language models")
    
    # Main mode selection
    parser.add_argument(
        "--mode", 
        choices=["quick", "tournament", "demo"], 
        default="quick",
        help="Battle mode: quick (1v1), tournament (all vs all), or demo (random agents)"
    )
    
    # Agent selection
    parser.add_argument(
        "--agent1", 
        default="groq",
        choices=["groq", "google", "random"],
        help="First agent type"
    )
    parser.add_argument(
        "--agent2", 
        default="google",
        choices=["groq", "google", "random"],
        help="Second agent type"
    )
    
    # Agent names
    parser.add_argument(
        "--name1", 
        default=None,
        help="Custom name for agent 1"
    )
    parser.add_argument(
        "--name2", 
        default=None,
        help="Custom name for agent 2"
    )
    
    # Tournament settings
    parser.add_argument(
        "--games", 
        type=int, 
        default=3,
        help="Number of games per match"
    )
    parser.add_argument(
        "--delay", 
        type=float, 
        default=3.0,
        help="Delay between games in seconds"
    )
    parser.add_argument(
        "--auto-restart", 
        action="store_true",
        help="Automatically restart games"
    )
    
    # Model settings
    parser.add_argument(
        "--groq-model", 
        default="llama-3.3-70b-versatile",
        help="Groq model to use"
    )
    parser.add_argument(
        "--google-model", 
        default="gemini-1.5-pro",
        help="Google model to use"
    )
    parser.add_argument(
        "--temperature", 
        type=float, 
        default=0.2,
        help="Temperature for LLM generation"
    )
    
    # Output settings
    parser.add_argument(
        "--output-dir", 
        default="tournament_results",
        help="Directory to save results"
    )
    
    return parser.parse_args()


def create_agent(agent_type: str, name: Optional[str] = None, args=None) -> BaseAgent:
    """Create an agent based on the specified type.
    
    Args:
        agent_type: Type of agent to create
        name: Custom name for the agent
        args: Command line arguments
        
    Returns:
        Instantiated agent
    """
    if agent_type == "groq":
        default_name = "Groq Claude"
        agent_name = name or default_name
        return GroqAgent(
            name=agent_name,
            model=args.groq_model,
            temperature=args.temperature
        )
    elif agent_type == "google":
        default_name = "Google Gemini"
        agent_name = name or default_name
        return GoogleAgent(
            name=agent_name,
            model=args.google_model,
            temperature=args.temperature
        )
    elif agent_type == "random":
        default_name = "Random Agent"
        agent_name = name or default_name
        return RandomAgent(name=agent_name)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


async def run_game_with_callback(get_llm_move_func, state_callback=None):
    """Run a game with the battle UI and record state.
    
    Args:
        get_llm_move_func: Function to get moves from LLMs
        state_callback: Callback to record game state
        
    Returns:
        Game result dictionary
    """
    # Initialize game state
    battle_ui.init_game()
    board = np.zeros((battle_ui.GRID_SIZE, battle_ui.GRID_SIZE), dtype=int)
    last_move = None
    current_player = 1
    
    # Wrap the get_llm_move_func to record state
    async def wrapped_get_llm_move(player, board_state):
        nonlocal board, last_move, current_player
        
        # Record state before move
        board = np.array(board_state["board"])
        current_player = player
        if state_callback:
            state_callback(board, last_move, current_player)
        
        # Get the move
        row, col = await get_llm_move_func(player, board_state)
        
        # Record the move
        last_move = (player, row, col)
        
        return row, col
    
    # Run the game
    continue_tournament = await battle_ui.run_game_loop(wrapped_get_llm_move)
    
    # Get final state
    player1_count, player2_count = battle_ui.count_pieces()
    winner = None
    if player1_count > player2_count:
        winner = 1
    elif player2_count > player1_count:
        winner = 2
    
    # Return result
    return {
        "winner": winner,
        "final_board": board.tolist(),
        "final_score": (player1_count, player2_count),
        "continue_tournament": continue_tournament
    }


async def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()
    
    # Load environment variables
    load_env_variables()
    
    print("🎮 LLM Battle System 🎮")
    print("=======================")
    
    if args.mode == "demo":
        print("Running demo mode with random agents")
        agent1 = RandomAgent(name="Random Agent 1")
        agent2 = RandomAgent(name="Random Agent 2")
        
        result = await run_quick_battle(
            agent1, 
            agent2, 
            num_games=args.games, 
            game_ui_func=run_game_with_callback
        )
        
        print("Demo complete!")
        return
    
    elif args.mode == "quick":
        print(f"Running quick battle: {args.agent1} vs {args.agent2}")
        
        # Create agents
        agent1 = create_agent(args.agent1, args.name1, args)
        agent2 = create_agent(args.agent2, args.name2, args)
        
        # Run battle
        result = await run_quick_battle(
            agent1, 
            agent2, 
            num_games=args.games, 
            game_ui_func=run_game_with_callback
        )
        
        print("Battle complete!")
        print(f"Results: {agent1.name} {result['agent1_wins']} - {result['agent2_wins']} {agent2.name} (Ties: {result['ties']})")
        
    elif args.mode == "tournament":
        print("Running tournament mode")
        
        # Create all agents
        agents = []
        
        if args.agent1 == "all" or args.agent1 == "groq":
            agents.append(create_agent("groq", args.name1, args))
        
        if args.agent2 == "all" or args.agent2 == "google":
            agents.append(create_agent("google", args.name2, args))
        
        if args.agent1 == "all" or args.agent1 == "random":
            agents.append(RandomAgent(name="Random Agent"))
        
        # If no agents were specified, use all available
        if not agents:
            print("No agents specified, using all available")
            agents = [
                create_agent("groq", args.name1, args),
                create_agent("google", args.name2, args),
                RandomAgent(name="Random Agent")
            ]
        
        # Create tournament
        tournament = Tournament(
            agents=agents,
            num_games=args.games,
            output_dir=args.output_dir,
            auto_restart=args.auto_restart,
            restart_delay=args.delay
        )
        
        # Run tournament
        results = await tournament.run_tournament(run_game_with_callback)
        
        # Display leaderboard
        print("\nTournament Leaderboard:")
        print("======================")
        
        for i, agent_stats in enumerate(tournament.get_leaderboard()):
            print(f"{i+1}. {agent_stats['name']}: {agent_stats['wins']}W {agent_stats['losses']}L {agent_stats['ties']}T (Win Rate: {agent_stats['win_rate']:.2f})")
    
    print("\nThanks for using LLM Battle!")


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())