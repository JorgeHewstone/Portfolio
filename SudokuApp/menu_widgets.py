from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()
        
        screen_width, screen_height = Window.size
        button_width = screen_width * (1/3)  # 1/3 del ancho de la pantalla
        button_height = screen_height * 0.08  # 8% del alto de la pantalla
        
        # Espaciado vertical entre botones (para centrarlos mejor)
        spacing = screen_height * 0.02  

        for i, difficulty in enumerate(["Easy", "Medium", "Hard"]):
            btn = Button(
                text=difficulty,
                font_size=button_width * 0.12,  # Ajustar tamaño de fuente basado en el ancho
                color=(1, 1, 1, 1),
                background_normal="",
                background_disabled_normal="",
                background_color=(0.5, 0.5, 1, 1),
                size_hint=(None, None),
                size=(button_width, button_height),
                pos=(
                    (screen_width - button_width) / 2,  # Centrado horizontalmente
                    screen_height * 0.6 - (i * (button_height + spacing))  # Distribución vertical
                )
            )
            btn.bind(on_release=self.on_difficulty_selected)
            layout.add_widget(btn)

        self.add_widget(layout)

    def on_difficulty_selected(self, button):
        """
        Handles button presses and switches to the Sudoku game screen.
        """
        selected_difficulty = button.text.lower()  # "easy", "medium", "hard"
        self.manager.get_screen("game").start_game(selected_difficulty)
        self.manager.current = "game"


