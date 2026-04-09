from __future__ import annotations

import os
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable, Optional

import chess
import chess.engine

PIECE_TO_UNICODE = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",
    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}

COLOR_MILK = "#F8F4EF"
COLOR_NAVY = "#40434E"
COLOR_PANEL = "#F8F4EF"
COLOR_PANEL_TEXT = "#5B6170"
COLOR_BOARD_LIGHT = "#F8F4EF"
COLOR_BOARD_DARK = "#A0A7B7"
COLOR_BOARD_BORDER = "#40434E"
COLOR_LAST_FROM = "#DCE0E8"
COLOR_LAST_TO = "#B8C0D1"
COLOR_SELECTED = "#6E7485"


def _draw_rounded_rect(
    canvas: tk.Canvas,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    radius: float,
    *,
    fill: str,
) -> None:
    r = max(0.0, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=fill)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=fill)
    canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, fill=fill, outline=fill)
    canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, fill=fill, outline=fill)
    canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, fill=fill, outline=fill)
    canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, fill=fill, outline=fill)


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master: tk.Widget,
        *,
        text: str,
        command: Callable[[], None],
        bg_color: str,
        hover_color: str,
        active_color: str,
        fg_color: str,
        font: tuple[str, int, str],
        height: int = 46,
        radius: int = 12,
        width: Optional[int] = None,
    ) -> None:
        canvas_kwargs: dict[str, object] = {
            "height": height,
            "highlightthickness": 0,
            "bd": 0,
            "bg": COLOR_PANEL,
            "cursor": "hand2",
        }
        if width is not None:
            canvas_kwargs["width"] = width
        super().__init__(
            master,
            **canvas_kwargs,
        )
        self._text = text
        self._command = command
        self._bg_color = bg_color
        self._hover_color = hover_color
        self._active_color = active_color
        self._fg_color = fg_color
        self._font = font
        self._radius = radius
        self._pressed = False
        self._hover = False

        self.bind("<Configure>", lambda _: self._redraw())
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _current_color(self) -> str:
        if self._pressed:
            return self._active_color
        if self._hover:
            return self._hover_color
        return self._bg_color

    def _redraw(self) -> None:
        self.delete("all")
        w = max(2, self.winfo_width())
        h = max(2, self.winfo_height())
        _draw_rounded_rect(self, 1, 1, w - 1, h - 1, self._radius, fill=self._current_color())
        self.create_text(
            w / 2,
            h / 2,
            text=self._text,
            fill=self._fg_color,
            font=self._font,
        )

    def _on_enter(self, _: tk.Event) -> None:
        self._hover = True
        self._redraw()

    def _on_leave(self, _: tk.Event) -> None:
        self._hover = False
        self._pressed = False
        self._redraw()

    def _on_press(self, _: tk.Event) -> None:
        self._pressed = True
        self._redraw()

    def _on_release(self, event: tk.Event) -> None:
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        was_pressed = self._pressed
        self._pressed = False
        self._redraw()
        if was_pressed and inside:
            self._command()


class RoundedHintCard(tk.Canvas):
    def __init__(
        self,
        master: tk.Widget,
        *,
        textvariable: tk.StringVar,
        min_height: int = 150,
        radius: int = 14,
    ) -> None:
        super().__init__(
            master,
            height=min_height,
            highlightthickness=0,
            bd=0,
            bg=COLOR_PANEL,
        )
        self._text_var = textvariable
        self._min_height = min_height
        self._radius = radius
        self._trace_id = self._text_var.trace_add("write", self._on_text_change)

        self.bind("<Configure>", lambda _: self._redraw())
        self._redraw()

    def destroy(self) -> None:
        try:
            self._text_var.trace_remove("write", self._trace_id)
        except Exception:
            pass
        super().destroy()

    def _on_text_change(self, *_: object) -> None:
        self._redraw()

    def _redraw(self) -> None:
        self.delete("all")
        w = max(2, self.winfo_width())
        h = max(self._min_height, self.winfo_height())

        _draw_rounded_rect(self, 1, 1, w - 1, h - 1, self._radius, fill=COLOR_NAVY)
        self.create_text(
            16,
            16,
            text="ПОДСКАЗКА:",
            fill=COLOR_MILK,
            font=("Trebuchet MS", 15, "bold"),
            anchor="nw",
        )
        body_id = self.create_text(
            16,
            44,
            text=self._text_var.get(),
            fill=COLOR_MILK,
            font=("Trebuchet MS", 18),
            anchor="nw",
            width=max(40, w - 32),
        )

        bbox = self.bbox(body_id)
        if bbox:
            needed_h = max(self._min_height, bbox[3] + 16)
            if abs(needed_h - self.winfo_height()) > 1:
                self.configure(height=needed_h)


