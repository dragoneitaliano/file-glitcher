import tkinter as tk
from tkinter import filedialog, Scrollbar, Tk
from PIL import Image, ImageTk
import io
import math


class ImmagineEditor:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.image_label = None
        self.img_bytes = None
        self.img = None
        self.text_box = None

        self.formati = ["JPEG", "PNG", "BMP", "TIFF"]
        self.formato_var = None
        self.formato_corrente = None

        # --- HEX WINDOW ---
        self.window_size = 1024      # byte visibili per finestra
        self.byte_offset = 0
        self.updating_textbox = False

        self.checkpoints = []
        self.checkpoint_index = -1
        self.max_checkpoints = 10

        self.checkpoint_label = None
        self.prev_btn = None
        self.next_btn = None

        self._update_job = None

        self.setup_gui()

    def setup_gui(self):
        self.root.geometry("1400x800")
        self.root.resizable(True, True)
        self.root.config(bg="#2e2e2e")

        main_frame = tk.Frame(self.root, bg="#2e2e2e")
        main_frame.pack(fill="both", expand=True)

        # ---- IMAGE PREVIEW ----
        image_frame = tk.Frame(main_frame, bg="#2e2e2e")
        image_frame.pack(side="left", padx=20, pady=20, fill="both", expand=True)

        self.image_label = tk.Label(
            image_frame,
            bg="#2e2e2e",
            text="Anteprima Immagine",
            fg="white",
            font=("Helvetica", 16)
        )
        self.image_label.pack(fill="both", expand=True)

        # ---- HEX EDITOR ----
        text_frame = tk.Frame(main_frame, bg="#2e2e2e")
        text_frame.pack(side="right", padx=20, pady=20, fill="both", expand=True)

        self.scrollbar = Scrollbar(
            text_frame,
            orient="vertical",
            command=self.scroll_bytes
        )

        self.text_box = tk.Text(
            text_frame,
            height=30,
            width=80,
            font=("Courier", 10),
            wrap="char",
            bg="#4d4d4d",
            fg="white"
        )

        self.text_box.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.text_box.bind("<KeyRelease>", self.modifica_bytes_in_diretta)

        # ---- BUTTONS ----
        tk.Button(
            self.root,
            text="Carica Immagine",
            command=self.carica_immagine,
            bg="#555",
            fg="white"
        ).pack(side="left", padx=10, pady=10)

        tk.Button(
            self.root,
            text="Salva Immagine",
            command=self.salva_immagine,
            bg="#555",
            fg="white"
        ).pack(side="right", padx=10, pady=10)

        self.formato_var = tk.StringVar(value="Formato")

        tk.OptionMenu(
            self.root,
            self.formato_var,
            *self.formati,
            command=self.converti_formato
        ).pack(side="bottom", pady=10)

        # ---- PAGINA NAVIGATION ----
        self.page_frame = tk.Frame(self.root, bg="#2e2e2e")
        self.page_frame.pack(side="bottom", pady=5)

        self.page_label = tk.Label(self.page_frame, text="Pagina 0/0", fg="white", bg="#2e2e2e")
        self.page_label.pack(side="left", padx=5)

        self.page_entry = tk.Entry(self.page_frame, width=5)
        self.page_entry.pack(side="left", padx=5)

        tk.Button(self.page_frame, text="Vai", command=self.goto_page, bg="#555", fg="white").pack(side="left")

        # ---- CHECKPOINT NAVIGATION sotto immagine ----
        checkpoint_frame = tk.Frame(image_frame, bg="#2e2e2e")
        checkpoint_frame.pack(side="bottom", pady=10)

        self.checkpoint_label = tk.Label(
            checkpoint_frame,
            text="Checkpoint: - / -",
            bg="#2e2e2e",
            fg="white"
        )
        self.checkpoint_label.pack(side="left", padx=5)

        self.prev_btn = tk.Button(
            checkpoint_frame,
            text="⏮ Precedente",
            command=self.checkpoint_precedente,
            state="disabled"
        )
        self.prev_btn.pack(side="left", padx=5)

        self.next_btn = tk.Button(
            checkpoint_frame,
            text="⏭ Successivo",
            command=self.checkpoint_successivo,
            state="disabled"
        )
        self.next_btn.pack(side="left", padx=5)

    # ============================================================
    # FILE HANDLING
    # ============================================================

    def carica_immagine(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("Images", "*.bmp;*.tiff;*.png;*.jpg;*.jpeg")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "rb") as f:
                self.img_bytes = bytearray(f.read())

            self.img = Image.open(io.BytesIO(self.img_bytes))
            self.img.load()

            self.formato_corrente = self.img.format
            self.formato_var.set(self.formato_corrente)

            self.byte_offset = 0
            self.aggiorna_textbox()
            self.update_scrollbar()

            self.root.after(1, self.aggiorna_interfaccia)

            self.checkpoints.clear()
            self.checkpoint_index = -1
            self.salva_checkpoint()

        except Exception:
            self.mostra_errore("File Corrotto")

    def salva_immagine(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("Bitmap", "*.bmp"), ("TIFF", "*.tiff")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "wb") as f:
                f.write(self.img_bytes)
        except Exception:
            self.mostra_errore("Errore di salvataggio")

    # ============================================================
    # IMAGE PREVIEW
    # ============================================================

    def aggiorna_interfaccia(self):
        try:
            max_size = 500
            w, h = self.img.size
            # calcolo fattore di scala
            scale = min(max_size / w, max_size / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_resized = self.img.resize((new_w, new_h), Image.LANCZOS)

            img_tk = ImageTk.PhotoImage(img_resized)
            self.image_label.config(image=img_tk, text="")
            self.image_label.image = img_tk
        except Exception:
            self.mostra_errore("File Corrotto")

    def _decodifica_preview(self):
        try:
            img = Image.open(io.BytesIO(self.img_bytes))
            img.load()

            self.img = img
            self.salva_checkpoint()
            self.aggiorna_interfaccia()

        except Exception:
            self.mostra_errore("File Corrotto")


    # ============================================================
    # HEX WINDOW LOGIC
    # ============================================================

    def aggiorna_textbox(self):
        if self.img_bytes is None:
            return

        self.updating_textbox = True

        start = self.byte_offset
        end = min(start + self.window_size, len(self.img_bytes))
        chunk = self.img_bytes[start:end]

        # hex senza maiuscole e senza andare a capo
        hex_string = "".join(f"{b:02x}" for b in chunk)

        self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, hex_string)

        self.updating_textbox = False
        self.update_scrollbar()
        self.aggiorna_pagina_label()

    def scroll_bytes(self, *args):
        if self.img_bytes is None:
            return

        max_offset = max(len(self.img_bytes) - self.window_size, 0)

        if args[0] == "moveto":
            fraction = float(args[1])
            self.byte_offset = (int(fraction * max_offset) // self.window_size) * self.window_size

        elif args[0] == "scroll":
            step = int(args[1])
            self.byte_offset += step * (self.window_size)

        self.byte_offset = max(0, min(self.byte_offset, max_offset))
        self.aggiorna_textbox()

    def update_scrollbar(self):
        """Aggiorna la scrollbar proporzionale all'offset"""
        if self.img_bytes is None:
            return
        total = len(self.img_bytes)
        if total <= self.window_size:
            self.scrollbar.set(0, 1)
        else:
            first = self.byte_offset / total
            last = min(self.byte_offset + self.window_size, total) / total
            self.scrollbar.set(first, last)

    def modifica_bytes_in_diretta(self, event=None):
        if self.img_bytes is None or self.updating_textbox:
            return

        hex_input = self.text_box.get(1.0, tk.END).strip()
        if len(hex_input) % 2 != 0:
            return

        try:
            new_bytes = bytearray.fromhex(hex_input)

            start = self.byte_offset
            #end = start + self.window_size
            end = start + len(new_bytes)

            # sostituzione a flusso continuo
            self.img_bytes[start:end] = new_bytes

            # riallinea offset alla pagina
            self.byte_offset = (self.byte_offset // self.window_size) * self.window_size

            self.update_scrollbar()

            if self._update_job:
                self.root.after_cancel(self._update_job)

            self._update_job = self.root.after(300, self._decodifica_preview)

        except ValueError:
            pass


    # ============================================================
    # FORMAT CONVERSION
    # ============================================================

    def converti_formato(self, nuovo_formato):
        if self.img is None:
            return

        try:
            buffer = io.BytesIO()
            save_kwargs = {}

            if nuovo_formato == "JPEG":
                save_kwargs["quality"] = 95
                save_kwargs["subsampling"] = 0

            self.img.save(buffer, format=nuovo_formato, **save_kwargs)

            self.img_bytes = bytearray(buffer.getvalue())
            self.img = Image.open(io.BytesIO(self.img_bytes))
            self.img.load()
            
            self.formato_corrente = nuovo_formato
            self.byte_offset = 0
            self.aggiorna_textbox()
            self.aggiorna_interfaccia()
            
            self.checkpoints.clear()
            self.checkpoint_index = -1
            self.salva_checkpoint()
        except Exception:
            self.mostra_errore("Errore conversione formato")

    # ============================================================
    # PAGINA NAVIGATION
    # ============================================================

    def aggiorna_pagina_label(self):
        if self.img_bytes is None:
            self.page_label.config(text="Pagina 0/0")
            return
        totale_pagine = math.ceil(len(self.img_bytes) / self.window_size)
        pagina_corrente = self.byte_offset // self.window_size + 1
        self.page_label.config(text=f"Pagina {pagina_corrente} / {totale_pagine}")

    def goto_page(self):
        if self.img_bytes is None:
            return
        try:
            pagina_scelta = int(self.page_entry.get())
            totale_pagine = math.ceil(len(self.img_bytes) / self.window_size)
            pagina_scelta = max(1, min(pagina_scelta, totale_pagine))
            self.byte_offset = (pagina_scelta - 1) * self.window_size
            self.aggiorna_textbox()
        except ValueError:
            pass

    # ============================================================
    # ERROR HANDLING
    # ============================================================

    def mostra_errore(self, messaggio):
        self.image_label.config(image="", text=messaggio, fg="red")
    
    def salva_checkpoint(self):
        # elimina eventuali checkpoint futuri
        if self.checkpoint_index < len(self.checkpoints) - 1:
            self.checkpoints = self.checkpoints[: self.checkpoint_index + 1]

        self.checkpoints.append(self.img_bytes[:])

        if len(self.checkpoints) > self.max_checkpoints:
            self.checkpoints.pop(0)
        else:
            self.checkpoint_index += 1

        self.update_checkpoint_ui()

    def update_checkpoint_ui(self):
        total = len(self.checkpoints)

        if total == 0:
            self.checkpoint_label.config(text="Checkpoint: - / -")
            self.prev_btn.config(state="disabled")
            self.next_btn.config(state="disabled")
            return

        self.checkpoint_label.config(
            text=f"Checkpoint: {self.checkpoint_index + 1} / {total}"
        )

        self.prev_btn.config(
            state="normal" if self.checkpoint_index > 0 else "disabled"
        )
        self.next_btn.config(
            state="normal" if self.checkpoint_index < total - 1 else "disabled"
        )
    
    def checkpoint_precedente(self):
        if self.checkpoint_index <= 0:
            return

        self.checkpoint_index -= 1
        self._ripristina_da_checkpoint()

    def checkpoint_successivo(self):
        if self.checkpoint_index >= len(self.checkpoints) - 1:
            return

        self.checkpoint_index += 1
        self._ripristina_da_checkpoint()

    def _ripristina_da_checkpoint(self):
        self.img_bytes = self.checkpoints[self.checkpoint_index][:]

        self.byte_offset = (self.byte_offset // self.window_size) * self.window_size

        try:
            self.img = Image.open(io.BytesIO(self.img_bytes))
            self.img.load()

            self.aggiorna_textbox()
            self.aggiorna_interfaccia()
            self.update_checkpoint_ui()

        except Exception:
            self.mostra_errore("Checkpoint non valido")


    def ripristina_immagine(self):
        if not self.checkpoints:
            return

        self.img_bytes = self.checkpoints[-1][:]

        self.byte_offset = (self.byte_offset // self.window_size) * self.window_size

        try:
            self.img = Image.open(io.BytesIO(self.img_bytes))
            self.img.load()

            self.aggiorna_textbox()
            self.aggiorna_interfaccia()

        except Exception:
            self.mostra_errore("Ripristino fallito")


# ============================================================
# MAIN
# ============================================================

root = tk.Tk()
root.title("Modifica Byte Immagine")
app = ImmagineEditor(root)
root.mainloop()
