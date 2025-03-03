# Neural Nexus

<div align="center">
  <img src="https://via.placeholder.com/200x200?text=Neural+Nexus" alt="Neural Nexus Logo">
  
  ![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
  ![Pygame](https://img.shields.io/badge/pygame-2.1.0-green.svg)
  ![License](https://img.shields.io/badge/license-MIT-orange.svg)
  
  **A strategic battle framework pitting LLMs against each other on the game board**
</div>

## 🎮 Overview

Neural Nexus creates an arena where different Large Language Models compete in a strategic board game similar to Othello/Reversi. Watch as AI agents make tactical decisions in real-time, with beautiful visualizations and tournament tracking.

<div align="center">
  <img src="https://via.placeholder.com/800x400?text=Game+Screenshot" alt="Neural Nexus Game Screenshot">
</div>

## ✨ Key Features

<div align="center">
  <table>
    <tr>
      <td align="center"><img src="https://via.placeholder.com/60x60?text=🎲" width="60px"><br><b>Game Engine</b><br>Robust rules enforcement</td>
      <td align="center"><img src="https://via.placeholder.com/60x60?text=🖥️" width="60px"><br><b>Visual UI</b><br>Animated battles</td>
      <td align="center"><img src="https://via.placeholder.com/60x60?text=🤖" width="60px"><br><b>LLM Agents</b><br>Multiple AI implementations</td>
    </tr>
    <tr>
      <td align="center"><img src="https://via.placeholder.com/60x60?text=🏆" width="60px"><br><b>Tournaments</b><br>Multi-game competitions</td>
      <td align="center"><img src="https://via.placeholder.com/60x60?text=📊" width="60px"><br><b>Statistics</b><br>Performance tracking</td>
      <td align="center"><img src="https://via.placeholder.com/60x60?text=🔌" width="60px"><br><b>Extensible</b><br>Easily add new agents</td>
    </tr>
  </table>
</div>

## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph Core["Core Components"]
        A[Game Engine] --> B[Board State]
        A --> C[Rules Enforcement]
        A --> D[Move Validation]
    end
    
    subgraph UI["Battle UI"]
        E[Pygame Interface] --> F[Board Visualization]
        E --> G[Animations]
        E --> H[User Interaction]
    end
    
    subgraph Agents["Agent System"]
        I[Base Agent] --- J[Random Agent]
        I --- K[Smart Random]
        I --- L[Groq Agent]
        I --- M[Google Agent]
    end
    
    subgraph Tournament["Tournament System"]
        N[Tournament Manager] --> O[Game Manager]
        N --> P[Statistics Tracking]
    end
    
    subgraph Utils["Utility Services"]
        Q[API Key Management]
        R[Error Handling]
    end
    
    Core <--> UI
    Core <--> Agents
    Core <--> Tournament
    Agents <--> Utils
```
## 🎮 Game Mechanics
```mermaid
graph TD
    A[Initial Setup] --> B[Players Take Turns]
    B --> C{Valid Move?}
    C -->|Yes| D[Place Piece]
    C -->|No| E[Skip Turn]
    D --> F[Capture Pieces]
    F --> G{Game Over?}
    E --> G
    G -->|Yes| H[Determine Winner]
    G -->|No| B
```


Capture Mechanism

## 🤖 LLM Agents
```mermaid
graph LR
    A[Base Agent] --> B[Random Agent]
    A --> C[Smart Random Agent]
    A --> D[Groq Agent]
    A --> E[Google Agent]
    
    B --> F[Random Moves]
    C --> G[Strategic Randomness]
    D --> H[Groq API]
    E --> I[Gemini API]
    
    H --> J[LLM Decision]
    I --> J
    J --> K[Move Selection]
```



```bash
# Clone repository
git clone https://github.com/yourusername/neural-nexus.git
cd neural-nexus

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

