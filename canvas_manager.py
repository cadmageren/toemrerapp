import tkinter as tk
import math

class CanvasManager:
    def __init__(self, canvas_widget, pdf_handler):
        self.canvas = canvas_widget
        self.pdf = pdf_handler
        
        # State
        self.scale_factor = 0.0
        self.zoom_level = 1.0
        self.temp_points = []
        self.is_calibrating = False
        
        # Billedstørrelse
        self.img_width = 0
        self.img_height = 0

    def set_image_size(self, width, height):
        self.img_width = width
        self.img_height = height

    def get_norm_pos(self, event_x, event_y):
        if self.img_width == 0 or self.img_height == 0: return (0,0)
        cx = self.canvas.canvasx(event_x)
        cy = self.canvas.canvasy(event_y)
        raw_x = cx / self.zoom_level
        raw_y = cy / self.zoom_level
        return (raw_x / self.img_width, raw_y / self.img_height)

    def set_zoom(self, factor):
        new_level = self.zoom_level * factor
        if 0.1 < new_level < 5.0:
            self.zoom_level = new_level
            return True
        return False

    def redraw(self, show_pdf, tk_image, categories, active_cat_name, highlighted_section, mouse_pos=None):
        self.canvas.delete("all")

        # 1. Tegn PDF
        if self.pdf.doc and self.img_width > 0:
            w = int(self.img_width * self.zoom_level)
            h = int(self.img_height * self.zoom_level)
            self.canvas.config(scrollregion=(0, 0, w, h))

            if show_pdf and tk_image:
                self.canvas.create_image(0, 0, image=tk_image, anchor=tk.NW)
            else:
                self.canvas.create_rectangle(0, 0, w, h, fill="white", outline="black")

        # 2. Tegn Gemte Målinger
        for cat_name, data in categories.items():
            if not data['visible']: continue 
            
            # Hent info
            cat_id = data.get('id', '?')
            c_type = data.get('type', 'lbm')
            col = data.get('color', 'blue')
            
            for section in data['measurements']:
                try:
                    is_hl = (highlighted_section and highlighted_section['cat'] == cat_name and highlighted_section['id'] == section['id'])
                    # Send cat_id med til draw_shape
                    self.draw_shape(section, col, is_hl, c_type, cat_id)
                except Exception as e:
                    print(f"Fejl ved tegning: {e}")

        # 3. Midlertidige punkter
        for pt in self.temp_points:
            sx = pt[0] * self.img_width * self.zoom_level
            sy = pt[1] * self.img_height * self.zoom_level
            self.canvas.create_oval(sx-3, sy-3, sx+3, sy+3, fill="red")
        
        # 4. Preview (Elastik)
        if self.temp_points and mouse_pos:
            p1 = self.temp_points[-1]
            sx1 = p1[0] * self.img_width * self.zoom_level
            sy1 = p1[1] * self.img_height * self.zoom_level
            sx2 = mouse_pos[0] * self.img_width * self.zoom_level
            sy2 = mouse_pos[1] * self.img_height * self.zoom_level
            
            active_type = "lbm"
            if active_cat_name and active_cat_name in categories:
                active_type = categories[active_cat_name].get('type', 'lbm')

            if active_type in ['m2', 'kvm']:
                self.canvas.create_rectangle(sx1, sy1, sx2, sy2, outline="red", dash=(4, 4))
                self.canvas.create_line(sx1, sy1, sx2, sy2, fill="red", dash=(2, 4))
            else:
                self.canvas.create_line(sx1, sy1, sx2, sy2, fill="red", dash=(4, 4))

    def draw_shape(self, section, color, highlight, c_type, cat_id):
        scale = self.zoom_level
        w_img = self.img_width
        h_img = self.img_height
        
        pts = section['points']
        width = 4 if highlight else 2
        col = "yellow" if highlight else color
        
        # Lav ID label: #1.5
        label_text = f"#{cat_id}.{section['id']}"
        
        if c_type in ['lbm', 'lbm_h']:
            p1, p2 = pts
            s1 = (p1[0]*w_img*scale, p1[1]*h_img*scale)
            s2 = (p2[0]*w_img*scale, p2[1]*h_img*scale)
            self.canvas.create_line(s1, s2, fill=col, width=width)
            
            mid = ((s1[0]+s2[0])/2, (s1[1]+s2[1])/2)
            # Tilføj mængde til label
            full_txt = f"{label_text}: {section['value']:.2f} m"
            self.canvas.create_text(mid, text=full_txt, font=("Arial", 8, "bold"), fill="black")
            
        elif c_type in ['m2', 'kvm']:
            p1, p2 = pts
            x1, y1 = p1[0]*w_img*scale, p1[1]*h_img*scale
            x2, y2 = p2[0]*w_img*scale, p2[1]*h_img*scale
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=col, width=width, stipple="gray25")
            
            mid = ((x1+x2)/2, (y1+y2)/2)
            full_txt = f"{label_text}\n{section['value']:.2f} m²"
            self.canvas.create_text(mid, text=full_txt, font=("Arial", 8), fill="black")

        elif c_type == 'stk':
            p1 = pts[0]
            cx, cy = p1[0]*w_img*scale, p1[1]*h_img*scale
            self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, fill=col, outline="black")
            # For Stk skriver vi bare ID'et over prikken
            self.canvas.create_text(cx, cy-10, text=label_text, font=("Arial", 8, "bold"), fill="black")

    def handle_click(self, norm_pt, active_cat_data):
        if self.is_calibrating:
            self.temp_points.append(norm_pt)
            if len(self.temp_points) == 2:
                p1, p2 = self.temp_points
                px_dist = math.dist((p1[0]*self.img_width, p1[1]*self.img_height), 
                                    (p2[0]*self.img_width, p2[1]*self.img_height))
                self.temp_points = []
                self.is_calibrating = False
                self.update_cursor()
                return {'type': 'calibration', 'pixel_dist': px_dist}
            return None 

        if not active_cat_data: return None

        m_type = active_cat_data.get('type', 'lbm')
        self.temp_points.append(norm_pt)
        
        if m_type in ["lbm", "lbm_h"]:
            if len(self.temp_points) >= 2:
                p1 = self.temp_points[-2]
                p2 = self.temp_points[-1]
                px_dist = math.dist((p1[0]*self.img_width, p1[1]*self.img_height), 
                                    (p2[0]*self.img_width, p2[1]*self.img_height))
                real_dist = px_dist * self.scale_factor 
                self.temp_points = [p2] 
                return {'type': m_type, 'value': real_dist, 'points': [p1, p2]}

        elif m_type in ["m2", "kvm"]:
            if len(self.temp_points) == 2:
                p1, p2 = self.temp_points
                w_px = abs(p2[0]-p1[0]) * self.img_width
                h_px = abs(p2[1]-p1[1]) * self.img_height
                area = (w_px * self.scale_factor) * (h_px * self.scale_factor)
                self.temp_points = []
                return {'type': 'kvm', 'value': area, 'points': [p1, p2]}

        elif m_type == "stk":
            p1 = self.temp_points[0]
            self.temp_points = []
            return {'type': 'stk', 'value': 1, 'points': [p1]}
        
        return None
        
    def start_calibration(self):
        self.is_calibrating = True
        self.temp_points = []
        self.update_cursor()

    def update_cursor(self, is_active_cat=False):
        if self.is_calibrating or is_active_cat:
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="")
    
    def zoom_fit(self, view_width, view_height):
        """Beregn zoom så hele billedet passer i vinduet"""
        # Sikr os at vi kender billedets størrelse (fra PDF handleren)
        if not self.pdf.original_pixmap: return False
        
        im_w = self.pdf.original_pixmap.width
        im_h = self.pdf.original_pixmap.height
        
        if im_w == 0 or im_h == 0: return False
        
        # Beregn forholdet mellem vindue og billede
        ratio_w = view_width / im_w
        ratio_h = view_height / im_h
        
        # Vælg den mindste faktor (så hele billedet er synligt)
        # 0.95 giver en lille margin (luft) i kanten
        self.zoom_level = min(ratio_w, ratio_h) * 0.95
        return True
    
    def cancel(self):
        self.temp_points = []
        self.is_calibrating = False
        self.update_cursor()
        
    def start_pan(self, event): self.canvas.scan_mark(event.x, event.y)
    def pan(self, event): self.canvas.scan_dragto(event.x, event.y, gain=1)