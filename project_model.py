import json

class ProjectModel:
    def __init__(self):
        self.categories = {}       # Gemmer alle konstruktioner og målinger
        self.scale_factor = 0.0    # Gemmer skalaen (px til mm)
        
    def to_json(self):
        """Returnerer hele projektets data som en dictionary klar til JSON"""
        return {
            "scale_factor": self.scale_factor,
            "categories": self.categories
        }

    def load_from_json(self, data):
        """Indlæser data fra en dictionary"""
        self.scale_factor = data.get("scale_factor", 0.0)
        self.categories = data.get("categories", {})

    # --- CRUD METODER (Create, Read, Update, Delete) ---
    
    def add_category(self, cat_id, master_id, c_type, color, height=2.30):
        # cat_id er nu det unikke navn, f.eks. "K_VÆG_01 (2.5m)"
        # master_id er originalen fra Excel, f.eks. "K_VÆG_01"
        if cat_id not in self.categories:
            self.categories[cat_id] = {
                'master_id': master_id,  # <--- NYT: Vi gemmer referencen til Excel
                'type': c_type,
                'color': color,
                'height': height,
                'visible': True,
                'measurements': []
            }

    def delete_category(self, cat_id):
        if cat_id in self.categories:
            del self.categories[cat_id]

    def add_measurement(self, cat_id, m_type, val, pts):
        if cat_id in self.categories:
            cat = self.categories[cat_id]
            # Find næste ledige ID
            current_ids = [m['id'] for m in cat['measurements']]
            new_id = max(current_ids) + 1 if current_ids else 1
            
            # Opret målingen
            cat['measurements'].append({
                'id': new_id,
                'type': m_type,
                'value': val,
                'points': pts,
                'note': ''
            })

    def delete_measurement(self, cat_id, m_id):
        if cat_id in self.categories:
            cat = self.categories[cat_id]
            cat['measurements'] = [m for m in cat['measurements'] if m['id'] != m_id]