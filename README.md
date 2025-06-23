# proyecto-de-intro-a-compu.
nombre del proyecto: Laberinto

Este proyecto programado se basa en programar un codigo que permita crear una pestaña en la cual se pueda jugar con un laberinto de 3 niveles.

instrucciones:
1. copiar el codigo proporcionado por los estudiantes.
2. colocarlo en alguna plataforma en la cual se pueda correr el codigo.
3. disfrutar del juego.

La unica libreria utilizada para la creacion del laberinto fue tkinter.

La logica del juego se basa en que el jugador debe de pasar el laberinto sin perder las 3 vidas proporcionadas, en el tercer nivel el jugaor debera recoger llavez para poder salir del laberinto.

#codigo

import tkinter as tk
from tkinter import messagebox
import random
import time
import csv
import os
from collections import deque

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
        self.root.geometry("650x700")
        
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
        
        # Mostrar menú principal al iniciar la app
        self.show_main_menu()

    def show_main_menu(self):
        """
        Muestra la interfaz del menú principal.
        Permite al usuario ingresar su nombre, elegir el nivel y otras opciones.
        """
        self.clear_frame()
        tk.Label(self.root, text="LABERINTO EXTREMO", font=("Arial", 24, "bold")).pack(pady=20)
        
        # Nombre del jugador
        tk.Label(self.root, text="Tu nombre:").pack()
        self.name_entry = tk.Entry(self.root, font=("Arial", 12))
        self.name_entry.pack(pady=5)
        self.name_entry.insert(0, "Jugador")
        
        # Selección de nivel
        tk.Label(self.root, text="Selecciona nivel:").pack(pady=10)
        self.level_var = tk.IntVar(value=1)
        levels = ["Nivel 1 (5x5) - Fácil", "Nivel 2 (8x8) - Difícil", "Nivel 3 (10x10) - Imposible"]
        for i, text in enumerate(levels, 1):
            tk.Radiobutton(self.root, text=text, variable=self.level_var, value=i, 
                            font=("Arial", 10)).pack(pady=2)
        
        # Botones principales
        buttons = [
            ("JUGAR", self.start_game, "#4CAF50"),
            ("VER PUNTUACIONES", self.show_scores, "#2196F3"),
            ("SALIR", self.root.quit, "#F44336")
        ]
        for text, cmd, color in buttons:
            tk.Button(self.root, text=text, command=cmd, bg=color, fg="white",
                            font=("Arial", 12 if text=="JUGAR" else 10, "bold"), 
                            width=20 if text=="JUGAR" else 15, 
                            height=2 if text=="JUGAR" else 1).pack(pady=8)

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
        self.maze[self.exit_pos[0]][self.exit_pos[1]] = 2 # Set exit in current maze too

        self.place_accessible_keys() # This updates self.maze and original_maze_content
        
        if self.level == 3:
            self.place_moving_walls() # This updates self.maze and original_maze_content
        
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
        # Ensure maze dimensions are odd for proper path generation with DFS
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
            # Fallback for very rare cases, might indicate an issue with maze generation for small sizes
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
                # Ensure it's an empty path cell and not player/exit
                if self.maze[i][j] == 0 and (i, j) != self.player_pos and (i, j) != self.exit_pos:
                    if self.is_accessible(self.player_pos, (i, j)):
                        accessible_positions.append((i, j))
        
        random.shuffle(accessible_positions) 

        for _ in range(min(self.keys_required, len(accessible_positions))):
            pos = accessible_positions.pop(0) 
            self.maze[pos[0]][pos[1]] = 3 # Llave
            self.original_maze_content[pos[0]][pos[1]] = 3 # Mark key in original content too

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
                    self.maze[nr][nc] in [0, 2, 3]): # Allow passing through exit and keys for pathfinding
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
                # Ensure it's an empty path cell, not player/exit, and not already a key
                if self.maze[i][j] == 0 and (i, j) != self.player_pos and \
                   (i, j) != self.exit_pos and self.maze[i][j] != 3:
                    # Also ensure the cell to the left/right of the potential wall placement is a path (0)
                    # This helps ensure walls have room to move horizontally.
                    if j > 1 and j < len(self.maze[0]) - 2: # Check valid column range for movement
                        if self.maze[i][j-1] == 0 and self.maze[i][j+1] == 0:
                            if self.is_accessible(self.player_pos, (i, j)):
                                accessible_positions.append((i, j))
        
        random.shuffle(accessible_positions)
        num_moving_walls = min(3, len(accessible_positions)) 
        for _ in range(num_moving_walls):
            if accessible_positions:
                pos = accessible_positions.pop(0)
                self.maze[pos[0]][pos[1]] = 4 # Pared móvil
                self.original_maze_content[pos[0]][pos[1]] = 0 # Moving walls are considered path in original layout
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
        
        # Panel de información superior
        info_frame = tk.Frame(self.root)
        info_frame.pack(fill=tk.X, pady=5)
        tk.Label(info_frame, text=f"Jugador: {self.player_name}").pack(side=tk.LEFT, padx=10)
        tk.Label(info_frame, text=f"Nivel: {self.level}").pack(side=tk.LEFT, padx=10)
        self.lives_label = tk.Label(info_frame, text=f"Vidas: {self.lives}")
        self.lives_label.pack(side=tk.LEFT, padx=10)
        self.keys_label = tk.Label(info_frame, text=f"Llaves: {self.keys_collected}/{self.keys_required}")
        self.keys_label.pack(side=tk.LEFT, padx=10)
        self.time_label = tk.Label(info_frame, text="Tiempo: 0.00s")
        self.time_label.pack(side=tk.LEFT, padx=10)
        self.update_timer()
        
        # Mapa del laberinto (grilla de celdas)
        maze_frame = tk.Frame(self.root)
        maze_frame.pack(pady=10)
        self.cells = []
        for i, row in enumerate(self.maze):
            cell_row = []
            for j, cell in enumerate(row):
                # Determine cell color based on maze content
                bg = "black" if cell == 1 else "green" if cell == 2 else "gold" if cell == 3 else "gray" if cell == 4 else "white"
                lbl = tk.Label(maze_frame, width=2, height=1, relief="solid", borderwidth=1, bg=bg)
                if (i, j) == self.player_pos:
                    lbl.config(bg="blue")
                lbl.grid(row=i, column=j)
                cell_row.append(lbl)
            self.cells.append(cell_row)
        
        # Controles de movimiento (flechas)
        controls = tk.Frame(self.root)
        controls.pack(pady=10)
        for text, dr, dc, row, col in [("↑", -1, 0, 0, 1), ("←", 0, -1, 1, 0), 
                                         ("→", 0, 1, 1, 2), ("↓", 1, 0, 2, 1)]:
            tk.Button(controls, text=text, command=lambda dr=dr, dc=dc: self.move_player(dr, dc), 
                            width=3).grid(row=row, column=col, padx=5, pady=5)
        
        # Botón para volver al menú
        tk.Button(self.root, text="Menú Principal", command=self.show_main_menu).pack(pady=10)

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
        walls_to_remove_from_directions = [] # To clean up old keys in dictionary
        
        # Iterate over a copy of moving_walls as it will be modified
        current_moving_walls = list(self.moving_walls) 
        
        for r, c in current_moving_walls:
            direction = self.moving_wall_directions.get((r,c), 1) # Get direction, default to 1 if not found

            new_c_candidate = c + direction
            
            # 1. Check for boundary conditions for the wall's movement
            if not (0 <= new_c_candidate < len(self.maze[0])):
                direction *= -1 # Reverse direction
                new_c_candidate = c + direction # Recalculate candidate position
            
            # 2. Check the content of the target cell.
            # Walls cannot move onto fixed walls, keys, or the exit.
            target_cell_content = self.maze[r][new_c_candidate]
            if target_cell_content in [1, 2, 3]: # Fixed wall, Exit, or Key
                direction *= -1 # Reverse direction
                new_c = c # Wall stays in current position for this turn
            else:
                new_c = new_c_candidate

            # 3. Handle collision with player if the wall *tries* to move into player's cell
            if (r, new_c) == self.player_pos:
                self.hit_wall()
                # The wall will stay in its original position for this turn, but reverses direction for next.
                # The player remains in their position and loses a life.
                self.maze[r][c] = 4 # Ensure wall stays at its current location in maze data
                if (r,c) not in new_moving_walls_state: # Add current position to new state to keep tracking
                    new_moving_walls_state.append((r,c)) 
                self.moving_wall_directions[(r,c)] = direction # Update direction for next turn
                # Visual update for the wall's current cell, ensuring it's gray
                self.cells[r][c].config(bg="gray") 
                continue # Skip remaining logic for this wall, move to next wall

            # 4. If wall moves, update maze data and UI
            if (r, c) != (r, new_c): # If the wall actually moved to a new cell
                # Restore the old cell to its original maze content
                self.maze[r][c] = self.original_maze_content[r][c] 
                self.cells[r][c].config(bg=self._get_cell_color(self.original_maze_content[r][c]))
                
                # Update maze with new wall position
                self.maze[r][new_c] = 4 
                self.cells[r][new_c].config(bg="gray") # New wall position is gray

                new_moving_walls_state.append((r, new_c))
                self.moving_wall_directions[(r, new_c)] = direction
                walls_to_remove_from_directions.append((r,c)) # Mark old position for removal
            else: # Wall didn't move (hit boundary or forbidden cell), just ensure it's gray
                self.maze[r][c] = 4 # Confirm it's still a wall in data
                self.cells[r][c].config(bg="gray")
                if (r,c) not in new_moving_walls_state: # Ensure it's added to the new state
                    new_moving_walls_state.append((r,c)) 
                self.moving_wall_directions[(r,c)] = direction # Ensure direction is updated

        self.moving_walls = new_moving_walls_state
        for old_pos in walls_to_remove_from_directions:
            if old_pos in self.moving_wall_directions and old_pos not in self.moving_walls:
                del self.moving_wall_directions[old_pos]

        self.root.after(500, self.animate_moving_walls) # Call again for continuous animation

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
            
            # Check for immediate collision with a moving wall
            if target_cell_content == 4: # Player trying to move into a moving wall
                self.hit_wall()
                return # Player doesn't move

            # Valid movement: path (0), exit (2), or key (3)
            if target_cell_content == 0 or target_cell_content == 2 or target_cell_content == 3:
                
                # Restore the old cell's visual based on its original content
                self.cells[r][c].config(bg=self._get_cell_color(self.original_maze_content[r][c]))

                if target_cell_content == 3: # If moving onto a key
                    self.keys_collected += 1
                    self.keys_label.config(text=f"Llaves: {self.keys_collected}/{self.keys_required}")
                    self.maze[new_r][new_c] = 0 # Key cell becomes path after collection
                    self.original_maze_content[new_r][new_c] = 0 # Mark key as collected in original content

                # Update player's position
                self.player_pos = (new_r, new_c)
                self.cells[new_r][new_c].config(bg="blue") # Paint new player position blue
                
                # Check if game won AFTER player has moved to new_pos
                if self.player_pos == self.exit_pos and self.keys_collected >= self.keys_required:
                    self.game_won()
            
            elif target_cell_content == 1: # Attempting to move into a fixed wall
                pass # Player doesn't move, no life lost for fixed walls.

    def _get_cell_color(self, cell_type):
        """Helper to get the background color for a cell type."""
        if cell_type == 1: return "black" # Wall
        if cell_type == 2: return "green" # Exit
        if cell_type == 3: return "gold"  # Key
        if cell_type == 4: return "gray"  # Moving Wall (though these are managed dynamically)
        return "white" # Path (0)

    def hit_wall(self):
        """
        Maneja el evento de que el jugador golpea una pared en movimiento.
        Reduce una vida y muestra un parpadeo rojo.
        """
        self.lives -= 1
        self.lives_label.config(text=f"Vidas: {self.lives}")
        
        # Visual effect of collision: player's cell flashes red
        r, c = self.player_pos
        original_player_color = "blue" # Player is always blue
        self.cells[r][c].config(bg="red")
        self.root.update_idletasks() # Ensure visual change is shown immediately
        self.root.after(200, lambda: self.cells[r][c].config(bg=original_player_color)) # Revert to blue
        
        # If player runs out of lives, end the game
        if self.lives <= 0:
            self.game_active = False # Stop the game before showing message
            messagebox.showinfo("Game Over", "¡Te quedaste sin vidas!")
            self.show_main_menu()

    def game_won(self):
        """
        Se llama cuando el jugador completa el nivel exitosamente.
        Guarda la puntuación y muestra un mensaje de felicitación.
        """
        self.game_active = False # Stop the game on win
        elapsed = time.time() - self.start_time
        with open(self.scores_file, 'a', newline='') as f:
            csv.writer(f).writerow([self.player_name, self.level, f"{elapsed:.2f}", self.lives, self.keys_collected])
        messagebox.showinfo("¡Ganaste!", f"¡Felicidades {self.player_name}!\nCompletaste el nivel en {elapsed:.2f} segundos.")
        self.show_main_menu()

    def game_over(self):
        """
        Se llama cuando el jugador pierde todas las vidas.
        Muestra un mensaje de 'Game Over'.
        (This function is currently not directly called as hit_wall handles game_over)
        """
        self.game_active = False # Stop the game on loss
        messagebox.showinfo("Game Over", "¡Te quedaste sin vidas!")
        self.show_main_menu()

    def show_scores(self):
        """
        Muestra la pantalla de mejores puntuaciones.
        Se cargan las puntuaciones desde el archivo CSV y se ordenan por tiempo.
        """
        self.clear_frame()
        tk.Label(self.root, text="MEJORES PUNTUACIONES", font=("Arial", 20)).pack(pady=20)
        
        frame = tk.Frame(self.root)
        frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Table Headers
        headers = ["Nombre", "Nivel", "Tiempo", "Vidas", "Llaves"]
        for col, header in enumerate(headers):
            tk.Label(frame, text=header, font=("Arial", 10, "bold"), relief="ridge", 
                            padx=10, pady=5).grid(row=0, column=col, sticky="nsew")
        
        # Table Content
        scores = []
        if os.path.exists(self.scores_file):
            with open(self.scores_file, 'r') as f:
                reader = csv.reader(f)
                next(reader) # Skip header
                raw_scores = [row for row in reader if len(row) == 5]
                try:
                    scores = sorted(raw_scores, key=lambda x: float(x[2]))[:10] # Top 10 by time
                except ValueError:
                    messagebox.showerror("Error de Puntuación", "Algunas puntuaciones en el archivo están corruptas y no se pudieron cargar correctamente.")
                    scores = [] 

        for row_idx, row in enumerate(scores, 1):
            for col_idx, value in enumerate(row):
                tk.Label(frame, text=value, relief="ridge", padx=10, pady=5).grid(
                    row=row_idx, column=col_idx, sticky="nsew")
        
        # Column expansion adjustment
        for i in range(len(headers)):
            frame.grid_columnconfigure(i, weight=1)
        
        # Button to return to menu
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
