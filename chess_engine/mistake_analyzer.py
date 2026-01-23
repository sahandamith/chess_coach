"""
Mistake Analyzer

This module categorizes chess mistakes and provides detailed analysis including
best move suggestions and mistake types (piece hanging, king safety, etc.).
"""

import chess
import chess.engine
from typing import List, Dict, Tuple, Optional


class MistakeAnalyzer:
    """
    Analyzes chess mistakes and categorizes them by type.
    """
    
    def __init__(self, engine):
        """
        Initialize the MistakeAnalyzer.
        
        Args:
            engine: The chess engine instance (e.g., Stockfish)
        """
        self.engine = engine
    
    def analyze_position(self, board: chess.Board, time_limit: float = 1.0) -> Dict:
        """
        Analyze a position and get evaluation and best moves.
        
        Args:
            board: The chess board position
            time_limit: Time limit for analysis in seconds
            
        Returns:
            Dictionary with 'eval', 'best_moves' (list of top moves), and 'info'
        """
        try:
            info = self.engine.analyse(board, chess.engine.Limit(time=time_limit), multipv=3)
            
            # Get evaluation
            score = info[0]["score"].white().score(mate_score=10000)
            
            # Get top 3 moves with full variations
            best_moves = []
            for i, move_info in enumerate(info[:3]):
                if "pv" in move_info and len(move_info["pv"]) > 0:
                    first_move = move_info["pv"][0]
                    move_eval = move_info["score"].white().score(mate_score=10000)
                    
                    # Get full variation (principal variation) - use all moves to show complete tactical/positional reason
                    variation_moves = []
                    temp_board = board.copy()
                    for move in move_info["pv"]:  # Use all moves in principal variation
                        if move in temp_board.legal_moves:
                            variation_moves.append({
                                'move': move,
                                'move_uci': move.uci(),
                                'move_san': temp_board.san(move)
                            })
                            temp_board.push(move)
                        else:
                            break
                    
                    best_moves.append({
                        'move': first_move,
                        'move_uci': first_move.uci(),
                        'move_san': board.san(first_move),
                        'eval': move_eval,
                        'depth': move_info.get('depth', 0),
                        'variation': variation_moves  # Full variation line
                    })
            
            return {
                'eval': score,
                'best_moves': best_moves,
                'info': info[0]
            }
        except Exception as e:
            print(f"Error analyzing position: {e}")
            return {'eval': None, 'best_moves': [], 'info': None}
    
    def categorize_mistake(self, board: chess.Board, prev_eval: float, curr_eval: float, 
                          move: chess.Move, board_before: chess.Board = None) -> Dict:
        """
        Categorize a mistake using explainable reason detectors.
        
        Args:
            board: The board position after the mistake
            prev_eval: Evaluation before the move (centipawns)
            curr_eval: Evaluation after the move (centipawns)
            move: The move that was played
            board_before: The board position before the mistake (optional)
            
        Returns:
            Dictionary with mistake category and details
        """
        if board_before is None:
            board_before = board.copy()
            try:
                board_before.pop()
            except:
                pass
        
        eval_drop = prev_eval - curr_eval  # Positive means position got worse
        mover = board.turn  # The player who just moved (opponent's turn now)
        
        # Run all detectors and collect reasons
        reasons = []
        
        # Priority 1: Immediate threats (highest priority)
        reason = self._hanging_piece(board, mover)
        if reason:
            reasons.append((1, reason))
        
        reason = self._missed_mate_threat(board, mover)
        if reason:
            reasons.append((1, reason))
        
        # Priority 2: Material issues
        reason = self._allowed_hanging_piece_next_move(board, mover)
        if reason:
            reasons.append((2, reason))
        
        reason = self._lost_material(board_before, board, mover)
        if reason:
            reasons.append((2, reason))
        
        reason = self._bad_trade_exchange(board_before, move, mover)
        if reason:
            reasons.append((2, reason))
        
        reason = self._missed_winning_capture(board_before, mover)
        if reason:
            reasons.append((2, reason))
        
        # Priority 3: Tactical issues
        reason = self._walked_into_knight_fork(board, mover)
        if reason:
            reasons.append((3, reason))
        
        reason = self._discovered_attack_allowed(board_before, board, mover)
        if reason:
            reasons.append((3, reason))
        
        reason = self._ignored_threat(board_before, board, eval_drop)
        if reason:
            reasons.append((3, reason))
        
        # Priority 4: King safety
        reason = self._king_safety_worsened(board_before, board, mover)
        if reason:
            reasons.append((4, reason))
        
        reason = self._opened_king_lines(board_before, board, mover)
        if reason:
            reasons.append((4, reason))
        
        reason = self._back_rank_weakness(board, mover)
        if reason:
            reasons.append((4, reason))
        
        # Priority 5: Positional issues
        reason = self._lost_center_control(board_before, board, mover)
        if reason:
            reasons.append((5, reason))
        
        reason = self._created_weak_square(board_before, board, mover)
        if reason:
            reasons.append((5, reason))
        
        # Priority 6: Endgame/Pawn issues
        reason = self._endgame_pawn_mistake(board_before, board)
        if reason:
            reasons.append((6, reason))
        
        reason = self._passed_pawn_allowed(board_before, board, mover)
        if reason:
            reasons.append((6, reason))
        
        # Priority 7: Tempo/Opening issues (lowest priority)
        reason = self._opening_principle_violation(board_before, move, board.fullmove_number)
        if reason:
            reasons.append((7, reason))
        
        # Choose best reason(s)
        if reasons:
            reasons.sort(key=lambda x: x[0])  # Sort by priority
            headline = reasons[0][1]
            details_list = [r[1] for r in reasons[1:3]]  # Up to 2 more details
            
            return {
                'categories': [headline.get('category', 'General Mistake')],
                'primary_category': headline.get('category', 'General Mistake'),
                'details': {
                    'headline': headline.get('message', ''),
                    'detail': headline.get('detail', ''),
                    'detail_lines': details_list
                },
                'eval_drop': eval_drop
            }
        else:
            # Fallback if no specific reason found
            return {
                'categories': ['General Mistake'],
                'primary_category': 'General Mistake',
                'details': {
                    'headline': f"Move worsened the position by {eval_drop/100.0:.2f} pawns",
                    'detail': '',
                    'detail_lines': []
                },
                'eval_drop': eval_drop
            }
    
    # ========== Explainable Reason Detectors ==========
    
    def _hanging_piece(self, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 1: You hung a piece (immediate)."""
        opponent = not mover
        for square in chess.SQUARES:
            piece = board_after.piece_at(square)
            if piece and piece.color == mover and piece.piece_type != chess.KING:
                attackers = board_after.attackers(opponent, square)
                defenders = board_after.attackers(mover, square)
                if len(attackers) > 0 and len(defenders) == 0:
                    piece_name = chess.piece_name(piece.piece_type).capitalize()
                    square_name = chess.square_name(square)
                    attacker_info = []
                    for attacker_sq in attackers:
                        attacker_piece = board_after.piece_at(attacker_sq)
                        if attacker_piece:
                            attacker_name = chess.piece_name(attacker_piece.piece_type).capitalize()
                            attacker_sq_name = chess.square_name(attacker_sq)
                            attacker_info.append(f"{attacker_name} on {attacker_sq_name}")
                    if attacker_info:
                        return {
                            'category': 'Hanging Piece',
                            'message': f"You left a piece undefended.",
                            'detail': f"{piece_name} on {square_name} can be captured by {', '.join(attacker_info)}"
                        }
        return None
    
    def _allowed_hanging_piece_next_move(self, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 2: You allowed a piece to be won next move."""
        opponent = not mover
        for move in board_after.legal_moves:
            if move.from_square is not None and board_after.piece_at(move.from_square) and board_after.piece_at(move.from_square).color == opponent:
                if board_after.piece_at(move.to_square) and board_after.piece_at(move.to_square).color == mover:
                    # Opponent can capture a piece
                    captured_piece = board_after.piece_at(move.to_square)
                    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                                   chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
                    captured_value = piece_values.get(captured_piece.piece_type, 0)
                    
                    # Check if recapture is possible and meaningful
                    board_temp = board_after.copy()
                    board_temp.push(move)
                    recaptures = [m for m in board_temp.legal_moves if m.to_square == move.to_square and 
                                 board_temp.piece_at(m.from_square) and board_temp.piece_at(m.from_square).color == mover]
                    
                    if not recaptures or captured_value >= 5:  # High value piece or no recapture
                        piece_name = chess.piece_name(captured_piece.piece_type).capitalize()
                        square_name = chess.square_name(move.to_square)
                        return {
                            'category': 'Material Loss',
                            'message': f"You allowed your opponent to win material.",
                            'detail': f"{piece_name} on {square_name} can be captured next move"
                        }
        return None
    
    def _lost_material(self, board_before: chess.Board, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 3: You lost material (net count changed)."""
        piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                       chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
        
        def material_count(board, color):
            total = 0
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.color == color:
                    total += piece_values.get(piece.piece_type, 0)
            return total
        
        mat_before = material_count(board_before, mover) - material_count(board_before, not mover)
        mat_after = material_count(board_after, mover) - material_count(board_after, not mover)
        
        if mat_after < mat_before:
            loss = mat_before - mat_after
            return {
                'category': 'Material Loss',
                'message': f"You lost material.",
                'detail': f"Material advantage changed from {mat_before:.1f} to {mat_after:.1f} (lost {loss:.1f} points)"
            }
        return None
    
    def _bad_trade_exchange(self, board_before: chess.Board, move: chess.Move, mover: bool) -> Optional[Dict]:
        """Detector 4: Bad trade (exchange / unequal swap)."""
        if board_before.piece_at(move.to_square):  # It's a capture
            captured_piece = board_before.piece_at(move.to_square)
            capturing_piece = board_before.piece_at(move.from_square)
            
            piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                           chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
            
            captured_value = piece_values.get(captured_piece.piece_type, 0)
            mover_value = piece_values.get(capturing_piece.piece_type, 0)
            
            if mover_value > captured_value + 1:  # Margin of 1 point
                captured_name = chess.piece_name(captured_piece.piece_type).capitalize()
                mover_name = chess.piece_name(capturing_piece.piece_type).capitalize()
                return {
                    'category': 'Bad Trade',
                    'message': f"That trade favored your opponent.",
                    'detail': f"You traded a {mover_name} ({mover_value} points) for a {captured_name} ({captured_value} points)"
                }
        return None
    
    def _missed_winning_capture(self, board_before: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 5: You missed a free win (missed winning capture)."""
        for move in board_before.legal_moves:
            if board_before.piece_at(move.from_square) and board_before.piece_at(move.from_square).color == mover:
                if board_before.piece_at(move.to_square):  # It's a capture
                    captured_piece = board_before.piece_at(move.to_square)
                    piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                                   chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
                    captured_value = piece_values.get(captured_piece.piece_type, 0)
                    
                    # Check if capture is safe
                    board_temp = board_before.copy()
                    board_temp.push(move)
                    recaptures = [m for m in board_temp.legal_moves 
                                 if m.to_square == move.to_square 
                                 and board_temp.piece_at(m.from_square) 
                                 and board_temp.piece_at(m.from_square).color == (not mover)]
                    
                    if not recaptures or captured_value >= 3:  # Safe capture or high value
                        try:
                            move_san = board_before.san(move)
                        except:
                            move_san = move.uci()
                        piece_name = chess.piece_name(captured_piece.piece_type).capitalize()
                        return {
                            'category': 'Missed Opportunity',
                            'message': f"You missed a chance to win material.",
                            'detail': f"You could have captured {piece_name} with {move_san}"
                        }
        return None
    
    def _walked_into_knight_fork(self, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 6a: Knight fork allowed."""
        opponent = not mover
        piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                       chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
        
        for square in chess.SQUARES:
            piece = board_after.piece_at(square)
            if piece and piece.piece_type == chess.KNIGHT and piece.color == opponent:
                for move in board_after.legal_moves:
                    if move.from_square == square:
                        board_temp = board_after.copy()
                        board_temp.push(move)
                        # Count high-value pieces attacked
                        attacked_targets = []
                        for target_sq in chess.SQUARES:
                            target_piece = board_temp.piece_at(target_sq)
                            if target_piece and target_piece.color == mover:
                                if board_temp.attackers(opponent, target_sq):
                                    attacked_targets.append((target_sq, target_piece))
                        
                        if len(attacked_targets) >= 2:
                            try:
                                move_san = board_after.san(move)
                            except:
                                move_san = move.uci()
                            targets_str = ", ".join([chess.piece_name(p.piece_type).capitalize() + " on " + chess.square_name(sq) 
                                                    for sq, p in attacked_targets[:2]])
                            return {
                                'category': 'Tactical Blunder',
                                'message': f"This move allows a tactic (fork).",
                                'detail': f"Knight can fork {targets_str} with {move_san}"
                            }
        return None
    
    def _discovered_attack_allowed(self, board_before: chess.Board, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 6b: Discovered attack allowed."""
        opponent = not mover
        king_sq = board_after.king(mover)
        if king_sq is None:
            return None
        
        # Check if a slider (bishop/rook/queen) can now attack high-value pieces
        for square in chess.SQUARES:
            piece = board_after.piece_at(square)
            if piece and piece.color == opponent and piece.piece_type in [chess.BISHOP, chess.ROOK, chess.QUEEN]:
                # Check if this piece can now attack something valuable
                for target_sq in chess.SQUARES:
                    target_piece = board_after.piece_at(target_sq)
                    if target_piece and target_piece.color == mover:
                        piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                                       chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
                        if piece_values.get(target_piece.piece_type, 0) >= 3:
                            # Check if line is open
                            if board_after.attackers(opponent, target_sq):
                                piece_name = chess.piece_name(piece.piece_type).capitalize()
                                target_name = chess.piece_name(target_piece.piece_type).capitalize()
                                return {
                                    'category': 'Tactical Blunder',
                                    'message': f"You opened a line for an attack.",
                                    'detail': f"Your move unblocked a {piece_name} that can attack {target_name}"
                                }
        return None
    
    def _missed_mate_threat(self, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 7: You missed an immediate mate threat."""
        opponent = not mover
        for move in board_after.legal_moves:
            if board_after.piece_at(move.from_square) and board_after.piece_at(move.from_square).color == opponent:
                board_temp = board_after.copy()
                board_temp.push(move)
                if board_temp.is_checkmate():
                    try:
                        move_san = board_after.san(move)
                    except:
                        move_san = move.uci()
                    return {
                        'category': 'Checkmate Threat',
                        'message': f"You allowed checkmate.",
                        'detail': f"Opponent can deliver checkmate with {move_san}"
                    }
        return None
    
    def _ignored_threat(self, board_before: chess.Board, board_after: chess.Board, eval_drop: float) -> Optional[Dict]:
        """Detector 8: You ignored a direct threat."""
        if eval_drop > 200:  # Large eval drop
            # Check if there was a hanging piece before
            for square in chess.SQUARES:
                piece = board_before.piece_at(square)
                if piece and piece.color == board_before.turn:
                    attackers = board_before.attackers(not piece.color, square)
                    if len(attackers) > 0:
                        return {
                            'category': 'Ignored Threat',
                            'message': f"You didn't address the threat.",
                            'detail': "A piece was already under attack"
                        }
        return None
    
    def _king_safety_worsened(self, board_before: chess.Board, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 9: You weakened your king."""
        def king_safety_proxy(board, color):
            king_sq = board.king(color)
            if king_sq is None:
                return 0
            attackers = len(board.attackers(not color, king_sq))
            if board.is_check():
                return attackers + 10  # Check is worse
            return attackers
        
        safety_before = king_safety_proxy(board_before, mover)
        safety_after = king_safety_proxy(board_after, mover)
        
        if safety_after > safety_before + 1:  # Threshold
            if board_after.is_check():
                return {
                    'category': 'King Safety',
                    'message': f"You left your king unsafe.",
                    'detail': "Your king is now in check"
                }
            else:
                return {
                    'category': 'King Safety',
                    'message': f"You left your king unsafe.",
                    'detail': "Enemy pieces are now attacking your king"
                }
        return None
    
    def _opened_king_lines(self, board_before: chess.Board, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 10: You opened dangerous lines near your king."""
        king_sq = board_after.king(mover)
        if king_sq is None:
            return None
        
        king_file = chess.square_file(king_sq)
        king_rank = chess.square_rank(king_sq)
        
        # Check if pawns moved from files near king
        # This is simplified - in full implementation, check if lines opened
        opponent = not mover
        for square in chess.SQUARES:
            piece = board_after.piece_at(square)
            if piece and piece.color == opponent and piece.piece_type in [chess.ROOK, chess.QUEEN]:
                # Check if this piece can now attack along file/rank toward king
                if chess.square_file(square) == king_file or chess.square_rank(square) == king_rank:
                    if board_after.attackers(opponent, king_sq):
                        return {
                            'category': 'King Safety',
                            'message': f"You opened a file/diagonal toward your king.",
                            'detail': "Pawn move weakened king cover"
                        }
        return None
    
    def _back_rank_weakness(self, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 11: Back-rank weakness created."""
        king_sq = board_after.king(mover)
        if king_sq is None:
            return None
        
        king_rank = chess.square_rank(king_sq)
        back_rank = 0 if mover == chess.WHITE else 7
        
        if king_rank == back_rank:
            # Check if king has escape squares
            escape_squares = []
            for offset in [8, -8, 1, -1, 9, -9, 7, -7]:  # All directions
                try:
                    escape_sq = king_sq + offset
                    if 0 <= escape_sq < 64:
                        if not board_after.piece_at(escape_sq) or board_after.piece_at(escape_sq).color != mover:
                            escape_squares.append(escape_sq)
                except:
                    pass
            
            if len(escape_squares) == 0:
                opponent = not mover
                # Check if opponent has rook/queen that can access back rank
                for square in chess.SQUARES:
                    piece = board_after.piece_at(square)
                    if piece and piece.color == opponent and piece.piece_type in [chess.ROOK, chess.QUEEN]:
                        if chess.square_rank(square) == back_rank:
                            return {
                                'category': 'King Safety',
                                'message': f"You created back-rank weaknesses.",
                                'detail': "Your king is trapped on the back rank"
                            }
        return None
    
    def _lost_center_control(self, board_before: chess.Board, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 12: You lost control of the center."""
        center_squares = [chess.E4, chess.E5, chess.D4, chess.D5]
        
        def center_control(board, color):
            control = 0
            for sq in center_squares:
                if board.attackers(color, sq):
                    control += 1
            return control
        
        before = center_control(board_before, mover)
        after = center_control(board_after, mover)
        
        if after < before:
            return {
                'category': 'Positional Mistake',
                'message': f"You lost control of the center.",
                'detail': f"Center control decreased from {before} to {after} squares"
            }
        return None
    
    def _created_weak_square(self, board_before: chess.Board, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 13: You created a weak square."""
        # Simplified: check if pawn moved and left weak squares
        # Full implementation would track which squares were controlled before
        return None  # Complex to implement fully
    
    def _endgame_pawn_mistake(self, board_before: chess.Board, board_after: chess.Board) -> Optional[Dict]:
        """Detector 16: Endgame pawn mistake."""
        piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                       chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
        
        total_non_pawn = 0
        for square in chess.SQUARES:
            piece = board_after.piece_at(square)
            if piece and piece.piece_type != chess.PAWN:
                total_non_pawn += piece_values.get(piece.piece_type, 0)
        
        if total_non_pawn <= 10:  # Endgame threshold
            # Check for isolated/doubled pawns (simplified)
            return {
                'category': 'Endgame Mistake',
                'message': f"In the endgame, king activity/pawn structure matters more.",
                'detail': "Consider centralizing your king and improving pawn structure"
            }
        return None
    
    def _passed_pawn_allowed(self, board_before: chess.Board, board_after: chess.Board, mover: bool) -> Optional[Dict]:
        """Detector 17: You allowed a passed pawn."""
        # Simplified: check if opponent has more passed pawns
        def count_passed_pawns(board, color):
            count = 0
            for square in chess.SQUARES:
                piece = board.piece_at(square)
                if piece and piece.color == color and piece.piece_type == chess.PAWN:
                    file = chess.square_file(square)
                    rank = chess.square_rank(square)
                    # Check if it's passed (no enemy pawns in front on adjacent files)
                    is_passed = True
                    for adj_file in [file - 1, file, file + 1]:
                        if 0 <= adj_file < 8:
                            for check_rank in range(rank + 1, 8) if color == chess.WHITE else range(rank - 1, -1, -1):
                                check_sq = chess.square(adj_file, check_rank)
                                check_piece = board.piece_at(check_sq)
                                if check_piece and check_piece.piece_type == chess.PAWN and check_piece.color != color:
                                    is_passed = False
                                    break
                    if is_passed:
                        count += 1
            return count
        
        opponent = not mover
        passed_before = count_passed_pawns(board_before, opponent)
        passed_after = count_passed_pawns(board_after, opponent)
        
        if passed_after > passed_before:
            return {
                'category': 'Endgame Mistake',
                'message': f"You allowed a dangerous passed pawn.",
                'detail': "Opponent created a passed pawn that can advance"
            }
        return None
    
    def _opening_principle_violation(self, board_before: chess.Board, move: chess.Move, ply: int) -> Optional[Dict]:
        """Detector 15: Opening principle violation."""
        if ply <= 20:
            piece = board_before.piece_at(move.from_square)
            if piece:
                # Queen out too early
                if piece.piece_type == chess.QUEEN:
                    # Check if minor pieces are developed
                    minor_developed = 0
                    for sq in chess.SQUARES:
                        p = board_before.piece_at(sq)
                        if p and p.color == piece.color and p.piece_type in [chess.KNIGHT, chess.BISHOP]:
                            if sq not in [chess.B1, chess.G1, chess.C1, chess.F1, chess.B8, chess.G8, chess.C8, chess.F8]:
                                minor_developed += 1
                    if minor_developed < 2:
                        return {
                            'category': 'Opening Mistake',
                            'message': f"In the opening, this breaks basic principles.",
                            'detail': "You brought the queen out too early - develop minor pieces first"
                        }
                
                # Edge pawn move
                if piece.piece_type == chess.PAWN:
                    file = chess.square_file(move.from_square)
                    if file in [0, 7]:  # a or h file
                        return {
                            'category': 'Opening Mistake',
                            'message': f"In the opening, this breaks basic principles.",
                            'detail': "This pawn move on the edge doesn't help development"
                        }
        return None
    
    # ========== Old methods (kept for compatibility) ==========
    
    def _is_piece_hanging(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if a piece is hanging (undefended and can be captured)."""
        # Check if the moved piece is now undefended
        to_square = move.to_square
        piece = board.piece_at(to_square)
        
        if piece is None:
            return False
        
        # Check if the piece can be captured
        attackers = board.attackers(not piece.color, to_square)
        defenders = board.attackers(piece.color, to_square)
        
        # If there are more attackers than defenders, piece is hanging
        if len(attackers) > len(defenders):
            return True
        
        # Check if a valuable piece was left undefended
        piece_values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, 
                       chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 100}
        if piece_values.get(piece.piece_type, 0) >= 3 and len(defenders) == 0:
            return True
        
        return False
    
    def _get_hanging_piece_info(self, board: chess.Board, move: chess.Move) -> str:
        """Get detailed information about a hanging piece."""
        to_square = move.to_square
        piece = board.piece_at(to_square)
        if piece:
            piece_name = chess.piece_name(piece.piece_type).capitalize()
            square_name = chess.square_name(to_square)
            attackers = board.attackers(not piece.color, to_square)
            defenders = board.attackers(piece.color, to_square)
            
            # Get attacker details
            attacker_info = []
            for attacker_sq in attackers:
                attacker_piece = board.piece_at(attacker_sq)
                if attacker_piece:
                    attacker_name = chess.piece_name(attacker_piece.piece_type).capitalize()
                    attacker_sq_name = chess.square_name(attacker_sq)
                    attacker_info.append(f"{attacker_name} on {attacker_sq_name}")
            
            if attacker_info:
                attackers_str = ", ".join(attacker_info)
                if len(defenders) == 0:
                    return f"{piece_name} on {square_name} is undefended and can be captured by {attackers_str}"
                else:
                    return f"{piece_name} on {square_name} is attacked by {attackers_str} (only {len(defenders)} defender(s))"
            return f"{piece_name} on {square_name} is hanging"
        return "Piece is hanging"
    
    def _is_king_safety_issue(self, board: chess.Board, move: chess.Move) -> bool:
        """Check if the move created king safety issues."""
        # Check if king is in check
        if board.is_check():
            return True
        
        # Check if king's safety was weakened (simplified check)
        king_square = board.king(board.turn)
        if king_square is not None:
            # Count attackers near the king
            attackers = len(board.attackers(not board.turn, king_square))
            if attackers > 0:
                return True
        
        return False
    
    def _get_king_safety_info(self, board: chess.Board) -> str:
        """Get detailed information about king safety issues."""
        if board.is_check():
            king_square = board.king(board.turn)
            if king_square:
                king_sq_name = chess.square_name(king_square)
                attackers = board.attackers(not board.turn, king_square)
                attacker_info = []
                for attacker_sq in attackers:
                    attacker_piece = board.piece_at(attacker_sq)
                    if attacker_piece:
                        attacker_name = chess.piece_name(attacker_piece.piece_type).capitalize()
                        attacker_sq_name = chess.square_name(attacker_sq)
                        attacker_info.append(f"{attacker_name} on {attacker_sq_name}")
                if attacker_info:
                    return f"King on {king_sq_name} is in check by {', '.join(attacker_info)}"
            return "King is in check"
        
        king_square = board.king(board.turn)
        if king_square:
            king_sq_name = chess.square_name(king_square)
            attackers = board.attackers(not board.turn, king_square)
            if attackers:
                attacker_info = []
                for attacker_sq in attackers:
                    attacker_piece = board.piece_at(attacker_sq)
                    if attacker_piece:
                        attacker_name = chess.piece_name(attacker_piece.piece_type).capitalize()
                        attacker_sq_name = chess.square_name(attacker_sq)
                        attacker_info.append(f"{attacker_name} on {attacker_sq_name}")
                if attacker_info:
                    return f"King on {king_sq_name} is under attack by {', '.join(attacker_info)}"
        return "King safety weakened"
    
    def _is_tactical_blunder(self, board: chess.Board, move: chess.Move, eval_drop: float) -> bool:
        """Check if this is a tactical blunder."""
        # Large evaluation drops often indicate tactical issues
        if eval_drop > 200:
            return True
        return False
    
    def _is_positional_mistake(self, board: chess.Board, move: chess.Move, eval_drop: float) -> bool:
        """Check if this is a positional mistake."""
        # Medium evaluation drops often indicate positional issues
        if 100 <= eval_drop <= 200:
            return True
        return False
    
    def _is_endgame_mistake(self, board: chess.Board, move: chess.Move, eval_drop: float) -> bool:
        """Check if this is an endgame mistake."""
        # Check if we're in endgame (few pieces left)
        piece_count = len(board.piece_map())
        if piece_count <= 10:  # Endgame threshold
            return True
        return False
    
    def _get_tactical_details(self, board: chess.Board, move: chess.Move, eval_drop: float) -> str:
        """Get detailed tactical mistake information."""
        move_san = board.san(move) if move in board.legal_moves else move.uci()
        to_square = move.to_square
        to_sq_name = chess.square_name(to_square)
        
        # Check if piece was left hanging
        if move.from_square is not None:
            from_sq_name = chess.square_name(move.from_square)
            piece = board.piece_at(to_square)
            if piece:
                piece_name = chess.piece_name(piece.piece_type).capitalize()
                attackers = board.attackers(not piece.color, to_square)
                if attackers:
                    return f"After {move_san}, {piece_name} on {to_sq_name} is vulnerable to tactical threats (eval drop: {eval_drop/100.0:.2f} pawns)"
        
        return f"Move {move_san} to {to_sq_name} fell into a tactical trap or missed a tactical opportunity (eval drop: {eval_drop/100.0:.2f} pawns)"
    
    def _get_positional_details(self, board: chess.Board, move: chess.Move) -> str:
        """Get detailed positional mistake information."""
        move_san = board.san(move) if move in board.legal_moves else move.uci()
        to_square = move.to_square
        to_sq_name = chess.square_name(to_square)
        piece = board.piece_at(to_square)
        
        if piece:
            piece_name = chess.piece_name(piece.piece_type).capitalize()
            
            # Check if piece is on a weak square
            attackers = board.attackers(not piece.color, to_square)
            defenders = board.attackers(piece.color, to_square)
            
            if len(attackers) > len(defenders):
                return f"{piece_name} on {to_sq_name} after {move_san} is poorly placed - more attackers than defenders"
            
            # Check if piece blocks important squares
            return f"Move {move_san} ({piece_name} to {to_sq_name}) weakens the position or loses control of key squares"
        
        return f"Move {move_san} to {to_sq_name} weakens the position"
    
    def _get_endgame_details(self, board: chess.Board, move: chess.Move) -> str:
        """Get detailed endgame mistake information."""
        move_san = board.san(move) if move in board.legal_moves else move.uci()
        to_square = move.to_square
        to_sq_name = chess.square_name(to_square)
        piece = board.piece_at(to_square)
        
        if piece:
            piece_name = chess.piece_name(piece.piece_type).capitalize()
            
            # Check king activity in endgame
            if piece.piece_type == chess.KING:
                return f"King move {move_san} to {to_sq_name} is suboptimal - king should be more active in endgame"
            
            # Check pawn moves
            if piece.piece_type == chess.PAWN:
                return f"Pawn move {move_san} to {to_sq_name} is poor endgame technique - consider king activity or pawn promotion"
            
            return f"{piece_name} move {move_san} to {to_sq_name} is suboptimal endgame play"
        
        return f"Move {move_san} shows poor endgame technique"
    
    def analyze_mistake_position(self, board: chess.Board, prev_eval: float, 
                                 curr_eval: float, move: chess.Move, best_moves=None) -> Dict:
        """
        Complete analysis of a mistake position.
        
        Args:
            board: The board position BEFORE the mistake (White to move)
            prev_eval: Evaluation before the move (already calculated)
            curr_eval: Evaluation after the move (already calculated)
            move: The move that was played
            best_moves: Pre-calculated best moves (optional, to avoid re-analysis)
            
        Returns:
            Dictionary with complete mistake analysis
        """
        # Use provided best moves if available, otherwise analyze
        if best_moves is None:
            analysis = self.analyze_position(board, time_limit=1.0)
            best_moves = analysis.get('best_moves', [])
        
        # Create board after the mistake to analyze what went wrong
        board_after = board.copy()
        board_after.push(move)
        
        # Categorize the mistake (using board after to see consequences)
        mistake_info = self.categorize_mistake(board_after, prev_eval, curr_eval, move)
        
        # Get move in SAN notation
        try:
            move_san = board.san(move)
        except:
            move_san = move.uci()
        
        return {
            'position_fen': board.fen(),  # Position BEFORE mistake
            'position_after_fen': board_after.fen(),  # Position AFTER mistake
            'move_played': move.uci(),
            'move_played_san': move_san,
            'prev_eval': prev_eval,
            'curr_eval': curr_eval,
            'eval_drop': mistake_info['eval_drop'],
            'categories': mistake_info['categories'],
            'primary_category': mistake_info['primary_category'],
            'details': mistake_info['details'],
            'best_moves': best_moves,  # Use provided best moves (from initial analysis)
            'position_eval': prev_eval  # Use provided eval (from initial analysis)
        }
