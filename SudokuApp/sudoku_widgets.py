from kivy.core.window import Window
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.properties import NumericProperty, BooleanProperty
from kivy.graphics import Color, Line

# Button widget representing a Sudoku cell.
class SudokuCell(Button):
    row = NumericProperty(0)
    col = NumericProperty(0)
    fixed = BooleanProperty(False)


# Grid widget for displaying the Sudoku board.
class SudokuGrid(GridLayout):
    def __init__(self, sudoku_puzzle, **kwargs):
        super().__init__(**kwargs)
        self.sudoku_puzzle = sudoku_puzzle
        self.cols = 9
        self.rows = 9
        self.cells = []
        self.selected_number = None
        self.scale_factor=1
        

        self.update_size(self.scale_factor)  # Llamar a update_size al inicio para calcular el tamaño inicial

        for i in range(9):
            row_cells = []
            for j in range(9):
                value = sudoku_puzzle.board[i][j]
                cell = SudokuCell(
                    text=str(value) if value != 0 else "",
                    row=i, col=j, fixed=(value != 0),
                    font_size=self.cell_size / 1,  # Ajustar tamaño de fuente
                    background_disabled_normal="", background_normal="",
                    background_color=(0.3, 0.3, 1, 1) if value != 0 else (0.5, 0.5, 1, 1),
                    disabled_color=(1, 1, 1, 1), color=(1, 1, 1, 1)
                )
                if value == 0:
                    cell.bind(on_release=self.on_cell_pressed)
                row_cells.append(cell)
                self.add_widget(cell)
            self.cells.append(row_cells)

        self.bind(size=self.update_lines, pos=self.update_lines)
        self.update_lines()

    def update_size(self, scale=1):
        """Actualiza el tamaño de la grilla según la escala del ZoomScatter"""
        self.scale_factor = scale
        screen_width, screen_height = Window.size
        grid_prop = 0.75 * scale  # Ajustar con la escala del ZoomScatter
        grid_size = min(screen_width * grid_prop, screen_height * grid_prop)
        self.size = (grid_size, grid_size)
        self.pos = ((screen_width - grid_size) / 2, screen_height * 0.4)
        self.cell_size = grid_size / 9  # Tamaño de celda ajustado
        for row in self.cells:
            for cell in row:
                cell.font_size = self.cell_size / 1  # Ajustar tamaño de fuente

        
    def on_cell_pressed(self, cell):
        """
        Called when a cell is pressed. It calls the update_cell method of the GameScreen
        to update the board and adjust the count of empty cells.
        """
        if self.selected_number is None:
            return

        row, col = cell.row, cell.col
        # Convertir la selección: si es cadena vacía se interpreta como 0
        new_value = self.selected_number if self.selected_number != "" else 0

        from kivy.app import App
        game_screen = App.get_running_app().root.get_screen("game")
        game_screen.update_cell(row, col, new_value)
        # Actualizar el texto del botón (celda) según el valor actual del board
        cell.text = str(game_screen.sudoku_puzzle.board[row][col]) if game_screen.sudoku_puzzle.board[row][col] != 0 else ""

    def update_lines(self, *args):
        """ Dibuja las líneas del Sudoku con grosor adecuado """
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 1)
            cell_size = self.size[0] / 9

            # Dibujar líneas verticales
            for i in range(10):
                line_width = 2.5 if i % 3 == 0 else 1
                Line(points=[self.x + i * cell_size, self.y, self.x + i * cell_size, self.y + self.size[1]], width=line_width)

            # Dibujar líneas horizontales
            for j in range(10):
                line_width = 2.5 if j % 3 == 0 else 1
                Line(points=[self.x, self.y + j * cell_size, self.x + self.size[0], self.y + j * cell_size], width=line_width)


# Number pad widget with 9 buttons for selecting a number.
class NumberPad(BoxLayout):
    def __init__(self, sudoku_grid, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = Window.width * 0.01
        self.padding = [Window.width * 0.01]
        self.sudoku_grid = sudoku_grid
        self.scale_factor=1
        self.update_size(self.scale_factor) 

        for i in range(0, 10):
            text_i = str(i) if i > 0 else "<"
            btn = Button(
                text=text_i,
                font_size=self.btn_size ,
                size=(self.btn_size, self.btn_size),
                size_hint=(None, None),
                background_normal="", background_color=(0.3, 0.3, 1, 1)
            )
            btn.bind(on_release=self.on_number_button_pressed)
            self.add_widget(btn)

    def update_size(self, scale=1):
        """Actualiza el tamaño del NumberPad según la escala del ZoomScatter"""
        self.scale_factor = scale
        screen_width, screen_height = Window.size
        grid_prop = 0.75 * scale
        pad_width = min(screen_width * grid_prop, screen_height * grid_prop)
        pad_height = pad_width * 0.1 * scale  # Escalar con zoom

        self.size = (pad_width, pad_height)
        self.pos = ((screen_width - pad_width) / 2, screen_height * 0.25)

        self.btn_size = pad_width / 10 - self.spacing*scale  # Ajustar botones al nuevo tamaño
        for btn in self.children:
            btn.size = (self.btn_size*scale, self.btn_size*scale)
            btn.font_size = self.btn_size*scale  # Ajustar tamaño de fuente en botones


    def on_number_button_pressed(self, button):
        """ Sets the selected number in the Sudoku grid and updates the button appearance. """
        if button.text == "<":
            self.sudoku_grid.selected_number = ""
        else:
            self.sudoku_grid.selected_number = int(button.text)
        for child in self.children:
            child.background_color = (0.3, 0.3, 1, 1)
        button.background_color = (0.5, 0.5, 1, 1)


from kivy.uix.widget import Widget

class MainWidget(Widget):
    def __init__(self, sudoku_grid, number_pad, **kwargs):
        super().__init__(**kwargs)

        # Definir posiciones absolutas en vez de usar un BoxLayout con padding/spacing
        sudoku_grid.pos = (Window.width * 0.125, Window.height * 0.2)
        number_pad.pos = (Window.width * 0.125, Window.height * 0.05)

        self.add_widget(sudoku_grid)
        self.add_widget(number_pad)