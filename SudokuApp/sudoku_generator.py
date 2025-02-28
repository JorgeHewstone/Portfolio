import random

# Class to generate a complete Sudoku board and create puzzles with a unique solution.
class SudokuGenerator:
    def __init__(self, size=9):
        self.size = size

    def generate_puzzle(self, difficulty="Easy"):
        """
        Generates a Sudoku puzzle (9x9) with a unique solution
        by removing cells based on the specified difficulty.
        """
        full_board = self.generate_full_solution()
        puzzle = [row[:] for row in full_board]
        puzzle = self.remove_cells_with_unique_check(puzzle, difficulty)
        return puzzle

    def generate_full_solution(self, board=None):
        """
        Generates a complete Sudoku board (solved) using classic backtracking.
        """
        if board is None:
            board = [[0] * self.size for _ in range(self.size)]
        pos = self.find_empty(board)
        if not pos:
            return board  # Board is complete
        row, col = pos
        nums = list(range(1, self.size + 1))
        random.shuffle(nums)
        for num in nums:
            if self.is_valid_move(board, row, col, num):
                board[row][col] = num
                if self.generate_full_solution(board):
                    return board
                board[row][col] = 0  # Backtrack
        return None



    def remove_cells_with_unique_check(self, board, difficulty):
        """
        Genera un puzzle de sudoku eliminando celdas de forma inteligente,
        comprobando que la solución siga siendo única en cada paso.
        """
        # Determinar la cantidad de celdas a remover según la dificultad
        if difficulty.lower() == "easy":
            target_removed = 30
        elif difficulty.lower() == "medium":
            target_removed = 40
        else:  # "difícil"
            target_removed = 50

        removed = 0

        # Paso 1: Por cada columna, eliminar el número correspondiente (columna i: número i+1)
        for col in range(9):
            if removed >= target_removed:
                break  # Detenerse si ya se alcanzó la meta
            num_to_remove = col + 1  # asumiendo números del 1 al 9
            for row in range(9):
                if board[row][col] == num_to_remove:
                    backup = board[row][col]
                    board[row][col] = 0
                    board_copy = [r[:] for r in board]
                    if self.solve_sudoku_check_uniqueness(board_copy) == 1:
                        removed += 1
                    else:
                        board[row][col] = backup
                    break  # se elimina solo una ocurrencia por columna

        # Paso 2: En cada caja 3x3 completa, eliminar una celda al azar
        for box_row in range(3):
            if removed >= target_removed:
                break
            for box_col in range(3):
                if removed >= target_removed:
                    break
                start_row = box_row * 3
                start_col = box_col * 3
                # Verificar si la caja está completa (sin ceros)
                complete_box = all(board[start_row + i][start_col + j] != 0 for i in range(3) for j in range(3))
                if complete_box:
                    # Seleccionar aleatoriamente una celda dentro de la caja
                    cells = [(start_row + i, start_col + j) for i in range(3) for j in range(3)]
                    random.shuffle(cells)
                    for (r, c) in cells:
                        if removed >= target_removed:
                            break
                        backup = board[r][c]
                        board[r][c] = 0
                        board_copy = [row[:] for row in board]
                        if self.solve_sudoku_check_uniqueness(board_copy) == 1:
                            removed += 1
                            break
                        else:
                            board[r][c] = backup

        # Paso 3: Revisar tríos de columnas (0-2, 3-5, 6-8)
        for trio_start in [0, 3, 6]:
            if removed >= target_removed:
                break
            columns = list(range(trio_start, trio_start + 3))
            nums = list(range(1, 10))
            random.shuffle(nums)
            for num in nums:
                if removed >= target_removed:
                    break
                # Verificar si 'num' está presente en cada una de las 3 columnas
                if all(any(board[r][c] == num for r in range(9)) for c in columns):
                    chosen_col = random.choice(columns)
                    for r in range(9):
                        if removed >= target_removed:
                            break
                        if board[r][chosen_col] == num:
                            backup = board[r][chosen_col]
                            board[r][chosen_col] = 0
                            board_copy = [row[:] for row in board]
                            if self.solve_sudoku_check_uniqueness(board_copy) == 1:
                                removed += 1
                            else:
                                board[r][chosen_col] = backup
                            break

        # Paso 4: Revisar tríos de filas (0-2, 3-5, 6-8)
        for trio_start in [0, 3, 6]:
            if removed >= target_removed:
                break
            rows = list(range(trio_start, trio_start + 3))
            nums = list(range(1, 10))
            random.shuffle(nums)
            for num in nums:
                if removed >= target_removed:
                    break
                # Verificar si 'num' está presente en cada una de las 3 filas
                if all(any(board[r][c] == num for c in range(9)) for r in rows):
                    chosen_row = random.choice(rows)
                    for c in range(9):
                        if removed >= target_removed:
                            break
                        if board[chosen_row][c] == num:
                            backup = board[chosen_row][c]
                            board[chosen_row][c] = 0
                            board_copy = [row[:] for row in board]
                            if self.solve_sudoku_check_uniqueness(board_copy) == 1:
                                removed += 1
                            else:
                                board[chosen_row][c] = backup
                            break

        # Paso 5: Si aún faltan celdas por remover, continuar con eliminación aleatoria
        while removed < target_removed:
            r = random.randint(0, 8)
            c = random.randint(0, 8)
            if board[r][c] != 0:
                backup = board[r][c]
                board[r][c] = 0
                board_copy = [row[:] for row in board]
                if self.solve_sudoku_check_uniqueness(board_copy) == 1:
                    removed += 1
                else:
                    board[r][c] = backup

        return board


    def solve_sudoku_check_uniqueness(self, board, found=0):
        """
        Uses backtracking to count solutions (up to 2).
        Returns:
          0 = no solution,
          1 = unique solution,
          2 = more than one solution.
        """
        if found > 1:
            return 2
        pos = self.find_empty(board)
        if not pos:
            return found + 1
        row, col = pos
        for num in range(1, self.size + 1):
            if self.is_valid_move(board, row, col, num):
                board[row][col] = num
                found = self.solve_sudoku_check_uniqueness(board, found)
                board[row][col] = 0
                if found > 1:
                    break
        return found

    def is_valid_move(self, board, row, col, value):
        """
        Checks if placing 'value' at (row, col) is valid according to Sudoku rules.
        """
        # Check row
        if value in board[row]:
            return False
        # Check column
        for r in range(self.size):
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

    def find_empty(self, board):
        """
        Finds the first empty cell (with value 0) in the board.
        Returns (row, col) or None if the board is full.
        """
        for i in range(self.size):
            for j in range(self.size):
                if board[i][j] == 0:
                    return (i, j)
        return None
