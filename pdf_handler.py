import fitz  # PyMuPDF
from PIL import Image, ImageTk

class PDFHandler:
    def __init__(self):
        self.doc = None
        self.file_path = None
        self.page_count = 0
        self.current_page_index = 0
        self.original_pixmap = None  # Gemmer den rå rendering fra PDF
        
    def load_file(self, path):
        """Åbner PDF filen og returnerer antal sider"""
        try:
            self.doc = fitz.open(path)
            self.file_path = path
            self.page_count = len(self.doc)
            return True
        except Exception as e:
            print(f"PDF Handler Fejl: {e}")
            return False

    def get_page_image(self, page_num, zoom_level):
        """
        Henter en side, og returnerer den som et Tkinter-klart billede 
        i den korrekte zoom-størrelse.
        """
        if not self.doc:
            return None, 0, 0

        # Gem pixmap hvis vi skifter side (så vi ikke renderer PDF'en hver gang vi bare zoomer)
        if page_num != self.current_page_index or self.original_pixmap is None:
            self.current_page_index = page_num
            page = self.doc.load_page(page_num)
            # Vi renderer i høj kvalitet (dpi=150) som base
            self.original_pixmap = page.get_pixmap(dpi=150, alpha=False)

        # Beregn ny bredde/højde baseret på zoom
        w = int(self.original_pixmap.width * zoom_level)
        h = int(self.original_pixmap.height * zoom_level)

        # Konverter til PIL Image
        img_data = self.original_pixmap.samples
        base_img = Image.frombytes("RGB", [self.original_pixmap.width, self.original_pixmap.height], img_data)
        
        # Resize med høj kvalitet (LANCZOS)
        resized_img = base_img.resize((w, h), Image.Resampling.LANCZOS)
        
        # Konverter til Tkinter billede
        tk_image = ImageTk.PhotoImage(resized_img)
        
        return tk_image, w, h

    def close(self):
        if self.doc:
            self.doc.close()
            self.doc = None