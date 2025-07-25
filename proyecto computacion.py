import tkinter as tk
from tkinter import messagebox
import random
import time
import csv
import os
from collections import deque
from PIL import Image, ImageTk
import pygame

class LaberintoApp:
    def __init__(self, root):
        """
        Constructor principal de la aplicación.

        Inicializa la ventana, crea variables de estado del juego, 
        y muestra el menú principal.

        :param root: ventana raíz de tkinter
        """
        self.root = root
        self.root.title("Laberinto Extremo")
        self.root.geometry("900x900")
        
        pygame.mixer.init()  # Inicializar el mezclador de pygame para sonidos
        try:
            pygame.mixer.music.load("musica.mp3")  # Cargar música de fondo
            pygame.mixer.music.play(-1)  # Reproducir en bucle
        except pygame.error as e:
            print(f"Error al cargar la música de fondo: {e}")
        # Variables de estado del juego
        self.player_name = ""       # Nombre del jugador
        self.level = 1              # Nivel seleccionado
        self.maze = []              # Matriz que representa el laberinto
        self.player_pos = (0, 0)    # Posición del jugador (fila, columna)
        self.exit_pos = (0, 0)      # Posición de la salida
        self.start_time = 0         # Tiempo de inicio de la partida
        self.scores_file = "puntuaciones.csv" # Archivo de puntuaciones
        self.lives = 3              # Cantidad de vidas
        self.game_active = False    # Bandera: si el juego está activo
        self.keys_collected = 0     # Llaves recogidas
        self.keys_required = 0      # Llaves necesarias para completar el nivel
        self.moving_walls = []      # Lista de posiciones de paredes móviles
        self.moving_wall_directions = {} # Dirección de movimiento de las paredes móviles (1: derecha, -1: izquierda)
        
        # Guardar el contenido original de las celdas (antes de que el jugador/pared las ocupe)
        # Esto es crucial para restaurar el color correcto después de que el jugador/pared se mueve.
        self.original_maze_content = [] 
        
        # Si el archivo de puntuaciones no existe, lo crea
        if not os.path.exists(self.scores_file):
            with open(self.scores_file, 'w', newline='') as f:
                csv.writer(f).writerow(["Nombre", "Nivel", "Tiempo(s)", "Vidas", "Llaves"])
        
        self.show_main_menu()

    def show_main_menu(self):
        """
        Muestra la interfaz del menú principal.
        Permite al usuario ingresar su nombre, elegir el nivel y otras opciones.
        """
        self.clear_frame()
        # Cargar imagen de fondo
        bg_image = Image.open("imagen.png")
        bg_image = bg_image.resize((900, 900))
        self.menu_bg_photo = ImageTk.PhotoImage(bg_image)
        bg_label = tk.Label(self.root, image=self.menu_bg_photo)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)
       
   
        #objetos de la interfaz del menú principal
        tk.Label(self.root, text="LABERINTO EXTREMO", font=("Press Start 2P", 26, "bold")).pack(pady=40)
        #nombre del jugador
        tk.Label(self.root, text="Tu nombre:", font=("Press Start 2P", 26)).pack()
        self.name_entry = tk.Entry(self.root, font=("Press Start 2P", 24))
        self.name_entry.pack(pady=15)

        #seleccion de nivel
        tk.Label(self.root, text="Selecciona nivel:", font=("Press Start 2P", 28)).pack(pady=50)
        self.level_var = tk.IntVar(value=1)
        levels = ["Nivel 1 (5x5) - Fácil", "Nivel 2 (8x8) - Difícil", "Nivel 3 (10x10) - Imposible"]
        for i, text in enumerate(levels, 1):
            tk.Radiobutton(self.root, text=text, variable=self.level_var, value=i, font=("Press Start 2P", 20)).pack(pady=2)
        buttons_frame = tk.Frame(self.root)
        buttons_frame.pack(pady=30)
        buttons = [
            ("JUGAR", self.start_game, "#4CAF50"),
            ("PUNTUACIONES", self.show_scores, "#2196F3"),
            ("SALIR", self.root.quit, "#F44336")
        ]
        for text, cmd, color in buttons:
            tk.Button(buttons_frame, text=text, command=cmd,bg=color, fg="white",
                      font=("Press Start 2P", 16,"bold"), 
                      width=14, 
                      height=2).pack(pady=8)

    def start_game(self):
        """
        Inicia una partida.

        Configura las variables de juego, genera el laberinto, 
        coloca las llaves y las paredes móviles si corresponde.
        """
        self.player_name = self.name_entry.get().strip() or "Jugador"
        self.level = self.level_var.get()
        self.lives = 3
        self.keys_collected = 0
        self.game_active = True
        self.moving_walls = []
        self.moving_wall_directions = {} 
        
        sizes = {1: 5, 2: 8, 3: 10}
        size = sizes[self.level]
        self.keys_required = self.level
        
        # Generar laberinto y posicionar elementos
        self.maze = self.generate_maze(size, size)
        
        # Guardar una copia profunda del laberinto original (sin jugador ni paredes móviles)
        # Esto es clave para restaurar el contenido real de las celdas.
        self.original_maze_content = [row[:] for row in self.maze] 

        self.player_pos = self.find_empty_cell()
        self.exit_pos = self.find_empty_cell(exclude=[self.player_pos])
        
        # Actualizar original_maze_content con la salida
        self.original_maze_content[self.exit_pos[0]][self.exit_pos[1]] = 2 
        self.maze[self.exit_pos[0]][self.exit_pos[1]] = 2 # Establecer salida en el laberinto actual

        self.place_accessible_keys() # Esto actualiza self.maze y original_maze_content

        if self.level == 3:
            self.place_moving_walls() # Esto actualiza self.maze y original_maze_content

        self.start_time = time.time()
        self.show_game_interface()
        
        # Activar animación de paredes móviles si es necesario
        if self.level == 3:
            self.animate_moving_walls()

    def generate_maze(self, rows, cols):
        """
        Genera un laberinto válido utilizando algoritmo DFS.

        :param rows: número de filas
        :param cols: número de columnas
        :return: matriz que representa el laberinto
        """
        # esto asegura que las dimensiones del laberinto sean impares para una generación de caminos adecuada
        if rows % 2 == 0: rows += 1
        if cols % 2 == 0: cols += 1

        maze = [[1] * cols for _ in range(rows)]
        stack = deque()
        start_row, start_col = 1, 1
        maze[start_row][start_col] = 0
        stack.append((start_row, start_col))
        
        while stack:
            r, c = stack[-1]
            neighbors = []
            for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                nr, nc = r + dr, c + dc
                if 0 < nr < rows-1 and 0 < nc < cols-1 and maze[nr][nc] == 1:
                    neighbors.append((nr, nc, dr//2, dc//2))
            
            if neighbors:
                next_r, next_c, dr, dc = random.choice(neighbors)
                maze[r + dr][c + dc] = 0
                maze[next_r][next_c] = 0
                stack.append((next_r, next_c))
            else:
                stack.pop()
        
        # Bordes sólidos
        for i in range(rows):
            maze[i][0] = maze[i][cols-1] = 1
        for j in range(cols):
            maze[0][j] = maze[rows-1][j] = 1
        
        return maze

    def find_empty_cell(self, exclude=[]):
        """
        Encuentra una celda vacía aleatoria.

        :param exclude: lista de posiciones a evitar
        :return: (fila, columna) de la celda vacía
        """
        available_cells = []
        for i in range(1, len(self.maze)-1):
            for j in range(1, len(self.maze[0])-1):
                if self.maze[i][j] == 0 and (i, j) not in exclude:
                    available_cells.append((i, j))
        
        if not available_cells:
            # El recurso alternativo para casos muy raros podría indicar un problema con la generación del laberinto para tamaños pequeños.
            print("Warning: No available empty cells found. Returning (1,1).")
            return (1, 1) 
        
        return random.choice(available_cells)

    def place_accessible_keys(self):
        """
        Coloca las llaves en posiciones accesibles desde la posición del jugador.
        """
        accessible_positions = []
        for i in range(1, len(self.maze)-1):
            for j in range(1, len(self.maze[0])-1):
                # Asegura de que sea celda de ruta vacia y no jugador/salida
                if self.maze[i][j] == 0 and (i, j) != self.player_pos and (i, j) != self.exit_pos:
                    if self.is_accessible(self.player_pos, (i, j)):
                        accessible_positions.append((i, j))
        
        random.shuffle(accessible_positions) 

        for _ in range(min(self.keys_required, len(accessible_positions))):
            pos = accessible_positions.pop(0) 
            self.maze[pos[0]][pos[1]] = 3 # Llave
            self.original_maze_content[pos[0]][pos[1]] = 3 # se marca la clave en el contenido original

    def is_accessible(self, start, end):
        """
        Verifica si existe un camino entre dos posiciones del laberinto usando BFS.

        :param start: posición inicial (fila, columna)
        :param end: posición destino (fila, columna)
        :return: True si existe un camino, False si no
        """
        rows, cols = len(self.maze), len(self.maze[0])
        visited = [[False] * cols for _ in range(rows)]
        queue = deque([start])
        visited[start[0]][start[1]] = True
        
        while queue:
            r, c = queue.popleft()
            if (r, c) == end:
                return True
            
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < rows and 0 <= nc < cols and 
                    not visited[nr][nc] and 
                    self.maze[nr][nc] in [0, 2, 3]): # Permite el paso de salidas y claves para la busqueda de rutas
                    visited[nr][nc] = True
                    queue.append((nr, nc))
        
        return False

    def place_moving_walls(self):
        """
        Coloca las paredes móviles en posiciones accesibles.
        Solo se usa en nivel 3.
        """
        accessible_positions = []
        for i in range(1, len(self.maze)-1):
            for j in range(1, len(self.maze[0])-1):
                # asegura de que sea celda de ruta vacia, no jugador/salida, y que no se a clave
                if self.maze[i][j] == 0 and (i, j) != self.player_pos and \
                   (i, j) != self.exit_pos and self.maze[i][j] != 3:
                    # También asegura que la celda a la izquierda/derecha de la posible colocación de la pared sea un camino (0)
                    # Esto ayuda a asegurar que las paredes tengan espacio para moverse horizontalmente.
                    if j > 1 and j < len(self.maze[0]) - 2: # Verifica el rango de columna válido para el movimiento
                        if self.maze[i][j-1] == 0 and self.maze[i][j+1] == 0:
                            if self.is_accessible(self.player_pos, (i, j)):
                                accessible_positions.append((i, j))
        
        random.shuffle(accessible_positions)
        num_moving_walls = min(3, len(accessible_positions)) 
        for _ in range(num_moving_walls):
            if accessible_positions:
                pos = accessible_positions.pop(0)
                self.maze[pos[0]][pos[1]] = 4 # Pared móvil
                self.original_maze_content[pos[0]][pos[1]] = 0 # los muros se consideran caminos en el diseño original
                self.moving_walls.append(pos)
                self.moving_wall_directions[pos] = random.choice([-1, 1])

    def show_game_interface(self):
        """
        Muestra la interfaz principal de la partida:
        - panel de información (vidas, llaves, tiempo)
        - representación visual del laberinto
        - controles de movimiento
        """
        self.clear_frame()
        # Cargar imagen de fondo para el laberinto
        maze_bg_image = Image.open("imagen.png")  
        maze_bg_image = maze_bg_image.resize((900, 900))
        self.maze_bg_photo = ImageTk.PhotoImage(maze_bg_image)
        bg_label = tk.Label(self.root, image=self.maze_bg_photo)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)   

        # Panel de información superior
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill=tk.X, pady=5)
        tk.Label(info_frame, text=f"Jugador: {self.player_name}").pack(side=tk.LEFT, padx=10)
        tk.Label(info_frame, text=f"Nivel: {self.level}").pack(side=tk.LEFT, padx=10)
        self.lives_label = tk.Label(info_frame, text=f"Vidas: {self.lives}", font=("Arial", 18))
        self.lives_label.pack(side=tk.LEFT, padx=10)
        self.keys_label = tk.Label(info_frame, text=f"Llaves: {self.keys_collected}/{self.keys_required}")
        self.keys_label.pack(side=tk.LEFT, padx=10)
        self.time_label = tk.Label(info_frame, text="Tiempo: 0.00s", font=("Arial", 18))
        self.time_label.pack(side=tk.LEFT, padx=10)
        self.update_timer()
        
        # Mapa del laberinto
        maze_frame = tk.Frame(self.root)
        maze_frame.pack(pady=30)
        self.cells = []
        for i, row in enumerate(self.maze):
            cell_row = []
            for j, cell in enumerate(row):
                # Determina el color de la celda según su tipo
                bg = "black" if cell == 1 else "green" if cell == 2 else "gold" if cell == 3 else "gray" if cell == 4 else "white"
                lbl = tk.Label(maze_frame, width=4, height=2, relief="solid", borderwidth=3, bg=bg)
                if (i, j) == self.player_pos:
                    lbl.config(bg="blue")
                lbl.grid(row=i, column=j)
                cell_row.append(lbl)
            self.cells.append(cell_row)
        
        # Controles de movimiento (flechas)
        controls = tk.Frame(self.root)
        controls.pack(pady=20)
        for text, dr, dc, row, col in [("↑", -1, 0, 0, 1), ("←", 0, -1, 1, 0), 
                                         ("→", 0, 1, 1, 2), ("↓", 1, 0, 2, 1)]:
            tk.Button(controls, text=text, command=lambda dr=dr, dc=dc: self.move_player(dr, dc), 
                            width=3, height=2, font=("Arial", 18)).grid(row=row, column=col, padx=12, pady=12)
        
        # Botón para volver al menú
        tk.Button(self.root, text="Menú Principal", command=self.show_main_menu, font=("Arial",18), width=20, height=2).pack(pady=10)

    def update_timer(self):
        """
        Actualiza continuamente el temporizador de la partida.
        Se llama recursivamente cada 100 ms.
        """
        if self.game_active:
            elapsed = time.time() - self.start_time
            self.time_label.config(text=f"Tiempo: {elapsed:.2f}s")
            self.root.after(100, self.update_timer)

    def animate_moving_walls(self):
        """
        Anima las paredes móviles en el nivel 3.
        Las paredes se mueven de lado a lado.
        Si el jugador es alcanzado por una pared en movimiento, pierde una vida.
        """
        if not self.game_active:
            return

        new_moving_walls_state = []
        walls_to_remove_from_directions = [] # Para limpiar claves antiguas en el diccionario
        
        # Iterar sobre una copia de moving_walls tal como se modificará
        current_moving_walls = list(self.moving_walls) 
        
        for r, c in current_moving_walls:
            direction = self.moving_wall_directions.get((r,c), 1) #   obtener dirección, por defecto 1 si no se encuentra

            new_c_candidate = c + direction
            
            # 1. Verifica las condiciones de contorno para el movimiento de la pared.
            if not (0 <= new_c_candidate < len(self.maze[0])):
                direction *= -1 # Dirección inversa
                new_c_candidate = c + direction # Recalcular posición candidata

            # 2. Verifica el contenido de la celda objetivo.
            # Las paredes no pueden moverse a muros fijos, llaves o la salida.
            target_cell_content = self.maze[r][new_c_candidate]
            if target_cell_content in [1, 2, 3]: # Muro fijo, Salida o Llave
                direction *= -1 # Dirección inversa
                new_c = c # La pared se queda en su posición actual durante este turno
            else:
                new_c = new_c_candidate

            # 3. Manejar la colisión con el jugador si la pared *intenta* moverse a la celda del jugador
            if (r, new_c) == self.player_pos:
                self.hit_wall()
                # La pared se quedará en su posición original durante este turno, pero invertirá la dirección para el siguiente.
                # El jugador permanece en su posición y pierde una vida.
               
            if (r, c) != (r, new_c): # Si la pared se mueve a una nueva posición
                # Restaurar la celda antigua a su contenido original del laberinto
                self.maze[r][c] = self.original_maze_content[r][c] 
                self.cells[r][c].config(bg=self._get_cell_color(self.original_maze_content[r][c]))

                # Actualizar el laberinto con la nueva posición de la pared
                self.maze[r][new_c] = 4
                self.cells[r][new_c].config(bg="gray") # La nueva posición de la pared es gris

                new_moving_walls_state.append((r, new_c))
                self.moving_wall_directions[(r, new_c)] = direction
                walls_to_remove_from_directions.append((r,c)) # Marcar posición antigua para eliminación
            else: # La pared no se movió (chocó con el límite o celda prohibida)
                self.maze[r][c] = 4 # Confirmar que sigue siendo una pared en los datos
                self.cells[r][c].config(bg="gray")
                if (r,c) not in new_moving_walls_state: # Asegurarse de que se agregue al nuevo estado
                    new_moving_walls_state.append((r,c))
                self.moving_wall_directions[(r,c)] = direction # Asegurarse de que la dirección se actualice

        self.moving_walls = new_moving_walls_state
        for old_pos in walls_to_remove_from_directions:
            if old_pos in self.moving_wall_directions and old_pos not in self.moving_walls:
                del self.moving_wall_directions[old_pos]

        self.root.after(500, self.animate_moving_walls) # llamar de nuevo para la siguiente animación
    def move_player(self, dr, dc):
        """
        Mueve al jugador en la dirección indicada.

        :param dr: delta fila (-1, 0, 1)
        :param dc: delta columna (-1, 0, 1)
        """
        if not self.game_active:
            return

        r, c = self.player_pos
        new_r, new_c = r + dr, c + dc
        
        if 0 <= new_r < len(self.maze) and 0 <= new_c < len(self.maze[0]):
            target_cell_content = self.maze[new_r][new_c]

            # Si es pared móvil, pierde vida y se mueve (parpadea en rojo la nueva celda)
            if target_cell_content == 4:
                self.cells[r][c].config(bg=self._get_cell_color(self.original_maze_content[r][c]))
                self.player_pos = (new_r, new_c)
                # Parpadeo en rojo en la nueva celda
                self.cells[new_r][new_c].config(bg="red")
                self.lives -= 1
                self.lives_label.config(text=f"Vidas: {self.lives}")
                self.root.update_idletasks()
                self.root.after(200, lambda: self.cells[new_r][new_c].config(bg="blue"))
                if self.lives <= 0:
                    self.game_active = False
                    messagebox.showinfo("Game Over", "¡Te quedaste sin vidas!")
                    self.show_main_menu()
                    return
                if self.player_pos == self.exit_pos and self.keys_collected >= self.keys_required:
                    self.game_won()
                return

            # Si es camino, salida o llave
            if target_cell_content in [0, 2, 3]:
                self.cells[r][c].config(bg=self._get_cell_color(self.original_maze_content[r][c]))

                if target_cell_content == 3:  # Si el jugador recoge una llave
                    self.keys_collected += 1
                    self.keys_label.config(text=f"Llaves: {self.keys_collected}/{self.keys_required}")
                    self.maze[new_r][new_c] = 0
                    self.original_maze_content[new_r][new_c] = 0

                self.player_pos = (new_r, new_c)
                self.cells[new_r][new_c].config(bg="blue")

                if self.player_pos == self.exit_pos and self.keys_collected >= self.keys_required:
                    self.game_won()
        # Si es pared fija, no hace nada

    def _get_cell_color(self, cell_type):
        """Ayuda para obtener el color de fondo para un tipo de celda."""
        if cell_type == 1: return "black" # Pared
        if cell_type == 2: return "green" # Salida
        if cell_type == 3: return "gold"  # Llave
        if cell_type == 4: return "gray"  # Pared en movimiento (aunque estas se gestionan dinámicamente)
        return "white" # Camino (0)

    def hit_wall(self):
        """
        Maneja el evento de que el jugador golpea una pared en movimiento.
        Reduce una vida y muestra un parpadeo rojo.
        """
        self.lives -= 1
        self.lives_label.config(text=f"Vidas: {self.lives}")

        # Efecto visual de colisión: la celda del jugador parpadea en rojo
        r, c = self.player_pos
        original_player_color = "blue" # El jugador siempre es azul
        self.cells[r][c].config(bg="red")
        self.root.update_idletasks() # Asegurarse de que el cambio visual se muestre inmediatamente
        self.root.after(200, lambda: self.cells[r][c].config(bg=original_player_color)) # Revertir a azul

        # Si el jugador se queda sin vidas, termina el juego
        if self.lives <= 0:
            self.game_active = False # Detener el juego antes de mostrar el mensaje
            messagebox.showinfo("Game Over", "¡Te quedaste sin vidas!")
            self.show_main_menu()

    def game_won(self):
        """
        Se llama cuando el jugador completa el laberinto.
        Muestra un mensaje de victoria y guarda la puntuación.
        """
        elapsed_time = time.time() - self.start_time
        messagebox.showinfo("¡Victoria!", f"¡Felicidades {self.player_name}! Has completado el laberinto en {elapsed_time:.2f} segundos.")
        
        # Guardar la puntuación en el archivo CSV
        with open(self.scores_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([self.player_name, self.level, f"{elapsed_time:.2f}", self.lives, self.keys_collected])
        
        self.show_main_menu()

    def game_over(self):
        """
        Se llama cuando el jugador pierde todas las vidas.
        Muestra un mensaje de 'Game Over'.
        (This function is currently not directly called as hit_wall handles game_over)
        """
        self.game_active = False # Detener el juego en la pérdida
        messagebox.showinfo("Game Over", "¡Te quedaste sin vidas!")
        self.show_main_menu()

    def show_scores(self):
        """
        Muestra la pantalla de mejores puntuaciones.
        Se cargan las puntuaciones desde el archivo CSV y se ordenan por tiempo.
        """
        self.clear_frame()
        tk.Label(self.root, text="MEJORES PUNTUACIONES", font=("Press Start 2P", 10)).pack(pady=20)
        
        frame = tk.Frame(self.root)
        frame.pack(pady=6, padx=15, fill=tk.BOTH, expand=True)

        # Encabezados de la tabla
        headers = ["Nombre", "Nivel", "Tiempo", "Vidas", "Llaves"]
        for col, header in enumerate(headers):
            tk.Label(frame, text=header, font=("Press Start 2P", 10, "bold"), relief="ridge", 
                            padx=10, pady=5).grid(row=0, column=col, sticky="nsew")

        # Contenido de la tabla
        scores = []
        if os.path.exists(self.scores_file):
            with open(self.scores_file, 'r') as f:
                reader = csv.reader(f)
                next(reader) # saltar encabezados
                raw_scores = [row for row in reader if len(row) == 5]
                try:
                    scores = sorted(raw_scores, key=lambda x: float(x[2]))[:10] # los primeros 10 por tiempo
                except ValueError:
                    messagebox.showerror("Error de Puntuación", "Algunas puntuaciones en el archivo están corruptas y no se pudieron cargar correctamente.")
                    scores = [] 

        for row_idx, row in enumerate(scores, 1):
            for col_idx, value in enumerate(row):
                tk.Label(frame, text=value, relief="ridge", padx=10, pady=5).grid(
                    row=row_idx, column=col_idx, sticky="nsew")

        # Ajuste de expansión de columnas
        for i in range(len(headers)):
            frame.grid_columnconfigure(i, weight=1)

        # Botón para volver al menú
        tk.Button(self.root, text="Volver al Menú", command=self.show_main_menu).pack(pady=20)

    def clear_frame(self):
        """
        Limpia todos los widgets de la ventana.
        Se usa para cambiar de pantalla (menú, juego, puntuaciones).
        """
        for widget in self.root.winfo_children():
            widget.destroy()

# ========================
# Ejecutar la aplicación
# ========================
if __name__ == "__main__":
    root = tk.Tk()
    app = LaberintoApp(root)
    root.mainloop()