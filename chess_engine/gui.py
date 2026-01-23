"""
Chess Analyzer GUI

This module contains the ChessGui class for displaying chess game analysis with a modern GUI.
"""

import chess
import tkinter as tk
from tkinter import font, messagebox
import matplotlib.pyplot as plt
import matplotlib
import numpy as np
from .analyzer import ChessAnalyzer
from typing import Optional, List

matplotlib.use('TkAgg')  # Use Tkinter backend


class ChessGui(tk.Tk):
    """
    Modern GUI application for displaying chess game analysis.
    """
    
    def __init__(self, analysis_data, mistake_analyses=None):
        """
        Initialize the GUI.
        
        Args:
            analysis_data: List of dictionaries containing 'fen' and 'eval' for each position
            mistake_analyses: List of detailed mistake analyses (optional)
        """
        super().__init__()
        self.title("Chess Analyzer - Modern Edition")
        self.analysis_data = analysis_data
        self.analysis_results = analysis_data  # Alias for compatibility
        self.mistake_analyses = mistake_analyses or []
        self.current_move_index = 0
        
        # Configure window
        self.configure(bg="#2C3E50")
        self.geometry("850x800")
        
        # Modern color scheme
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

        # Chess piece symbols
        self.piece_symbols = {
            'P': '♟', 'N': '♞', 'B': '♝', 'R': '♜', 'Q': '♛', 'K': '♚',
            'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
        }

        self.square_size = 55
        self.setup_ui()
        self.bind_keys()
        self.update_display()

    def setup_ui(self):
        """Set up the user interface."""
        # Title
        title_label = tk.Label(
            self,
            text="Chess Game Analyzer",
            font=("Segoe UI", 18, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"]
        )
        title_label.pack(pady=(10, 5))

        # Main container
        main_container = tk.Frame(self, bg=self.colors["bg"])
        main_container.pack(expand=True, fill=tk.BOTH, padx=15, pady=5)

        # Left side - Board
        board_container = tk.Frame(main_container, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        board_container.pack(side=tk.LEFT, padx=(0, 10))

        # Board canvas with border
        self.board_canvas = tk.Canvas(
            board_container,
            width=self.square_size*8 + 40,
            height=self.square_size*8 + 40,
            bg=self.colors["card"],
            highlightthickness=0
        )
        self.board_canvas.pack(padx=8, pady=8)

        # Navigation buttons
        nav_frame = tk.Frame(board_container, bg=self.colors["card"])
        nav_frame.pack(pady=(10, 0))

        self.prev_button = tk.Button(
            nav_frame,
            text="◀ Previous",
            command=self.prev_move,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))

        self.next_button = tk.Button(
            nav_frame,
            text="Next ▶",
            command=self.next_move,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.next_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Right side - Info Panel
        info_panel = tk.Frame(main_container, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        info_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=(0, 5))

        # Evaluation display
        eval_frame = tk.Frame(info_panel, bg=self.colors["card"])
        eval_frame.pack(pady=10, padx=15, fill=tk.X)

        eval_title = tk.Label(
            eval_frame,
            text="Evaluation",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        eval_title.pack()

        self.eval_label = tk.Label(
            eval_frame,
            text="0.0",
            font=("Segoe UI", 24, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        self.eval_label.pack(pady=5)

        # Move info
        move_frame = tk.Frame(info_panel, bg=self.colors["card"])
        move_frame.pack(pady=10, padx=15, fill=tk.X)

        move_title = tk.Label(
            move_frame,
            text="Current Position",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        move_title.pack()

        self.move_label = tk.Label(
            move_frame,
            text="Start Position",
            font=("Segoe UI", 12),
            bg=self.colors["card"],
            fg=self.colors["accent"]
        )
        self.move_label.pack(pady=3)

        # Progress bar
        progress_frame = tk.Frame(info_panel, bg=self.colors["card"])
        progress_frame.pack(pady=10, padx=20, fill=tk.X)

        progress_title = tk.Label(
            progress_frame,
            text="Progress",
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        progress_title.pack()

        self.progress_label = tk.Label(
            progress_frame,
            text="0 / 0",
            font=("Segoe UI", 11),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        self.progress_label.pack(pady=3)

        # Controls
        control_frame = tk.Frame(info_panel, bg=self.colors["card"])
        control_frame.pack(side=tk.BOTTOM, pady=15, padx=15, fill=tk.X)

        # Modern styled buttons
        button_style = {
            "font": ("Segoe UI", 10, "bold"),
            "bg": self.colors["accent"],
            "fg": "white",
            "activebackground": "#2980B9",
            "activeforeground": "white",
            "relief": tk.FLAT,
            "bd": 0,
            "padx": 15,
            "pady": 8,
            "cursor": "hand2"
        }

        self.prev_button = tk.Button(
            control_frame,
            text="◀ Previous",
            command=self.prev_move,
            **button_style
        )
        self.prev_button.pack(fill=tk.X, pady=3)

        self.next_button = tk.Button(
            control_frame,
            text="Next ▶",
            command=self.next_move,
            **button_style
        )
        self.next_button.pack(fill=tk.X, pady=3)

        # Show graph button
        self.graph_button = tk.Button(
            control_frame,
            text="📊 Show Evaluation Graph",
            command=self.show_evaluation_graph,
            font=("Segoe UI", 9, "bold"),
            bg="#9B59B6",
            fg="white",
            activebackground="#8E44AD",
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.graph_button.pack(fill=tk.X, pady=(5, 3))
        
        # Evaluation table phase selection label
        table_label = tk.Label(
            control_frame,
            text="📋 Evaluation Tables by Phase:",
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["card"],
            fg="#ECF0F1"
        )
        table_label.pack(fill=tk.X, pady=(3, 2))
        
        # Phase selection buttons frame
        phase_frame = tk.Frame(control_frame, bg=self.colors["card"], relief=tk.FLAT, bd=0)
        phase_frame.pack(fill=tk.X, pady=(2, 3), padx=5)
        
        # Opening table button
        self.opening_table_button = tk.Button(
            phase_frame,
            text="Opening",
            command=self._show_opening_table,
            font=("Segoe UI", 9, "bold"),
            bg="#3498DB",
            fg="white",
            activebackground="#2980B9",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=6,
            cursor="hand2",
            state=tk.NORMAL
        )
        self.opening_table_button.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 2), ipady=5)
        
        # Middlegame table button
        self.middlegame_table_button = tk.Button(
            phase_frame,
            text="Middlegame",
            command=self._show_middlegame_table,
            font=("Segoe UI", 9, "bold"),
            bg="#E67E22",
            fg="white",
            activebackground="#D35400",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=6,
            cursor="hand2",
            state=tk.NORMAL
        )
        self.middlegame_table_button.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(2, 2), ipady=5)
        
        # Endgame table button
        self.endgame_table_button = tk.Button(
            phase_frame,
            text="Endgame",
            command=self._show_endgame_table,
            font=("Segoe UI", 9, "bold"),
            bg="#9B59B6",
            fg="white",
            activebackground="#8E44AD",
            activeforeground="white",
            relief=tk.RAISED,
            bd=2,
            padx=10,
            pady=6,
            cursor="hand2",
            state=tk.NORMAL
        )
        self.endgame_table_button.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(2, 0), ipady=5)
        
        # Show mistakes button
        self.mistakes_button = tk.Button(
            control_frame,
            text="🔍 Explore Mistakes",
            command=self.show_mistakes_explorer,
            font=("Segoe UI", 9, "bold"),
            bg="#E67E22",
            fg="white",
            activebackground="#D35400",
            activeforeground="white",
            relief=tk.FLAT,
            bd=0,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.mistakes_button.pack(fill=tk.X, pady=3)

        # Keyboard hint
        hint_label = tk.Label(
            control_frame,
            text="Use Left/Right arrows to navigate moves",
            font=("Segoe UI", 9),
            bg=self.colors["card"],
            fg=self.colors["text"],
            pady=5
        )
        hint_label.pack(fill=tk.X)

    def update_display(self):
        """Update the chessboard and evaluation display."""
        if not self.analysis_data:
            return

        # Get current position data
        current_data = self.analysis_data[self.current_move_index]
        fen = current_data['fen']
        evaluation = current_data['eval']

        # Draw board
        self.draw_board(fen)

        # Update move label with proper chess move numbering
        chess_move = self.position_to_chess_move(self.current_move_index)
        if self.current_move_index == 0:
            move_text = "Start Position"
        elif chess_move == int(chess_move):
            move_text = f"Move {int(chess_move)}"
        else:
            move_text = f"Move {chess_move:.1f}"
        self.move_label.config(text=move_text)

        # Update evaluation label
        if isinstance(evaluation, (int, float)):
            eval_in_pawns = evaluation / 100.0
            color = self.colors["positive"] if eval_in_pawns >= 0 else self.colors["negative"]
            self.eval_label.config(text=f"{eval_in_pawns:+.2f}", fg=color)
        else:
            self.eval_label.config(text=f"{evaluation}", fg=self.colors["text"])

        # Update progress (show chess move number, not position index)
        total_positions = len(self.analysis_data) - 1
        total_chess_moves = self.position_to_chess_move(total_positions)
        self.progress_label.config(text=f"{chess_move:.1f} / {total_chess_moves:.1f}")

        # Update navigation button states
        self.prev_button.config(
            state=tk.NORMAL if self.current_move_index > 0 else tk.DISABLED,
            bg=self.colors["accent"] if self.current_move_index > 0 else "#7F8C8D"
        )
        self.next_button.config(
            state=tk.NORMAL if self.current_move_index < len(self.analysis_data) - 1 else tk.DISABLED,
            bg=self.colors["accent"] if self.current_move_index < len(self.analysis_data) - 1 else "#7F8C8D"
        )

    def draw_board(self, fen: str):
        """Draw the chess board from FEN."""
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
        coord_font = font.Font(family='Segoe UI', size=10, weight='bold')
        files = "abcdefgh"
        ranks = "87654321"
        
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
        piece_font = font.Font(family='Segoe UI', size=40, weight='bold')
        for i in range(64):
            piece = board.piece_at(i)
            if piece:
                symbol = self.piece_symbols[piece.symbol()]
                piece_color = "#FFFFFF" if piece.color == chess.WHITE else "#000000"
                row, col = divmod(i, 8)
                display_row = 7 - row
                x = 20 + col * self.square_size + self.square_size / 2
                y = 20 + display_row * self.square_size + self.square_size / 2
                if piece.color == chess.BLACK:
                    self.board_canvas.create_text(x-0.5, y-0.5, text=symbol, font=piece_font, fill="#000000")
                self.board_canvas.create_text(x, y, text=symbol, font=piece_font, fill=piece_color)

    def next_move(self):
        """Move to the next position"""
        if self.current_move_index < len(self.analysis_data) - 1:
            self.current_move_index += 1
            self.update_display()

    def prev_move(self):
        """Move to the previous position"""
        if self.current_move_index > 0:
            self.current_move_index -= 1
            self.update_display()

    def bind_keys(self):
        """Bind keyboard arrow keys for navigation."""
        self.bind("<Left>", lambda event: self.prev_move())
        self.bind("<Right>", lambda event: self.next_move())
        self.focus_set()

    @staticmethod
    def position_to_chess_move(position_index: int) -> float:
        """Convert position index to chess move number."""
        return position_index / 2.0

    @staticmethod
    def get_phase(chess_move_number: float) -> str:
        """Determine the phase of the game."""
        move_num = int(chess_move_number)
        if move_num <= 15:
            return "Opening"
        elif move_num <= 30:
            return "Middlegame"
        else:
            return "Endgame"

    def show_evaluation_graph(self):
        """Display graphs showing evaluation over time and mistakes by phase"""
        # Extract position indices and evaluations
        position_indices = []
        evals = []
        
        # Also extract mistake data for plotting
        blunders = []
        mistakes = []
        inaccuracies = []

        for i, data in enumerate(self.analysis_data):
            position_indices.append(i)
            eval_val = data['eval']
            if isinstance(eval_val, (int, float)):
                evals.append(eval_val / 100.0)  # Convert to pawns for plotting
            else:
                evals.append(0.0)

        # Prepare mistake data for plotting
        for mistake in self.mistake_analyses:
            chess_move_num = self.position_to_chess_move(mistake['position_index'])
            
            if mistake['severity'] == 'Blunder':
                blunders.append((chess_move_num, evals[mistake['position_index']]))
            elif mistake['severity'] == 'Mistake':
                mistakes.append((chess_move_num, evals[mistake['position_index']]))
            elif mistake['severity'] == 'Inaccuracy':
                inaccuracies.append((chess_move_num, evals[mistake['position_index']]))

        # Convert to numpy arrays
        evals_np = np.array(evals)
        evals_clipped = np.clip(evals_np, -8.0, 8.0)
        chess_move_numbers = [self.position_to_chess_move(i) for i in position_indices]

        # --- Figure 1: Evaluation Plot ---
        fig1, ax1 = plt.subplots(figsize=(14, 7))
        
        ax1.plot(chess_move_numbers, evals_clipped, label='Evaluation', color='#3498DB', linewidth=2, zorder=2)
        ax1.axhline(0, color='gray', linestyle='--', linewidth=0.8, zorder=1)

        # Add phase divisions
        ax1.axvline(15.0, color='green', linestyle=':', linewidth=1, label='Middlegame Start', zorder=1)
        ax1.axvline(30.0, color='red', linestyle=':', linewidth=1, label='Endgame Start', zorder=1)
        
        # Add mistake markers
        if blunders:
            blunder_chess_moves = [m[0] for m in blunders]
            blunder_evals = [m[1] for m in blunders]
            ax1.scatter(blunder_chess_moves, blunder_evals, color='#E74C3C', s=150, 
                       marker='X', zorder=5, label=f'Blunder ({len(blunders)})', edgecolors='black', linewidths=1)

        if mistakes:
            mistake_chess_moves = [m[0] for m in mistakes]
            mistake_evals = [m[1] for m in mistakes]
            ax1.scatter(mistake_chess_moves, mistake_evals, color='#F39C12', s=100, 
                       marker='o', zorder=4, label=f'Mistake ({len(mistakes)})', edgecolors='black', linewidths=1)

        if inaccuracies:
            inaccuracy_chess_moves = [m[0] for m in inaccuracies]
            inaccuracy_evals = [m[1] for m in inaccuracies]
            ax1.scatter(inaccuracy_chess_moves, inaccuracy_evals, color='#95E1D3', s=70, 
                       marker='^', zorder=3, label=f'Inaccuracy ({len(inaccuracies)})', edgecolors='black', linewidths=1)
        
        ax1.set_xlabel('Move Number (1 move = White + Black)', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Evaluation (pawns)', fontsize=12, fontweight='bold')
        ax1.set_title('Game Evaluation Over Time with Mistake Analysis', fontsize=14, fontweight='bold', pad=15)
        ax1.grid(True, alpha=0.2, linestyle='--', zorder=1)
        ax1.legend(loc='upper left', fontsize=9, framealpha=0.9, ncol=2)
        ax1.set_facecolor('#ECF0F1')
        ax1.set_ylim([-8.5, 8.5])

        plt.tight_layout()
        plt.show()

        # --- Figure 2: Mistakes per Phase ---
        fig2, ax2 = plt.subplots(figsize=(10, 6))

        # Count mistakes per phase
        opening_blunders = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Opening' and m['severity'] == 'Blunder')
        opening_mistakes = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Opening' and m['severity'] == 'Mistake')
        opening_inaccuracies = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Opening' and m['severity'] == 'Inaccuracy')

        middlegame_blunders = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Middlegame' and m['severity'] == 'Blunder')
        middlegame_mistakes = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Middlegame' and m['severity'] == 'Mistake')
        middlegame_inaccuracies = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Middlegame' and m['severity'] == 'Inaccuracy')

        endgame_blunders = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Endgame' and m['severity'] == 'Blunder')
        endgame_mistakes = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Endgame' and m['severity'] == 'Mistake')
        endgame_inaccuracies = sum(1 for m in self.mistake_analyses if self.get_phase(self.position_to_chess_move(m['position_index'])) == 'Endgame' and m['severity'] == 'Inaccuracy')

        blunder_counts = [opening_blunders, middlegame_blunders, endgame_blunders]
        mistake_counts = [opening_mistakes, middlegame_mistakes, endgame_mistakes]
        inaccuracy_counts = [opening_inaccuracies, middlegame_inaccuracies, endgame_inaccuracies]

        phases = ['Opening', 'Middlegame', 'Endgame']
        x = np.arange(len(phases))
        width = 0.25

        bars1 = ax2.bar(x - width, blunder_counts, width, label='Blunders', color='#E74C3C', edgecolor='black')
        bars2 = ax2.bar(x, mistake_counts, width, label='Mistakes', color='#F39C12', edgecolor='black')
        bars3 = ax2.bar(x + width, inaccuracy_counts, width, label='Inaccuracies', color='#95E1D3', edgecolor='black')

        ax2.set_ylabel('Number of Occurrences', fontsize=12, fontweight='bold')
        ax2.set_title('Mistakes per Game Phase (White\'s Perspective)', fontsize=14, fontweight='bold', pad=15)
        ax2.set_xticks(x)
        ax2.set_xticklabels(phases)
        ax2.legend(loc='upper right', fontsize=10, framealpha=0.9)
        ax2.grid(True, alpha=0.2, linestyle='--', axis='y')
        ax2.set_facecolor('#ECF0F1')
        
        # Add value labels on bars
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax2.text(bar.get_x() + bar.get_width()/2., height,
                            f'{int(height)}',
                            ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        plt.show()
    
    def _show_opening_table(self):
        """Show opening phase table."""
        try:
            self.show_evaluation_table('Opening')
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to show Opening table: {e}")
    
    def _show_middlegame_table(self):
        """Show middlegame phase table."""
        try:
            self.show_evaluation_table('Middlegame')
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to show Middlegame table: {e}")
    
    def _show_endgame_table(self):
        """Show endgame phase table."""
        try:
            self.show_evaluation_table('Endgame')
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to show Endgame table: {e}")
    
    def show_evaluation_table(self, phase_name=None):
        """Display evaluation table for a specific phase with White/Black columns."""
        import matplotlib.pyplot as plt
        
        def get_phase(move_num):
            """Get phase for a move number."""
            move_num_int = int(move_num)
            if move_num_int <= 15:
                return "Opening"
            elif move_num_int <= 30:
                return "Middlegame"
            else:
                return "Endgame"
        
        # Process moves into full moves (White + Black pairs)
        full_moves = []
        
        # Process each move in pairs (White, then Black)
        # Use pre-calculated delta evals and mistake categories from analysis_results
        move_num = 1
        for i in range(1, len(self.analysis_data), 2):  # Process in pairs
            white_result = self.analysis_data[i] if i < len(self.analysis_data) else None
            black_result = self.analysis_data[i+1] if i+1 < len(self.analysis_data) else None
            
            # White's move - use pre-calculated data
            white_eval = white_result.get('eval', 0) if white_result else None
            white_delta = white_result.get('delta_eval') if white_result else None
            white_category = white_result.get('mistake_category', '') if white_result else ''
            white_move = white_result.get('move_san', white_result.get('move_uci', '')) if white_result else '-'
            
            # Black's move - calculate delta from White's eval
            black_eval = None
            black_delta = None
            black_move = '-'
            
            if black_result:
                black_eval = black_result.get('eval', 0)
                if isinstance(black_eval, (int, float)) and isinstance(white_eval, (int, float)):
                    black_delta = black_result.get('delta_eval')  # Use pre-calculated if available
                    if black_delta is None:
                        black_delta = black_eval - white_eval  # Fallback calculation
                    black_move = black_result.get('move_san', black_result.get('move_uci', ''))
            
            phase = get_phase(move_num)
            
            # Only include this row if White made a mistake (inaccuracy, mistake, or blunder)
            if white_category:  # Only show rows where White made a mistake
                # Find corresponding mistake analysis for best moves
                mistake_analysis = None
                chess_move_float = move_num
                for mistake in self.mistake_analyses:
                    if abs(mistake.get('chess_move', 0) - chess_move_float) < 0.1:
                        mistake_analysis = mistake
                        break
                
                full_moves.append({
                    'move_num': move_num,
                    'white_move': white_move,
                    'white_eval': white_eval / 100.0 if isinstance(white_eval, (int, float)) else '-',
                    'white_delta': white_delta / 100.0 if white_delta is not None else '-',
                    'white_category': white_category,
                    'black_move': black_move,
                    'black_eval': black_eval / 100.0 if isinstance(black_eval, (int, float)) else '-',
                    'black_delta': black_delta / 100.0 if black_delta is not None else '-',
                    'black_category': '',
                    'phase': phase,
                    'mistake_analysis': mistake_analysis
                })
            
            move_num += 1
        
        # Filter moves by selected phase
        if phase_name:
            moves = [m for m in full_moves if m['phase'] == phase_name]
            if not moves:
                messagebox.showinfo("No Moves", f"No moves found in the {phase_name} phase.")
                return
        else:
            opening_moves = [m for m in full_moves if m['phase'] == 'Opening']
            middlegame_moves = [m for m in full_moves if m['phase'] == 'Middlegame']
            endgame_moves = [m for m in full_moves if m['phase'] == 'Endgame']
            
            phases_data = [
                ('Opening', opening_moves),
                ('Middlegame', middlegame_moves),
                ('Endgame', endgame_moves)
            ]
            
            for p_name, mvs in phases_data:
                if not mvs:
                    continue
                self._create_table_for_phase(p_name, mvs)
            return
        
        # Create table for selected phase
        self._create_table_for_phase(phase_name, moves)
    
    def _create_table_for_phase(self, phase_name, moves):
        """Helper method to create a table for a specific phase."""
        import matplotlib.pyplot as plt
        
        fig, ax = plt.subplots(figsize=(18, max(10, len(moves) * 0.6)))
        ax.axis('tight')
        ax.axis('off')
        
        # Create table data
        table_data = []
        for move in moves:
            # White column - include move played and best moves for mistakes
            if move['white_move'] != '-':
                white_text = f"Played: {move['white_move']}"
                white_text += f"\nEval: {move['white_eval']:+.2f}" if isinstance(move['white_eval'], float) else f"\nEval: {move['white_eval']}"
                if move['white_delta'] != '-':
                    white_text += f"\nΔ: {move['white_delta']:+.2f}" if isinstance(move['white_delta'], float) else f"\nΔ: {move['white_delta']}"
                if move['white_category']:
                    white_text += f"\n[{move['white_category']}]"
                
                # Add best moves variation if available
                mistake_analysis = move.get('mistake_analysis')
                if mistake_analysis:
                    best_moves = mistake_analysis.get('best_moves', [])
                    if best_moves and len(best_moves) > 0:
                        # Get the first best move's variation (consecutive moves)
                        first_best = best_moves[0]
                        variation = first_best.get('variation', [])
                        if variation:
                            # Show first 3 consecutive moves in the variation
                            variation_moves = []
                            for var_move in variation[:3]:
                                move_san = var_move.get('move_san', var_move.get('move_uci', 'N/A'))
                                variation_moves.append(move_san)
                            
                            if variation_moves:
                                eval_pawns = first_best.get('eval', 0) / 100.0
                                white_text += f"\nBest: {' '.join(variation_moves)} ({eval_pawns:+.2f})"
                        else:
                            # Fallback: just show the first move if no variation
                            move_san = first_best.get('move_san', first_best.get('move_uci', 'N/A'))
                            eval_pawns = first_best.get('eval', 0) / 100.0
                            white_text += f"\nBest: {move_san} ({eval_pawns:+.2f})"
            else:
                white_text = '-'
            
            # Black column (no move notation, just eval and delta, no category)
            if move['black_move'] != '-':
                black_text = f"Eval: {move['black_eval']:+.2f}" if isinstance(move['black_eval'], float) else f"Eval: {move['black_eval']}"
                if move['black_delta'] != '-':
                    black_text += f"\nΔ: {move['black_delta']:+.2f}" if isinstance(move['black_delta'], float) else f"\nΔ: {move['black_delta']}"
            else:
                black_text = '-'
            
            table_data.append([
                str(move['move_num']) if move['move_num'] > 0 else 'Start',
                white_text,
                black_text
            ])
        
        # Create table
        table = ax.table(cellText=table_data,
                        colLabels=['Move', 'White', 'Black'],
                        cellLoc='center',
                        loc='center')
        
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 2.5)
        
        # Color code cells based on category
        for i, move in enumerate(moves):
            row_idx = i + 1
            
            # White cell
            if move['white_category'] == 'Blunder':
                table[(row_idx, 1)].set_facecolor('#FF6B6B')
                table[(row_idx, 1)].set_text_props(weight='bold')
            elif move['white_category'] == 'Mistake':
                table[(row_idx, 1)].set_facecolor('#FFD93D')
            elif move['white_category'] == 'Inaccuracy':
                table[(row_idx, 1)].set_facecolor('#95E1D3')
            else:
                table[(row_idx, 1)].set_facecolor('#FFFFFF')
            
            # Black cell
            table[(row_idx, 2)].set_facecolor('#FFFFFF')
        
        # Header styling
        for j in range(3):
            table[(0, j)].set_facecolor('#34495E')
            table[(0, j)].set_text_props(weight='bold', color='white')
        
        # Add note about interactive viewing
        ax.text(0.5, -0.02, '💡 Tip: Use "🔍 Explore Mistakes" button to view moves interactively on the board',
                transform=ax.transAxes, ha='center', fontsize=9, style='italic', color='gray')
        
        plt.title(f'{phase_name} - Move-by-Move Evaluation Analysis', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.show()

    def show_mistakes_explorer(self):
        """Open a window to explore mistakes with details."""
        if not self.mistake_analyses:
            messagebox.showinfo("No Mistakes", "No mistakes found. Run mistake analysis first.")
            return
        
        # Create mistake explorer window
        mistake_window = MistakeExplorerWindow(self, self.mistake_analyses, self.analysis_data)
        mistake_window.mainloop()
    
    def show_mistake_on_board(self, mistake_analysis):
        """Open an interactive board window to view a specific mistake and its best moves."""
        if not mistake_analysis:
            return
        
        # Create interactive board window for this mistake
        board_window = MistakeBoardWindow(self, mistake_analysis)
        board_window.mainloop()


class MistakeExplorerWindow(tk.Toplevel):
    """Window for exploring mistakes in detail."""
    
    def __init__(self, parent, mistake_analyses, analysis_data):
        super().__init__(parent)
        self.mistake_analyses = mistake_analyses
        self.analysis_data = analysis_data
        self.current_mistake_index = 0
        self.current_best_move_index = 0
        
        self.title("Mistake Explorer")
        self.geometry("1200x800")
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
        self.setup_ui()
        self.display_mistake(0)
    
    def setup_ui(self):
        """Set up the mistake explorer UI."""
        # Title
        title = tk.Label(
            self,
            text=f"Mistake Explorer ({len(self.mistake_analyses)} total)",
            font=("Segoe UI", 20, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"]
        )
        title.pack(pady=10)
        
        # Main container
        main_frame = tk.Frame(self, bg=self.colors["bg"])
        main_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)
        
        # Left: Mistake list
        list_frame = tk.Frame(main_frame, bg=self.colors["card"], relief=tk.RAISED, bd=2, width=300)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        list_frame.pack_propagate(False)
        
        list_title = tk.Label(
            list_frame,
            text="Mistakes",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        list_title.pack(pady=10)
        
        self.mistake_listbox = tk.Listbox(
            list_frame,
            font=("Segoe UI", 11),
            bg=self.colors["bg"],
            fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground="white",
            borderwidth=0,
            highlightthickness=0,
            relief=tk.FLAT
        )
        self.mistake_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.mistake_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.mistake_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate list
        for i, mistake in enumerate(self.mistake_analyses):
            move_num = mistake.get('chess_move', i)
            severity = mistake.get('severity', 'Mistake')
            text = f"Move {move_num:.1f}: {severity}"
            self.mistake_listbox.insert(tk.END, text)
        
        self.mistake_listbox.bind('<<ListboxSelect>>', self.on_mistake_select)
        self.mistake_listbox.selection_set(0)
        
        # Right: Board and details
        right_frame = tk.Frame(main_frame, bg=self.colors["bg"])
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        
        # Board display
        board_frame = tk.Frame(right_frame, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        board_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.board_canvas = tk.Canvas(
            board_frame,
            width=self.square_size*8 + 40,
            height=self.square_size*8 + 40,
            bg=self.colors["card"],
            highlightthickness=0
        )
        self.board_canvas.pack(padx=10, pady=10)
        
        # Interactive board button
        interactive_btn = tk.Button(
            board_frame,
            text="🎯 View on Interactive Board",
            command=self.show_interactive_board,
            font=("Segoe UI", 10, "bold"),
            bg="#2ECC71",
            fg="white",
            activebackground="#27AE60",
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        interactive_btn.pack(pady=(0, 10))
        
        # Details frame
        details_frame = tk.Frame(right_frame, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        details_frame.pack(fill=tk.BOTH, expand=True)
        
        details_title = tk.Label(
            details_frame,
            text="Mistake Details",
            font=("Segoe UI", 14, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        details_title.pack(pady=10)
        
        self.details_text = tk.Text(
            details_frame,
            font=("Segoe UI", 11),
            bg=self.colors["card"],
            fg=self.colors["text"],
            wrap=tk.WORD,
            height=10,
            padx=15,
            pady=15
        )
        self.details_text.pack(expand=True, fill=tk.BOTH)
    
    def on_mistake_select(self, event):
        """Handle mistake selection from list."""
        selection = self.mistake_listbox.curselection()
        if selection:
            self.current_mistake_index = selection[0]
            self.display_mistake(self.current_mistake_index)
    
    def show_interactive_board(self):
        """Open interactive board window for current mistake."""
        if self.current_mistake_index < len(self.mistake_analyses):
            mistake = self.mistake_analyses[self.current_mistake_index]
            board_window = MistakeBoardWindow(self, mistake)
            board_window.mainloop()
    
    def display_mistake(self, index):
        """Display the selected mistake."""
        if index >= len(self.mistake_analyses):
            return
        
        mistake = self.mistake_analyses[index]
        
        # Draw board - show position BEFORE the mistake
        position_fen = mistake.get('position_before_fen', mistake.get('position_fen'))
        self.draw_board(position_fen)
        
        # Update details
        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        
        details = f"Move: {mistake.get('chess_move', 'N/A'):.1f}\n"
        details += f"Phase: {mistake.get('phase', 'N/A')}\n\n"
        details += f"Severity: {mistake.get('severity', 'Mistake')}\n"
        details += f"Move Played: {mistake.get('move_played_san', mistake.get('move_played', 'N/A'))}\n"
        details += f"Evaluation Drop: {mistake.get('eval_drop', 0) / 100.0:.2f} pawns\n\n"
        details += f"Category: {mistake.get('primary_category', 'General')}\n"
        
        categories = mistake.get('categories', [])
        if len(categories) > 1:
            details += f"All Categories: {', '.join(categories)}\n"
        
        details += "\nDetails:\n"
        mistake_details = mistake.get('details', {})
        for key, value in mistake_details.items():
            details += f"• {value}\n"
        
        self.details_text.insert(1.0, details)
        self.details_text.config(state=tk.DISABLED)
    
    def draw_board(self, fen: str):
        """Draw the chess board from FEN with coordinates."""
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
        ranks = "87654321"
        
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
        piece_font = font.Font(family='Segoe UI', size=40, weight='bold')
        for i in range(64):
            piece = board.piece_at(i)
            if piece:
                symbol = self.piece_symbols[piece.symbol()]
                piece_color = "#FFFFFF" if piece.color == chess.WHITE else "#000000"
                row, col = divmod(i, 8)
                display_row = 7 - row
                x = 20 + col * self.square_size + self.square_size / 2
                y = 20 + display_row * self.square_size + self.square_size / 2
                if piece.color == chess.BLACK:
                    self.board_canvas.create_text(x-0.5, y-0.5, text=symbol, font=piece_font, fill="#000000")
                self.board_canvas.create_text(x, y, text=symbol, font=piece_font, fill=piece_color)


class MistakeBoardWindow(tk.Toplevel):
    """Interactive window to view a mistake with two boards: why it's a mistake vs best alternative."""
    
    def __init__(self, parent, mistake_analysis):
        super().__init__(parent)
        self.mistake_analysis = mistake_analysis
        self.current_continuation_index = 0  # For left board (why it's a mistake)
        self.current_best_variation_index = 0  # For right board (best alternative)
        
        self.title("Interactive Mistake Analysis")
        self.geometry("1400x850")
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
        
        self.square_size = 45  # Smaller to fit two boards and buttons
        self.setup_ui()
        self.display_initial_positions()
    
    def setup_ui(self):
        """Set up the interactive board UI with two boards side by side."""
        # Title
        title = tk.Label(
            self,
            text=f"Move {self.mistake_analysis.get('chess_move', 'N/A'):.1f} - {self.mistake_analysis.get('severity', 'Mistake')}",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["text"]
        )
        title.pack(pady=5)
        
        # Mistake explanation section (above boards)
        explanation_frame = tk.Frame(self, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        explanation_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        explanation_title = tk.Label(
            explanation_frame,
            text="Mistake Explanation",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["card"],
            fg=self.colors["text"]
        )
        explanation_title.pack(pady=(8, 3))
        
        self.explanation_text = tk.Text(
            explanation_frame,
            font=("Segoe UI", 9),
            bg=self.colors["card"],
            fg=self.colors["text"],
            wrap=tk.WORD,
            height=3,
            padx=10,
            pady=8,
            relief=tk.FLAT,
            borderwidth=0
        )
        self.explanation_text.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.explanation_text.config(state=tk.DISABLED)  # Make it read-only
        
        # Main container for two boards
        main_container = tk.Frame(self, bg=self.colors["bg"])
        main_container.pack(expand=True, fill=tk.BOTH, padx=20, pady=5)
        
        # Left board: Why it's a mistake (continuation after mistake)
        left_frame = tk.Frame(main_container, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        left_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=(0, 10))
        
        left_title = tk.Label(
            left_frame,
            text="Why It's a Mistake",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["card"],
            fg=self.colors["negative"]
        )
        left_title.pack(pady=(8, 3))
        
        self.left_board_canvas = tk.Canvas(
            left_frame,
            width=self.square_size*8 + 40,
            height=self.square_size*8 + 40,
            bg=self.colors["card"],
            highlightthickness=0
        )
        self.left_board_canvas.pack(padx=8, pady=5)
        
        self.left_info_label = tk.Label(
            left_frame,
            text="",
            font=("Segoe UI", 9),
            bg=self.colors["card"],
            fg=self.colors["text"],
            wraplength=280,
            justify=tk.LEFT,
            padx=8,
            pady=3
        )
        self.left_info_label.pack()
        
        # Left board navigation
        left_nav_frame = tk.Frame(left_frame, bg=self.colors["card"])
        left_nav_frame.pack(pady=5)
        
        self.left_prev_button = tk.Button(
            left_nav_frame,
            text="◀ Prev",
            command=self.left_prev_move,
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.left_prev_button.pack(side=tk.LEFT, padx=2)
        
        self.left_reset_button = tk.Button(
            left_nav_frame,
            text="Reset",
            command=self.left_reset,
            font=("Segoe UI", 9, "bold"),
            bg="#95A5A6",
            fg="white",
            activebackground="#7F8C8D",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.left_reset_button.pack(side=tk.LEFT, padx=2)
        
        self.left_next_button = tk.Button(
            left_nav_frame,
            text="Next ▶",
            command=self.left_next_move,
            font=("Segoe UI", 9, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        self.left_next_button.pack(side=tk.LEFT, padx=2)
        
        # Right board: Best alternative
        right_frame = tk.Frame(main_container, bg=self.colors["card"], relief=tk.RAISED, bd=2)
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=(10, 0))
        
        right_title = tk.Label(
            right_frame,
            text="Best Alternative",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["card"],
            fg=self.colors["positive"]
        )
        right_title.pack(pady=(8, 3))
        
        self.right_board_canvas = tk.Canvas(
            right_frame,
            width=self.square_size*8 + 40,
            height=self.square_size*8 + 40,
            bg=self.colors["card"],
            highlightthickness=0
        )
        self.right_board_canvas.pack(padx=8, pady=5)
        
        self.right_info_label = tk.Label(
            right_frame,
            text="",
            font=("Segoe UI", 9),
            bg=self.colors["card"],
            fg=self.colors["text"],
            wraplength=280,
            justify=tk.LEFT,
            padx=8,
            pady=3
        )
        self.right_info_label.pack()
        
        # Right board navigation
        right_nav_frame = tk.Frame(right_frame, bg=self.colors["card"])
        right_nav_frame.pack(pady=5)
        
        self.right_prev_button = tk.Button(
            right_nav_frame,
            text="◀ Prev",
            command=self.right_prev_move,
            font=("Segoe UI", 8, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            cursor="hand2"
        )
        self.right_prev_button.pack(side=tk.LEFT, padx=2)
        
        self.right_reset_button = tk.Button(
            right_nav_frame,
            text="Reset",
            command=self.right_reset,
            font=("Segoe UI", 8, "bold"),
            bg="#95A5A6",
            fg="white",
            activebackground="#7F8C8D",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            cursor="hand2"
        )
        self.right_reset_button.pack(side=tk.LEFT, padx=2)
        
        self.right_next_button = tk.Button(
            right_nav_frame,
            text="Next ▶",
            command=self.right_next_move,
            font=("Segoe UI", 8, "bold"),
            bg=self.colors["accent"],
            fg="white",
            activebackground="#2980B9",
            relief=tk.FLAT,
            padx=8,
            pady=4,
            cursor="hand2"
        )
        self.right_next_button.pack(side=tk.LEFT, padx=2)
    
    def display_initial_positions(self):
        """Display initial positions for both boards."""
        # Left board: Start at position BEFORE mistake (so user can see the mistake move first)
        position_before_fen = self.mistake_analysis.get('position_before_fen', self.mistake_analysis.get('position_fen'))
        self.current_continuation_index = -1  # -1 means before mistake move, 0 means after mistake, 1+ means continuation
        self.draw_left_board(position_before_fen)
        self.left_info_label.config(text="Position before the mistake.\nClick 'Next ▶' to see the mistake move, then how Black exploits it.")
        
        # Right board: Show position before mistake
        self.current_best_variation_index = 0
        self.draw_right_board(position_before_fen)
        self.right_info_label.config(text="Position before the mistake.\nClick 'Next ▶' to see the best alternative.")
        
        # Display initial explanation
        self.update_explanation()
        
        self.update_navigation_buttons()
    
    def update_explanation(self):
        """Update the mistake explanation text based on current position."""
        self.explanation_text.config(state=tk.NORMAL)
        self.explanation_text.delete(1.0, tk.END)
        
        # Get mistake details
        move_played = self.mistake_analysis.get('move_played_san', self.mistake_analysis.get('move_played', 'N/A'))
        severity = self.mistake_analysis.get('severity', 'Mistake')
        eval_drop = self.mistake_analysis.get('eval_drop', 0) / 100.0
        primary_category = self.mistake_analysis.get('primary_category', 'General Mistake')
        details = self.mistake_analysis.get('details', {})
        
        # Build explanation text using new explainable format
        explanation = f"❌ {severity}: {move_played} was played, losing {eval_drop:.2f} pawns in evaluation.\n\n"
        
        # Use new explainable format
        if 'headline' in details:
            explanation += f"🔴 {details['headline']}\n\n"
            if 'detail' in details:
                explanation += f"   → {details['detail']}\n\n"
        elif 'detail' in details:
            explanation += f"🔴 {details['detail']}\n\n"
        
        # Add detail lines if available
        if 'detail_lines' in details and details['detail_lines']:
            for detail_line in details['detail_lines']:
                if isinstance(detail_line, dict):
                    if 'message' in detail_line:
                        explanation += f"   • {detail_line['message']}\n"
                    if 'detail' in detail_line:
                        explanation += f"     → {detail_line['detail']}\n"
                else:
                    explanation += f"   • {detail_line}\n"
            explanation += "\n"
        
        # Fallback to old format if new format not available
        if 'headline' not in details and 'detail' not in details:
            explanation += f"📋 Category: {primary_category}\n\n"
            if 'hanging_piece' in details:
                explanation += f"🔴 {details['hanging_piece']}\n\n"
            if 'king_safety' in details:
                explanation += f"👑 {details['king_safety']}\n\n"
            if 'tactical' in details:
                explanation += f"⚔️ {details['tactical']}\n\n"
            if 'positional' in details:
                explanation += f"📐 {details['positional']}\n\n"
            if 'endgame' in details:
                explanation += f"🏁 {details['endgame']}\n\n"
            if 'calculation' in details:
                explanation += f"🧮 {details['calculation']}\n\n"
            if 'general' in details:
                explanation += f"ℹ️ {details['general']}\n\n"
        
        explanation += "💡 Navigate through the variations below to see how the mistake unfolds and what the best alternative would have been."
        
        self.explanation_text.insert(1.0, explanation)
        self.explanation_text.config(state=tk.DISABLED)
    
    def left_reset(self):
        """Reset left board to position before mistake."""
        position_before_fen = self.mistake_analysis.get('position_before_fen', self.mistake_analysis.get('position_fen'))
        self.current_continuation_index = -1  # -1 = before mistake, 0 = after mistake, 1+ = continuation
        self.draw_left_board(position_before_fen)
        self.left_info_label.config(text="Position before the mistake.\nClick 'Next ▶' to see the mistake move, then how Black exploits it.")
        self.update_navigation_buttons()
    
    def right_reset(self):
        """Reset right board to position before mistake."""
        position_before_fen = self.mistake_analysis.get('position_before_fen', self.mistake_analysis.get('position_fen'))
        self.current_best_variation_index = 0
        self.draw_right_board(position_before_fen)
        self.right_info_label.config(text="Position before the mistake.\nClick 'Next ▶' to see the best alternative.")
        self.update_navigation_buttons()
    
    def left_next_move(self):
        """Move forward: show mistake move first, then continuation."""
        # If at position before mistake (-1), show the mistake move (0)
        if self.current_continuation_index == -1:
            position_before_fen = self.mistake_analysis.get('position_before_fen', self.mistake_analysis.get('position_fen'))
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
                self.current_continuation_index = 0  # Now at position after mistake
                
                self.draw_left_board(board.fen(),
                                   highlight_squares=[move_played.from_square, move_played.to_square],
                                   arrow_from=move_played.from_square,
                                   arrow_to=move_played.to_square)
                
                move_san = self.mistake_analysis.get('move_played_san', move_played.uci())
                eval_drop = self.mistake_analysis.get('eval_drop', 0) / 100.0
                info_text = f"Mistake move: {move_san} (Eval drop: {eval_drop:+.2f} pawns)\n"
                info_text += "Click 'Next ▶' to see how Black exploits it."
                self.left_info_label.config(text=info_text)
                self.update_navigation_buttons()
            return
        
        # Now continue with continuation moves (index 0+)
        continuation_moves = self.mistake_analysis.get('continuation_moves', [])
        if not continuation_moves or len(continuation_moves) == 0:
            return
        
        first_continuation = continuation_moves[0]
        variation = first_continuation.get('variation', [])
        
        if not variation:
            return
        
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
        
        # current_continuation_index: -1 = before mistake, 0 = after mistake, 1+ = continuation moves
        # When current_continuation_index = 0 (after mistake), we want to show variation[0] (first continuation move)
        # When current_continuation_index = 1, we want to show variation[1] (second continuation move)
        # So: variation_index = current_continuation_index (when >= 0, but we're already past 0, so it's current_continuation_index)
        # Actually: when we're at index 0 (after mistake), next click should show variation[0]
        # So variation_index should be current_continuation_index when current_continuation_index > 0
        # But wait, we're already at index 0, so the next move should be variation[0]
        # So: variation_index = current_continuation_index (since we're already at 0, next is variation[0])
        
        # When current_continuation_index = 0, we want variation_index = 0
        # When current_continuation_index = 1, we want variation_index = 1
        # So: variation_index = current_continuation_index
        variation_index = self.current_continuation_index  # Index into variation array (0-based)
        
        # Check if we have more moves to show
        if variation_index >= len(variation):
            # No more moves, show end message
            self.left_info_label.config(text="End of continuation shown.")
            return
        
        # Apply all moves up to and including the current continuation move
        for i in range(variation_index + 1):  # +1 to include current move
            if i < len(variation):
                var_move_data = variation[i]
                var_move = var_move_data.get('move')
                
                # Convert to Move object if needed (should already be a Move object from analysis)
                if not isinstance(var_move, chess.Move):
                    if isinstance(var_move, str):
                        try:
                            var_move = chess.Move.from_uci(var_move)
                        except ValueError:
                            # Try parsing as SAN - need board state before this move
                            try:
                                temp_board = board.copy()
                                # Apply all previous moves in variation to get correct board state
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
                
                # Apply the move if it's valid
                if var_move and isinstance(var_move, chess.Move) and var_move in board.legal_moves:
                    board.push(var_move)
                else:
                    # If move is invalid, break out of loop
                    break
        
        # Now draw the board with the current position
        # Highlight the last move that was played
        if variation_index >= 0 and variation_index < len(variation):
            last_move_data = variation[variation_index]
            last_move = last_move_data.get('move')
            
            # Convert to Move object if needed (should already be a Move object)
            if not isinstance(last_move, chess.Move):
                if isinstance(last_move, str):
                    try:
                        last_move = chess.Move.from_uci(last_move)
                    except ValueError:
                        # Try parsing as SAN - need board state before this move
                        try:
                            temp_board = chess.Board(position_after_fen)
                            for j in range(variation_index):
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
                            last_move = temp_board.parse_san(last_move)
                        except ValueError:
                            last_move = None
                else:
                    last_move = None
            
            if last_move and isinstance(last_move, chess.Move):
                self.draw_left_board(board.fen(),
                                   highlight_squares=[last_move.from_square, last_move.to_square],
                                   arrow_from=last_move.from_square,
                                   arrow_to=last_move.to_square)
            else:
                self.draw_left_board(board.fen())
        else:
            self.draw_left_board(board.fen())
        
        # Update info text
        move_san = variation[variation_index].get('move_san', 'N/A')
        move_num = self.current_continuation_index
        info_text = f"Continuation - Move {move_num}: {move_san}\n"
        if variation_index + 1 < len(variation):
            next_move_san = variation[variation_index + 1].get('move_san', 'N/A')
            info_text += f"Next: {next_move_san}"
        else:
            info_text += "End of continuation shown."
        
        self.left_info_label.config(text=info_text)
        self.current_continuation_index += 1  # Move to next position
        self.update_navigation_buttons()
    
    def left_prev_move(self):
        """Move backward: go from continuation → mistake move → before mistake."""
        if self.current_continuation_index <= -1:
            return
        
        self.current_continuation_index -= 1
        
        # If going back to position after mistake (index 0), show the mistake move
        if self.current_continuation_index == 0:
            position_before_fen = self.mistake_analysis.get('position_before_fen', self.mistake_analysis.get('position_fen'))
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
                            move_played = None
            
            if move_played and isinstance(move_played, chess.Move) and move_played in board.legal_moves:
                board.push(move_played)
                self.draw_left_board(board.fen(),
                                   highlight_squares=[move_played.from_square, move_played.to_square],
                                   arrow_from=move_played.from_square,
                                   arrow_to=move_played.to_square)
                
                move_san = self.mistake_analysis.get('move_played_san', move_played.uci())
                eval_drop = self.mistake_analysis.get('eval_drop', 0) / 100.0
                info_text = f"Mistake move: {move_san} (Eval drop: {eval_drop:+.2f} pawns)\n"
                info_text += "Click 'Next ▶' to see how Black exploits it."
                self.left_info_label.config(text=info_text)
                self.update_navigation_buttons()
            return
        
        # If going back to before mistake (index -1)
        if self.current_continuation_index == -1:
            self.left_reset()
            return
        
        # Otherwise, show previous continuation move
        continuation_moves = self.mistake_analysis.get('continuation_moves', [])
        variation = continuation_moves[0].get('variation', []) if continuation_moves else []
        
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
        
        # Apply continuation moves up to current index (after decrement)
        # When we decrement, current_continuation_index goes from 1 to 0, so we want variation[0]
        # When current_continuation_index = 0, variation_index = 0
        variation_index = self.current_continuation_index  # After decrement, this is the index we want to show
        
        # Apply all moves up to and including the current continuation move
        for i in range(variation_index + 1):  # +1 to include current move
            if i < len(variation):
                var_move_data = variation[i]
                var_move = var_move_data.get('move')
                
                # Convert to Move object if needed (should already be a Move object)
                if not isinstance(var_move, chess.Move):
                    if isinstance(var_move, str):
                        try:
                            var_move = chess.Move.from_uci(var_move)
                        except ValueError:
                            # Try parsing as SAN - need board state before this move
                            try:
                                temp_board = board.copy()
                                # Apply all previous moves in variation to get correct board state
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
                
                # Apply the move if it's valid
                if var_move and isinstance(var_move, chess.Move) and var_move in board.legal_moves:
                    board.push(var_move)
                else:
                    break
        
        # Highlight the last move that was played
        if variation_index >= 0 and variation_index < len(variation):
            last_move_data = variation[variation_index]
            last_move = last_move_data.get('move')
            
            # Convert to Move object if needed
            if not isinstance(last_move, chess.Move):
                if isinstance(last_move, str):
                    try:
                        last_move = chess.Move.from_uci(last_move)
                    except ValueError:
                        try:
                            temp_board = chess.Board(position_after_fen)
                            for j in range(variation_index):
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
                            last_move = temp_board.parse_san(last_move)
                        except ValueError:
                            last_move = None
                else:
                    last_move = None
            
            if last_move and isinstance(last_move, chess.Move):
                self.draw_left_board(board.fen(),
                                   highlight_squares=[last_move.from_square, last_move.to_square],
                                   arrow_from=last_move.from_square,
                                   arrow_to=last_move.to_square)
            else:
                self.draw_left_board(board.fen())
        else:
            self.draw_left_board(board.fen())
        
        move_san = variation[variation_index].get('move_san', 'N/A') if variation_index >= 0 and variation_index < len(variation) else 'N/A'
        info_text = f"Continuation - Move {self.current_continuation_index}: {move_san}"
        self.left_info_label.config(text=info_text)
        self.update_navigation_buttons()
    
    def right_next_move(self):
        """Move forward in the best variation."""
        best_moves = self.mistake_analysis.get('best_moves', [])
        if not best_moves or len(best_moves) == 0:
            return
        
        first_best = best_moves[0]
        variation = first_best.get('variation', [])
        
        if not variation:
            return
        
        position_fen = self.mistake_analysis.get('position_before_fen', self.mistake_analysis.get('position_fen'))
        board = chess.Board(position_fen)
        
        for i in range(self.current_best_variation_index):
            if i < len(variation):
                var_move_data = variation[i]
                var_move = var_move_data.get('move')
                if isinstance(var_move, str):
                    try:
                        var_move = chess.Move.from_uci(var_move)
                    except ValueError:
                        try:
                            var_move = board.parse_san(var_move)
                        except ValueError:
                            continue
                if var_move and var_move in board.legal_moves:
                    board.push(var_move)
        
        if self.current_best_variation_index < len(variation):
            var_move_data = variation[self.current_best_variation_index]
            var_move = var_move_data.get('move')
            if isinstance(var_move, str):
                try:
                    var_move = chess.Move.from_uci(var_move)
                except ValueError:
                    try:
                        var_move = board.parse_san(var_move)
                    except ValueError:
                        return
            
            if var_move and var_move in board.legal_moves:
                board.push(var_move)
                self.current_best_variation_index += 1
                
                self.draw_right_board(board.fen(),
                                    highlight_squares=[var_move.from_square, var_move.to_square],
                                    arrow_from=var_move.from_square,
                                    arrow_to=var_move.to_square)
                
                move_san = variation[self.current_best_variation_index - 1].get('move_san', 'N/A')
                move_num = self.current_best_variation_index
                info_text = f"Best variation - Move {move_num}: {move_san}\n"
                if self.current_best_variation_index < len(variation):
                    next_move_san = variation[self.current_best_variation_index].get('move_san', 'N/A')
                    info_text += f"Next: {next_move_san}"
                else:
                    info_text += "End of variation shown."
                
                self.right_info_label.config(text=info_text)
                self.update_navigation_buttons()
    
    def right_prev_move(self):
        """Move backward in the best variation."""
        if self.current_best_variation_index <= 0:
            return
        
        self.current_best_variation_index -= 1
        
        if self.current_best_variation_index == 0:
            self.right_reset()
        else:
            position_fen = self.mistake_analysis.get('position_before_fen', self.mistake_analysis.get('position_fen'))
            board = chess.Board(position_fen)
            variation = self.mistake_analysis.get('best_moves', [{}])[0].get('variation', [])
            
            for i in range(self.current_best_variation_index):
                if i < len(variation):
                    var_move_data = variation[i]
                    var_move = var_move_data.get('move')
                    if isinstance(var_move, str):
                        try:
                            var_move = chess.Move.from_uci(var_move)
                        except ValueError:
                            try:
                                var_move = board.parse_san(var_move)
                            except ValueError:
                                continue
                    if var_move and var_move in board.legal_moves:
                        board.push(var_move)
            
            if self.current_best_variation_index > 0:
                prev_move_data = variation[self.current_best_variation_index - 1]
                prev_move = prev_move_data.get('move')
                if isinstance(prev_move, str):
                    try:
                        prev_move = chess.Move.from_uci(prev_move)
                    except ValueError:
                        try:
                            prev_move = board.parse_san(prev_move)
                        except ValueError:
                            prev_move = None
                
                if prev_move:
                    self.draw_right_board(board.fen(),
                                        highlight_squares=[prev_move.from_square, prev_move.to_square],
                                        arrow_from=prev_move.from_square,
                                        arrow_to=prev_move.to_square)
            
            move_san = variation[self.current_best_variation_index - 1].get('move_san', 'N/A') if self.current_best_variation_index > 0 else 'N/A'
            info_text = f"Best variation - Move {self.current_best_variation_index}: {move_san}"
            self.right_info_label.config(text=info_text)
            self.update_navigation_buttons()
    
    def update_navigation_buttons(self):
        """Update navigation button states for both boards."""
        # Left board (continuation)
        # Index: -1 = before mistake, 0 = after mistake, 1+ = continuation moves
        # When current_continuation_index = 0, we show variation[0] (first continuation move)
        # When current_continuation_index = len(variation)-1, we show the last move
        # When current_continuation_index = len(variation), we're past the end
        continuation_moves = self.mistake_analysis.get('continuation_moves', [])
        continuation_variation = continuation_moves[0].get('variation', []) if continuation_moves else []
        # Maximum index: we can go up to len(variation) (showing all moves)
        # When current_continuation_index = len(variation), we're past the end
        max_continuation_index = len(continuation_variation)
        
        self.left_prev_button.config(state=tk.NORMAL if self.current_continuation_index > -1 else tk.DISABLED)
        self.left_next_button.config(state=tk.NORMAL if self.current_continuation_index < max_continuation_index else tk.DISABLED)
        
        # Right board (best variation)
        best_moves = self.mistake_analysis.get('best_moves', [])
        best_variation = best_moves[0].get('variation', []) if best_moves else []
        
        self.right_prev_button.config(state=tk.NORMAL if self.current_best_variation_index > 0 else tk.DISABLED)
        self.right_next_button.config(state=tk.NORMAL if self.current_best_variation_index < len(best_variation) else tk.DISABLED)
    
    def draw_left_board(self, fen, highlight_squares=None, arrow_from=None, arrow_to=None):
        """Draw the left chess board from FEN with optional highlights."""
        self.draw_board(self.left_board_canvas, fen, highlight_squares, arrow_from, arrow_to)
    
    def draw_right_board(self, fen, highlight_squares=None, arrow_from=None, arrow_to=None):
        """Draw the right chess board from FEN with optional highlights."""
        self.draw_board(self.right_board_canvas, fen, highlight_squares, arrow_from, arrow_to)
    
    def draw_board(self, canvas, fen, highlight_squares=None, arrow_from=None, arrow_to=None):
        """Draw the chess board from FEN with optional highlights."""
        canvas.delete("all")
        board = chess.Board(fen)
        
        # Draw squares
        for row in range(8):
            for col in range(8):
                color = self.colors["light"] if (row + col) % 2 == 0 else self.colors["dark"]
                x1, y1 = col * self.square_size + 20, row * self.square_size + 20
                x2, y2 = x1 + self.square_size, y1 + self.square_size
                canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
        
        # Draw coordinates
        coord_font = font.Font(family='Segoe UI', size=9, weight='bold')
        files = "abcdefgh"
        ranks = "87654321"
        
        for i in range(8):
            # Files (bottom)
            canvas.create_text(
                20 + i * self.square_size + self.square_size / 2,
                20 + 8 * self.square_size + 12,
                text=files[i],
                font=coord_font,
                fill=self.colors["dark"] if i % 2 == 0 else self.colors["light"]
            )
            # Ranks (left)
            canvas.create_text(
                8,
                20 + i * self.square_size + self.square_size / 2,
                text=ranks[i],
                font=coord_font,
                fill=self.colors["light"] if i % 2 == 0 else self.colors["dark"]
            )
        
        # Draw pieces
        piece_font = font.Font(family='Segoe UI', size=38, weight='bold')
        for i in range(64):
            piece = board.piece_at(i)
            if piece:
                symbol = self.piece_symbols[piece.symbol()]
                piece_color = "#FFFFFF" if piece.color == chess.WHITE else "#000000"
                row, col = divmod(i, 8)
                display_row = 7 - row
                x = 20 + col * self.square_size + self.square_size / 2
                y = 20 + display_row * self.square_size + self.square_size / 2
                if piece.color == chess.BLACK:
                    canvas.create_text(x-0.5, y-0.5, text=symbol, font=piece_font, fill="#000000")
                canvas.create_text(x, y, text=symbol, font=piece_font, fill=piece_color)
        
        # Draw arrow first (behind highlights) if provided
        if arrow_from is not None and arrow_to is not None:
            from_row, from_col = chess.square_rank(arrow_from), chess.square_file(arrow_from)
            to_row, to_col = chess.square_rank(arrow_to), chess.square_file(arrow_to)
            
            from_display_row = 7 - from_row
            to_display_row = 7 - to_row

            x1 = 20 + from_col * self.square_size + self.square_size / 2
            y1 = 20 + from_display_row * self.square_size + self.square_size / 2
            x2 = 20 + to_col * self.square_size + self.square_size / 2
            y2 = 20 + to_display_row * self.square_size + self.square_size / 2

            # Draw arrow with bright red color for better visibility
            canvas.create_line(x1, y1, x2, y2, arrow=tk.LAST, arrowshape=(18, 22, 7), width=6, fill="#FF0000", tags="arrow")
        
        # Highlight squares if provided (draw after pieces so they're visible)
        if highlight_squares:
            for square in highlight_squares:
                try:
                    if isinstance(square, int):
                        row, col = chess.square_rank(square), chess.square_file(square)
                        display_row = 7 - row
                        x1, y1 = col * self.square_size + 20, display_row * self.square_size + 20
                        x2, y2 = x1 + self.square_size, y1 + self.square_size
                        # Draw highlight with bright yellow for better visibility
                        canvas.create_rectangle(x1, y1, x2, y2, outline="#FFD700", width=5, tags="highlight")
                        # Also add an inner highlight for better visibility
                        canvas.create_rectangle(x1+3, y1+3, x2-3, y2-3, outline="#FFA500", width=2, tags="highlight")
                except Exception as e:
                    print(f"Error highlighting square {square}: {e}")
