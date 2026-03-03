from flask import render_template

def register(app):
    @app.get("/shop/about")
    def shop_about():
        return render_template("shop/about.html")