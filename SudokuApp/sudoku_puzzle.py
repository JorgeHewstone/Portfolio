# Class to hold the Sudoku board and provide move validation.
class SudokuPuzzle:
    def __init__(self, board):
        self.board = board

    def is_valid_move(self, board, row, col, value):
        """
        Checks if placing the given value in the board at (row, col) is valid.
        """
        # Check row
        if value in board[row]:
            return False
        # Check column
        for r in range(9):
            if board[r][col] == value:
                return False
        # Check 3x3 subgrid
        sub_row = (row // 3) * 3
        sub_col = (col // 3) * 3
        for i in range(3):
            for j in range(3):
                if board[sub_row + i][sub_col + j] == value:
                    return False
        return True
    
