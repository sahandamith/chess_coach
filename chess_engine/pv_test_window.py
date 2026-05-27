"""
PV Analysis Test Window

A simple test window to show PV moves and analysis for a single mistake.
This helps isolate and fix the analysis logic before applying it to all moves.
"""

import chess
import tkinter as tk
from tkinter import font
from typing import Optional, Dict, Any, List

from .mistake_analyzer import get_piece_counts, get_piece_count_differences


class PVAnalysisTestWindow(tk.Toplevel):
    """Simple test window to show PV analysis for one mistake."""
    
    def __init__(self, parent, mistake_analysis):
        super().__init__(parent)
        self.mistake_analysis = mistake_analysis
        self.current_pv_index = -1  # -1 = before mistake, 0 = after mistake, 1+ = PV moves
        
        self.title("PV Analysis Test - Single Mistake")
        self.geometry("1400x900")
        self.configure(bg="#2C3E50")
        
        self.colors = {
            "light": "#F0D9B5",
            "dark": "#B58863",
            "bg": "#2C3E50",
            "card": "#34495E",
            "text": "#ECF0F1",
            "accent": "#3498DB",
            "positive": "#2ECC71",
            "negative": "#E74C3C"
        }
        
        self.piece_symbols = {
            'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
        }
        
        self.square_size = 50
        self.position_after_mistake = None  # Position after White's mistake (move 0.5)
        self.significant_issue_found = False
        self.significant_issue_move = None
        self.potential_issue_after_black = None  # Store potential issue detected after Black's move (to verify after White's response)
        self.position_after_black_move = None  # Store position after Black's move
        self.potential_issue_after_black = None  # Store potential issue detected after Black's move
        self.position_after_black_move = None  # Store position after Black's move to verify issue
        
        self.setup_ui()
        self.display_initial_position()
    
    def setup_ui(self):
        """Set up the test window UI."""
        # Title
        title = tk.Label(
            self,
            text=f"PV Analysis Test - Move {self.mistake_analysis.get('chess_move', 'N/A'):.1f}",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"]
        )
        title.pack(pady=10)
        
        # Main container
        main_frame = tk.Frame(self, bg=self.colors["bg"])
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)
        
        # Left: Chess board
        board_frame = tk.Frame(main_frame, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        board_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.board_canvas = tk.Canvas(
            board_frame,
            width=self.square_size*8 + 40,
            height=self.square_size*8 + 40,
            bg=self.colors["card"],
            highlightthickness=0
        )
        self.board_canvas.pack(padx=10, pady=10)
        
        # Right: Analysis panel
        analysis_frame = tk.Frame(main_frame, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        analysis_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        # Position info
        position_label = tk.Label(
            analysis_frame,
            text="Position Info",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        position_label.pack(pady=(10, 5))
        
        self.position_info_text = tk.Text(
            analysis_frame,
            font=("Courier New", 10),
            bg=self.colors["bg"],
            fg=self.colors["text"],
            wrap=tk.WORD,
            height=8,
            padx=10,
            pady=10
        )
        self.position_info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.position_info_text.config(state=tk.DISABLED)
        
        # Analysis results
        analysis_label = tk.Label(
            analysis_frame,
            text="Analysis Results",
            font=("Segoe UI", 12, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        analysis_label.pack(pady=(10, 5))
        
        self.analysis_text = tk.Text(
            analysis_frame,
            font=("Courier New", 10),
            bg=self.colors["bg"],
            fg="#95E1D3",
            wrap=tk.WORD,
            height=12,
            padx=10,
            pady=10
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.analysis_text.config(state=tk.DISABLED)
        
        # Navigation buttons
        nav_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        self.prev_button = tk.Button(
            nav_frame,
            text="◀ Previous",
            command=self.prev_move,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            relief=tk.RAISED,
            bd=2,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = tk.Button(
            nav_frame,
            text="Next ▶",
            command=self.next_move,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            relief=tk.RAISED,
            bd=2,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        self.reset_button = tk.Button(
            nav_frame,
            text="Reset",
            command=self.reset,
            font=("Segoe UI", 10, "bold"),
            bg="#95A5A6",
            fg="white",
            activebackground="#7F8C8D",
            relief=tk.RAISED,
            bd=2,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.reset_button.pack(side=tk.LEFT, padx=5)
    
    def build_pv_move_table(self) -> str:
        """
        Build the per-move PV table: move number, move SAN, eval, and piece counts (P,N,B,R,Q,K)
        for every move from 0.5 until the PV ends. Piece counts are for the side that made the mistake.
        """
        lines: List[str] = []
        position_before_fen = self.mistake_analysis.get('position_before_fen') or self.mistake_analysis.get('position_fen')
        if not position_before_fen:
            return "No position data."
        board = chess.Board(position_before_fen)
        mistake_player = board.turn  # who made the mistake
        move_played = self.mistake_analysis.get('move_played_obj')
        if not move_played:
            move_played_str = self.mistake_analysis.get('move_played')
            if isinstance(move_played_str, str):
                try:
                    move_played = chess.Move.from_uci(move_played_str)
                except ValueError:
                    try:
                        move_played = board.parse_san(move_played_str)
                    except ValueError:
                        move_played = None
        move_0_5_san = self.mistake_analysis.get('move_played_san', move_played.uci() if move_played else '?')
        curr_eval = self.mistake_analysis.get('curr_eval')
        try:
            eval_pawns = float(curr_eval) / 100.0 if curr_eval is not None else None
        except (TypeError, ValueError):
            eval_pawns = None
        
        # Move 0.5: after the mistake
        if move_played and move_played in board.legal_moves:
            board.push(move_played)
            diffs = get_piece_count_differences(board)
            diff_str = ", ".join([f"{k}={v}" for k, v in sorted(diffs.items())]) if diffs else "equal"
            eval_str = f"{eval_pawns:.1f}" if eval_pawns is not None else "N/A"
            lines.append(f"move 0.5 ({move_0_5_san}): eval: {eval_str}, {diff_str}")
        
        continuation_moves = self.mistake_analysis.get('continuation_moves', [])
        variation = continuation_moves[0].get('variation', []) if continuation_moves else []
        
        for i, var_move_data in enumerate(variation):
            var_move = var_move_data.get('move')
            if not isinstance(var_move, chess.Move):
                if isinstance(var_move, str):
                    try:
                        var_move = chess.Move.from_uci(var_move)
                    except ValueError:
                        var_move = None
            if not var_move or var_move not in board.legal_moves:
                break
            move_san = var_move_data.get('move_san')
            if not move_san:
                try:
                    move_san = board.san(var_move)
                except Exception:
                    move_san = var_move.uci()
            board.push(var_move)
            move_number = 1 + i / 2.0  # 1, 1.5, 2, 2.5, ...
            move_num_str = str(int(move_number)) if move_number == int(move_number) else f"{move_number:.1f}"
            diffs = get_piece_count_differences(board)
            diff_str = ", ".join([f"{k}={v}" for k, v in sorted(diffs.items())]) if diffs else "equal"
            lines.append(f"move {move_num_str} ({move_san}): eval: N/A, {diff_str}")
        
        return "\n".join(lines) if lines else "No PV moves."
    
    def display_initial_position(self):
        """Display the initial position (before mistake)."""
        position_before_fen = self.mistake_analysis.get('position_before_fen')
        if not position_before_fen:
            position_before_fen = self.mistake_analysis.get('position_fen')
        
        self.current_pv_index = -1
        self.draw_board(position_before_fen)
        self.update_position_info("Move 0: Before White's mistake (White to move)")
        self.update_analysis(self.build_pv_move_table())
        self.update_buttons()
    
    def reset(self):
        """Reset to initial position."""
        self.current_pv_index = -1
        self.significant_issue_found = False
        self.significant_issue_move = None
        self.potential_issue_after_black = None
        self.position_after_black_move = None
        self.display_initial_position()
    
    def next_move(self):
        """Move to next position in PV."""
        # Get continuation moves (PV)
        continuation_moves = self.mistake_analysis.get('continuation_moves', [])
        if not continuation_moves:
            return
        
        first_continuation = continuation_moves[0]
        variation = first_continuation.get('variation', [])
        
        if not variation:
            return
        
        # Handle initial states
        if self.current_pv_index == -1:
            # Show position after White's mistake (move 0.5)
            position_before_fen = self.mistake_analysis.get('position_before_fen')
            board = chess.Board(position_before_fen)
            move_played = self.mistake_analysis.get('move_played_obj')
            
            if not move_played:
                move_played_str = self.mistake_analysis.get('move_played')
                if move_played_str and isinstance(move_played_str, str):
                    try:
                        move_played = chess.Move.from_uci(move_played_str)
                    except ValueError:
                        try:
                            move_played = board.parse_san(move_played_str)
                        except ValueError:
                            return
            
            if move_played and isinstance(move_played, chess.Move) and move_played in board.legal_moves:
                board.push(move_played)
                self.current_pv_index = 0
                self.position_after_mistake = board.copy()  # Store for comparison
                
                move_san = self.mistake_analysis.get('move_played_san', move_played.uci())
                self.draw_board(board.fen(),
                              highlight_squares=[move_played.from_square, move_played.to_square],
                              arrow_from=move_played.from_square,
                              arrow_to=move_played.to_square)
                self.update_position_info(f"Move 0.5: After White's mistake: {move_san} (Black to move)")
                self.update_analysis(self.build_pv_move_table())
                self.update_buttons()
            return
        
        # Now handle PV moves (index 0+)
        if self.current_pv_index >= len(variation):
            return  # End of variation
        
        # Get starting position (after mistake)
        position_after_fen = self.mistake_analysis.get('position_after_fen')
        if not position_after_fen:
            position_before_fen = self.mistake_analysis.get('position_before_fen')
            board = chess.Board(position_before_fen)
            move_played = self.mistake_analysis.get('move_played_obj')
            if move_played and isinstance(move_played, chess.Move) and move_played in board.legal_moves:
                board.push(move_played)
                position_after_fen = board.fen()
            else:
                position_after_fen = position_before_fen
        
        board = chess.Board(position_after_fen)
        
        # Apply all moves up to current_pv_index
        for i in range(self.current_pv_index + 1):  # +1 to include current move
            if i < len(variation):
                var_move_data = variation[i]
                var_move = var_move_data.get('move')
                
                # Convert to Move object if needed
                if not isinstance(var_move, chess.Move):
                    if isinstance(var_move, str):
                        try:
                            var_move = chess.Move.from_uci(var_move)
                        except ValueError:
                            try:
                                temp_board = board.copy()
                                for j in range(i):
                                    if j < len(variation):
                                        prev_move = variation[j].get('move')
                                        if isinstance(prev_move, chess.Move) and prev_move in temp_board.legal_moves:
                                            temp_board.push(prev_move)
                                        elif isinstance(prev_move, str):
                                            try:
                                                prev_move_uci = chess.Move.from_uci(prev_move)
                                                if prev_move_uci in temp_board.legal_moves:
                                                    temp_board.push(prev_move_uci)
                                            except ValueError:
                                                pass
                                var_move = temp_board.parse_san(var_move)
                            except ValueError:
                                continue
                    else:
                        continue
                
                if var_move and isinstance(var_move, chess.Move) and var_move in board.legal_moves:
                    board.push(var_move)
                else:
                    break
        
        # Get the move that was just applied
        if self.current_pv_index < len(variation):
            last_move_data = variation[self.current_pv_index]
            last_move = last_move_data.get('move')
            
            # Convert to Move object if needed
            if not isinstance(last_move, chess.Move):
                if isinstance(last_move, str):
                    try:
                        last_move = chess.Move.from_uci(last_move)
                    except ValueError:
                        last_move = None
                else:
                    last_move = None
            
            move_san = last_move_data.get('move_san', last_move.uci() if last_move else 'N/A')
            
            # Draw board
            if last_move and isinstance(last_move, chess.Move):
                self.draw_board(board.fen(),
                              highlight_squares=[last_move.from_square, last_move.to_square],
                              arrow_from=last_move.from_square,
                              arrow_to=last_move.to_square)
            else:
                self.draw_board(board.fen())
            
            # Determine move number and whose turn
            # variation_index: 0 = after mistake (Black to move), 1 = after Black's move (White to move), etc.
            full_move_num = (self.current_pv_index + 1) // 2  # Full move number
            is_white_turn = (board.turn == chess.WHITE)
            
            if is_white_turn:
                # It's White's turn, so Black just finished their move
                # First, verify if the previous potential issue (from previous Black move) actually happened
                move_desc = f"Move {full_move_num}: After Black's move: {move_san} (White to move)"
                self.update_position_info(move_desc)
                
                if not self.significant_issue_found and self.position_after_mistake:
                    # Check if we need to verify a previous potential issue
                    if self.potential_issue_after_black and self.position_after_black_move:
                        # We have a potential issue from previous Black move - verify if it actually happened
                        # by comparing position after mistake with position after White's previous response
                        # (which is the current board state before this Black move)
                        prev_black_move_num = full_move_num - 1
                        verification_text, issue_actually_happened, issue_details = self.verify_issue_at_next_black_move(
                            board,  # Current position after Black's move (White to move)
                            self.position_after_mistake,  # Position after White's mistake (move 0.5)
                            self.position_after_black_move,  # Position after previous Black move
                            prev_black_move_num  # Previous Black move number
                        )
                        
                        if issue_actually_happened:
                            # Issue actually happened! Stop PV here
                            self.significant_issue_found = True
                            self.significant_issue_move = full_move_num
                            self.update_analysis(self.build_pv_move_table() + "\n\n" + verification_text)
                        else:
                            # Issue didn't happen, now detect new potential issues for this Black move
                            potential_issue_text, potential_issue_details = self.detect_potential_issue_after_black(
                                board,  # Position after Black's move (White to move)
                                self.position_after_mistake,  # Position after White's mistake (move 0.5, Black to move)
                                last_move,  # Black's move
                                full_move_num  # Full move number
                            )
                            
                            # Store potential issue and position for verification at next Black move
                            self.potential_issue_after_black = potential_issue_details
                            self.position_after_black_move = board.copy()
                            
                            combined_text = verification_text + "\n\n" + potential_issue_text
                            self.update_analysis(self.build_pv_move_table() + "\n\n" + combined_text)
                    else:
                        # No previous potential issue to verify, just detect new potential issues
                        potential_issue_text, potential_issue_details = self.detect_potential_issue_after_black(
                            board,  # Position after Black's move (White to move)
                            self.position_after_mistake,  # Position after White's mistake (move 0.5, Black to move)
                            last_move,  # Black's move
                            full_move_num  # Full move number
                        )
                        
                        # Store potential issue and position for verification at next Black move
                        self.potential_issue_after_black = potential_issue_details
                        self.position_after_black_move = board.copy()
                        
                        self.update_analysis(self.build_pv_move_table() + "\n\n" + potential_issue_text)
                elif self.significant_issue_found:
                    self.update_analysis(
                        self.build_pv_move_table() + "\n\n"
                        f"Significant issue already found at move {self.significant_issue_move}.\n"
                        f"PV analysis continues — keep navigating to the end."
                    )
                else:
                    self.update_analysis(self.build_pv_move_table() + "\n\nWaiting for position after mistake to be set...")
            else:
                # It's Black's turn, so White just moved
                # Just show the move, don't analyze yet - analysis happens at next Black move
                move_desc = f"Move {full_move_num + 0.5}: After White's move: {move_san} (Black to move)"
                self.update_position_info(move_desc)
                self.update_analysis(self.build_pv_move_table())
        else:
            self.draw_board(board.fen())
            self.update_position_info("End of variation")
            self.update_analysis(self.build_pv_move_table())
        
        self.current_pv_index += 1
        self.update_buttons()
    
    def prev_move(self):
        """Move to previous position in PV."""
        if self.current_pv_index <= -1:
            return
        
        self.current_pv_index -= 1
        
        if self.current_pv_index == -1:
            self.display_initial_position()
            return
        
        # Reconstruct position
        continuation_moves = self.mistake_analysis.get('continuation_moves', [])
        if not continuation_moves:
            return
        
        first_continuation = continuation_moves[0]
        variation = first_continuation.get('variation', [])
        
        position_after_fen = self.mistake_analysis.get('position_after_fen')
        if not position_after_fen:
            position_before_fen = self.mistake_analysis.get('position_before_fen')
            board = chess.Board(position_before_fen)
            move_played = self.mistake_analysis.get('move_played_obj')
            if move_played and isinstance(move_played, chess.Move) and move_played in board.legal_moves:
                board.push(move_played)
                position_after_fen = board.fen()
            else:
                position_after_fen = position_before_fen
        
        board = chess.Board(position_after_fen)
        
        # Apply moves up to current_pv_index
        for i in range(self.current_pv_index + 1):
            if i < len(variation):
                var_move_data = variation[i]
                var_move = var_move_data.get('move')
                
                if not isinstance(var_move, chess.Move):
                    if isinstance(var_move, str):
                        try:
                            var_move = chess.Move.from_uci(var_move)
                        except ValueError:
                            continue
                    else:
                        continue
                
                if var_move and isinstance(var_move, chess.Move) and var_move in board.legal_moves:
                    board.push(var_move)
        
        # Get move info
        if self.current_pv_index < len(variation):
            last_move_data = variation[self.current_pv_index]
            last_move = last_move_data.get('move')
            
            if not isinstance(last_move, chess.Move):
                if isinstance(last_move, str):
                    try:
                        last_move = chess.Move.from_uci(last_move)
                    except ValueError:
                        last_move = None
                else:
                    last_move = None
            
            move_san = last_move_data.get('move_san', last_move.uci() if last_move else 'N/A')
            
            if last_move and isinstance(last_move, chess.Move):
                self.draw_board(board.fen(),
                              highlight_squares=[last_move.from_square, last_move.to_square],
                              arrow_from=last_move.from_square,
                              arrow_to=last_move.to_square)
            else:
                self.draw_board(board.fen())
            
            full_move_num = (self.current_pv_index + 1) // 2
            is_white_turn = (board.turn == chess.WHITE)
            
            if is_white_turn:
                # It's White's turn, so Black just finished their move
                # First, verify if the previous potential issue (from previous Black move) actually happened
                move_desc = f"Move {full_move_num}: After Black's move: {move_san} (White to move)"
                self.update_position_info(move_desc)
                
                if not self.significant_issue_found and self.position_after_mistake:
                    # Check if we need to verify a previous potential issue
                    if self.potential_issue_after_black and self.position_after_black_move:
                        # We have a potential issue from previous Black move - verify if it actually happened
                        prev_black_move_num = full_move_num - 1
                        verification_text, issue_actually_happened, issue_details = self.verify_issue_at_next_black_move(
                            board,  # Current position after Black's move (White to move)
                            self.position_after_mistake,  # Position after White's mistake (move 0.5)
                            self.position_after_black_move,  # Position after previous Black move
                            prev_black_move_num  # Previous Black move number
                        )
                        
                        if issue_actually_happened:
                            # Issue actually happened! Stop PV here
                            self.significant_issue_found = True
                            self.significant_issue_move = full_move_num
                            self.update_analysis(self.build_pv_move_table() + "\n\n" + verification_text)
                        else:
                            # Issue didn't happen, now detect new potential issues for this Black move
                            potential_issue_text, potential_issue_details = self.detect_potential_issue_after_black(
                                board,  # Position after Black's move (White to move)
                                self.position_after_mistake,  # Position after White's mistake (move 0.5, Black to move)
                                last_move,  # Black's move
                                full_move_num  # Full move number
                            )
                            
                            # Store potential issue and position for verification at next Black move
                            self.potential_issue_after_black = potential_issue_details
                            self.position_after_black_move = board.copy()
                            
                            combined_text = verification_text + "\n\n" + potential_issue_text
                            self.update_analysis(self.build_pv_move_table() + "\n\n" + combined_text)
                    else:
                        # No previous potential issue to verify, just detect new potential issues
                        potential_issue_text, potential_issue_details = self.detect_potential_issue_after_black(
                            board,  # Position after Black's move (White to move)
                            self.position_after_mistake,  # Position after White's mistake (move 0.5, Black to move)
                            last_move,  # Black's move
                            full_move_num  # Full move number
                        )
                        
                        # Store potential issue and position for verification at next Black move
                        self.potential_issue_after_black = potential_issue_details
                        self.position_after_black_move = board.copy()
                        
                        self.update_analysis(self.build_pv_move_table() + "\n\n" + potential_issue_text)
                elif self.significant_issue_found:
                    self.update_analysis(
                        self.build_pv_move_table() + "\n\n"
                        f"Significant issue already found at move {self.significant_issue_move}.\n"
                        f"PV analysis continues — keep navigating to the end."
                    )
                else:
                    self.update_analysis(self.build_pv_move_table() + "\n\nWaiting for position after mistake to be set...")
            else:
                # It's Black's turn, so White just moved
                # Just show the move, don't analyze yet - analysis happens at next Black move
                move_desc = f"Move {full_move_num + 0.5}: After White's move: {move_san} (Black to move)"
                self.update_position_info(move_desc)
                self.update_analysis(self.build_pv_move_table())
        else:
            self.draw_board(board.fen())
            self.update_position_info("End of variation")
            self.update_analysis(self.build_pv_move_table())
        
        self.update_buttons()
    
    def detect_potential_issue_after_black(self, board_after_black: chess.Board, board_after_mistake: chess.Board,
                                           black_move: chess.Move, full_move_num: int):
        """
        Detect potential issues after Black's move. This is just detection - we'll verify after White's response.
        
        Args:
            board_after_black: Board position after Black's move (White to move)
            board_after_mistake: Board position after White's mistake (move 0.5, Black to move)
            black_move: The move Black just played
            full_move_num: Full move number (1, 2, 3...)
            
        Returns:
            Tuple of (analysis_text: str, potential_issue_details: dict or None)
        """
        from .mistake_analyzer import MistakeAnalyzer
        
        # Create analyzer instance
        analyzer = MistakeAnalyzer(None)  # Engine not needed for position analysis
        
        # Analysis from White's perspective
        eval_drop = 0  # We don't have eval drop here, but the method needs it
        
        # Check for potential reasons (but don't stop yet - need to verify after White's response)
        reason = analyzer._check_position_reasons(
            board_after_mistake,  # Position after White's mistake (move 0.5, Black to move)
            board_after_black,  # Position after Black's move (White to move - Black has finished)
            black_move,  # The move that was played (Black's move)
            chess.WHITE,  # mistake_player (White made the mistake) - analysis from White's perspective
            eval_drop,
            full_move_num  # Full move number
        )
        
        if reason and reason.get('found_reason'):
            # Potential issue detected - but we need to verify after White's response
            headline = reason.get('details', {}).get('headline', 'Potential issue detected')
            detail = reason.get('details', {}).get('detail', '')
            category = reason.get('primary_category', 'Issue')
            
            analysis_text = f"Move {full_move_num}: ⚠ POTENTIAL ISSUE DETECTED\n"
            analysis_text += f"  Category: {category}\n"
            analysis_text += f"  {headline}\n"
            if detail:
                analysis_text += f"  → {detail}\n"
            analysis_text += f"\n  ⏳ Waiting for White's response to verify if issue actually happens..."
            
            return analysis_text, reason
        else:
            # No potential issue found
            analysis_text = f"Move {full_move_num}: No potential issue detected.\n"
            analysis_text += "  → Position analyzed (compared to move 0.5): Material, king safety, hanging pieces checked.\n"
            analysis_text += "  → Continue PV to find the mistake reason..."
            
            return analysis_text, None
    
    def verify_issue_at_next_black_move(self, board_after_current_black: chess.Board, board_after_mistake: chess.Board,
                                        board_after_prev_black: chess.Board, prev_black_move_num: int):
        """
        Verify if the potential issue detected after previous Black's move actually happened.
        This is called at the NEXT Black move (e.g., move 3) to verify the issue from previous Black move (e.g., move 2).
        We compare position after mistake (0.5) with position after CURRENT Black move (integer move).
        Analysis (piece checks, material imbalance) only happens at integer moves, not half moves.
        
        Args:
            board_after_current_black: Current board position after Black's move (White to move) - e.g., move 3
            board_after_mistake: Board position after White's mistake (move 0.5, Black to move)
            board_after_prev_black: Board position after previous Black move (White to move) - e.g., move 2
            prev_black_move_num: Previous Black move number (1, 2, 3...)
            
        Returns:
            Tuple of (verification_text: str, issue_actually_happened: bool, issue_details: dict or None)
        """
        from .mistake_analyzer import MistakeAnalyzer
        
        # Create analyzer instance
        analyzer = MistakeAnalyzer(None)
        
        # Compare position after mistake (0.5) with position after CURRENT Black move (integer move)
        # This ensures analysis only happens at integer moves (1, 2, 3...), not half moves (0.5, 1.5, 2.5...)
        # Use a dummy move (we're comparing positions, not moves)
        dummy_move = chess.Move.null()
        eval_drop = 0
        
        current_move_num = prev_black_move_num + 1
        
        # Check for actual materialized issues by comparing position after mistake with current position (after Black's move)
        reason = analyzer._check_position_reasons(
            board_after_mistake,  # Position after White's mistake (move 0.5)
            board_after_current_black,  # Position after CURRENT Black move (integer move - White to move)
            dummy_move,  # Dummy move (we're comparing positions)
            chess.WHITE,  # mistake_player (White made the mistake)
            eval_drop,
            current_move_num  # Current move number (integer)
        )
        
        if reason and reason.get('found_reason'):
            # Issue actually happened!
            headline = reason.get('details', {}).get('headline', 'Issue confirmed')
            detail = reason.get('details', {}).get('detail', '')
            category = reason.get('primary_category', 'Issue')
            
            verification_text = f"Move {current_move_num}: ✓ ISSUE CONFIRMED\n"
            verification_text += f"  Category: {category}\n"
            verification_text += f"  {headline}\n"
            if detail:
                verification_text += f"  → {detail}\n"
            verification_text += f"\n  ✓ The issue actually happened at move {current_move_num}!\n"
            verification_text += f"  PV analysis continues (checking remaining PV moves)."
            
            return verification_text, True, reason
        else:
            # Issue did not actually happen - White may have defended
            verification_text = f"Move {current_move_num}: Issue from move {prev_black_move_num} did NOT materialize.\n"
            verification_text += f"  → White's response may have defended against the threat.\n"
            
            return verification_text, False, None
    
    def update_position_info(self, text: str):
        """Update the position info text."""
        self.position_info_text.config(state=tk.NORMAL)
        self.position_info_text.delete(1.0, tk.END)
        self.position_info_text.insert(1.0, text)
        self.position_info_text.config(state=tk.DISABLED)
    
    def update_analysis(self, text: str):
        """Update the analysis text."""
        self.analysis_text.config(state=tk.NORMAL)
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(1.0, text)
        self.analysis_text.config(state=tk.DISABLED)
    
    def update_buttons(self):
        """Update navigation button states."""
        continuation_moves = self.mistake_analysis.get('continuation_moves', [])
        variation = continuation_moves[0].get('variation', []) if continuation_moves else []
        max_index = len(variation)
        
        self.prev_button.config(state=tk.NORMAL if self.current_pv_index > -1 else tk.DISABLED)
        # Continue through entire PV - don't stop when issue is found
        self.next_button.config(state=tk.NORMAL if self.current_pv_index < max_index else tk.DISABLED)
    
    def draw_board(self, fen: str, highlight_squares=None, arrow_from=None, arrow_to=None):
        """Draw the chess board from FEN with optional highlights. Always shows from White's perspective."""
        self.board_canvas.delete("all")
        board = chess.Board(fen)
        
        # Draw squares
        for row in range(8):
            for col in range(8):
                color = self.colors["light"] if (row + col) % 2 == 0 else self.colors["dark"]
                x1, y1 = col * self.square_size + 20, row * self.square_size + 20
                x2, y2 = x1 + self.square_size, y1 + self.square_size
                self.board_canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
        
        # Draw coordinates
        coord_font = font.Font(family='Segoe UI', size=9, weight='bold')
        files = "abcdefgh"
        ranks = "87654321"  # Rank 8 at top, rank 1 at bottom (White's perspective)
        
        for i in range(8):
            # Files (bottom)
            self.board_canvas.create_text(
                20 + i * self.square_size + self.square_size / 2,
                20 + 8 * self.square_size + 12,
                text=files[i],
                font=coord_font,
                fill=self.colors["dark"] if i % 2 == 0 else self.colors["light"]
            )
            # Ranks (left)
            self.board_canvas.create_text(
                8,
                20 + i * self.square_size + self.square_size / 2,
                text=ranks[i],
                font=coord_font,
                fill=self.colors["light"] if i % 2 == 0 else self.colors["dark"]
            )
        
        # Draw pieces
        piece_font = font.Font(family='Segoe UI', size=45, weight='bold')
        for i in range(64):
            piece = board.piece_at(i)
            if piece:
                symbol = self.piece_symbols[piece.symbol()]
                piece_color = "#FFFFFF" if piece.color == chess.WHITE else "#000000"
                row, col = divmod(i, 8)
                display_row = 7 - row  # Flip row for display (White at bottom)
                x = 20 + col * self.square_size + self.square_size / 2
                y = 20 + display_row * self.square_size + self.square_size / 2
                if piece.color == chess.BLACK:
                    self.board_canvas.create_text(x-0.5, y-0.5, text=symbol, font=piece_font, fill="#000000")
                self.board_canvas.create_text(x, y, text=symbol, font=piece_font, fill=piece_color)
        
        # Draw arrow if provided
        if arrow_from is not None and arrow_to is not None:
            from_row, from_col = chess.square_rank(arrow_from), chess.square_file(arrow_from)
            to_row, to_col = chess.square_rank(arrow_to), chess.square_file(arrow_to)
            
            from_display_row = 7 - from_row
            to_display_row = 7 - to_row
            
            x1 = 20 + from_col * self.square_size + self.square_size / 2
            y1 = 20 + from_display_row * self.square_size + self.square_size / 2
            x2 = 20 + to_col * self.square_size + self.square_size / 2
            y2 = 20 + to_display_row * self.square_size + self.square_size / 2
            
            self.board_canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, arrowshape=(18, 22, 7), width=6, fill="#FF0000")
        
        # Highlight squares if provided
        if highlight_squares:
            for square in highlight_squares:
                try:
                    if isinstance(square, int):
                        row, col = chess.square_rank(square), chess.square_file(square)
                        display_row = 7 - row
                        x1, y1 = col * self.square_size + 20, display_row * self.square_size + 20
                        x2, y2 = x1 + self.square_size, y1 + self.square_size
                        self.board_canvas.create_rectangle(x1, y1, x2, y2, outline="#FFD700", width=5)
                        self.board_canvas.create_rectangle(x1+3, y1+3, x2-3, y2-3, outline="#FFA500", width=2)
                except Exception as e:
                    print(f"Error highlighting square {square}: {e}")
