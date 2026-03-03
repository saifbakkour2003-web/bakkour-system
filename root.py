# root.py
from flask import redirect

def register(app):
    @app.get("/")
    def root_index():
        return redirect("/shop/")
