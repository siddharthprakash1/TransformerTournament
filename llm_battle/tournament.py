"""
Tournament system for LLM Battle.
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
from datetime import datetime

from .agents.base_agent import BaseAgent
from .utils import save_game_record, visualize_game_stats


class Tournament:
    """Tournament system for running multiple games between LLM agents."""

    def __init__(
        self,
        agents: List[BaseAgent],
        num_games: int = 5,
        output_dir: str = "tournament_results",
        auto_restart: bool = True,
        restart_delay: float = 3.0
    ):
        """Initialize the tournament.

        Args:
            agents: List of agents to compete
            num_games: Number of games to play between each pair of agents
            output_dir: Directory to save results
            auto_restart: Whether to automatically restart games
            restart_delay: Delay between games in seconds
        """
        self.agents = agents
        self.num_games = num_games
        self.output_dir = output_dir
        self.auto_restart = auto_restart
        self.restart_delay = restart_delay

        self.results = []
        self.current_game_id = 0

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    async def run_match(self, agent1: BaseAgent, agent2: BaseAgent, game_ui_func) -> Dict[str, Any]:
        """Run a match between two agents.

        Args:
            agent1: First agent
            agent2: Second agent
            game_ui_func: Function to run the game UI

        Returns:
            Dictionary of match results
        """
        print(f"Starting match: {agent1.name} vs {agent2.name}")

        # Set up match tracking
        match_results = {
            "agent1": agent1.name,
            "agent2": agent2.name,
            "games": [],
            "agent1_wins": 0,
            "agent2_wins": 0,
            "ties": 0
        }

        # Set up the game UI
        from battle_ui import set_llm_names, set_tournament_config
        set_llm_names(agent1.name, agent2.name)
        set_tournament_config(1, self.num_games, self.auto_restart, self.restart_delay)

        # Create move function that will be called by the game UI
        async def get_llm_move(player, board_state):
            if player == 1:
                return await agent1.get_move(board_state)
            else:
                return await agent2.get_move(board_state)

        # Run the games
        for game_num in range(1, self.num_games + 1):
            self.current_game_id += 1
            print(f"Starting game {game_num}/{self.num_games}")

            # Update game number in UI
            set_tournament_config(game_num, self.num_games, self.auto_restart, self.restart_delay)

            # Track board and move history
            board_history = []
            moves_history = []

            # Define a callback to record game state
            def record_state_callback(board, last_move, current_player):
                board_history.append(board.copy())
                if last_move:
                    player, row, col = last_move
                    moves_history.append((player, row, col))

            # Run the game
            game_result = await game_ui_func(get_llm_move, record_state_callback)

            # Process game result
            winner = game_result.get("winner")
            final_board = game_result.get("final_board")

            # Record game
            game_record = {
                "game_id": self.current_game_id,
                "game_num": game_num,
                "winner": winner,
                "winner_name": agent1.name if winner == 1 else agent2.name if winner == 2 else "Tie",
                "final_score": game_result.get("final_score", (0, 0))
            }

            # Save detailed game record
            record_file = save_game_record(
                self.current_game_id,
                board_history,
                moves_history,
                winner,
                agent1.name,
                agent2.name,
                os.path.join(self.output_dir, "games")
            )
            game_record["record_file"] = record_file

            # Update match results
            match_results["games"].append(game_record)

            if winner == 1:
                match_results["agent1_wins"] += 1
                agent1.record_result("win")
                agent2.record_result("loss")
            elif winner == 2:
                match_results["agent2_wins"] += 1
                agent1.record_result("loss")
                agent2.record_result("win")
            else:
                match_results["ties"] += 1
                agent1.record_result("tie")
                agent2.record_result("tie")

            print(f"Game {game_num} result: {game_record['winner_name']} wins")

        # Save match results
        match_file = os.path.join(
            self.output_dir,
            f"match_{agent1.name}_vs_{agent2.name}_{int(time.time())}.json"
        )
        with open(match_file, "w") as f:
            json.dump(match_results, f, indent=2)

        print(f"Match complete: {agent1.name} {match_results['agent1_wins']} - {match_results['agent2_wins']} {agent2.name} (Ties: {match_results['ties']})")

        return match_results

    async def run_tournament(self, game_ui_func) -> Dict[str, Any]:
        """Run a full tournament between all agents.

        Args:
            game_ui_func: Function to run the game UI

        Returns:
            Dictionary of tournament results
        """
        tournament_start_time = time.time()
        tournament_id = int(tournament_start_time)

        print(f"Starting tournament with {len(self.agents)} agents")
        print(f"Each match will consist of {self.num_games} games")

        tournament_results = {
            "tournament_id": tournament_id,
            "timestamp": datetime.now().isoformat(),
            "agents": [agent.name for agent in self.agents],
            "num_games_per_match": self.num_games,
            "matches": []
        }

        # Run matches between all pairs of agents
        for i, agent1 in enumerate(self.agents):
            for j, agent2 in enumerate(self.agents):
                if i != j:  # Don't play against self
                    match_results = await self.run_match(agent1, agent2, game_ui_func)
                    tournament_results["matches"].append(match_results)

        # Calculate tournament statistics
        stats = self._calculate_tournament_stats()
        tournament_results["stats"] = stats

        # Save tournament results
        results_file = os.path.join(
            self.output_dir,
            f"tournament_{tournament_id}.json"
        )
        with open(results_file, "w") as f:
            json.dump(tournament_results, f, indent=2)

        # Generate visualization
        vis_file = os.path.join(
            self.output_dir,
            f"tournament_{tournament_id}_stats.png"
        )
        visualize_game_stats(stats, vis_file)

        print(f"Tournament complete! Results saved to {results_file}")
        print(f"Visualization saved to {vis_file}")

        return tournament_results

    def _calculate_tournament_stats(self) -> Dict[str, Any]:
        """Calculate statistics for the tournament.

        Returns:
            Dictionary of statistics
        """
        stats = {
            "agents": []
        }

        for agent in self.agents:
            agent_stats = agent.get_stats()
            stats["agents"].append(agent_stats)

        # Sort agents by win rate
        stats["agents"].sort(key=lambda x: x["win_rate"], reverse=True)

        return stats

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get the tournament leaderboard.

        Returns:
            List of agent statistics, sorted by win rate
        """
        stats = self._calculate_tournament_stats()
        return stats["agents"]


async def run_quick_battle(agent1: BaseAgent, agent2: BaseAgent, num_games: int = 1, game_ui_func=None) -> Dict[str, Any]:
    """Run a quick battle between two agents.

    Args:
        agent1: First agent
        agent2: Second agent
        num_games: Number of games to play
        game_ui_func: Function to run the game UI

    Returns:
        Dictionary of battle results
    """
    tournament = Tournament(
        agents=[agent1, agent2],
        num_games=num_games,
        auto_restart=True,
        restart_delay=2.0
    )

    match_results = await tournament.run_match(agent1, agent2, game_ui_func)
    return match_results