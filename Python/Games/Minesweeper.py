import tkinter as tk
from tkinter import messagebox
import random

class Minesweeper:
    def __init__(self, root, rows=10, cols=10, mines=10):
        self.root = root
        self.rows = rows
        self.cols = cols
        self.mines = mines
        self.grid = [[0 for _ in range(cols)] for _ in range(rows)]
        self.revealed = [[False for _ in range(cols)] for _ in range(rows)]
        self.flagged = [[False for _ in range(cols)] for _ in range(rows)]
        self.game_over = False
        self.first_click = True
        self.buttons = []
        self.place_mines()
        self.set_numbers()
        self.create_gui()

    def place_mines(self):
        mine_positions = random.sample(range(self.rows * self.cols), self.mines)
        for pos in mine_positions:
            row = pos // self.cols
            col = pos % self.cols
            self.grid[row][col] = -1

    def set_numbers(self):
        for i in range(self.rows):
            for j in range(self.cols):
                if self.grid[i][j] != -1:
                    self.grid[i][j] = self.count_adjacent_mines(i, j)

    def count_adjacent_mines(self, row, col):
        count = 0
        for i in range(max(0, row-1), min(self.rows, row+2)):
            for j in range(max(0, col-1), min(self.cols, col+2)):
                if self.grid[i][j] == -1:
                    count += 1
        return count

    def move_mine(self, row, col):
        for i in range(self.rows):
            for j in range(self.cols):
                if self.grid[i][j] != -1 and (i != row or j != col):
                    self.grid[i][j] = -1
                    self.grid[row][col] = 0
                    self.set_numbers()
                    return

    def reveal_cell(self, row, col):
        if self.game_over or self.revealed[row][col] or self.flagged[row][col]:
            return
        if self.first_click:
            if self.grid[row][col] == -1:
                self.move_mine(row, col)
            self.first_click = False
        self.revealed[row][col] = True
        if self.grid[row][col] == -1:
            self.game_over = True
            self.show_all_mines()
            messagebox.showinfo("Game Over", "You hit a mine!")
            return
        if self.grid[row][col] == 0:
            for i in range(max(0, row-1), min(self.rows, row+2)):
                for j in range(max(0, col-1), min(self.cols, col+2)):
                    if not self.revealed[i][j]:
                        self.reveal_cell(i, j)
        self.update_button(row, col)
        self.check_win()

    def flag_cell(self, row, col, event):
        if self.game_over or self.revealed[row][col]:
            return
        self.flagged[row][col] = not self.flagged[row][col]
        self.update_button(row, col)

    def update_button(self, row, col):
        button = self.buttons[row][col]
        if self.revealed[row][col]:
            if self.grid[row][col] == -1:
                button.config(text="*", bg="red")
            elif self.grid[row][col] == 0:
                button.config(text="", bg="lightgray")
            else:
                button.config(text=str(self.grid[row][col]), bg="lightgray")
        elif self.flagged[row][col]:
            button.config(text="F", bg="yellow")
        else:
            button.config(text="", bg="gray")

    def show_all_mines(self):
        for i in range(self.rows):
            for j in range(self.cols):
                if self.grid[i][j] == -1:
                    self.revealed[i][j] = True
                    self.update_button(i, j)

    def check_win(self):
        revealed_count = sum(sum(row) for row in self.revealed)
        if revealed_count == self.rows * self.cols - self.mines:
            self.game_over = True
            messagebox.showinfo("Congratulations", "You won!")

    def create_gui(self):
        for i in range(self.rows):
            row = []
            for j in range(self.cols):
                button = tk.Button(self.root, width=2, height=1, command=lambda r=i, c=j: self.reveal_cell(r, c))
                button.bind("<Button-3>", lambda event, r=i, c=j: self.flag_cell(r, c, event))
                button.grid(row=i, column=j)
                row.append(button)
            self.buttons.append(row)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Minesweeper")
    game = Minesweeper(root)
    root.mainloop()