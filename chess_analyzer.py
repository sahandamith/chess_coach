"""
Chess Analyzer - Main Entry Point

This is the main script that uses the chess_engine module to analyze chess games.
"""

import os
from chess_engine import ChessAnalyzer, ChessGui

# --- Configuration ---
STOCKFISH_PATH = r"C:\Users\sahan\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe"

PGN_DATA = """
[Event "Live Chess"]
[Site "Chess.com"]
[Date "2023.03.06"]
[Round "?"]
[White "sd_sahan"]
[Black "Suptoo"]
[Result "0-1"]
[TimeControl "60"]
[WhiteElo "1683"]
[BlackElo "1698"]
[Termination "Suptoo won on time"]
[ECO "B01"]
[EndTime "14:20:53 GMT+0000"]
[Link "https://www.chess.com/game/live/71851422455?move=0"]

1. e4 d5 2. exd5 Qxd5 3. d4 Qd8 4. c4 Nf6 5. Nc3 e6 6. Bd3 Be7 7. Qc2 O-O 8. Nf3
g6 9. O-O Ne8 10. Bh6 Ng7 11. Rfe1 Bf6 12. Ne5 Nd7 13. f4 Re8 14. Re2 Nf5 15.
Bg5 Bxg5 16. fxg5 Qxg5 17. Bxf5 exf5 18. Nxd7 Bxd7 19. Rae1 Rxe2 20. Rxe2 Rf8
21. Nd5 c6 22. Ne3 Re8 23. Qb3 b5 24. cxb5 cxb5 25. a3 a6 26. d5 Re4 27. Kf2 f4
28. Nf1 Rxe2+ 29. Kxe2 Qe5+ 30. Kf2 Bf5 31. Nd2 Qd4+ 32. Ke1 Kg7 33. h3 h5 34.
g4 hxg4 35. hxg4 Bxg4 36. Nf3 Qe4+ 37. Kf2 Qe3+ 38. Qxe3 fxe3+ 39. Kxe3 Bd7 40.
Kd4 f5 41. Ne5 Bc8 42. Nc6 Bd7 43. Ne7 g5 44. d6 g4 45. Kd5 g3 46. Nxf5+ Bxf5
47. Ke5 Bd7 48. Kf4 g2 49. Ke5 g1=Q 50. a4 Qb1 0-1
"""


def main():
    """Main function to run the chess analyzer."""
    if not os.path.exists(STOCKFISH_PATH):
        print(f"Error: Stockfish engine not found at '{STOCKFISH_PATH}'.")
        print("Please download Stockfish and update the STOCKFISH_PATH variable.")
        return

    analyzer = None
    try:
        # Create analyzer instance
        analyzer = ChessAnalyzer(STOCKFISH_PATH, move_time_ms=500)
        
        # Load PGN
        if not analyzer.load_pgn_string(PGN_DATA):
            print("Failed to load PGN data.")
            return
        
        # Analyze game
        analysis_data = analyzer.analyze_game()
        
        if analysis_data:
            # Analyze mistakes
            print("\nAnalyzing mistakes...")
            mistake_analyses = analyzer.analyze_mistakes()
            
            # Launch GUI
            app = ChessGui(analysis_data, mistake_analyses)
            app.mainloop()
        else:
            print("No analysis data generated.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if analyzer:
            analyzer.close_engine()


if __name__ == "__main__":
    main()
