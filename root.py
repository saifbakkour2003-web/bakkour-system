from flask import redirect

@app.get("/")
def root():
  return redirect("/shop")
