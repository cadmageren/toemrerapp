import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import json
import os
import pandas as pd

# VORES MODULER
from pdf_handler import PDFHandler
from gui import ToemrerGUI
from excel_manager import ExcelManager
from canvas_manager import CanvasManager 

class ToemrerMaalerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tømrer Opmålings App (v2.1)")
        self.root.state('zoomed')
        self.show_pdf = tk.BooleanVar(value=True)
        
        # 1. INITIALISER MODULER
        self.pdf = PDFHandler() 
        self.excel = ExcelManager()
        self.gui = ToemrerGUI(root, self)

        self.canvas_mgr = CanvasManager(self.gui.canvas, self.pdf)

        # 2. APP DATA
        self.current_pdf_path = None
        self.json_path = None 
        self.categories = {} 
        self.active_category_name = None
        self.highlighted_section = None 
        self.last_mouse_pos = None
        
        # NYT: Tæller til konstruktions ID
        self.next_cat_id = 1 
        


    # --- FIL HÅNDTERING ---
    def load_pdf(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if not file_path: return
        
        if self.pdf.load_file(file_path):
            self.tk_image, w, h = self.pdf.get_page_image(0, 1.0)
            self.canvas_mgr.set_image_size(w, h)
            
            self.current_pdf_path = file_path
            self.json_path = file_path.replace(".pdf", ".json")
            
            # Reset
            self.categories = {}
            self.active_category_name = None
            self.canvas_mgr.scale_factor = 0.0
            self.next_cat_id = 1 # Nulstil ID tæller
            self.gui.lbl_scale.config(text="Skala: Ikke sat", fg="red")
            
            if os.path.exists(self.json_path):
                self.load_config()

            self.update_cat_list()
            self.update_section_list()
            self.refresh_view()
            self.update_ui_state()
            self.log(f"Indlæst: {os.path.basename(file_path)}")
        else:
            messagebox.showerror("Fejl", "Kunne ikke åbne PDF.")

    def reload_master_data(self):
        self.excel.load_data()

    # --- INPUT DELEGERING ---
    def on_type_selected(self, event=None):
        val = self.gui.combo_type.get()
        self.gui.toggle_height_field(val == "Lbm x Højde")

    def create_category(self):
        name = self.gui.entry_name.get().strip()
        raw_type = self.gui.combo_type.get() 
        
        if not name:
            messagebox.showwarning("Fejl", "Angiv et navn")
            return
            
        c_type = "lbm"
        if raw_type == "Stk": c_type = "stk"
        elif raw_type == "m²": c_type = "kvm"
        elif raw_type == "Lbm x Højde": c_type = "lbm_h"
        
        h_val = 0.0
        if c_type == "lbm_h":
            try: h_val = float(self.gui.entry_height.get().replace(',', '.'))
            except: h_val = 2.50
            
        if name not in self.categories:
            col = self.gui.btn_color.cget("bg")
            
            # Tildel ID
            new_id = self.next_cat_id
            self.next_cat_id += 1
            
            self.categories[name] = {
                'id': new_id, # Gem ID
                'type': c_type,
                'color': col,
                'height': h_val,
                'visible': True,
                'measurements': []
            }
            self.active_category_name = name
            self.gui.entry_name.delete(0, tk.END)
            self.update_cat_list()
            
            # Vælg i listen
            for item in self.gui.tree_cats.get_children():
                if str(self.gui.tree_cats.item(item)['values'][1]) == name: # Navn er nu kolonne 1
                    self.gui.tree_cats.selection_set(item)
                    break
            self.update_ui_state()
        else:
            messagebox.showwarning("Fejl", "Navnet findes allerede")

    def on_canvas_click(self, event):
        if self.canvas_mgr.img_width == 0: return

        norm_pt = self.canvas_mgr.get_norm_pos(event.x, event.y)
        cat_data = self.categories.get(self.active_category_name) if self.active_category_name else None
        
        res = self.canvas_mgr.handle_click(norm_pt, cat_data)
        
        if res:
            if res['type'] == 'calibration':
                self.gui.canvas.config(cursor="")
                px_dist = res['pixel_dist']
                if px_dist > 0:
                    dist_str = simpledialog.askstring("Kalibrering", "Afstand i meter:")
                    if dist_str:
                        try:
                            real_m = float(dist_str.replace(',', '.'))
                            self.canvas_mgr.scale_factor = real_m / px_dist
                            self.gui.lbl_scale.config(text=f"1 px = {self.canvas_mgr.scale_factor:.4f} m", fg="green")
                            self.log(f"Kalibreret: {real_m}m")
                        except: pass
            else:
                self.add_measurement(cat_data, res['type'], res['value'], res['points'])
                self.log(f"Måling: {res['value']:.2f}")

        self.refresh_view()
        self.gui.canvas.update()

    def start_calibration(self):
        if self.canvas_mgr.img_width == 0:
            messagebox.showwarning("Hov", "Du skal åbne en PDF fil først!")
            return
        self.canvas_mgr.start_calibration()
        self.gui.canvas.config(cursor="crosshair")
        messagebox.showinfo("Kalibrering", "Klik på to punkter på tegningen.\n\nMarkøren er nu et kryds.")

    # --- LISTER OG VISNING ---
    def update_cat_list(self):
        for i in self.gui.tree_cats.get_children(): self.gui.tree_cats.delete(i)
        
        # Sorter efter ID
        sorted_cats = sorted(self.categories.items(), key=lambda item: item[1].get('id', 0))
        
        for name, data in sorted_cats:
            cat_id = data.get('id', '?')
            ct = data.get('type', 'lbm')
            
            # Pæn type-tekst
            disp_type = ct
            if ct == 'lbm_h': disp_type = "Lbm x H"
            elif ct == 'kvm': disp_type = "m²"
            
            # Ikon for synlighed
            vis_icon = "👁" if data.get('visible', True) else "🚫"
            
            # Indsæt i listen
            self.gui.tree_cats.insert("", "end", values=(cat_id, name, disp_type, vis_icon))
    def toggle_category_visibility(self, item_id):
        # 1. Find navnet på kategorien ud fra rækken i GUI
        item_vals = self.gui.tree_cats.item(item_id)['values']
        if not item_vals: return
        
        # Navnet står i kolonne 1 (husk: kolonne 0 er ID)
        cat_name = str(item_vals[1])
        
        # 2. Find data og skift status
        if cat_name in self.categories:
            current_state = self.categories[cat_name].get('visible', True)
            self.categories[cat_name]['visible'] = not current_state # Skift True <-> False
            
            # 3. Opdater UI
            self.update_cat_list()     # Opdater ikonet i listen
            self.refresh_view()        # Opdater tegningen (skjul/vis streger)
            self.save_config()         # Gem ændringen

    def update_section_list(self):
        for i in self.gui.tree_sections.get_children(): self.gui.tree_sections.delete(i)
        if not self.active_category_name: return
        
        cat = self.categories[self.active_category_name]
        # Hent ID (hvis det findes, ellers ?)
        cat_id = cat.get('id', '?')
        c_type = cat.get('type', 'lbm')
        h = cat.get('height', 0)
        
        for m in cat['measurements']:
            val = m['value']
            disp_val = f"{val:.2f}"
            
            # Formater med enheder
            if c_type == 'lbm_h':
                 areal = val * h
                 disp_val = f"{val:.2f} m ({areal:.2f} m²)"
            elif c_type == 'stk':
                 disp_val = f"{int(val)} stk"
            elif c_type == 'kvm':
                 disp_val = f"{val:.2f} m²"
            else:
                 # Standard LBM får nu 'm' på
                 disp_val = f"{val:.2f} m"
            
            # Vi viser #CatID.MålingID i listen for overblik
            full_id = f"#{cat_id}.{m['id']}"
            
            self.gui.tree_sections.insert("", "end", values=(full_id, disp_val, m.get('note', '')))

    def add_measurement(self, cat_data, m_type, val, pts):
        new_id = 1 if not cat_data['measurements'] else max(m['id'] for m in cat_data['measurements']) + 1
        cat_data['measurements'].append({
            'id': new_id, 'type': m_type, 'value': val, 'points': pts, 'note': ''
        })
        self.update_section_list()
        self.save_config()

    def refresh_view(self):
        self.tk_image, _, _ = self.pdf.get_page_image(0, self.canvas_mgr.zoom_level)
        self.canvas_mgr.redraw(
            self.show_pdf.get(),  # <--- Her!
            self.tk_image, 
            self.categories, 
            self.active_category_name, 
            self.highlighted_section, 
            self.last_mouse_pos
        )
        if self.canvas_mgr.scale_factor:
            self.gui.lbl_scale.config(text=f"1 px = {self.canvas_mgr.scale_factor:.4f} m", fg="green")

    def export_report(self):
        # 1. Tjek om vi har data og en åben fil
        if not self.categories: 
            messagebox.showinfo("Info", "Ingen data at eksportere.")
            return
            
        if not self.current_pdf_path:
            messagebox.showwarning("Fejl", "Ingen PDF fil er aktiv.")
            return

        # 2. Beregn filnavn automatisk (samme som PDF, men .xlsx)
        base_name = os.path.splitext(self.current_pdf_path)[0]
        save_path = base_name + ".xlsx"
        
        # 3. Kald Excel Manageren
        # (Vi spørger ikke brugeren, vi kører bare)
        success, msg = self.excel.export_full_report(save_path, self.categories)
        
        if success:
            if messagebox.askyesno("Succes", f"Rapport opdateret:\n{os.path.basename(save_path)}\n\nVil du åbne filen nu?"):
                try:
                    os.startfile(save_path)
                except:
                    pass
            self.log(f"Gemt: {os.path.basename(save_path)}")
        else:
            # Fejlhåndtering (f.eks. hvis filen er åben i Excel)
            messagebox.showerror("Fejl", f"Kunne ikke gemme:\n{msg}\n\n(Tjek om filen er åben i Excel)")
            
    def on_mouse_move(self, event):
        self.last_mouse_pos = self.canvas_mgr.get_norm_pos(event.x, event.y)
        if self.canvas_mgr.temp_points: self.refresh_view()
    def start_pan(self, event): self.canvas_mgr.start_pan(event)
    def pan(self, event): self.canvas_mgr.pan(event)
    def cancel_drawing(self, event=None): 
        self.canvas_mgr.cancel()
        self.refresh_view()
    def on_mouse_wheel(self, event):
        if event.delta > 0: self.canvas_mgr.set_zoom(1.2)
        else: self.canvas_mgr.set_zoom(0.8)
        self.refresh_view()

    def on_canvas_right_double_click(self, event):
        # 1. Hent størrelsen på tegne-området lige nu
        w = self.gui.canvas.winfo_width()
        h = self.gui.canvas.winfo_height()
        
        # 2. Udfør Zoom Fit
        if self.canvas_mgr.zoom_fit(w, h):
            self.refresh_view()
            self.log("Zoom: Tilpas til vindue")

    def update_ui_state(self): 
        has_cat = self.active_category_name is not None
        self.canvas_mgr.update_cursor(is_active_cat=has_cat)
        
    def undo_last(self):
        if self.active_category_name:
            cat = self.categories[self.active_category_name]
            if cat['measurements']:
                cat['measurements'].pop()
                self.update_section_list()
                self.refresh_view()
                self.save_config()
    
    def on_category_select(self, event):
        sel = self.gui.tree_cats.selection()
        if not sel: return
        
        # Navn er nu kolonne 1 (indeks 1) pga ID kolonnen
        raw_val = self.gui.tree_cats.item(sel[0])['values'][1]
        name = str(raw_val)
        
        self.active_category_name = name
        self.update_section_list()
        self.refresh_view()
        self.update_ui_state()
    
    def on_section_select(self, event):
        sel = self.gui.tree_sections.selection()
        if not sel: 
            self.highlighted_section = None
            return
            
        item = self.gui.tree_sections.item(sel[0])
        
        # 1. Hent ID korrekt til Highlighting
        # I listen står der nu f.eks "#1.5", men systemet forventer tallet 5
        raw_id_str = str(item['values'][0]) 
        try:
            # Split ved punktum og tag del nr 2 (f.eks "5" fra "#1.5")
            meas_id = int(raw_id_str.split('.')[1])
        except:
            meas_id = 0 # Fallback
            
        self.highlighted_section = {'cat': self.active_category_name, 'id': meas_id}
        
       
        self.refresh_view()
        
    def delete_category(self):
        if self.active_category_name and messagebox.askyesno("Slet", f"Slet {self.active_category_name}?"):
            del self.categories[self.active_category_name]
            self.active_category_name = None
            self.update_cat_list()
            self.update_section_list()
            self.refresh_view()
            self.save_config()
            
    def delete_selected_section(self):
        if self.highlighted_section:
            cat = self.categories[self.highlighted_section['cat']]
            cat['measurements'] = [m for m in cat['measurements'] if m['id'] != self.highlighted_section['id']]
            self.highlighted_section = None
            self.update_section_list()
            self.refresh_view()
            self.save_config()

    def save_note_from_entry(self):
        if self.highlighted_section:
            cat = self.categories[self.highlighted_section['cat']]
            for m in cat['measurements']:
                if m['id'] == self.highlighted_section['id']:
                    m['note'] = self.gui.entry_note.get()
            self.update_section_list()
            self.save_config()
    # --- IN-LINE EDITING LOGIK ---
    def on_inline_edit_finish(self, item_id, new_text, tree_type):
        new_text = new_text.strip()
        self.gui.close_edit_entry() # Fjern feltet
        
        if tree_type == "cats":
            # item_id i Treeview er en intern ID. Vi skal finde det gamle navn.
            # Vi kan slå op i træet for at finde det gamle navn (som er i kolonne 1)
            # Men en nemmere måde er at bruge self.active_category_name hvis det er den valgte.
            
            # Vi itererer over kategorier for at finde den der matcher item_id i GUI
            # (Dette er nødvendigt hvis man redigerer en række der ikke er aktiv)
            target_cat_key = None
            for name, data in self.categories.items():
                # Vi har ikke gemt træ-id'et, så vi må stole på active selection eller genopbygge
                # Det nemmeste: Vi ved at brugeren klikkede på en række.
                # Lad os finde navnet ud fra rækken i GUI'en.
                item_vals = self.gui.tree_cats.item(item_id)['values']
                if str(item_vals[1]) == name:
                    target_cat_key = name
                    break
            
            if target_cat_key:
                self.rename_category(target_cat_key, new_text)

        elif tree_type == "sections":
            # Her skal vi finde målingen.
            # Rækken i sections træet indeholder ID i kolonne 0 (#catid.measid)
            item_vals = self.gui.tree_sections.item(item_id)['values']
            full_id = str(item_vals[0]) # F.eks "#1.5"
            meas_id = int(full_id.split('.')[1]) # Hent 5 tallet
            
            if self.active_category_name:
                cat = self.categories[self.active_category_name]
                for m in cat['measurements']:
                    if m['id'] == meas_id:
                        m['note'] = new_text
                        self.log(f"Note opdateret: {new_text}")
                        break
                self.update_section_list()
                self.save_config()

    def rename_category(self, old_name, new_name):
        if old_name == new_name: return
        if not new_name: return
        if new_name in self.categories:
            messagebox.showwarning("Fejl", "Navnet findes allerede")
            return
            
        # 1. Flyt data til ny nøgle
        self.categories[new_name] = self.categories.pop(old_name)
        
        # 2. Hvis den var aktiv, opdater active pointer
        if self.active_category_name == old_name:
            self.active_category_name = new_name
            
        # 3. Opdater GUI
        self.update_cat_list()
        self.update_section_list()
        self.save_config()
        self.log(f"Omdøbt: {old_name} -> {new_name}")

    def load_config(self):
        try:
            with open(self.json_path, 'r') as f: data = json.load(f)
            self.canvas_mgr.scale_factor = data.get("scale_factor", 0.0)
            self.categories = data.get("categories", {})
            self.next_cat_id = data.get("next_cat_id", 1) # Hent tæller
            
            # --- MIGRERING AF GAMLE DATA ---
            # Hvis vi indlæser en fil uden ID'er, skal vi tildele dem
            max_id = 0
            for name, cat_data in self.categories.items():
                if 'id' not in cat_data:
                    cat_data['id'] = self.next_cat_id
                    self.next_cat_id += 1
                max_id = max(max_id, cat_data['id'])
            
            # Sikr at tælleren er højere end højeste ID
            if self.next_cat_id <= max_id:
                self.next_cat_id = max_id + 1
            # -------------------------------
            
        except: pass

    def save_config(self):
        if self.json_path:
            with open(self.json_path, 'w') as f:
                json.dump({
                    "scale_factor": self.canvas_mgr.scale_factor, 
                    "categories": self.categories,
                    "next_cat_id": self.next_cat_id # Gem tæller
                }, f)
    
    def log(self, msg): self.gui.log_message(msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = ToemrerMaalerApp(root)
    root.mainloop()