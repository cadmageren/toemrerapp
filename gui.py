import tkinter as tk
from tkinter import ttk, colorchooser

class ToemrerGUI:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        
        # Globale UI elementer
        self.canvas = None
        self.txt_log = None
        self.tree_cats = None
        self.tree_sections = None
        self.lbl_scale = None
        
        # Input felter
        self.entry_name = None
        self.combo_type = None
        self.entry_height = None
        self.btn_color = None
        self.entry_note = None # (Beholder denne som backup/alternativ)
        
        self.edit_entry = None # Midlertidigt felt til inline-editing
        self.left_panel = None 

        self.setup_ui()

    def setup_ui(self):
        # --- VENSTRE PANEL ---
        self.left_panel = tk.Frame(self.root, width=380, bg="#f0f0f0")
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        self.left_panel.pack_propagate(False)

        # 1. Opsætning
        tk.Label(self.left_panel, text="1. Opsætning", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(pady=(10,5))
        f_tools = tk.Frame(self.left_panel, bg="#f0f0f0")
        f_tools.pack(fill=tk.X, padx=5)
        
        tk.Button(f_tools, text="Åbn PDF", command=self.controller.load_pdf, width=15).grid(row=0, column=0, padx=2)
        tk.Button(f_tools, text="Kalibrer Skala", command=self.controller.start_calibration, width=15).grid(row=0, column=1, padx=2)
        
        self.lbl_scale = tk.Label(self.left_panel, text="Skala: Ikke sat", bg="#f0f0f0", fg="red")
        self.lbl_scale.pack(pady=2)
        
        tk.Checkbutton(self.left_panel, text="Vis PDF Baggrund", 
                       variable=self.controller.show_pdf, 
                       command=self.controller.refresh_view, 
                       bg="#f0f0f0").pack(anchor="w", padx=10, pady=(0, 5))
        
        # 2. Opret Konstruktion
        tk.Label(self.left_panel, text="2. Opret Konstruktion", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(pady=(15, 5))
        
        f_create = tk.Frame(self.left_panel, bg="#f0f0f0")
        f_create.pack(fill=tk.X, padx=5)
        
        # Navn
        tk.Label(f_create, text="Navn:", bg="#f0f0f0", anchor="w").pack(fill=tk.X)
        self.entry_name = tk.Entry(f_create)
        self.entry_name.pack(fill=tk.X, pady=(0, 5))

        # Type
        tk.Label(f_create, text="Type:", bg="#f0f0f0", anchor="w").pack(fill=tk.X)
        type_options = ["Lbm", "m²", "Stk", "Lbm x Højde"]
        self.combo_type = ttk.Combobox(f_create, values=type_options, state="readonly")
        self.combo_type.pack(fill=tk.X, pady=(0, 5))
        self.combo_type.set("Lbm")
        self.combo_type.bind("<<ComboboxSelected>>", self.controller.on_type_selected)
        
        # Farve og Højde
        f_conf = tk.Frame(f_create, bg="#f0f0f0")
        f_conf.pack(fill=tk.X, pady=2)
        
        self.btn_color = tk.Button(f_conf, text="Farve", bg="red", width=5, command=self.pick_color)
        self.btn_color.pack(side=tk.LEFT, padx=2)

        self.frame_height = tk.Frame(f_conf, bg="#f0f0f0")
        tk.Label(self.frame_height, text="H:", bg="#f0f0f0").pack(side=tk.LEFT)
        self.entry_height = tk.Entry(self.frame_height, width=5, justify="center")
        self.entry_height.insert(0, "2.50")
        self.entry_height.pack(side=tk.LEFT)

        tk.Button(f_conf, text="Opret", command=self.controller.create_category, bg="#b3ffb3", width=10).pack(side=tk.RIGHT, padx=2, fill=tk.X, expand=True)

        # Liste over kategorier
        columns = ("id", "navn", "type", "vis")
        self.tree_cats = ttk.Treeview(self.left_panel, columns=columns, show="headings", height=6)
        
        self.tree_cats.heading("id", text="#", anchor="w")
        self.tree_cats.heading("navn", text="Navn (Dobbeltklik)", anchor="w")
        self.tree_cats.heading("type", text="Type", anchor="w")
        self.tree_cats.heading("vis", text="Vis", anchor="center") # Centreret overskrift
        
        self.tree_cats.column("id", width=30, anchor="center")
        self.tree_cats.column("navn", width=140)
        self.tree_cats.column("type", width=80)
        self.tree_cats.column("vis", width=40, anchor="center") # Centreret ikon
        
        self.tree_cats.pack(padx=5, pady=5, fill=tk.X)
        self.tree_cats.bind('<<TreeviewSelect>>', self.controller.on_category_select)
        self.tree_cats.bind('<Delete>', lambda e: self.controller.delete_category())
        
        # BINDINGS
        # 1. Dobbeltklik for at redigere navn (Inline Edit)
        self.tree_cats.bind("<Double-1>", lambda e: self.on_tree_double_click(e, "cats"))
        
        # 2. Enkeltklik for at skifte synlighed (Toggle) - NYT!
        self.tree_cats.bind("<Button-1>", self.on_tree_single_click)

        # 3. Målinger
        tk.Label(self.left_panel, text="3. Målinger", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(pady=(10, 5))
        
        sec_cols = ("id", "val", "note")
        self.tree_sections = ttk.Treeview(self.left_panel, columns=sec_cols, show="headings", height=6)
        
        self.tree_sections.heading("id", text="#", anchor="w")
        self.tree_sections.column("id", width=40, anchor="w")
        
        self.tree_sections.heading("val", text="Mængde", anchor="e") 
        self.tree_sections.column("val", width=100, anchor="e")
        
        self.tree_sections.heading("note", text="Note (Dobbeltklik)", anchor="w") # Hint
        self.tree_sections.column("note", width=100, anchor="w")
        
        self.tree_sections.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.tree_sections.bind('<<TreeviewSelect>>', self.controller.on_section_select)
        self.tree_sections.bind('<Delete>', lambda e: self.controller.delete_selected_section())
        self.tree_sections.bind("<Double-1>", lambda e: self.on_tree_double_click(e, "sections"))


        # 4. Eksport
        tk.Label(self.left_panel, text="4. Eksport", bg="#ddd", font=("Arial", 10, "bold")).pack(fill=tk.X, pady=(15,0))
        f_reports = tk.Frame(self.left_panel, bg="#ddd", pady=5)
        f_reports.pack(fill=tk.X)
        
        # Én samlet knap
        tk.Button(f_reports, text="Eksportér Samlet Rapport (Excel)", command=self.controller.export_report, bg="#e6f2ff", height=2).pack(fill=tk.X, padx=5, pady=2)


        tk.Label(self.left_panel, text="5. Log", bg="#f0f0f0", font=("Arial", 10, "bold")).pack(pady=(10, 5))

        self.txt_log = tk.Text(self.left_panel, height=15, font=("Consolas", 8), state=tk.DISABLED, bg="#fff")
        self.txt_log.pack(padx=5, pady=5, fill=tk.X, side=tk.BOTTOM)
        
        # --- HØJRE PANEL (CANVAS) ---
        frame_canvas = tk.Frame(self.root)
        frame_canvas.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(frame_canvas, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Binds
        self.canvas.bind("<Button-1>", self.controller.on_canvas_click)
        self.canvas.bind("<Motion>", self.controller.on_mouse_move)
        self.canvas.bind("<ButtonPress-3>", self.controller.start_pan)
        self.canvas.bind("<B3-Motion>", self.controller.pan)
        self.canvas.bind("<MouseWheel>", self.controller.on_mouse_wheel) 
        self.canvas.bind("<Double-Button-3>", self.controller.on_canvas_right_double_click)
        self.root.bind("<Escape>", self.controller.cancel_drawing)
        self.root.bind("<Control-z>", lambda e: self.controller.undo_last())
        self.root.bind("<Control-s>", lambda e: self.controller.save_config())

    # --- LOGIK TIL IN-LINE EDITING ---
    def on_tree_double_click(self, event, tree_type):
        """Håndterer oprettelse af Entry felt ovenpå en celle"""
        # Luk evt. åbent felt først
        self.close_edit_entry()
        
        tree = event.widget
        # Find række og kolonne
        region = tree.identify("region", event.x, event.y)
        if region != "cell": return
        
        column = tree.identify_column(event.x) # Returnerer f.eks. "#1", "#2"
        item_id = tree.identify_row(event.y)
        
        if not item_id: return
        
        # KONSTRUKTIONER: Vi vil kun redigere Navn (Kolonne #2)
        if tree_type == "cats":
            if column != "#2": return 
            
        # MÅLINGER: Vi vil kun redigere Note (Kolonne #3)
        if tree_type == "sections":
            if column != "#3": return
            
        # Hent position af cellen (x, y, bredde, højde)
        bbox = tree.bbox(item_id, column)
        if not bbox: return
        
        # Hent nuværende tekst
        current_value = tree.item(item_id).get("values")[int(column[1:]) - 1]
        
        # Opret Entry widget ovenpå cellen
        self.edit_entry = tk.Entry(tree, width=bbox[2]//7) # Bredde justering
        self.edit_entry.place(x=bbox[0], y=bbox[1], width=bbox[2], height=bbox[3])
        self.edit_entry.insert(0, str(current_value))
        self.edit_entry.select_range(0, tk.END)
        self.edit_entry.focus()
        
        # Bind events til at gemme eller annullere
        # Vi sender data med til controlleren via lambda
        self.edit_entry.bind("<Return>", lambda e: self.controller.on_inline_edit_finish(item_id, self.edit_entry.get(), tree_type))
        self.edit_entry.bind("<FocusOut>", lambda e: self.close_edit_entry())
    def on_tree_single_click(self, event):
        """Håndterer klik på 'Vis' ikonet for at toggle synlighed"""
        tree = event.widget
        region = tree.identify("region", event.x, event.y)
        
        # Vi vil kun reagere hvis man klikker på en celle
        if region == "cell":
            col = tree.identify_column(event.x)
            
            # Kolonne #4 er "Vis" kolonnen
            if col == "#4":
                item_id = tree.identify_row(event.y)
                if item_id:
                    # Bed controlleren om at skifte status
                    self.controller.toggle_category_visibility(item_id)
                    
                    # Returner "break" for at forhindre at rækken bliver valgt/markeret 
                    # (valgfrit - men føles ofte bedre ved knapper)
                    return "break"
    def close_edit_entry(self):
        if self.edit_entry:
            self.edit_entry.destroy()
            self.edit_entry = None
    # ---------------------------------

    def toggle_height_field(self, show):
        if show:
            self.frame_height.pack(side=tk.LEFT, padx=(10, 2))
        else:
            self.frame_height.pack_forget()

    def pick_color(self):
        c = colorchooser.askcolor()[1]
        if c: self.btn_color.config(bg=c)

    def log_message(self, msg):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.insert(tk.END, f"{msg}\n")
        self.txt_log.see(tk.END)
        self.txt_log.config(state=tk.DISABLED)