class ColorModeSwitch(tk.Frame):
    def __init__(
        self,
        master: tk.Widget,
        *,
        text: str,
        variable: tk.BooleanVar,
        command: Callable[[], None],
    ) -> None:
        super().__init__(master, bg=COLOR_PANEL, bd=0)
        self._variable = variable
        self._command = command
        self._trace_id = self._variable.trace_add("write", self._on_value_change)
        self._switch_w = 74
        self._switch_h = 36

        self._label = tk.Label(
            self,
            text=text,
            bg=COLOR_PANEL,
            fg=COLOR_NAVY,
            font=("Trebuchet MS", 18, "bold"),
            anchor="w",
        )
        self._label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._switch = tk.Canvas(
            self,
            width=self._switch_w,
            height=self._switch_h,
            bg=COLOR_PANEL,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self._switch.pack(side=tk.RIGHT)

        for widget in (self, self._label, self._switch):
            widget.bind("<Button-1>", self._toggle)

        self._redraw()

    def destroy(self) -> None:
        try:
            self._variable.trace_remove("write", self._trace_id)
        except Exception:
            pass
        super().destroy()

    def _toggle(self, _: tk.Event) -> None:
        self._variable.set(not self._variable.get())
        self._command()

    def _on_value_change(self, *_: object) -> None:
        self._redraw()

    def _redraw(self) -> None:
        self._switch.delete("all")
        w = self._switch_w
        h = self._switch_h
        is_on = self._variable.get()
        track_color = COLOR_NAVY if is_on else "#C4CAD6"
        knob_x = 54 if is_on else 20

        _draw_rounded_rect(self._switch, 2, 2, w - 2, h - 2, 17, fill=track_color)
        self._switch.create_oval(
            knob_x - 12,
            6,
            knob_x + 12,
            h - 6,
            fill=COLOR_MILK,
            outline="",
        )


class ChessHelperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Chess Helper")

        self.board = chess.Board()
        self.last_move: Optional[chess.Move] = None
        self.selected_square: Optional[chess.Square] = None
        self.my_color = chess.WHITE

        self.square_size = 68
        self.margin = 24
        self.board_px = self.square_size * 8
        self.canvas_px = self.board_px + self.margin * 2
        self.sidebar_width = 360
        self.piece_font_size = int(self.square_size * 0.66)

        self.play_black_var = tk.BooleanVar(value=False)
        self.engine_status_var = tk.StringVar(value="Подготовка приложения...")
        self.hint_var = tk.StringVar(value="Движок запускается...")
        self.moves_var = tk.StringVar(value="Ходы: -")

        self.engine: Optional[chess.engine.SimpleEngine] = None
        self.engine_lock = threading.Lock()
        self.analysis_limit = chess.engine.Limit(time=0.35)
        self.analysis_request_id = 0
        self.suggested_move: Optional[chess.Move] = None

        window_width = self.canvas_px + self.sidebar_width + 64
        window_height = self.canvas_px + 36
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(window_width, window_height)

        self._configure_theme()
        self._build_ui()
        self._draw_board()
        self._refresh_moves_text()
        self._load_engine_async()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_theme(self) -> None:
        self.root.configure(bg=COLOR_MILK)
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background=COLOR_MILK)
        style.configure("Panel.TFrame", background=COLOR_PANEL)

        style.configure(
            "Title.TLabel",
            background=COLOR_PANEL,
            foreground=COLOR_NAVY,
            font=("Trebuchet MS", 40, "bold"),
        )
        style.configure(
            "App.TLabel",
            background=COLOR_PANEL,
            foreground=COLOR_NAVY,
            font=("Trebuchet MS", 16),
        )
        style.configure(
            "Panel.TLabel",
            background=COLOR_PANEL,
            foreground=COLOR_PANEL_TEXT,
            font=("Trebuchet MS", 14),
        )
        style.configure(
            "Status.TLabel",
            background=COLOR_PANEL,
            foreground="#7B808F",
            font=("Trebuchet MS", 11),
        )

        style.configure(
            "App.TButton",
            font=("Trebuchet MS", 13, "bold"),
            padding=(14, 10),
            background=COLOR_NAVY,
            foreground=COLOR_MILK,
            borderwidth=0,
            focusthickness=0,
        )
        style.map(
            "App.TButton",
            background=[("active", "#4B5060"), ("pressed", "#333642")],
            foreground=[("disabled", "#CFC8BF")],
        )

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, style="App.TFrame", padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        layout = ttk.Frame(container, style="App.TFrame")
        layout.pack(fill=tk.BOTH, expand=True)

        board_zone = ttk.Frame(layout, style="App.TFrame")
        board_zone.pack(side=tk.LEFT, fill=tk.Y)

        self.canvas = tk.Canvas(
            board_zone,
            width=self.canvas_px,
            height=self.canvas_px,
            highlightthickness=0,
            bg=COLOR_MILK,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        side_panel = ttk.Frame(layout, style="Panel.TFrame", padding=14)
        side_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12, 0))
        side_panel.configure(width=self.sidebar_width)
        side_panel.pack_propagate(False)

        ttk.Label(side_panel, text="Chess Helper", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            side_panel,
            text="Разработка iglakovmaks",
            style="Panel.TLabel",
        ).pack(anchor=tk.W, pady=(2, 20))

        self.color_mode_switch = ColorModeSwitch(
            side_panel,
            text="Играть за чёрных",
            variable=self.play_black_var,
            command=self._on_color_toggle,
        )
        self.color_mode_switch.pack(fill=tk.X, pady=(0, 12))

        button_panel = tk.Frame(side_panel, bg=COLOR_PANEL, bd=0)
        button_panel.pack(fill=tk.X, pady=(0, 14))

        RoundedButton(
            button_panel,
            text="Новая партия",
            command=self._new_game,
            bg_color=COLOR_NAVY,
            hover_color="#4B5060",
            active_color="#333642",
            fg_color=COLOR_MILK,
            font=("Trebuchet MS", 16, "bold"),
            height=48,
            radius=12,
        ).pack(fill=tk.X, pady=(0, 10))
        RoundedButton(
            button_panel,
            text="Отменить ход",
            command=self._undo_move,
            bg_color=COLOR_NAVY,
            hover_color="#4B5060",
            active_color="#333642",
            fg_color=COLOR_MILK,
            font=("Trebuchet MS", 16, "bold"),
            height=48,
            radius=12,
        ).pack(fill=tk.X)

        self.hint_card = RoundedHintCard(
            side_panel,
            textvariable=self.hint_var,
            min_height=148,
            radius=12,
        )
        self.hint_card.pack(fill=tk.X)

        info_panel = ttk.Frame(side_panel, style="Panel.TFrame", padding=(0, 12, 0, 0))
        info_panel.pack(fill=tk.BOTH, expand=True)

        ttk.Label(info_panel, textvariable=self.engine_status_var, style="Status.TLabel").pack(anchor=tk.W)
        ttk.Label(
            info_panel,
            textvariable=self.moves_var,
            style="Panel.TLabel",
            justify=tk.LEFT,
            wraplength=self.sidebar_width - 36,
        ).pack(anchor=tk.W, pady=(6, 0))

    def _resolve_engine_path(self) -> str:
        env_path = os.environ.get("STOCKFISH_PATH")
        if env_path and Path(env_path).exists():
            return env_path

        from_path = shutil.which("stockfish")
        if from_path:
            return from_path

        local_binary = Path(__file__).resolve().parent / "stockfish"
        if local_binary.exists():
            return str(local_binary)

        raise FileNotFoundError(
            "Stockfish не найден. Установите `stockfish` в PATH "
            "или задайте переменную окружения STOCKFISH_PATH."
        )

    def _load_engine_async(self) -> None:
        worker = threading.Thread(target=self._load_engine_worker, daemon=True)
        worker.start()

    def _load_engine_worker(self) -> None:
        try:
            engine_path = self._resolve_engine_path()
            engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            self._configure_engine(engine)
        except Exception:
            self.root.after(0, lambda: self.engine_status_var.set("Не удалось запустить движок"))
            self.root.after(0, lambda: self.hint_var.set("Проверьте установку Stockfish и попробуйте снова."))
            return

        def finish() -> None:
            with self.engine_lock:
                self.engine = engine
            self.engine_status_var.set("Приложение готово к работе")
            self._refresh_hint_for_turn()

        self.root.after(0, finish)

    def _configure_engine(self, engine: chess.engine.SimpleEngine) -> None:
        cpu_threads = os.cpu_count() or 1
        options = {
            "Threads": max(1, min(4, cpu_threads)),
            "Hash": 128,
        }
        available = engine.options
        filtered = {key: value for key, value in options.items() if key in available}
        if filtered:
            engine.configure(filtered)

    def _on_color_toggle(self) -> None:
        self.my_color = chess.BLACK if self.play_black_var.get() else chess.WHITE
        self._draw_board()
        self._refresh_hint_for_turn()

    def _new_game(self) -> None:
        self.board = chess.Board()
        self.last_move = None
        self.selected_square = None
        self.suggested_move = None
        self._draw_board()
        self._refresh_moves_text()
        self._refresh_hint_for_turn()

    def _undo_move(self) -> None:
        if not self.board.move_stack:
            return

        self.board.pop()
        self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
        self.selected_square = None
        self.suggested_move = None

        self._draw_board()
        self._refresh_moves_text()
        self._refresh_hint_for_turn()

    def _on_canvas_click(self, event: tk.Event) -> None:
        col = (event.x - self.margin) // self.square_size
        row = (event.y - self.margin) // self.square_size
        if not (0 <= col < 8 and 0 <= row < 8):
            return

        square = self._grid_to_square(col, row)
        piece = self.board.piece_at(square)

        if self.selected_square is None:
            if piece is None:
                return
            if piece.color != self.board.turn:
                self.hint_var.set("Сейчас ход другой стороны. Выберите фигуру, которой можно ходить.")
                return
            self.selected_square = square
            self._draw_board()
            return

        if square == self.selected_square:
            self.selected_square = None
            self._draw_board()
            return

        if piece is not None and piece.color == self.board.turn:
            self.selected_square = square
            self._draw_board()
            return

        self._attempt_move(self.selected_square, square)

    def _attempt_move(self, from_square: chess.Square, to_square: chess.Square) -> None:
        candidates = [
            move
            for move in self.board.legal_moves
            if move.from_square == from_square and move.to_square == to_square
        ]

        if not candidates:
            self.hint_var.set("Нелегальный ход для текущей позиции.")
            self.selected_square = None
            self._draw_board()
            return

        move = self._choose_move(candidates)
        if move is None:
            self.selected_square = None
            self._draw_board()
            return

        self.board.push(move)
        self.last_move = move
        self.selected_square = None
        self.suggested_move = None

        self._draw_board()
        self._refresh_moves_text()

        if self.board.is_checkmate():
            winner = "Белые" if self.board.turn == chess.BLACK else "Черные"
            self.hint_var.set(f"Мат. Победили {winner}.")
            return

        if self.board.is_stalemate() or self.board.is_insufficient_material():
            self.hint_var.set("Ничья в текущей позиции.")
            return

        self._refresh_hint_for_turn()

    def _choose_move(self, candidates: list[chess.Move]) -> Optional[chess.Move]:
        if len(candidates) == 1:
            return candidates[0]

        promotion_moves = [move for move in candidates if move.promotion]
        if not promotion_moves:
            return candidates[0]

        chosen_piece = self._show_promotion_popup(self.board.turn)
        if chosen_piece is None:
            return None

        for move in promotion_moves:
            if move.promotion == chosen_piece:
                return move

        return promotion_moves[0]

    def _show_promotion_popup(self, color: chess.Color) -> Optional[chess.PieceType]:
        selected_piece: dict[str, Optional[chess.PieceType]] = {"piece": None}

        popup = tk.Toplevel(self.root)
        popup.title("Превращение пешки")
        popup.configure(bg=COLOR_PANEL)
        popup.resizable(False, False)
        popup.transient(self.root)

        container = tk.Frame(popup, bg=COLOR_PANEL, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            container,
            text="Выберите фигуру для превращения",
            bg=COLOR_PANEL,
            fg=COLOR_NAVY,
            font=("Trebuchet MS", 14, "bold"),
        ).pack(anchor="w")

        options_frame = tk.Frame(container, bg=COLOR_PANEL)
        options_frame.pack(pady=(12, 8))

        option_defs: list[tuple[chess.PieceType, str]] = [
            (chess.QUEEN, "Ферзь"),
            (chess.ROOK, "Ладья"),
            (chess.BISHOP, "Слон"),
            (chess.KNIGHT, "Конь"),
        ]

        def choose(piece_type: chess.PieceType) -> None:
            selected_piece["piece"] = piece_type
            popup.destroy()

        def make_card(parent: tk.Frame, piece_type: chess.PieceType, label: str) -> tk.Canvas:
            symbol = PIECE_TO_UNICODE[chess.Piece(piece_type, color).symbol()]
            card = tk.Canvas(
                parent,
                width=88,
                height=106,
                bg=COLOR_PANEL,
                highlightthickness=0,
                bd=0,
                cursor="hand2",
            )

            def draw(hovered: bool = False) -> None:
                card.delete("all")
                outer = "#CBD2DF" if not hovered else "#B0B9CA"
                _draw_rounded_rect(card, 1, 1, 87, 105, 14, fill=outer)
                _draw_rounded_rect(card, 3, 3, 85, 103, 12, fill=COLOR_MILK)
                card.create_text(
                    44,
                    40,
                    text=symbol,
                    font=("DejaVu Sans", 32),
                    fill=COLOR_NAVY,
                )
                card.create_text(
                    44,
                    82,
                    text=label,
                    font=("Trebuchet MS", 11, "bold"),
                    fill=COLOR_NAVY,
                )

            draw(False)
            card.bind("<Enter>", lambda _: draw(True))
            card.bind("<Leave>", lambda _: draw(False))
            card.bind("<Button-1>", lambda _: choose(piece_type))
            return card

        for index, (piece_type, label) in enumerate(option_defs):
            card = make_card(options_frame, piece_type, label)
            card.grid(row=0, column=index, padx=6)

        cancel_row = tk.Frame(container, bg=COLOR_PANEL, bd=0)
        cancel_row.pack(fill=tk.X, pady=(4, 0))
        RoundedButton(
            cancel_row,
            text="Отмена",
            command=popup.destroy,
            bg_color=COLOR_NAVY,
            hover_color="#4B5060",
            active_color="#333642",
            fg_color=COLOR_MILK,
            font=("Trebuchet MS", 12, "bold"),
            height=42,
            radius=10,
            width=132,
        ).pack(anchor="e")

        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        popup.update_idletasks()
        self._center_popup(popup)
        popup.grab_set()
        popup.wait_window()
        return selected_piece["piece"]

    def _center_popup(self, popup: tk.Toplevel) -> None:
        self.root.update_idletasks()
        popup.update_idletasks()

        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()
        popup_w = popup.winfo_width()
        popup_h = popup.winfo_height()

        x = root_x + (root_w - popup_w) // 2
        y = root_y + (root_h - popup_h) // 2
        popup.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _suggest_move(self) -> None:
        if self.board.turn != self.my_color:
            self.hint_var.set("Сейчас ход соперника. Сначала внесите его ход на доску.")
            return

        with self.engine_lock:
            engine = self.engine

        if engine is None:
            self.hint_var.set("Движок еще не готов.")
            return

        self.analysis_request_id += 1
        request_id = self.analysis_request_id
        request_fen = self.board.fen()
        board_snapshot = self.board.copy(stack=False)

        self.hint_var.set("Stockfish думает...")
        worker = threading.Thread(
            target=self._analyze_position_worker,
            args=(request_id, request_fen, board_snapshot),
            daemon=True,
        )
        worker.start()

    def _analyze_position_worker(self, request_id: int, request_fen: str, board_snapshot: chess.Board) -> None:
        try:
            with self.engine_lock:
                engine = self.engine
                if engine is None:
                    raise RuntimeError("Движок недоступен.")

                infos = engine.analyse(
                    board_snapshot,
                    self.analysis_limit,
                    multipv=1,
                    info=chess.engine.INFO_SCORE | chess.engine.INFO_PV,
                )
        except Exception as exc:
            self.root.after(
                0,
                lambda: self._apply_analysis(request_id, request_fen, None, None, f"Ошибка анализа: {exc}"),
            )
            return

        entry = infos[0] if isinstance(infos, list) else infos
        pv = entry.get("pv")
        if not pv:
            self.root.after(
                0,
                lambda: self._apply_analysis(request_id, request_fen, None, None, "Не удалось получить вариант."),
            )
            return

        move = pv[0]
        line = self._format_move_hint(board_snapshot, move)
        self.root.after(
            0,
            lambda: self._apply_analysis(request_id, request_fen, line, move.uci(), None),
        )

    def _apply_analysis(
        self,
        request_id: int,
        request_fen: str,
        line: Optional[str],
        suggested_move_uci: Optional[str],
        error: Optional[str],
    ) -> None:
        if request_id != self.analysis_request_id:
            return

        if request_fen != self.board.fen():
            return

        if error:
            self.hint_var.set(error)
            self.suggested_move = None
            self._draw_board()
            return

        assert line is not None
        self.hint_var.set(line)

        self.suggested_move = None
        if suggested_move_uci:
            move = chess.Move.from_uci(suggested_move_uci)
            if move in self.board.legal_moves:
                self.suggested_move = move
        self._draw_board()

    def _format_move_hint(self, board_snapshot: chess.Board, move: chess.Move) -> str:
        if board_snapshot.is_castling(move):
            if chess.square_file(move.to_square) > chess.square_file(move.from_square):
                return "Короткая рокировка"
            return "Длинная рокировка"

        piece = board_snapshot.piece_at(move.from_square)
        if piece is None:
            return f"Ход на {chess.square_name(move.to_square)}"

        names = {
            chess.PAWN: "Пешка",
            chess.KNIGHT: "Конь",
            chess.BISHOP: "Слон",
            chess.ROOK: "Ладья",
            chess.QUEEN: "Ферзь",
            chess.KING: "Король",
        }
        piece_name = names.get(piece.piece_type, "Фигура")
        target_square = chess.square_name(move.to_square)

        if move.promotion:
            promotion_names = {
                chess.QUEEN: "ферзя",
                chess.ROOK: "ладью",
                chess.BISHOP: "слона",
                chess.KNIGHT: "коня",
            }
            promoted_to = promotion_names.get(move.promotion, "фигуру")
            return f"{piece_name} на {target_square} с превращением в {promoted_to}"

        return f"{piece_name} на {target_square}"

    def _refresh_hint_for_turn(self) -> None:
        if self.board.turn != self.my_color:
            self.suggested_move = None
            self._draw_board()
            self.hint_var.set("Сейчас ход соперника.\nВведите его ход на доске.")
            return

        with self.engine_lock:
            engine_ready = self.engine is not None

        if not engine_ready:
            self.suggested_move = None
            self._draw_board()
            self.hint_var.set("Ваш ход. Движок пока запускается.")
            return

        self._suggest_move()

    def _refresh_moves_text(self) -> None:
        if not self.board.move_stack:
            self.moves_var.set("Ходы: -")
            return

        preview: list[str] = []
        temp = chess.Board()
        for idx, move in enumerate(self.board.move_stack):
            if idx % 2 == 0:
                preview.append(f"{idx // 2 + 1}.")
            preview.append(temp.san(move))
            temp.push(move)

        tail = preview[-24:]
        self.moves_var.set(f"Ходы: {' '.join(tail)}")

    def _grid_to_square(self, col: int, row: int) -> chess.Square:
        if self.my_color == chess.WHITE:
            file_idx = col
            rank_idx = 7 - row
        else:
            file_idx = 7 - col
            rank_idx = row
        return chess.square(file_idx, rank_idx)

    def _draw_piece(self, square_x1: float, square_y1: float, square_x2: float, square_y2: float, piece: chess.Piece) -> None:
        piece_symbol = PIECE_TO_UNICODE[piece.symbol()]
        self.canvas.create_text(
            (square_x1 + square_x2) / 2,
            (square_y1 + square_y2) / 2,
            text=piece_symbol,
            font=("DejaVu Sans", self.piece_font_size),
            fill="#20232D",
        )

    def _square_to_canvas_center(self, square: chess.Square) -> tuple[float, float]:
        file_idx = chess.square_file(square)
        rank_idx = chess.square_rank(square)

        if self.my_color == chess.WHITE:
            col = file_idx
            row = 7 - rank_idx
        else:
            col = 7 - file_idx
            row = rank_idx

        x = self.margin + col * self.square_size + self.square_size / 2
        y = self.margin + row * self.square_size + self.square_size / 2
        return x, y

    def _draw_suggestion_arrow(self, move: chess.Move) -> None:
        from_x, from_y = self._square_to_canvas_center(move.from_square)
        to_x, to_y = self._square_to_canvas_center(move.to_square)
        dx = to_x - from_x
        dy = to_y - from_y
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1e-6:
            return

        # Уводим начало/конец стрелки от центров клеток, чтобы не перекрывать фигуры.
        start_offset = self.square_size * 0.30
        end_offset = self.square_size * 0.20
        ux = dx / dist
        uy = dy / dist

        start_x = from_x + ux * start_offset
        start_y = from_y + uy * start_offset
        end_x = to_x - ux * end_offset
        end_y = to_y - uy * end_offset

        self.canvas.create_line(
            start_x,
            start_y,
            end_x,
            end_y,
            fill="#CCD3E1",
            width=9,
            capstyle=tk.ROUND,
            arrow=tk.LAST,
            arrowshape=(18, 20, 8),
        )
        self.canvas.create_line(
            start_x,
            start_y,
            end_x,
            end_y,
            fill=COLOR_NAVY,
            width=5,
            capstyle=tk.ROUND,
            arrow=tk.LAST,
            arrowshape=(15, 17, 7),
        )

    def _draw_board(self) -> None:
        self.canvas.delete("all")
        self.canvas.create_rectangle(
            self.margin - 4,
            self.margin - 4,
            self.margin + self.board_px + 4,
            self.margin + self.board_px + 4,
            outline=COLOR_BOARD_BORDER,
            width=3,
            fill="",
        )

        last_from = self.last_move.from_square if self.last_move else None
        last_to = self.last_move.to_square if self.last_move else None

        for row in range(8):
            for col in range(8):
                square = self._grid_to_square(col, row)
                x1 = self.margin + col * self.square_size
                y1 = self.margin + row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                base_color = COLOR_BOARD_LIGHT if (row + col) % 2 == 0 else COLOR_BOARD_DARK
                fill_color = base_color

                if square == last_from:
                    fill_color = COLOR_LAST_FROM
                if square == last_to:
                    fill_color = COLOR_LAST_TO
                if square == self.selected_square:
                    fill_color = COLOR_SELECTED

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill_color, outline=fill_color)

                piece = self.board.piece_at(square)
                if piece:
                    self._draw_piece(x1, y1, x2, y2, piece)

        if self.suggested_move and self.suggested_move in self.board.legal_moves:
            self._draw_suggestion_arrow(self.suggested_move)

        self._draw_coords()

    def _draw_coords(self) -> None:
        for col in range(8):
            file_char = chr(ord("a") + col)
            if self.my_color == chess.BLACK:
                file_char = chr(ord("a") + (7 - col))

            x = self.margin + col * self.square_size + self.square_size / 2
            y = self.margin + self.board_px + 15
            self.canvas.create_text(
                x,
                y,
                text=file_char,
                font=("Trebuchet MS", 11, "bold"),
                fill=COLOR_NAVY,
            )

        for row in range(8):
            rank_number = str(8 - row)
            if self.my_color == chess.BLACK:
                rank_number = str(row + 1)

            x = self.margin - 14
            y = self.margin + row * self.square_size + self.square_size / 2
            self.canvas.create_text(
                x,
                y,
                text=rank_number,
                font=("Trebuchet MS", 11, "bold"),
                fill=COLOR_NAVY,
            )

    def _on_close(self) -> None:
        with self.engine_lock:
            engine = self.engine
            self.engine = None

        if engine is not None:
            try:
                engine.quit()
            except Exception:
                pass

        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ChessHelperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
