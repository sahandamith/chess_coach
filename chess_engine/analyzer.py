"""
Chess Game Analyzer

This module contains the ChessAnalyzer class for analyzing chess games using Stockfish.
"""

import chess
import chess.pgn
import chess.engine
import io
from .mistake_analyzer import MistakeAnalyzer


class ChessAnalyzer:
    """
    A class to analyze chess games using a UCI-compatible chess engine (e.g., Stockfish).
    """
    
    def __init__(self, engine_path, move_time_ms=500):
        """
        Initialize the ChessAnalyzer.
        
        Args:
            engine_path: Path to the chess engine executable (e.g., Stockfish)
            move_time_ms: Time limit per move analysis in milliseconds (default: 500)
        """
        self.engine_path = engine_path
        self.move_time_ms = move_time_ms
        self.engine = None
        self.analysis_results = []
        self.mistake_analyses = []  # Detailed mistake analyses
        self.game = None
        self.mistake_analyzer = None
    
    def open_engine(self):
        """Start the chess engine process."""
        if self.engine is None:
            self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
            self.mistake_analyzer = MistakeAnalyzer(self.engine)
            print("Chess engine started successfully.")
        return self.engine
    
    def close_engine(self):
        """Close the chess engine process."""
        if self.engine:
            self.engine.quit()
            self.engine = None
            print("Chess engine closed.")
    
    def load_pgn_string(self, pgn_string):
        """
        Load a chess game from a PGN string.
        
        Args:
            pgn_string: The PGN content as a string
            
        Returns:
            bool: True if game loaded successfully, False otherwise
        """
        try:
            pgn_io = io.StringIO(pgn_string)
            self.game = chess.pgn.read_game(pgn_io)
            if self.game is None:
                print("Error: Invalid PGN string.")
                return False
            print("Game loaded successfully from PGN string.")
            return True
        except Exception as e:
            print(f"An error occurred while loading PGN: {e}")
            return False
    
    def analyze_game(self):
        """
        Analyze the entire game and store the FEN and evaluation for each position.
        
        Returns:
            list: List of dictionaries containing 'fen' and 'eval' for each position
        """
        if not self.game:
            print("No game loaded. Please load a PGN first.")
            return []
        
        if not self.engine:
            self.open_engine()
        
        board = self.game.board()
        moves = list(self.game.mainline_moves())
        self.analysis_results = []

        print("Analyzing game... this may take a moment.")

        # For the starting position, evaluation is always 0.0
        self.analysis_results.append({
            'fen': board.fen(), 
            'eval': 0.0,
            'move_uci': None,
            'move_san': None,
            'delta_eval': None,
            'mistake_category': None,
            'is_white_move': None
        })

        # Analyze each subsequent position
        for i, move in enumerate(moves):
            # Get SAN before pushing the move (needs the board state before the move)
            move_san = board.san(move) if move in board.legal_moves else move.uci()
            
            board.push(move)
            # Get evaluation and best moves in one analysis to avoid re-analyzing later
            info = self.engine.analyse(board, chess.engine.Limit(time=self.move_time_ms / 1000.0), multipv=3)
            score = info[0]["score"].white().score(mate_score=10000)
            
            # Extract best moves for this position (to avoid re-analysis in mistake analysis)
            best_moves_data = []
            for move_info in info[:3]:
                if "pv" in move_info and len(move_info["pv"]) > 0:
                    first_move = move_info["pv"][0]
                    move_eval = move_info["score"].white().score(mate_score=10000)
                    
                    # Get full variation (principal variation) - use all moves to show complete tactical/positional reason
                    variation_moves = []
                    temp_board = board.copy()
                    for pv_move in move_info["pv"]:  # Use all moves in principal variation
                        if pv_move in temp_board.legal_moves:
                            variation_moves.append({
                                'move': pv_move,
                                'move_uci': pv_move.uci(),
                                'move_san': temp_board.san(pv_move)
                            })
                            temp_board.push(pv_move)
                        else:
                            break
                    
                    best_moves_data.append({
                        'move': first_move,
                        'move_uci': first_move.uci(),
                        'move_san': board.san(first_move),
                        'eval': move_eval,
                        'depth': move_info.get('depth', 0),
                        'variation': variation_moves
                    })
            
            # Calculate delta evaluation and categorize mistakes
            prev_eval = self.analysis_results[-1]['eval']
            delta_eval = None
            mistake_category = None
            is_white_move = (i % 2 == 0)  # Even indices (0, 2, 4...) are White's moves
            
            if isinstance(prev_eval, (int, float)) and isinstance(score, (int, float)):
                # Calculate delta for all moves
                delta_eval = score - prev_eval
                
                # Only categorize White's moves (when White's position gets worse)
                if is_white_move:
                    # Negative delta means White got worse (from White's perspective)
                    drop = -delta_eval  # Positive drop means White got worse
                    if drop > 200:
                        mistake_category = "Blunder"
                    elif drop > 100:
                        mistake_category = "Mistake"
                    elif drop > 50:
                        mistake_category = "Inaccuracy"
            
            self.analysis_results.append({
                'fen': board.fen(), 
                'eval': score if score is not None else "N/A",
                'move_uci': move.uci(),
                'move_san': move_san,
                'delta_eval': delta_eval,
                'mistake_category': mistake_category,
                'is_white_move': is_white_move,
                'best_moves': best_moves_data  # Store to avoid re-analysis
            })
            
            # Convert to chess move number for display (position i+1 corresponds to chess move (i+1)/2)
            chess_move = (i + 1) / 2.0
            if chess_move == int(chess_move):
                print(f"Analyzed move {int(chess_move)}/{len(moves)/2:.0f}", end='\r')
            else:
                print(f"Analyzing move {chess_move:.1f}...", end='\r')

        print("\nAnalysis complete.")
        return self.analysis_results
    
    def analyze_mistakes(self):
        """
        Analyze all mistakes in the game with detailed categorization.
        
        Returns:
            list: List of mistake analyses
        """
        if not self.analysis_results or len(self.analysis_results) < 2:
            print("No analysis results available. Run analyze_game() first.")
            return []
        
        if not self.mistake_analyzer:
            if not self.engine:
                self.open_engine()
            else:
                self.mistake_analyzer = MistakeAnalyzer(self.engine)
        
        print("Analyzing mistakes... this may take a moment.")
        self.mistake_analyses = []
        
        board = self.game.board()
        moves = list(self.game.mainline_moves())
        
        for i in range(1, len(self.analysis_results)):
            prev_eval = self.analysis_results[i-1]['eval']
            curr_eval = self.analysis_results[i]['eval']
            
            if not (isinstance(prev_eval, (int, float)) and isinstance(curr_eval, (int, float))):
                continue
            
            # Calculate evaluation drop (from White's perspective)
            change = curr_eval - prev_eval
            drop = -change  # Positive means White got worse
            
            # Only analyze White's mistakes (White's turn is when position index is even)
            # Position 0 = start (White to move), Position 1 = after White's move (Black to move)
            # Position 2 = after Black's move (White to move), etc.
            # So White moves at positions 0, 2, 4, 6... (even indices)
            is_white_move = (i - 1) % 2 == 0
            
            if not is_white_move:
                continue  # Skip Black's moves
            
            # Categorize by severity: Inaccuracy (>50), Mistake (>100), Blunder (>200)
            severity = None
            if drop > 200:
                severity = "Blunder"
            elif drop > 100:
                severity = "Mistake"
            elif drop > 50:
                severity = "Inaccuracy"
            
            # Analyze if it's an inaccuracy, mistake, or blunder
            if severity:
                # Reconstruct board to the position BEFORE the mistake (White's turn)
                temp_board = self.game.board()
                for j in range(i - 1):  # Go to position before the mistake
                    if j < len(moves):
                        temp_board.push(moves[j])
                
                # Get the move that was played
                if i - 1 < len(moves):
                    move_played = moves[i - 1]
                    
                    # Use stored best moves from initial analysis to avoid re-analysis
                    prev_result = self.analysis_results[i - 1] if i > 0 else None
                    best_moves_before = prev_result.get('best_moves', []) if prev_result else []
                    
                    # Get continuation moves from position AFTER mistake (stored in current result)
                    curr_result = self.analysis_results[i] if i < len(self.analysis_results) else None
                    continuation_moves = curr_result.get('best_moves', []) if curr_result else []
                    
                    # Analyze the mistake using stored evaluations and best moves
                    mistake_analysis = self.mistake_analyzer.analyze_mistake_position(
                        temp_board, prev_eval, curr_eval, move_played, best_moves_before
                    )
                    
                    # Add continuation moves (how Black exploits the mistake)
                    mistake_analysis['continuation_moves'] = continuation_moves
                    
                    # Create board after mistake for FEN
                    board_after_mistake = temp_board.copy()
                    board_after_mistake.push(move_played)
                    
                    mistake_analysis['position_index'] = i
                    mistake_analysis['position_before_fen'] = temp_board.fen()  # Position before mistake
                    mistake_analysis['position_after_fen'] = board_after_mistake.fen()  # Position after mistake
                    mistake_analysis['chess_move'] = self.position_to_chess_move(i)
                    mistake_analysis['phase'] = self.get_phase(mistake_analysis['chess_move'])
                    mistake_analysis['severity'] = severity  # Add severity label
                    mistake_analysis['move_played_obj'] = move_played  # Store the actual Move object for GUI use
                    
                    self.mistake_analyses.append(mistake_analysis)
                    
                    chess_move = self.position_to_chess_move(i)
                    print(f"Analyzed White's {severity.lower()} at move {chess_move:.1f}...", end='\r')
        
        print(f"\nFound {len(self.mistake_analyses)} mistakes.")
        return self.mistake_analyses
    
    def get_analysis_results(self):
        """Get the analysis results."""
        return self.analysis_results
    
    def get_mistake_analyses(self):
        """Get the detailed mistake analyses."""
        return self.mistake_analyses
    
    @staticmethod
    def position_to_chess_move(position_index):
        """
        Convert position index to chess move number (where move 1 = both sides played).
        
        Args:
            position_index: The position index (0 = start, 1 = after White's 1st, etc.)
            
        Returns:
            float: Chess move number (0.0, 0.5, 1.0, 1.5, 2.0, etc.)
        """
        return position_index / 2.0
    
    @staticmethod
    def get_phase(chess_move_number):
        """
        Determine game phase based on chess move number.
        
        Args:
            chess_move_number: The chess move number (where move 1 = both sides played)
            
        Returns:
            str: "Opening", "Middlegame", or "Endgame"
        """
        move_num = int(chess_move_number)
        if move_num <= 15:
            return "Opening"
        elif move_num <= 30:
            return "Middlegame"
        else:
            return "Endgame"
