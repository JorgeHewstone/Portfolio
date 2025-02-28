from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout

from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')


from sudoku_generator import SudokuGenerator
from sudoku_puzzle import SudokuPuzzle
from sudoku_widgets import SudokuGrid, NumberPad

from kivy.uix.scatter import Scatter

class ZoomScatter(Scatter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_rotation = False  # Deshabilita la rotación (para evitar gestos innecesarios)
        self.do_translation = True  # Permitir mover con los dedos
        self.do_scale = True  # Permitir zoom con pellizco (pinch-to-zoom)
        self.auto_bring_to_front = False  # Evitar que se mueva en jerarquía de widgets

    def on_touch_down(self, touch):
        if touch.is_mouse_scrolling:
            return True 
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current == self:
            return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        return super().on_touch_up(touch)


class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        screen_width, screen_height = Window.size
        self.font_size=screen_height*0.04
        self.sudoku_grid = None
        self.number_pad = None
        self.back_button = None
        self.timer_label = None  # Inicializar en None
        self.timer_seconds = 0  # ← Agregado para evitar el error
        self.clock_event = None  # ← Agregado para evitar el error
        self.timer_label = Label(
            text="00:00",
            font_size=self.font_size,
            size_hint=(None, None)
        )
        Window.bind(size=self.update_layout)
    def start_game(self, difficulty):
        """
        Initializes a new Sudoku game based on the selected difficulty.
        """
        screen_width, screen_height = Window.size
        generator = SudokuGenerator()
        board = generator.generate_puzzle(difficulty)
        puzzle = SudokuPuzzle(board)
                # Luego de: puzzle = SudokuPuzzle(board)
        self.sudoku_puzzle = puzzle  # Guarda el puzzle en un atributo para usar en validaciones

        # Definir la cuenta inicial según la dificultad
        if difficulty == "easy":
            self.remaining_zeros_count = 30
        elif difficulty == "medium":
            self.remaining_zeros_count = 40
        elif difficulty == "hard":
            self.remaining_zeros_count = 50


        # Sudoku Grid (centrado)
        self.sudoku_grid = SudokuGrid(puzzle)

        # Panel de números (centrado abajo)
        self.number_pad = NumberPad(self.sudoku_grid)
        self.number_pad.size_hint=(None,None) 
        # Reiniciar temporizador
        self.timer_seconds = 0  
        self.timer_label.text = "00:00"

        if self.timer_label.parent:
            self.timer_label.parent.remove_widget(self.timer_label)

        # Detener temporizador anterior (si existe)
        if self.clock_event:
            Clock.unschedule(self.clock_event)
        self.clock_event = Clock.schedule_interval(self.update_timer, 1)

        # Crear botón "Main Menu"
        self.back_button = Button(
            text="Main Menu",
            font_size=self.font_size,
            size_hint=(None, None),
            background_color=(0.4, 0.4, 1, 1)
        )
        self.back_button.bind(on_release=self.go_to_menu)

        # Limpiar widgets anteriores
        self.clear_widgets()

        # Contenedor principal
        container = Widget()  # Si prefieres posicionamiento absoluto, también podrías usar FloatLayout.
        container.add_widget(self.back_button)
        container.add_widget(self.timer_label)
        container.add_widget(self.sudoku_grid)
        container.add_widget(self.number_pad)
        
        
        # Envolver el contenedor en ZoomScatter para habilitar zoom y arrastre
        self.zoom_scatter = ZoomScatter(do_translation=True, do_scale=True, scale=1)
        self.zoom_scatter.scale_min = 1
        self.zoom_scatter.scale_max = 3
        self.zoom_scatter.size = (Window.width, Window.height)
        self.zoom_scatter.add_widget(container)
        
        self.zoom_scatter.bind(scale=self.on_zoom)

        self.add_widget(self.zoom_scatter)

        Clock.schedule_once(self.update_layout)
    def on_zoom(self, instance, scale):
        """🔥 Notifica a `SudokuGrid` y `NumberPad` cuando cambia el zoom"""
        self.sudoku_grid.update_size(scale)
        self.number_pad.update_size(scale)
    def update_layout(self, *args):
        """Actualiza la posición del menú, timer y Sudoku Grid."""
        # **Evita errores si los widgets no están creados**
        if not self.sudoku_grid or not self.back_button or not self.timer_label:
            return

        screen_width, screen_height = Window.size
        if self.zoom_scatter and len(self.zoom_scatter.children) > 0:
            container = self.zoom_scatter.children[0]  # Tomamos el primer widget
            container.size = (screen_width, screen_height)


        # Actualiza el zoom scatter para que cubra toda la pantalla
        self.zoom_scatter.pos = (0, 0)
        self.zoom_scatter.size = (screen_width, screen_height)
        
        grid_size = min(screen_width * 0.75, screen_height * 0.75)

        # **Posicionar Sudoku Grid centrado**
        grid_x = (screen_width - grid_size) / 2
        grid_y = screen_height * 0.4
        self.sudoku_grid.pos = (grid_x, grid_y)
        self.sudoku_grid.size = (grid_size, grid_size)

        # **Posicionar Panel de Números abajo centrado**
        self.number_pad.pos = (grid_x,grid_y - grid_size*0.25 )
        self.number_pad.size = (grid_size, grid_size  * 0.1)

        # **Definir tamaños**
        button_width = grid_size 
        button_height = grid_size * 0.15
        timer_width = grid_size * 0.25
        timer_height = grid_size * 0.08
        spacing = grid_size * 0.05  

        # **Posicionar Botón de Menú (izquierda del Sudoku)**
        self.back_button.size = (button_width, button_height)
        self.back_button.pos = (grid_x, grid_y + grid_size + spacing+button_height)

        # **Posicionar Timer (derecha del Sudoku)**
        self.timer_label.size = (timer_width, timer_height)
        self.timer_label.pos = (grid_x + grid_size - timer_width, grid_y + grid_size + spacing)

    def update_timer(self, dt):
        """Updates the timer every second."""
        if self.timer_label:  # ← Asegurar que el label existe antes de modificarlo
            self.timer_seconds += 1
            minutes = self.timer_seconds // 60
            seconds = self.timer_seconds % 60
            self.timer_label.text = f"{minutes:02}:{seconds:02}"

    def go_to_menu(self, instance):
        """Returns to the main menu and clears the game screen."""
        if self.clock_event:
            Clock.unschedule(self.clock_event)  # Detener temporizador si existe
        self.clear_widgets()
        self.manager.current = "menu"
        
    def update_cell(self, row, col, new_value):
        # Si la celda estaba en 0 y ahora se le asigna un número distinto
        if self.sudoku_puzzle.board[row][col] == 0 and new_value != 0:
            if self.sudoku_puzzle.is_valid_move(self.sudoku_puzzle.board, row, col, new_value):
                self.remaining_zeros_count -= 1
                self.sudoku_puzzle.board[row][col] = new_value
        # Si la celda tenía un valor y ahora se pone 0
        elif self.sudoku_puzzle.board[row][col] != 0 and new_value == 0:
            self.remaining_zeros_count += 1
            self.sudoku_puzzle.board[row][col] = new_value

        # Verificar si la cuenta llegó a 0 (condición de victoria)
        if self.remaining_zeros_count == 0:
            # Detener el timer
            if self.clock_event:
                Clock.unschedule(self.clock_event)
            # Capturar el texto actual del timer (congelado)
            timer_text = self.timer_label.text
            # Agregar y cambiar a la pantalla de victoria
            winning_screen = WinningScreen(timer_text, name="winning")
            self.manager.add_widget(winning_screen)
            self.manager.current = "winning"


class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.add_widget(self.layout)

        # Agregar evento de cambio de tamaño
        Window.bind(on_resize=self.update_positions)

        self.create_buttons()

    def create_buttons(self):
        """Crea los botones de dificultad con posiciones relativas."""
        self.layout.clear_widgets()  # Limpiar widgets antes de recrearlos
        
        screen_width, screen_height = Window.size
        button_width = screen_width * (2/5)
        button_height = screen_height * 0.1
        spacing = screen_height * 0.02  # Espaciado vertical entre botones

        for i, difficulty in enumerate(["Easy", "Medium", "Hard"]):
            btn = Button(
                text=difficulty,
                font_size=button_width * 0.2,
                color=(1, 1, 1, 1),
                background_normal="",
                background_disabled_normal="",
                background_color=(0.5, 0.5, 1, 1),
                size_hint=(None, None),
                size=(button_width, button_height),
                pos=(
                    (screen_width - button_width) / 2,
                    screen_height * 0.6 - (i * (button_height + spacing))
                )
            )
            btn.bind(on_release=self.on_difficulty_selected)
            self.layout.add_widget(btn)

    def update_positions(self, *args):
        """Reajusta la posición de los botones cuando cambia el tamaño de la ventana."""
        self.create_buttons()

    def on_difficulty_selected(self, button):
        selected_difficulty = button.text.lower()
        self.manager.get_screen("game").start_game(selected_difficulty)
        self.manager.current = "game"

class WinningScreen(Screen):
    def __init__(self, timer_text, **kwargs):
        super().__init__(**kwargs)
        # Usamos un BoxLayout vertical para organizar los widgets
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Título: "Ganaste!"
        title = Label(text="Completed!", font_size=48)
        
        # Mostrar el timer congelado (el valor que se pasa como parámetro)
        frozen_timer = Label(text=timer_text, font_size=32)
        
        # Botón para volver al MenuScreen
        btn_menu = Button(text="Main Menu", size_hint=(None, None), size=(200, 50))
        btn_menu.bind(on_release=self.go_to_menu)
        
        layout.add_widget(title)
        layout.add_widget(frozen_timer)
        layout.add_widget(btn_menu)
        self.add_widget(layout)
        
    def go_to_menu(self, instance):
        self.manager.current = "menu"



class SudokuApp(App):
    def build(self):
#         screen_width, screen_height = Window.system_size  # Obtiene la resolución del monitor
#         aspect_ratio = 9/19.5  # Relación de aspecto típica de un celular

#         # Ajustar el tamaño de la ventana manteniendo la proporción
#         if screen_width / screen_height > aspect_ratio:
#             Window.size = (screen_height * aspect_ratio, screen_height * 0.9)  # Basado en altura
#         else:
#             Window.size = (screen_width * 0.9, screen_width / aspect_ratio)  # Basado en ancho

        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(GameScreen(name="game"))

        sm.current = "menu"
        return sm


if __name__ == '__main__':
    SudokuApp().run()

